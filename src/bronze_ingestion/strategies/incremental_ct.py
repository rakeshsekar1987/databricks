"""
Incremental load strategy leveraging SQL Server Change Tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pyspark.sql import functions as F

from ..metadata.models import CdfCheckpoint, LoadMode
from ..services.retry import RetryExecutor
from ..sources.base import SourceReadContext
from .base import LoadResult, LoadStrategy, StrategyContext


class IncrementalCTStrategy(LoadStrategy):
    mode = LoadMode.INCREMENTAL

    def execute(self, context: StrategyContext) -> LoadResult:
        audit_handle = context.audit_service.start_table(context.table_metadata, self.mode, context.run_id)

        def _action() -> LoadResult:
            predicate = self._build_ct_predicate(context.checkpoint)
            read_context = SourceReadContext(
                spark=context.spark,
                table_metadata=context.table_metadata,
                options=context.source_options,
                incremental_filter=predicate,
            )
            source_df = context.source_adapter.read(read_context)
            rows_read = source_df.count()
            self._logger.info(
                "strategy.incremental.read_complete",
                {"table": context.table_metadata.table_name, "rows_read": rows_read, "predicate": predicate},
            )

            if rows_read == 0:
                context.audit_service.complete(
                    audit_handle,
                    rows_read=0,
                    rows_written=0,
                    status="NOOP",
                )
                return LoadResult(
                    table_name=context.table_metadata.table_name,
                    rows_read=0,
                    rows_written=0,
                    status="NOOP",
                    checkpoint=context.checkpoint,
                )

            context.schema_service.detect_and_log(source_df, context.table_metadata, context.run_id)
            optimized_df = self._optimize_dataframe(source_df, context.table_metadata, rows_read)
            written_df = self._write_delta(optimized_df, context.table_metadata, mode="append")
            checkpoint = self._derive_checkpoint(written_df, context, context.checkpoint)
            if checkpoint:
                context.metadata_provider.upsert_cdf_checkpoint(checkpoint)

            context.audit_service.complete(
                audit_handle,
                rows_read=rows_read,
                rows_written=rows_read,
                status="SUCCESS",
            )

            return LoadResult(
                table_name=context.table_metadata.table_name,
                rows_read=rows_read,
                rows_written=rows_read,
                status="SUCCESS",
                checkpoint=checkpoint,
            )

        executor = RetryExecutor(context.table_metadata.retry_policy, context.logger, context.table_metadata.table_name)
        try:
            return executor.run(_action)
        except Exception as exc:
            context.audit_service.complete(
                audit_handle,
                rows_read=0,
                rows_written=0,
                status="FAILED",
                error_message=str(exc),
            )
            raise

    @staticmethod
    def _build_ct_predicate(checkpoint: Optional[CdfCheckpoint]) -> Optional[str]:
        if not checkpoint:
            return None
        return f"SYS_CHANGE_VERSION > {checkpoint.max_version}"

    def _derive_checkpoint(
        self,
        dataframe,
        context: StrategyContext,
        previous: Optional[CdfCheckpoint],
    ) -> Optional[CdfCheckpoint]:
        if "SYS_CHANGE_VERSION" not in dataframe.columns:
            return previous
        latest_version = dataframe.agg(F.max("SYS_CHANGE_VERSION")).collect()[0][0]
        if latest_version is None:
            return previous
        latest_ts = datetime.now(timezone.utc)
        if "SYS_CHANGE_CREATION_TIME" in dataframe.columns:
            ts_value = dataframe.agg(F.max("SYS_CHANGE_CREATION_TIME")).collect()[0][0]
            if ts_value:
                latest_ts = ts_value
        return CdfCheckpoint(
            catalog=context.table_metadata.catalog_name,
            schema=context.table_metadata.schema_name,
            table=context.table_metadata.table_name,
            max_version=int(latest_version),
            max_commit_timestamp=latest_ts,
            run_id=context.run_id,
        )
