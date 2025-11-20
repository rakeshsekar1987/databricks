"""
Metadata provider interfaces and simple implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, List, Optional

from pyspark.sql import DataFrame, SparkSession

from .models import (
    AuditRecord,
    CdfCheckpoint,
    LoadMode,
    PartitioningHints,
    RetryPolicy,
    SchemaDriftRecord,
    SourceConnectionMetadata,
    TableMetadata,
)


class MetadataProvider(ABC):
    """Metadata provider contract."""

    @abstractmethod
    def list_tables(self, source_id: str, mode: LoadMode) -> List[TableMetadata]:
        ...

    @abstractmethod
    def get_source(self, source_id: str) -> SourceConnectionMetadata:
        ...

    @abstractmethod
    def get_cdf_checkpoint(self, catalog: str, schema: str, table: str) -> Optional[CdfCheckpoint]:
        ...

    @abstractmethod
    def upsert_cdf_checkpoint(self, checkpoint: CdfCheckpoint) -> None:
        ...

    @abstractmethod
    def record_audit(self, record: AuditRecord) -> None:
        ...

    @abstractmethod
    def record_schema_drift(self, record: SchemaDriftRecord) -> None:
        ...


class DeltaMetadataProvider(MetadataProvider):
    """
    Metadata provider backed by Delta tables inside Unity Catalog.

    The tables are expected to have a schema aligning with the dataclasses in `metadata.models`.
    """

    def __init__(self, spark: SparkSession, catalog: str, schema: str):
        self._spark = spark
        self._catalog = catalog
        self._schema = schema

    def _table(self, name: str) -> DataFrame:
        return self._spark.table(f"{self._catalog}.{self._schema}.{name}")

    def list_tables(self, source_id: str, mode: LoadMode) -> List[TableMetadata]:
        df = self._table("table_metadata").where("is_active = true").where(f"source_id = '{source_id}'")
        rows = df.collect()
        tables: List[TableMetadata] = []
        for row in rows:
            partition_hints = PartitioningHints(
                partition_columns=row.partition_cols,
                max_rows_per_file=row.max_rows_per_file,
                spark_partitions=row.spark_partitions,
                enable_dynamic_partitioning=row.dynamic_partitioning,
            )
            retry_policy = RetryPolicy(
                attempts=row.retry_attempts,
                initial_backoff_seconds=row.retry_backoff_seconds,
                backoff_multiplier=row.retry_backoff_multiplier,
            )
            tables.append(
                TableMetadata(
                    id=row.id,
                    source_id=row.source_id,
                    full_table_name=row.full_table_name,
                    table_name=row.table_name,
                    catalog_name=row.catalog_name,
                    schema_name=row.schema_name,
                    ct_enabled=row.ct_enabled,
                    include_list=row.include_list,
                    exclude_list=row.exclude_list,
                    id_columns=row.id_columns,
                    partition_hints=partition_hints,
                    retry_policy=retry_policy,
                    is_append_only=row.is_append_only,
                    is_active=row.is_active,
                    concurrency_weight=row.concurrency_weight,
                    sla_priority=row.sla_priority,
                    table_run_properties=row.table_run_properties,
                    fallback_mode=LoadMode(row.fallback_mode) if row.fallback_mode else None,
                )
            )
        return tables

    def get_source(self, source_id: str) -> SourceConnectionMetadata:
        row = (
            self._table("source_metadata")
            .where("is_active = true")
            .where(f"id = '{source_id}'")
            .limit(1)
            .collect()
        )
        if not row:
            raise ValueError(f"Source '{source_id}' not found or inactive.")

        entry = row[0]
        return SourceConnectionMetadata(
            id=entry.id,
            data_source_type=entry.data_source_type,
            catalog_name=entry.catalog_name,
            logical_name=entry.table_name,
            db_details=entry.db_details,
            is_active=entry.is_active,
            include_list=entry.include_list,
            exclude_list=entry.exclude_list,
            is_ct_enabled=entry.db_details.get("is_ct_enabled", False),
        )

    def get_cdf_checkpoint(self, catalog: str, schema: str, table: str) -> Optional[CdfCheckpoint]:
        df = (
            self._table("cdf_checkpoint")
            .where(f"catalog = '{catalog}' AND schema = '{schema}' AND table = '{table}'")
            .orderBy("max_commit_timestamp", ascending=False)
            .limit(1)
        )
        rows = df.collect()
        if not rows:
            return None
        row = rows[0]
        return CdfCheckpoint(
            catalog=row.catalog,
            schema=row.schema,
            table=row.table,
            max_version=row.max_version,
            max_commit_timestamp=row.max_commit_timestamp,
            run_id=row.run_id,
        )

    def upsert_cdf_checkpoint(self, checkpoint: CdfCheckpoint) -> None:
        data = [
            (
                checkpoint.catalog,
                checkpoint.schema,
                checkpoint.table,
                checkpoint.max_version,
                checkpoint.max_commit_timestamp,
                checkpoint.run_id,
                datetime.utcnow(),
            )
        ]
        self._spark.createDataFrame(
            data,
            schema="catalog string, schema string, table string, max_version long, max_commit_timestamp timestamp, run_id string, updated_at timestamp",
        ).write.mode("append").saveAsTable(f"{self._catalog}.{self._schema}.cdf_checkpoint")

    def record_audit(self, record: AuditRecord) -> None:
        data = [
            (
                record.run_id,
                record.table_name,
                record.source_table,
                record.mode.value,
                record.start_time,
                record.end_time,
                record.rows_read,
                record.rows_written,
                record.status,
                record.error_message,
                record.throughput_rows_per_sec,
                datetime.utcnow(),
            )
        ]
        self._spark.createDataFrame(
            data,
            schema="run_id string, table_name string, source_table string, mode string, start_time timestamp, end_time timestamp, "
            "rows_read long, rows_written long, status string, error_message string, throughput_rows_per_sec double, created_at timestamp",
        ).write.mode("append").saveAsTable(f"{self._catalog}.{self._schema}.audit_log")

    def record_schema_drift(self, record: SchemaDriftRecord) -> None:
        data = [
            (
                record.run_id,
                record.table_name,
                record.drift_type,
                record.details,
                record.detected_at,
            )
        ]
        self._spark.createDataFrame(
            data,
            schema="run_id string, table_name string, drift_type string, details map<string,string>, detected_at timestamp",
        ).write.mode("append").saveAsTable(f"{self._catalog}.{self._schema}.schema_drift")


class InMemoryMetadataProvider(MetadataProvider):
    """Simple in-memory provider primarily for unit tests or dry-runs."""

    def __init__(
        self,
        tables: Iterable[TableMetadata],
        sources: Iterable[SourceConnectionMetadata],
        checkpoints: Optional[Iterable[CdfCheckpoint]] = None,
    ):
        self._tables = list(tables)
        self._sources = {source.id: source for source in sources}
        self._checkpoints = {(c.catalog, c.schema, c.table): c for c in checkpoints or []}
        self._audit_records: List[AuditRecord] = []
        self._drifts: List[SchemaDriftRecord] = []

    def list_tables(self, source_id: str, mode: LoadMode) -> List[TableMetadata]:
        return [t for t in self._tables if t.source_id == source_id and t.is_active]

    def get_source(self, source_id: str) -> SourceConnectionMetadata:
        return self._sources[source_id]

    def get_cdf_checkpoint(self, catalog: str, schema: str, table: str) -> Optional[CdfCheckpoint]:
        return self._checkpoints.get((catalog, schema, table))

    def upsert_cdf_checkpoint(self, checkpoint: CdfCheckpoint) -> None:
        self._checkpoints[(checkpoint.catalog, checkpoint.schema, checkpoint.table)] = checkpoint

    def record_audit(self, record: AuditRecord) -> None:
        self._audit_records.append(record)

    def record_schema_drift(self, record: SchemaDriftRecord) -> None:
        self._drifts.append(record)

    @property
    def audit_records(self) -> List[AuditRecord]:
        return self._audit_records

    @property
    def schema_drifts(self) -> List[SchemaDriftRecord]:
        return self._drifts
