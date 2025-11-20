"""
One-time full load strategy.
"""

from __future__ import annotations

import time

from pyspark.sql import DataFrame

from ..metadata.models import LoadMode
from ..services.retry import RetryExecutor
from ..sources.base import SourceReadContext
from .base import LoadResult, LoadStrategy, StrategyContext


class FullLoadStrategy(LoadStrategy):
    mode = LoadMode.FULL

    def execute(self, context: StrategyContext) -> LoadResult:
        audit_handle = context.audit_service.start_table(context.table_metadata, self.mode, context.run_id)

        def _action() -> LoadResult:
            start_ts = time.perf_counter()
            read_context = SourceReadContext(
                spark=context.spark,
                table_metadata=context.table_metadata,
                options=context.source_options,
            )
            source_df = context.source_adapter.read(read_context)
            rows_read = source_df.count()
            self._logger.info(
                "strategy.full.read_complete",
                {"table": context.table_metadata.table_name, "rows_read": rows_read},
            )

            context.schema_service.detect_and_log(source_df, context.table_metadata, context.run_id)
            optimized_df = self._optimize_dataframe(source_df, context.table_metadata, rows_read)
            written_df = self._write_delta(optimized_df, context.table_metadata, mode="overwrite")
            target_df: DataFrame = context.spark.table(
                f"{context.table_metadata.catalog_name}.{context.table_metadata.schema_name}.{context.table_metadata.table_name}"
            )
            dq_result = context.dq_service.validate_row_counts(
                source_df,
                target_df,
                tolerance_percent=context.table_metadata.dq_tolerance_percent,
            )
            context.dq_service.validate_schema_alignment(source_df, target_df)

            result = LoadResult(
                table_name=context.table_metadata.table_name,
                rows_read=rows_read,
                rows_written=dq_result.actual_count,
                status="SUCCESS",
            )
            result.duration_seconds = time.perf_counter() - start_ts

            context.audit_service.complete(
                audit_handle,
                rows_read=result.rows_read,
                rows_written=result.rows_written,
                status=result.status,
                duration_seconds=result.duration_seconds,
            )
            return result

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
