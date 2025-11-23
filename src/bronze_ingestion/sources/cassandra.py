"""
Cassandra adapter leveraging the Spark Cassandra connector.
"""

from __future__ import annotations

from ..logging_utils import StructuredLogger
from .base import SourceAdapter, SourceReadContext

try:  # pragma: no cover - optional dependency
    from pyspark.sql import DataFrame
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    DataFrame = object  # type: ignore


class CassandraAdapter(SourceAdapter):
    def __init__(self, logger: StructuredLogger):
        self._logger = logger

    def read(self, context: SourceReadContext) -> DataFrame:
        keyspace = context.options.get("keyspace")
        table = context.options.get("table", context.table_metadata.table_name)
        if not keyspace:
            raise ValueError("CassandraAdapter requires 'keyspace' in options.")

        reader = (
            context.spark.read.format("org.apache.spark.sql.cassandra")
            .options(table=table, keyspace=keyspace)
        )
        extra_options = context.options.get("reader_options", {})
        for key, value in extra_options.items():
            reader = reader.option(key, value)

        self._logger.info(
            "source.cassandra.read",
            {
                "keyspace": keyspace,
                "table": table,
                "columns": context.options.get("columns"),
            },
        )

        return reader.load()
