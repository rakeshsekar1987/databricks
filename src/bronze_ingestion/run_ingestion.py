"""
CLI entry point for running the Bronze ingestion framework on Databricks.
"""

from __future__ import annotations

import argparse
import os
from typing import Dict

from pyspark.sql import SparkSession

from .config import RuntimeConfig
from .execution.orchestrator import IngestionOrchestrator
from .logging_utils import StructuredLogger
from .metadata.provider import DeltaMetadataProvider
from .services.notifier import LoggerNotifier
from .services.secrets import EnvironmentSecretManager, KeyVaultSecretManager, resolve_dbutils
from .sources.sql_server import SqlServerAdapter
from .spark.session import SparkSessionFactory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Bronze ingestion job")
    parser.add_argument("--mode", help="Load mode: full|incremental|mixed")
    parser.add_argument("--source-id", help="Source identifier from metadata")
    parser.add_argument("--catalog", help="Target catalog for Bronze tables")
    parser.add_argument("--schema", help="Target schema for Bronze tables")
    parser.add_argument("--metadata-schema", help="Schema hosting metadata tables")
    parser.add_argument("--bronze-path", help="Base storage path for Bronze data")
    parser.add_argument("--parallelism", type=int, help="Max parallel tables")
    parser.add_argument("--run-id", help="Optional run identifier")
    return parser.parse_args()


def build_runtime_config(args: argparse.Namespace) -> RuntimeConfig:
    env: Dict[str, str] = dict(os.environ)
    if args.mode:
        env["MODE"] = args.mode
    if args.source_id:
        env["SOURCE_ID"] = args.source_id
    if args.catalog:
        env["CATALOG"] = args.catalog
    if args.schema:
        env["SCHEMA"] = args.schema
    if args.metadata_schema:
        env["METADATA_SCHEMA"] = args.metadata_schema
    if args.bronze_path:
        env["BRONZE_PATH"] = args.bronze_path
    if args.parallelism:
        env["PARALLELISM"] = str(args.parallelism)
    if args.run_id:
        env["RUN_ID"] = args.run_id
    return RuntimeConfig.from_env(env)


def build_secret_manager(logger: StructuredLogger):
    scope = os.environ.get("KEY_VAULT_SCOPE")
    if scope:
        try:
            dbutils = resolve_dbutils()
            logger.info("secret_manager.keyvault", {"scope": scope})
            return KeyVaultSecretManager(scope=scope, dbutils=dbutils)
        except RuntimeError as exc:
            logger.warning("secret_manager.fallback", {"scope": scope, "error": str(exc)})
    logger.info("secret_manager.env", {})
    return EnvironmentSecretManager()


def main():
    args = parse_args()
    logger = StructuredLogger()
    runtime_config = build_runtime_config(args)

    spark = SparkSessionFactory(runtime_config).build(SparkSession.getActiveSession())

    metadata_provider = DeltaMetadataProvider(
        spark,
        catalog=runtime_config.metadata_catalog,
        schema=runtime_config.metadata_schema,
    )

    secret_manager = build_secret_manager(logger)
    source_adapter = SqlServerAdapter(secret_manager, logger)
    notifier = LoggerNotifier(logger)

    orchestrator = IngestionOrchestrator(
        spark=spark,
        runtime_config=runtime_config,
        metadata_provider=metadata_provider,
        source_adapter=source_adapter,
        notifier=notifier,
        logger=logger,
    )

    summary = orchestrator.run()
    logger.info(
        "orchestrator.summary",
        {
            "success_count": len(summary.successes),
            "failure_count": len(summary.failures),
        },
    )


if __name__ == "__main__":
    main()
