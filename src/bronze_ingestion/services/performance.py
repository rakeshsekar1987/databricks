"""
Performance and benchmarking services.
"""

from __future__ import annotations

from dataclasses import dataclass
from ..config import RuntimeConfig
from ..logging_utils import StructuredLogger
from ..metadata.models import BenchmarkRecord, LoadMode, TableBenchmarkRecord
from ..metadata.provider import MetadataProvider


@dataclass
class BenchmarkService:
    provider: MetadataProvider
    runtime_config: RuntimeConfig
    logger: StructuredLogger

    def record(
        self,
        run_id: str,
        mode: LoadMode,
        successes_count: int,
        total_rows: int,
        duration_seconds: float,
    ) -> None:
        record = BenchmarkRecord(
            benchmark_id=run_id,
            catalog=self.runtime_config.catalog,
            schema=self.runtime_config.schema,
            mode=mode,
            table_count=successes_count,
            total_rows=total_rows,
            duration_seconds=duration_seconds,
            cluster_profile=self.runtime_config.cluster_profile,
            met_sla=duration_seconds <= (self.runtime_config.sla_minutes * 60),
        )
        self.provider.record_benchmark(record)
        self.logger.info(
            "benchmark.recorded",
            {
                "run_id": run_id,
                "duration_seconds": duration_seconds,
                "met_sla": record.met_sla,
            },
        )

    def record_table(
        self,
        run_id: str,
        table_name: str,
        mode: LoadMode,
        duration_seconds: float,
        rows_read: int,
        rows_written: int,
    ) -> None:
        record = TableBenchmarkRecord(
            run_id=run_id,
            table_name=table_name,
            mode=mode,
            duration_seconds=duration_seconds,
            rows_read=rows_read,
            rows_written=rows_written,
        )
        self.provider.record_table_benchmark(record)
        self.logger.info(
            "benchmark.table.recorded",
            {
                "table": table_name,
                "duration_seconds": duration_seconds,
                "rows_written": rows_written,
            },
        )


