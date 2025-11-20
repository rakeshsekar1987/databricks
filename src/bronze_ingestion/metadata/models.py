"""
Metadata dataclasses used throughout the Bronze ingestion framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class LoadMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int
    initial_backoff_seconds: int
    backoff_multiplier: float = 2.0


@dataclass(frozen=True, slots=True)
class PartitioningHints:
    partition_columns: List[str] = field(default_factory=list)
    max_rows_per_file: Optional[int] = None
    spark_partitions: Optional[int] = None
    enable_dynamic_partitioning: bool = True


@dataclass(frozen=True, slots=True)
class TableMetadata:
    """
    Represents a single table configuration as captured in the metadata control plane.

    Example row:
    full_table_name='dbo.[FontReplacement]', table_name='FontReplacement', id_columns=['Id'],
    partition_cols=['created_date'], ct_enabled=True, source_id='AEXML-004', catalog_name='AEXML', entity_name='usft'
    """

    id: str
    source_id: str
    full_table_name: str
    table_name: str
    catalog_name: str
    schema_name: str
    ct_enabled: bool
    include_list: List[str]
    exclude_list: List[str]
    id_columns: List[str]
    partition_hints: PartitioningHints
    retry_policy: RetryPolicy
    is_append_only: bool
    is_active: bool
    concurrency_weight: int = 1
    sla_priority: int = 3
    table_run_properties: Dict[str, str] = field(default_factory=dict)
    dq_tolerance_percent: float = 1.0
    max_parallelism: Optional[int] = None
    estimated_row_count: Optional[int] = None
    size_bucket: str = "M"
    cost_allocation_code: Optional[str] = None
    fallback_mode: Optional[LoadMode] = None


@dataclass(frozen=True, slots=True)
class SourceConnectionMetadata:
    id: str
    data_source_type: str
    catalog_name: str
    logical_name: str
    db_details: Dict[str, str]
    is_active: bool
    include_list: List[str]
    exclude_list: List[str]
    is_ct_enabled: bool
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CdfCheckpoint:
    catalog: str
    schema: str
    table: str
    max_version: int
    max_commit_timestamp: datetime
    run_id: str


@dataclass(frozen=True, slots=True)
class AuditRecord:
    run_id: str
    table_name: str
    source_table: str
    mode: LoadMode
    start_time: datetime
    end_time: Optional[datetime]
    rows_read: int
    rows_written: int
    status: str
    error_message: Optional[str] = None
    throughput_rows_per_sec: Optional[float] = None


@dataclass(frozen=True, slots=True)
class SchemaDriftRecord:
    run_id: str
    table_name: str
    drift_type: str
    details: Dict[str, str]
    detected_at: datetime


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    benchmark_id: str
    catalog: str
    schema: str
    mode: LoadMode
    table_count: int
    total_rows: int
    duration_seconds: float
    cluster_profile: str
    met_sla: bool


@dataclass(frozen=True, slots=True)
class CostRecord:
    run_id: str
    cluster_profile: str
    duration_seconds: float
    dbu_cost: float
    storage_cost: float
    total_cost: float
    notes: Optional[str] = None
