from bronze_ingestion.config import RuntimeConfig
from bronze_ingestion.logging_utils import StructuredLogger
from bronze_ingestion.metadata.models import LoadMode
from bronze_ingestion.services.performance import BenchmarkService


class StubMetadataProvider:
    def __init__(self):
        self.benchmarks = []
        self.table_benchmarks = []

    # Unused abstract requirements
    def list_tables(self, *args, **kwargs):  # pragma: no cover - not needed in tests
        raise NotImplementedError

    def get_source(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def get_cdf_checkpoint(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def upsert_cdf_checkpoint(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def record_audit(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def record_schema_drift(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def record_benchmark(self, record):
        self.benchmarks.append(record)

    def record_table_benchmark(self, record):
        self.table_benchmarks.append(record)


def base_runtime_config():
    env = {
        "SOURCE_ID": "SRC",
        "BRONZE_PATH": "/mnt/bronze",
        "CLUSTER_PROFILE": "job-small",
        "SLA_MINUTES": "5",
    }
    return RuntimeConfig.from_env(env)


def test_benchmark_service_records_entry():
    provider = StubMetadataProvider()
    service = BenchmarkService(provider, base_runtime_config(), StructuredLogger("bench"))
    service.record("run-1", LoadMode.INCREMENTAL, successes_count=200, total_rows=1_000_000, duration_seconds=120.0)

    assert len(provider.benchmarks) == 1
    record = provider.benchmarks[0]
    assert record.met_sla is True
    assert record.table_count == 200


def test_benchmark_service_records_table_entry():
    provider = StubMetadataProvider()
    service = BenchmarkService(provider, base_runtime_config(), StructuredLogger("bench"))
    service.record_table(
        run_id="run-1",
        table_name="dim_customer",
        mode=LoadMode.INCREMENTAL,
        duration_seconds=12.5,
        rows_read=1000,
        rows_written=1000,
    )

    assert len(provider.table_benchmarks) == 1
    record = provider.table_benchmarks[0]
    assert record.table_name == "dim_customer"
    assert record.duration_seconds == 12.5
