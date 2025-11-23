# Bronze Ingestion Framework

Metadata-driven PySpark framework that ingests 260+ on-prem SQL Server tables into Delta (Bronze) on Azure Databricks, while staying extensible for 10–15 future sources (REST, Cassandra, Blob, MariaDB, PostgreSQL, OData, ABFSS, WABS).

## Highlights
- SOLID-aligned Python package with dependency injection, thin orchestration layer, and pluggable adapters.
- Full + incremental (SQL Server Change Tracking) loads, with dynamic fallback to LMD/append/full modes.
- Exactly-once semantics using Delta transactions, CT/CDF checkpoints, and schema evolution support.
- Metadata-first design: table/source/audit metadata drive every decision (parallelism, retries, partitioning, notifications).
- Observability built-in: JSON logging, audit tables, Azure Log Analytics hooks, notification providers.

## Quick Folder Guide

Need a simple mental model? Start with `docs/project_structure.md`. In short:

- **notebooks/** – `bronze_ingestion_quickstart.py` is a Databricks-friendly driver. Drop it into a workspace, set a few parameters (mode, source ID, catalog, path, parallelism), and call `run_bronze_ingestion()` to kick off a run without digging into the library internals.
- **src/bronze_ingestion/** – The reusable ingestion library: configs, metadata models/providers, all source adapters (SQL Server, REST/OData, ABFSS/WABS, Cassandra, etc.), load strategies (full, CT incremental, append/LMD), shared services (audit, data-quality, schema drift, retry, notifier, benchmarking, secrets), orchestration, utilities, and the `run_ingestion.py` CLI entry point.
- **tests/** – Lightweight pytest suite for config parsing, retry/backoff, data-quality checks, adapter factory routing, and benchmarking helpers (`PYTHONPATH=./src python3 -m pytest`).
- **docs/** – `optimization_guide.md` (Delta/Spark/cluster tuning playbook) and `project_structure.md` (plain-language layout overview).

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
