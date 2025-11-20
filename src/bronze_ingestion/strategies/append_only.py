"""
Append-only / last-modified-date fallback strategy.
"""

from __future__ import annotations

from typing import Optional

from pyspark.sql import functions as F

from ..metadata.models import CdfCheckpoint, LoadMode
from ..services.retry import RetryExecutor
from ..sources.base import SourceReadContext
from .base import LoadResult, LoadStrategy, StrategyContext


class AppendOnlyStrategy(LoadStrategy):
    mode = LoadMode.MIXED

    def execute(self, context: StrategyContext) -> LoadResult:
        audit_handle = context.audit_service.start_table(context.table_metadata, self.mode, context.run_id)

        def _action() -> LoadResult:
            predicate = self._build_append_predicate(context.table_metadata, context.checkpoint)
            read_context = SourceReadContext(
                spark=context.spark,
                table_metadata=context.table_metadata,
                options=context.source_options,
                incremental_filter=predicate,
            )
            source_df = context.source_adapter.read(read_context)
            rows_read = source_df.count()

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
            written_df = self._write_delta(source_df, context.table_metadata, mode="append")
            checkpoint = self._derive_checkpoint(
                written_df,
                context.table_metadata,
                context.run_id,
                context.checkpoint,
            )
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
    def _build_append_predicate(table, checkpoint: Optional[CdfCheckpoint]) -> Optional[str]:
        last_modified_column = table.table_run_properties.get("last_modified_column")
        if not last_modified_column or not checkpoint:
            return None
        timestamp = checkpoint.max_commit_timestamp.isoformat()
        return f"{last_modified_column} > '{timestamp}'"

    def _derive_checkpoint(
        self,
        dataframe,
        table,
        run_id: str,
        previous: Optional[CdfCheckpoint],
    ) -> Optional[CdfCheckpoint]:
        last_modified_column = table.table_run_properties.get("last_modified_column")
        if not last_modified_column or last_modified_column not in dataframe.columns:
            return previous
        latest_ts = dataframe.agg(F.max(last_modified_column)).collect()[0][0]
        if not latest_ts:
            return previous
        return CdfCheckpoint(
            catalog=table.catalog_name,
            schema=table.schema_name,
            table=table.table_name,
            max_version=int((previous.max_version if previous else 0) + 1),
            max_commit_timestamp=latest_ts,
            run_id=run_id,
        )
