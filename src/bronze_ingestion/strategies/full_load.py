"""
One-time full load strategy.
"""

from __future__ import annotations

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
            written_df = self._write_delta(source_df, context.table_metadata, mode="overwrite")
            target_df: DataFrame = context.spark.table(
                f"{context.table_metadata.catalog_name}.{context.table_metadata.schema_name}.{context.table_metadata.table_name}"
            )
            context.dq_service.validate_row_counts(written_df, target_df)

            context.audit_service.complete(
                audit_handle,
                rows_read=rows_read,
                rows_written=target_df.count(),
                status="SUCCESS",
            )

            return LoadResult(
                table_name=context.table_metadata.table_name,
                rows_read=rows_read,
                rows_written=target_df.count(),
                status="SUCCESS",
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
