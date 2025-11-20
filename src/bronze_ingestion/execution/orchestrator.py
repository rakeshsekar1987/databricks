"""
Parallel ingestion orchestrator responsible for coordinating strategies per table.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List

from pyspark.sql import SparkSession

from ..config import RuntimeConfig
from ..exceptions import StrategySelectionError
from ..logging_utils import StructuredLogger
from ..metadata.models import LoadMode, TableMetadata
from ..metadata.provider import MetadataProvider
from ..services.audit import AuditService
from ..services.data_quality import DataQualityService
from ..services.notifier import Notifier
from ..services.schema_evolution import SchemaEvolutionService
from ..sources.base import SourceAdapter
from ..strategies.append_only import AppendOnlyStrategy
from ..strategies.base import LoadResult, LoadStrategy, StrategyContext
from ..strategies.full_load import FullLoadStrategy
from ..strategies.incremental_ct import IncrementalCTStrategy


@dataclass
class IngestionSummary:
    successes: List[LoadResult]
    failures: Dict[str, str]


class IngestionOrchestrator:
    def __init__(
        self,
        spark: SparkSession,
        runtime_config: RuntimeConfig,
        metadata_provider: MetadataProvider,
        source_adapter: SourceAdapter,
        notifier: Notifier,
        logger: StructuredLogger,
    ):
        self._spark = spark
        self._runtime_config = runtime_config
        self._metadata_provider = metadata_provider
        self._source_adapter = source_adapter
        self._audit_service = AuditService(metadata_provider, logger)
        self._schema_service = SchemaEvolutionService(spark, metadata_provider, notifier, logger)
        self._dq_service = DataQualityService(logger)
        self._notifier = notifier
        self._logger = logger
        self._strategies: Dict[LoadMode, LoadStrategy] = {
            LoadMode.FULL: FullLoadStrategy(logger),
            LoadMode.INCREMENTAL: IncrementalCTStrategy(logger),
            LoadMode.MIXED: AppendOnlyStrategy(logger),
        }

    def run(self) -> IngestionSummary:
        run_id = self._runtime_config.run_id or str(uuid.uuid4())
        load_mode = LoadMode(self._runtime_config.mode)
        source_metadata = self._metadata_provider.get_source(self._runtime_config.source_id)
        tables = self._metadata_provider.list_tables(self._runtime_config.source_id, load_mode)
        tables = sorted(
            (table for table in tables if table.is_active),
            key=lambda t: t.concurrency_weight,
            reverse=True,
        )

        self._logger.info(
            "orchestrator.start",
            {"run_id": run_id, "table_count": len(tables), "mode": load_mode.value},
        )

        successes: List[LoadResult] = []
        failures: Dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=self._runtime_config.parallelism) as executor:
            future_map = {
                executor.submit(
                    self._run_single_table,
                    table,
                    load_mode,
                    run_id,
                    source_metadata.db_details,
                ): table
                for table in tables
            }

            for future in as_completed(future_map):
                table = future_map[future]
                try:
                    result = future.result()
                    successes.append(result)
                except Exception as exc:  # pragma: no cover - runtime path
                    failures[table.table_name] = str(exc)
                    self._notifier.notify(
                        subject=f"Bronze load failed: {table.table_name}",
                        body=f"Run {run_id} failed for {table.table_name}: {exc}",
                    )
                    self._logger.exception(
                        "table.failure",
                        {"table": table.table_name, "error": str(exc), "mode": load_mode.value},
                    )

        self._send_summary(run_id, successes, failures)
        return IngestionSummary(successes=successes, failures=failures)

    def _run_single_table(
        self,
        table: TableMetadata,
        load_mode: LoadMode,
        run_id: str,
        connection_details: Dict[str, str],
    ) -> LoadResult:
        strategy = self._select_strategy(table, load_mode)
        checkpoint = None
        if load_mode != LoadMode.FULL:
            checkpoint = self._metadata_provider.get_cdf_checkpoint(
                table.catalog_name, table.schema_name, table.table_name
            )
        source_options = {**table.table_run_properties, "db_details": connection_details}
        context = StrategyContext(
            spark=self._spark,
            runtime_config=self._runtime_config,
            table_metadata=table,
            metadata_provider=self._metadata_provider,
            source_options=source_options,
            source_adapter=self._source_adapter,
            audit_service=self._audit_service,
            schema_service=self._schema_service,
            dq_service=self._dq_service,
            logger=self._logger,
            run_id=run_id,
            checkpoint=checkpoint,
        )
        self._logger.info("table.start", {"table": table.table_name, "strategy": strategy.mode.value})
        result = strategy.execute(context)
        self._logger.info(
            "table.complete",
            {"table": table.table_name, "status": result.status, "rows_written": result.rows_written},
        )
        return result

    def _select_strategy(self, table: TableMetadata, requested_mode: LoadMode) -> LoadStrategy:
        if requested_mode == LoadMode.FULL:
            return self._strategies[LoadMode.FULL]

        if requested_mode == LoadMode.INCREMENTAL:
            if table.ct_enabled:
                return self._strategies[LoadMode.INCREMENTAL]
            if table.is_append_only or table.fallback_mode == LoadMode.MIXED:
                return self._strategies[LoadMode.MIXED]
            return self._strategies[LoadMode.FULL]

        # MIXED mode
        if table.ct_enabled:
            return self._strategies[LoadMode.INCREMENTAL]
        if table.is_append_only or table.fallback_mode in (LoadMode.MIXED, LoadMode.INCREMENTAL):
            return self._strategies[LoadMode.MIXED]
        if table.fallback_mode == LoadMode.FULL:
            return self._strategies[LoadMode.FULL]

        raise StrategySelectionError(f"No strategy available for table {table.table_name}")

    def _send_summary(self, run_id: str, successes: List[LoadResult], failures: Dict[str, str]) -> None:
        subject = f"Bronze ingestion run {run_id} summary"
        body_lines = [
            f"Run ID: {run_id}",
            f"Successful tables: {len(successes)}",
            f"Failed tables: {len(failures)}",
        ]
        if failures:
            body_lines.append("Failures:")
            for table, error in failures.items():
                body_lines.append(f"- {table}: {error}")
        self._notifier.notify(subject=subject, body="\n".join(body_lines))
