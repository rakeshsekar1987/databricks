"""
Load strategy abstraction used by the orchestrator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession

from ..config import RuntimeConfig
from ..logging_utils import StructuredLogger
from ..metadata.models import CdfCheckpoint, LoadMode, TableMetadata
from ..metadata.provider import MetadataProvider
from ..services.audit import AuditService
from ..services.data_quality import DataQualityService
from ..services.schema_evolution import SchemaEvolutionService
from ..sources.base import SourceAdapter


@dataclass
class StrategyContext:
    spark: SparkSession
    runtime_config: RuntimeConfig
    table_metadata: TableMetadata
    metadata_provider: MetadataProvider
    source_options: Dict[str, Any]
    source_adapter: SourceAdapter
    audit_service: AuditService
    schema_service: SchemaEvolutionService
    dq_service: DataQualityService
    logger: StructuredLogger
    run_id: str
    checkpoint: Optional[CdfCheckpoint] = None


@dataclass
class LoadResult:
    table_name: str
    rows_read: int
    rows_written: int
    status: str
    checkpoint: Optional[CdfCheckpoint] = None
    duration_seconds: Optional[float] = None


class LoadStrategy(ABC):
    mode: LoadMode

    def __init__(self, logger: StructuredLogger):
        self._logger = logger

    @abstractmethod
    def execute(self, context: StrategyContext) -> LoadResult:
        ...

    def _write_delta(self, dataframe: DataFrame, target_table: TableMetadata, mode: str = "append") -> DataFrame:
        (
            dataframe.write
            .format("delta")
            .mode(mode)
            .option("mergeSchema", "true")
            .saveAsTable(f"{target_table.catalog_name}.{target_table.schema_name}.{target_table.table_name}")
        )
        return dataframe

    def _optimize_dataframe(
        self,
        dataframe: DataFrame,
        table_metadata: TableMetadata,
        rows_read: int,
    ) -> DataFrame:
        hints = table_metadata.partition_hints
        partitions = hints.spark_partitions
        if hints.enable_dynamic_partitioning and rows_read:
            partitions = partitions or self._estimate_partitions(table_metadata, rows_read)
        if table_metadata.max_parallelism and partitions:
            partitions = min(partitions, table_metadata.max_parallelism)
        if partitions and partitions > 0:
            dataframe = dataframe.repartition(partitions)

        if hints.max_rows_per_file and rows_read:
            target_files = max(1, rows_read // hints.max_rows_per_file)
            dataframe = dataframe.coalesce(target_files)

        return dataframe

    def _estimate_partitions(self, table_metadata: TableMetadata, rows_read: int) -> int:
        avg_row_size_bytes = int(table_metadata.table_run_properties.get("avg_row_size_bytes", 1024))
        target_file_mb = int(table_metadata.table_run_properties.get("target_file_mb", 128))
        approx_size_mb = max(1, (rows_read * avg_row_size_bytes) // (1024 * 1024))
        return max(1, approx_size_mb // target_file_mb)
