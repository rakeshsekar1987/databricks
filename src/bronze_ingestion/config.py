"""
Runtime configuration helpers for the Bronze ingestion framework.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import constants


@dataclass(frozen=True, slots=True)
class SparkRuntimeConfig:
    """Spark settings applied when building the Spark session."""

    enable_aqe: bool = True
    shuffle_partitions: Optional[int] = None
    adaptive_coalesce_partitions_enabled: bool = True
    delta_auto_optimize: bool = True
    extra_conf: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """High-level config resolved from environment variables and metadata."""

    mode: str
    source_id: str
    catalog: str
    schema: str
    metadata_catalog: str
    metadata_schema: str
    bronze_path: str
    parallelism: int = constants.DEFAULT_PARALLELISM
    run_id: Optional[str] = None
    log_workspace: str = constants.DEFAULT_LOG_ANALYTICS_WORKSPACE
    spark: SparkRuntimeConfig = field(default_factory=SparkRuntimeConfig)

    @staticmethod
    def _parse_extra_conf(raw: str) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - runtime safety
            raise ValueError(f"Invalid JSON in EXTRA_SPARK_CONF: {raw}") from exc

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "RuntimeConfig":
        env = env or os.environ
        mode = env.get("MODE", "incremental").lower()
        if mode not in constants.SUPPORTED_MODES:
            raise ValueError(f"Unsupported mode '{mode}'. Supported: {constants.SUPPORTED_MODES}")

        spark_conf = SparkRuntimeConfig(
            enable_aqe=env.get("ENABLE_AQE", "true").lower() == "true",
            shuffle_partitions=int(env["SHUFFLE_PARTITIONS"]) if env.get("SHUFFLE_PARTITIONS") else None,
            adaptive_coalesce_partitions_enabled=env.get("COALESCE_ENABLED", "true").lower() == "true",
            delta_auto_optimize=env.get("DELTA_AUTO_OPTIMIZE", "true").lower() == "true",
            extra_conf=cls._parse_extra_conf(env.get("EXTRA_SPARK_CONF", "")),
        )

        return cls(
            mode=mode,
            source_id=env["SOURCE_ID"],
            catalog=env.get("CATALOG", "masterdata_alpha"),
            schema=env.get("SCHEMA", "bronze"),
            metadata_catalog=env.get("METADATA_CATALOG", env.get("CATALOG", "masterdata_alpha")),
            metadata_schema=env.get("METADATA_SCHEMA", "metadata"),
            bronze_path=env["BRONZE_PATH"],
            parallelism=int(env.get("PARALLELISM", constants.DEFAULT_PARALLELISM)),
            run_id=env.get("RUN_ID"),
            log_workspace=env.get("LOG_ANALYTICS_WORKSPACE", constants.DEFAULT_LOG_ANALYTICS_WORKSPACE),
            spark=spark_conf,
        )
