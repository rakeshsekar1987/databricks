"""
Schema evolution and drift detection utilities.
"""

from __future__ import annotations

from typing import Dict, List

from pyspark.sql import DataFrame, SparkSession

from ..logging_utils import StructuredLogger
from ..metadata.models import SchemaDriftRecord, TableMetadata
from ..metadata.provider import MetadataProvider
from .notifier import Notifier


class SchemaEvolutionService:
    def __init__(
        self,
        spark: SparkSession,
        provider: MetadataProvider,
        notifier: Notifier,
        logger: StructuredLogger,
    ):
        self._spark = spark
        self._provider = provider
        self._notifier = notifier
        self._logger = logger

    def detect_and_log(self, dataframe: DataFrame, table: TableMetadata, run_id: str) -> None:
        target_table = f"{table.catalog_name}.{table.schema_name}.{table.table_name}"
        try:
            target_df = self._spark.table(target_table)
        except Exception:
            # Table does not exist yet - nothing to compare
            return

        source_schema = {field.name: field.dataType.simpleString() for field in dataframe.schema.fields}
        target_schema = {field.name: field.dataType.simpleString() for field in target_df.schema.fields}

        drifts: List[Dict[str, str]] = []

        for column, dtype in source_schema.items():
            if column not in target_schema:
                drifts.append({"type": "ADDED_COLUMN", "column": column, "dtype": dtype})
            elif target_schema[column] != dtype:
                drifts.append(
                    {"type": "TYPE_CHANGE", "column": column, "source_dtype": dtype, "target_dtype": target_schema[column]}
                )

        for column in target_schema:
            if column not in source_schema:
                drifts.append({"type": "REMOVED_COLUMN", "column": column})

        for drift in drifts:
            record = SchemaDriftRecord(
                run_id=run_id,
                table_name=table.table_name,
                drift_type=drift["type"],
                details=drift,
                detected_at=dataframe.sparkSession.sql("SELECT current_timestamp()").collect()[0][0],
            )
            self._provider.record_schema_drift(record)
            message = f"Schema drift detected for {table.table_name}: {drift}"
            self._notifier.notify(subject=f"Schema drift on {table.table_name}", body=message)
            self._logger.warning("schema.drift", {"table": table.table_name, **drift})
