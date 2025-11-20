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
src/bronze_ingestion
├── config.py               # Runtime & environment configuration helpers
├── constants.py            # Global constants and defaults
├── exceptions.py           # Custom domain exceptions
├── logging_utils.py        # Structured logging facade
├── spark/
│   └── session.py          # Spark session builder & optimizations
├── metadata/
│   ├── models.py           # Dataclasses for metadata records
│   └── provider.py         # Provider interfaces & sample implementations
├── sources/
│   ├── base.py             # Source adapter contract
│   ├── sql_server.py       # JDBC adapter w/ CT support
│   └── rest_api.py         # Example REST adapter stub
├── strategies/
│   ├── base.py             # Strategy interface
│   ├── full_load.py        # Full-load logic
│   ├── incremental_ct.py   # CT-based incremental logic
│   └── append_only.py      # Append/LMD fallback logic
├── services/
│   ├── audit.py            # Audit + benchmark persistence
│   ├── data_quality.py     # Row-count + schema validation
│   ├── notifier.py         # Email/webhook notifications
│   ├── retry.py            # Exponential backoff executor
│   └── schema_evolution.py # Drift detection + logging
├── execution/
│   └── orchestrator.py     # Parallel ingestion controller
├── utils/
│   ├── concurrency.py      # Thread utilities + cancellation tokens
│   └── timer.py            # Timing helper
└── run_ingestion.py        # Entry point for Databricks jobs
```

## Metadata Expectations
- **Table metadata**: schema, PKs, partition columns, CT flag, retry policy, include/exclude, append-only, concurrency weight, SLA priority.
- **Source metadata**: connection info, Key Vault secret IDs, CT enablement, include/exclude lists, throttling hints.
- **Audit metadata**: CT/CDF checkpoints, run status, throughput, cost, schema drift logs.

Metadata can live in Unity Catalog tables or an external control database; provide a concrete provider by subclassing `MetadataProvider`.

## Running the Framework
1. Install the wheel on Databricks (`pip install .`).
2. Configure secrets/environment variables (`KEY_VAULT_SCOPE`, `PARALLELISM`, etc.).
3. Create Delta metadata tables (samples in `metadata/models.py` docstrings).
4. Submit `python -m bronze_ingestion.run_ingestion --mode incremental --source MYSGS-group-01`.

## Extensibility
- Add new data sources by subclassing `SourceAdapter`.
- Add new load behaviors by subclassing `LoadStrategy`.
- Register new metadata providers (e.g., Cassandra, Cosmos DB) without touching orchestration code.

## Testing & Quality
- Unit tests can be added under `tests/` targeting pure Python services.
- Use Databricks' `run submit --json` to orchestrate integration tests in lower environments.

## Next Steps
- Populate metadata tables.
- Connect Azure Monitor/Log Analytics workspace for structured logs.
- Roll out automated benchmarks to validate the 10-minute incremental SLA.
