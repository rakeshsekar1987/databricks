# Bronze Ingestion Framework

Metadata-driven PySpark framework that ingests 260+ on-prem SQL Server tables into Delta (Bronze) on Azure Databricks, while staying extensible for 10–15 future sources (REST, Cassandra, Blob, MariaDB, PostgreSQL, OData, ABFSS, WABS).

## Highlights
- SOLID-aligned Python package with dependency injection, thin orchestration layer, and pluggable adapters.
- Full + incremental (SQL Server Change Tracking) loads, with dynamic fallback to LMD/append/full modes.
- Exactly-once semantics using Delta transactions, CT/CDF checkpoints, and schema evolution support.
- Metadata-first design: table/source/audit metadata drive every decision (parallelism, retries, partitioning, notifications).
- Observability built-in: JSON logging, audit tables, Azure Log Analytics hooks, notification providers.

## Package Layout

```
src/
└── bronze_ingestion
    ├── config.py               # Runtime & environment configuration helpers
    ├── constants.py            # Global constants and defaults
    ├── exceptions.py           # Custom domain exceptions
    ├── logging_utils.py        # Structured logging + Log Analytics emitter
    ├── spark/
    │   └── session.py          # Spark session builder & optimizations
    ├── metadata/
    │   ├── models.py           # Dataclasses for table/source/audit/benchmark metadata
    │   └── provider.py         # Provider interfaces & Delta-backed implementation
    ├── sources/
    │   ├── base.py             # Source adapter contract + read context
    │   ├── sql_server.py       # JDBC adapter with CT predicate pushdown
    │   ├── rest_api.py         # REST/OData adapter
    │   ├── file_system.py      # ABFSS/WABS/Blob adapter
    │   ├── cassandra.py        # Cassandra adapter
    │   └── factory.py          # Metadata-driven adapter factory
    ├── strategies/
    │   ├── base.py             # Strategy interface + load result helpers
    │   ├── full_load.py        # Initial bulk ingestion
    │   ├── incremental_ct.py   # CT-based incremental logic
    │   └── append_only.py      # LMD/append fallback logic
    ├── services/
    │   ├── audit.py            # Audit logging with per-table durations
    │   ├── data_quality.py     # Row-count + schema validation
    │   ├── performance.py      # Run-level & per-table benchmarking
    │   ├── notifier.py         # Email/SendGrid/Logger notifications
    │   ├── retry.py            # Exponential backoff executor
    │   ├── schema_evolution.py # Drift detection + alerting
    │   └── secrets.py          # Key Vault/environment secret helpers
    ├── execution/
    │   └── orchestrator.py     # Parallel ingestion controller + benchmarking hooks
    ├── utils/
    │   ├── concurrency.py      # Thread utilities + cancellation tokens
    │   └── timer.py            # Timing helper
    └── run_ingestion.py        # CLI entry point for Databricks jobs

docs/
└── optimization_guide.md       # Detailed Spark/Delta/cluster tuning playbook

tests/
├── test_config.py              # RuntimeConfig parsing coverage
├── test_data_quality_service.py# DQ row-count + schema checks
├── test_performance_services.py# Benchmark recorder coverage
├── test_retry_executor.py      # Backoff + retry behavior
└── test_source_adapter_factory.py # Adapter selection logic
```

## Metadata Expectations
- **Table metadata**: schema, PKs, partition columns, CT flag, retry policy, include/exclude, append-only flag, concurrency weight, SLA priority, DQ tolerance, size bucket, max parallelism.
- **Source metadata**: connection info, Key Vault secret IDs, source type (SQLSERVER/REST/ABFSS/WABS/CASSANDRA/etc.), CT enablement, include/exclude lists, throttling hints.
- **Audit metadata**: CT/CDF checkpoints, run status, throughput, schema drift logs, benchmark tables for SLA validation.

Metadata can live in Unity Catalog tables or an external control database; provide a concrete provider by subclassing `MetadataProvider`.

## Running the Framework
1. Install the wheel on Databricks (`pip install .`).
2. Configure secrets/environment variables (`KEY_VAULT_SCOPE`, `PARALLELISM`, `LOG_ANALYTICS_*`, `SENDGRID_*`, `CLUSTER_PROFILE`, etc.).
3. Create Delta metadata tables (samples in `metadata/models.py` docstrings).
4. Submit `python -m bronze_ingestion.run_ingestion --mode incremental --source MYSGS-group-01`.

## Extensibility
- Add new data sources by subclassing `SourceAdapter` or plugging into `SourceAdapterFactory`.
- Add new load behaviors by subclassing `LoadStrategy`.
- Register new metadata providers (e.g., Cassandra, Cosmos DB, control-plane APIs) without touching orchestration code.
- Reference the full optimization playbook in `docs/optimization_guide.md` for Delta/Lakehouse tuning tips (file sizing, Z-order, AQE, caching, skew handling, cluster sizing, etc.).

## Testing & Quality
- Unit tests can be added under `tests/` targeting pure Python services (metadata, adapters, strategies).
- Use Databricks' `run submit --json` to orchestrate integration tests in lower environments.
- Benchmark jobs automatically record SLA metrics via `BenchmarkService`.

## Next Steps
- Populate metadata tables (table/source/audit/benchmark).
- Configure Azure Monitor/Log Analytics workspace credentials or SendGrid API key for notifications.
- Roll out automated benchmarks to validate the 10-minute incremental SLA and feed the metadata benchmark table.
