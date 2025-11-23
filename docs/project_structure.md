## Project Structure (Simplified Overview)

This guide explains the repository layout in plain language so new contributors can quickly orient themselves.

```
project-root/
├─ notebooks/
│   └─ bronze_ingestion_quickstart.py   # Databricks-friendly entry point to run the pipeline
├─ src/
│   └─ bronze_ingestion/                # Reusable ingestion library (configs, adapters, services)
├─ tests/                               # Lightweight unit tests for core helpers/services
├─ docs/
│   ├─ optimization_guide.md            # Performance & tuning best practices
│   └─ project_structure.md             # (this file)
└─ pyproject.toml / README.md / etc.    # Build metadata & documentation
```

### Key folders

- **notebooks/** – Ready-to-run helper notebook/script for Databricks. Adjust parameters and execute `run_bronze_ingestion()` to kick off a load without diving into the library internals.
- **src/bronze_ingestion/** – The main Python package split into subfolders:
  - `config.py`, `constants.py`, `logging_utils.py`, `exceptions.py`: foundational utilities.
  - `metadata/`: dataclasses and providers for table/source/audit/benchmark metadata stored in Delta/Unity Catalog.
  - `sources/`: adapters (SQL Server, REST/OData, ABFSS/WABS, Cassandra) plus a factory that picks the right one per data source.
  - `strategies/`: full load, CT incremental, and append/LMD fallback logic built on the shared `LoadStrategy` base.
  - `services/`: reusable building blocks (audit logging, data quality checks, schema drift detection, retry/backoff, notifications, benchmarking, secrets).
  - `execution/`: orchestration layer that reads metadata, instantiates adapters/strategies, manages parallelism, and records benchmarks.
  - `utils/`: small helpers for concurrency control and timing.
  - `run_ingestion.py`: CLI/entry point that wires everything together for job clusters or local usage.
- **tests/** – Pytest-based smoke tests covering configuration parsing, retry logic, data-quality checks, adapter selection, and benchmarking. Run via `PYTHONPATH=./src python3 -m pytest`.
- **docs/** – Written guidance on architecture and tuning. `optimization_guide.md` captures detailed best practices for Delta Lake, Spark shuffles, caching, cluster sizing, etc.

### How to get started quickly

1. Open `notebooks/bronze_ingestion_quickstart.py` (or import it into a Databricks notebook).
2. Configure the few key parameters (`mode`, `source_id`, `catalog`, `bronze_path`, `parallelism`).
3. Run `run_bronze_ingestion()` to trigger a full or incremental load using the metadata-driven pipeline.

For deeper customization (e.g., adding a new source type, tweaking strategies, or changing metadata schemas), jump into the relevant `src/bronze_ingestion/...` submodule listed above.
