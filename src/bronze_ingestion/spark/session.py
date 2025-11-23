"""
Spark session builder and optimizer configuration.
"""

from __future__ import annotations

from typing import Optional

from pyspark.sql import SparkSession

from ..config import RuntimeConfig


class SparkSessionFactory:
    """
    Builds Spark sessions with the optimizations required by the Bronze framework.
    Intended to be invoked inside Databricks notebook or job cluster context.
    """

    def __init__(self, runtime_config: RuntimeConfig):
        self._config = runtime_config

    def build(self, existing: Optional[SparkSession] = None) -> SparkSession:
        spark = existing or SparkSession.builder.getOrCreate()
        spark.conf.set("spark.databricks.delta.properties.defaults.enableChangeDataFeed", "true")
        spark.conf.set("spark.databricks.delta.properties.defaults.logRetentionDuration", "interval 7 days")
        spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")
        spark.conf.set("spark.sql.adaptive.enabled", str(self._config.spark.enable_aqe).lower())
        spark.conf.set(
            "spark.databricks.delta.optimizeWrite.enabled", str(self._config.spark.delta_auto_optimize).lower()
        )
        spark.conf.set(
            "spark.databricks.io.cache.enabled", "true"
        )  # Cache frequently read dimension tables for incremental jobs

        if self._config.spark.shuffle_partitions:
            spark.conf.set("spark.sql.shuffle.partitions", self._config.spark.shuffle_partitions)
        if self._config.spark.adaptive_coalesce_partitions_enabled:
            spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")

        for key, value in self._config.spark.extra_conf.items():
            spark.conf.set(key, value)

        return spark
