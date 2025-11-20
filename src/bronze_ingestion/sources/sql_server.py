"""
SQL Server JDBC adapter with CT-aware predicate pushdown.
"""

from __future__ import annotations

from typing import Dict, TYPE_CHECKING

from ..logging_utils import StructuredLogger
from ..services.secrets import SecretManager
from .base import SourceAdapter, SourceReadContext

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyspark.sql import DataFrame


class SqlServerAdapter(SourceAdapter):
    def __init__(self, secret_manager: SecretManager, logger: StructuredLogger):
        self._secret_manager = secret_manager
        self._logger = logger

    def _jdbc_base_options(self, table_metadata: TableMetadata, runtime_options: Dict[str, str]) -> Dict[str, str]:
        details = runtime_options.get("db_details", {})
        host = details.get("db_host") or details.get("db_host_secondary") or details.get("db_host_backup")
        if not host:
            raise ValueError("No SQL Server host provided in metadata.")

        password = self._secret_manager.get_secret(details["password_key"])
        url = f"jdbc:sqlserver://{host}:{details.get('db_port', '1433')};databaseName={details['db_name']}"

        options: Dict[str, str] = {
            "url": url,
            "dbtable": table_metadata.full_table_name,
            "user": details["user_name"],
            "password": password,
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
            "fetchsize": str(runtime_options.get("fetchsize", table_metadata.table_run_properties.get("fetchsize", 5000))),
            "batchsize": str(runtime_options.get("batchsize", table_metadata.table_run_properties.get("batchsize", 10000))),
        }
        return options

    def read(self, context: SourceReadContext) -> "DataFrame":
        options = self._jdbc_base_options(context.table_metadata, context.options)
        reader = context.spark.read.format("jdbc").options(**options)

        partition_column = context.table_metadata.table_run_properties.get("partition_column")
        if partition_column:
            reader = reader.option("partitionColumn", partition_column)
            reader = reader.option("lowerBound", context.table_metadata.table_run_properties.get("partition_lower_bound", 0))
            reader = reader.option(
                "upperBound", context.table_metadata.table_run_properties.get("partition_upper_bound", 100_000_000)
            )
            reader = reader.option(
                "numPartitions",
                context.table_metadata.partition_hints.spark_partitions
                or context.options.get("spark_partitions", 8),
            )

        if context.incremental_filter:
            self._logger.info(
                "source.incremental_filter",
                {
                    "table": context.table_metadata.table_name,
                    "filter": context.incremental_filter,
                },
            )
            reader = reader.option("pushDownPredicate", context.incremental_filter)

        return reader.load()
