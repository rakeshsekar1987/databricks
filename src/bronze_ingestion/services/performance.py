"""
Performance, benchmarking, and cost tracking services.
"""

from __future__ import annotations

from dataclasses import dataclass
from ..config import RuntimeConfig
from ..logging_utils import StructuredLogger
from ..metadata.models import BenchmarkRecord, CostRecord, LoadMode
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


@dataclass
class CostService:
    provider: MetadataProvider
    runtime_config: RuntimeConfig
    logger: StructuredLogger

    def record(self, run_id: str, duration_seconds: float) -> None:
        hours = duration_seconds / 3600
        driver_cost = self.runtime_config.driver_dbu_per_hour * hours * self.runtime_config.dbu_rate
        worker_cost = (
            self.runtime_config.worker_dbu_per_hour
            * self.runtime_config.num_workers
            * hours
            * self.runtime_config.dbu_rate
        )
        storage_cost = (
            self.runtime_config.storage_cost_per_tb_month
            * self.runtime_config.estimated_bronze_tb
            / (30 * 24)
            * duration_seconds
            / 3600
        )
        total_cost = driver_cost + worker_cost + storage_cost

        record = CostRecord(
            run_id=run_id,
            cluster_profile=self.runtime_config.cluster_profile,
            duration_seconds=duration_seconds,
            dbu_cost=driver_cost + worker_cost,
            storage_cost=storage_cost,
            total_cost=total_cost,
            notes=f"{self.runtime_config.num_workers} workers @ {self.runtime_config.worker_dbu_per_hour} DBU/h",
        )
        self.provider.record_cost(record)
        self.logger.info(
            "cost.recorded",
            {
                "run_id": run_id,
                "dbu_cost": record.dbu_cost,
                "storage_cost": storage_cost,
                "total_cost": total_cost,
            },
        )
