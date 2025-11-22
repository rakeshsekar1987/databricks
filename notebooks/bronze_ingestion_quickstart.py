"""
Bronze Ingestion Quickstart Notebook
------------------------------------

Use this file as a lightweight Databricks-friendly entry point. Attach the notebook to a cluster,
set the environment variables (or DB widgets), and run the `run_bronze_ingestion()` cell.
"""

import os

from bronze_ingestion.config import RuntimeConfig
from bronze_ingestion.execution.orchestrator import IngestionOrchestrator
from bronze_ingestion.logging_utils import StructuredLogger
from bronze_ingestion.metadata.provider import DeltaMetadataProvider
from bronze_ingestion.services.notifier import LoggerNotifier
from bronze_ingestion.services.secrets import EnvironmentSecretManager
from bronze_ingestion.sources.factory import SourceAdapterFactory
from bronze_ingestion.spark.session import SparkSessionFactory


def run_bronze_ingestion(
    *,
    mode: str = "incremental",
    source_id: str = "MY_SOURCE",
    catalog: str = "main",
    schema: str = "bronze",
    bronze_path: str = "dbfs:/mnt/bronze",
    parallelism: int = 8,
) -> None:
    """
    Quickstart helper to execute the Bronze ingestion workflow with a handful of parameters.

    Args:
        mode: "full", "incremental", or "mixed"
        source_id: Identifier from the metadata table (e.g., MYSGS-group-01)
        catalog: Unity Catalog name containing the Bronze schema and metadata tables
        schema: Bronze schema name
        bronze_path: Base path for Delta outputs
        parallelism: Max number of tables to load in parallel
    """

    env = {
        "MODE": mode,
        "SOURCE_ID": source_id,
        "CATALOG": catalog,
        "SCHEMA": schema,
        "METADATA_CATALOG": catalog,
        "METADATA_SCHEMA": f"{schema}_meta",
        "BRONZE_PATH": bronze_path,
        "PARALLELISM": str(parallelism),
    }

    runtime_config = RuntimeConfig.from_env(env)
    logger = StructuredLogger("bronze-ingestion-notebook")
    spark = SparkSessionFactory(runtime_config).build()
    metadata_provider = DeltaMetadataProvider(
        spark,
        catalog=runtime_config.metadata_catalog,
        schema=runtime_config.metadata_schema,
    )
    secret_manager = EnvironmentSecretManager()
    adapter_factory = SourceAdapterFactory(secret_manager, logger)
    notifier = LoggerNotifier(logger)

    orchestrator = IngestionOrchestrator(
        spark=spark,
        runtime_config=runtime_config,
        metadata_provider=metadata_provider,
        adapter_factory=adapter_factory,
        notifier=notifier,
        logger=logger,
    )

    summary = orchestrator.run()
    logger.info(
        "notebook.run.complete",
        {
            "success_count": len(summary.successes),
            "failure_count": len(summary.failures),
        },
    )


# Example usage (uncomment in a Databricks notebook cell):
# run_bronze_ingestion(
#     mode="incremental",
#     source_id=dbutils.widgets.get("source_id"),
#     catalog=dbutils.widgets.get("catalog"),
#     schema=dbutils.widgets.get("schema"),
#     bronze_path=dbutils.widgets.get("bronze_path"),
#     parallelism=int(dbutils.widgets.get("parallelism")),
# )
