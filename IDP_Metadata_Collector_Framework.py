"""IDP Metadata Collector Framework
===================================

Highly structured and extensible metadata collector that converts every
configured IDP data-source into the canonical `meta_data_registry` dataset.
The module follows SOLID principles and applies strategy, factory, repository,
and builder patterns so that new connectors can be added with no changes to the
existing workflow.
"""

from __future__ import annotations

import ast
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

try:  # pragma: no cover - pyspark is available at runtime
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import Row
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
    from pyspark.sql.window import Window
except ImportError:  # pragma: no cover - allows unit tests without Spark
    DataFrame = Any  # type: ignore
    SparkSession = Any  # type: ignore
    Row = Any  # type: ignore
    F = None  # type: ignore
    T = None  # type: ignore
    Window = None  # type: ignore

try:  # pragma: no cover - provided in Databricks workspace
    from DPCommonFunctions import write_table
except ImportError:  # pragma: no cover - inject your own writer in tests
    def write_table(*args: Any, **kwargs: Any) -> None:  # type: ignore
        raise RuntimeError(
            "write_table helper is not available. Import DPCommonFunctions or "
            "inject a compatible write_table implementation before calling run_job()."
        )

LOGGER = logging.getLogger(__name__)
DEFAULT_LOG_LEVEL = os.getenv("IDP_METADATA_LOG_LEVEL", "INFO")
DEFAULT_SECRET_SCOPE = os.getenv("IDP_SECRET_SCOPE")

CONFIG_TABLE = "qa_idp.config.metadata_source_connection_details"
DEFAULT_REGISTRY_TABLE = "qa_idp.config.meta_data_registry"
DEFAULT_SUMMARY_TABLE = "qa_idp.logs.meta_data_registry_summary"

SUPPORTED_SOURCE_TYPES = {
    "ABFSS_STORAGE",
    "WABS_STORAGE",
    "WASBS_SAS_STORAGE",
    "SQLSERVER",
    "POSTGRESQL",
    "MARIADB",
    "CASSANDRA",
    "REST_API",
}

# Spark schemas --------------------------------------------------------------
if T is not None:
    COLUMN_DETAILS_SCHEMA = T.ArrayType(  # type: ignore[assignment]
        T.StructType(
            [
                T.StructField("name", T.StringType(), False),
                T.StructField("data_type", T.StringType(), True),
                T.StructField("nullable", T.BooleanType(), False),
                T.StructField("metadata", T.MapType(T.StringType(), T.StringType()), True),
            ]
        )
    )
    REGISTRY_SCHEMA = T.StructType(
        [
            T.StructField("full_table_name", T.StringType(), False),
            T.StructField("table_name", T.StringType(), False),
            T.StructField("id_columns", T.ArrayType(T.StringType()), True),
            T.StructField("partition_cols", T.ArrayType(T.StringType()), True),
            T.StructField("ct_enabled", T.IntegerType(), False),
            T.StructField("source_id", T.StringType(), False),
            T.StructField("catalog_name", T.StringType(), False),
            T.StructField("entity_name", T.StringType(), True),
            T.StructField("db_name", T.StringType(), True),
            T.StructField("id", T.StringType(), False),
            T.StructField("include_list", T.ArrayType(T.StringType()), True),
            T.StructField("exclude_list", T.ArrayType(T.StringType()), True),
            T.StructField("is_included", T.IntegerType(), False),
            T.StructField("is_append_only", T.IntegerType(), False),
            T.StructField("is_active", T.IntegerType(), False),
            T.StructField("table_run_properties", T.IntegerType(), False),
            T.StructField("idp_db_name", T.StringType(), False),
            T.StructField("idp_id_columns", T.ArrayType(T.StringType()), True),
            T.StructField("idp_cdc_hash", T.StringType(), False),
            T.StructField("idp_created_date", T.TimestampType(), True),
            T.StructField("idp_modified_date", T.TimestampType(), True),
            T.StructField("table_row_count", T.LongType(), True),
            T.StructField("column_count", T.IntegerType(), False),
            T.StructField("source_schema", T.ArrayType(T.StringType()), False),
            T.StructField("idp_schema", T.ArrayType(T.StringType()), False),
            T.StructField("column_details", COLUMN_DETAILS_SCHEMA, False),
            T.StructField("file_size_bytes", T.LongType(), True),
            T.StructField("file_last_modified", T.TimestampType(), True),
            T.StructField("sample_file_paths", T.ArrayType(T.StringType()), True),
        ]
    )
else:  # pragma: no cover - Spark not present during unit tests
    COLUMN_DETAILS_SCHEMA = None
    REGISTRY_SCHEMA = None


# ---------------------------------------------------------------------------
#  Generic helpers
# ---------------------------------------------------------------------------
def _ensure_logger() -> logging.Logger:
    if LOGGER.handlers:
        return LOGGER
    LOGGER.setLevel(getattr(logging, DEFAULT_LOG_LEVEL.upper(), logging.INFO))
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    return LOGGER


def _now_ts() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_ts().isoformat()


def _coerce_datetime(value: Optional[Any], fallback: Optional[datetime] = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        val = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            pass
    return fallback or _now_ts()


def _safe_json_loads(value: str) -> Dict[str, Any]:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except Exception:
            return {}


def _normalize_list(value: Optional[Iterable[str]]) -> List[str]:
    return [item for item in value or [] if item is not None]


def to_snake_case(value: str) -> str:
    if not value:
        return value
    cleaned: List[str] = []
    prev_lower = False
    for char in value.strip():
        if char.isalnum():
            if char.isupper() and prev_lower:
                cleaned.append("_")
            cleaned.append(char.lower())
            prev_lower = char.islower()
        else:
            cleaned.append("_")
            prev_lower = False
    result = "".join(cleaned)
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_")


def to_snake_case_list(values: Optional[Sequence[str]]) -> List[str]:
    return [to_snake_case(val) for val in values or []]


def build_sha256_hash(payload: str) -> str:
    return sha256(payload.encode("utf-8")).hexdigest()


def chunked(sequence: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for idx in range(0, len(sequence), size):
        yield sequence[idx : idx + size]


# ---------------------------------------------------------------------------
#  Contracts and data models
# ---------------------------------------------------------------------------
@runtime_checkable
class SecretProvider(Protocol):
    def get(self, key: str, fallback: Optional[str] = None) -> str:
        ...


class DatabricksSecretProvider:
    def __init__(self, dbutils_module: Any, default_scope: Optional[str] = None) -> None:
        self._dbutils = dbutils_module
        self._default_scope = default_scope or DEFAULT_SECRET_SCOPE

    def get(self, key: str, fallback: Optional[str] = None) -> str:  # pragma: no cover
        scope, secret_key = self._resolve_scope_and_key(key)
        try:
            return self._dbutils.secrets.get(scope=scope, key=secret_key)
        except Exception:
            if fallback is not None:
                return fallback
            raise

    def _resolve_scope_and_key(self, key: str) -> Tuple[str, str]:
        if ":" in key:
            scope, secret_key = key.split(":", 1)
            if scope and secret_key:
                return scope, secret_key
        if self._default_scope:
            return self._default_scope, key
        raise ValueError(
            "Secret reference must either be 'scope:key' or provide IDP_SECRET_SCOPE env var"
        )


@runtime_checkable
class FileSystemClient(Protocol):
    def list(self, path: str) -> List[Dict[str, Any]]:
        ...


class DbutilsFileSystemClient:
    def __init__(self, dbutils_module: Any) -> None:
        self._dbutils = dbutils_module

    def list(self, path: str) -> List[Dict[str, Any]]:  # pragma: no cover
        entries = self._dbutils.fs.ls(path)
        return [
            {
                "path": entry.path,
                "name": entry.name,
                "size": entry.size,
                "modification_time": entry.modificationTime,
            }
            for entry in entries
        ]


@dataclass
class DataSourceConfig:
    id: str
    data_source_type: str
    catalog_name: str
    table_name: Optional[str]
    metadata_enabled: bool
    db_details: Dict[str, Any]
    is_active: bool
    idp_cdc_hash: Optional[str]
    idp_created_date: Optional[str]
    idp_modified_date: Optional[str]

    @staticmethod
    def from_row(row: Dict[str, Any]) -> "DataSourceConfig":
        db_details = _safe_json_loads(row.get("db_details", "{}"))
        return DataSourceConfig(
            id=row["id"],
            data_source_type=row.get("data_source_type", "").upper(),
            catalog_name=row.get("catalog_name", ""),
            table_name=row.get("table_name"),
            metadata_enabled=bool(row.get("metadata_enabled", True)),
            db_details=db_details,
            is_active=bool(row.get("is_active", True)),
            idp_cdc_hash=row.get("idp_cdc_hash"),
            idp_created_date=row.get("idp_created_date"),
            idp_modified_date=row.get("idp_modified_date"),
        )

    @property
    def include_list(self) -> List[str]:
        return _normalize_list(self.db_details.get("include_list"))

    @property
    def exclude_list(self) -> List[str]:
        return _normalize_list(self.db_details.get("exclude_list"))

    @property
    def append_only_list(self) -> List[str]:
        return _normalize_list(self.db_details.get("append_only_list"))


@dataclass
class TableMetadata:
    config: DataSourceConfig
    full_table_name: str
    table_name: str
    source_schema: List[str]
    column_details: List[Dict[str, Any]]
    id_columns: List[str] = field(default_factory=list)
    partition_cols: List[str] = field(default_factory=list)
    ct_enabled: int = 0
    db_name: Optional[str] = None
    entity_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_last_modified: Optional[datetime] = None
    sample_file_paths: Optional[List[str]] = None
    table_row_count: Optional[int] = None

    def to_row(self) -> Dict[str, Any]:
        include_list = self.config.include_list
        exclude_list = self.config.exclude_list
        append_only_list = self.config.append_only_list
        is_included = 1 if InclusionEvaluator.evaluate(self.table_name, include_list, exclude_list) else 0
        is_append_only = 1 if self._contains_case_insensitive(append_only_list, self.table_name) else 0
        ct_enabled = int(self.ct_enabled)
        is_active = is_included
        idp_schema = to_snake_case_list(self.source_schema)
        idp_id_columns = to_snake_case_list(self.id_columns)
        idp_db_name = to_snake_case(self.table_name)
        source_id = self.config.id
        table_name = self.table_name
        metadata_hash = build_sha256_hash(
            json.dumps(
                {
                    "source_id": source_id,
                    "full_table_name": self.full_table_name,
                    "columns": self.source_schema,
                    "id_columns": self.id_columns,
                    "ct_enabled": ct_enabled,
                    "partition_cols": self.partition_cols,
                },
                sort_keys=True,
            )
        )
        now_ts = _now_ts()
        created_ts = _coerce_datetime(self.config.idp_created_date, now_ts)
        modified_ts = now_ts
        db_name = self.db_name or self.config.db_details.get("db_name") or self.config.catalog_name
        entity_name = self.entity_name or self.config.table_name or self.table_name
        column_count = len(self.source_schema)
        sample_paths = self.sample_file_paths or []
        row = {
            "full_table_name": self.full_table_name,
            "table_name": table_name,
            "id_columns": self.id_columns,
            "partition_cols": self.partition_cols,
            "ct_enabled": ct_enabled,
            "source_id": source_id,
            "catalog_name": self.config.catalog_name.upper(),
            "entity_name": entity_name,
            "db_name": db_name,
            "id": f"{source_id}_{table_name}",
            "include_list": include_list,
            "exclude_list": exclude_list,
            "is_included": is_included,
            "is_append_only": is_append_only,
            "is_active": is_active,
            "table_run_properties": (is_included << 2) | (ct_enabled << 1) | is_append_only,
            "idp_db_name": idp_db_name,
            "idp_id_columns": idp_id_columns,
            "idp_cdc_hash": metadata_hash,
            "idp_created_date": created_ts,
            "idp_modified_date": modified_ts,
            "table_row_count": self.table_row_count,
            "column_count": column_count,
            "source_schema": self.source_schema,
            "idp_schema": idp_schema,
            "column_details": self._format_column_details(),
            "file_size_bytes": self.file_size_bytes,
            "file_last_modified": self.file_last_modified,
            "sample_file_paths": sample_paths,
        }
        return row

    def _format_column_details(self) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for column in self.column_details:
            metadata = {k: (str(v) if v is not None else "") for k, v in column.get("metadata", {}).items()}
            formatted.append(
                {
                    "name": column.get("name"),
                    "data_type": column.get("data_type"),
                    "nullable": bool(column.get("nullable", True)),
                    "metadata": metadata,
                }
            )
        return formatted

    @staticmethod
    def _contains_case_insensitive(items: Sequence[str], value: str) -> bool:
        lowered = {item.lower() for item in items}
        return value.lower() in lowered if value else False


@dataclass
class CollectorOutput:
    rows: List[TableMetadata]
    summary: Tuple[str, str, Optional[str]]


@dataclass
class CollectorContext:
    spark: SparkSession
    secret_provider: SecretProvider
    filesystem_client: Optional[FileSystemClient] = None
    compute_row_count: bool = False
    sample_file_limit: int = 5


# ---------------------------------------------------------------------------
#  Config repository (Repository pattern)
# ---------------------------------------------------------------------------
class ConfigRepository:
    def __init__(
        self,
        spark: SparkSession,
        table_name: str = CONFIG_TABLE,
        include_inactive: bool = False,
        require_metadata_enabled: bool = False,
    ) -> None:
        self._spark = spark
        self._table = table_name
        self._include_inactive = include_inactive
        self._require_metadata_enabled = require_metadata_enabled

    def load(self) -> List[DataSourceConfig]:
        df = self._spark.table(self._table)
        filters = []
        if not self._include_inactive:
            filters.append("is_active = true")
        if self._require_metadata_enabled:
            filters.append("metadata_enabled = true")
        if filters:
            df = df.filter(" AND ".join(filters))
        rows = df.collect()
        configs: List[DataSourceConfig] = []
        for row in rows:
            config = DataSourceConfig.from_row(row.asDict(True))
            if config.data_source_type in SUPPORTED_SOURCE_TYPES:
                configs.append(config)
        return configs


# ---------------------------------------------------------------------------
#  Inclusion helper
# ---------------------------------------------------------------------------
class InclusionEvaluator:
    @staticmethod
    def evaluate(table_name: str, include_list: Sequence[str], exclude_list: Sequence[str]) -> bool:
        name = (table_name or "").lower()
        includes = {item.lower() for item in include_list}
        excludes = {item.lower() for item in exclude_list}
        if includes and name not in includes:
            return False
        if name in excludes:
            return False
        return True


# ---------------------------------------------------------------------------
#  Collector hierarchy (Strategy pattern)
# ---------------------------------------------------------------------------
class BaseCollector:
    def __init__(self, context: CollectorContext) -> None:
        self.context = context
        self.spark = context.spark
        self.secret_provider = context.secret_provider
        self.fs_client = context.filesystem_client
        self.logger = _ensure_logger()

    def collect(self, config: DataSourceConfig) -> CollectorOutput:
        try:
            rows = self._collect_impl(config)
            return CollectorOutput(rows, (config.id, "Success", None))
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.exception("Failed collecting metadata for %s", config.id)
            return CollectorOutput([], (config.id, "Failure", str(exc)))

    def _collect_impl(self, config: DataSourceConfig) -> List[TableMetadata]:
        raise NotImplementedError


class CollectorFactory:
    def __init__(self, context: CollectorContext) -> None:
        self.context = context
        self._cache: Dict[str, BaseCollector] = {}
        self._lock = Lock()

    def get(self, source_type: str) -> BaseCollector:
        key = source_type.upper()
        with self._lock:
            collector = self._cache.get(key)
            if collector is None:
                collector = self._build_collector(key)
                self._cache[key] = collector
        return collector

    def _build_collector(self, source_type: str) -> BaseCollector:
        if source_type in {"SQLSERVER", "POSTGRESQL", "MARIADB"}:
            return JdbcMetadataCollector(self.context, source_type)
        if source_type in {"ABFSS_STORAGE", "WABS_STORAGE", "WASBS_SAS_STORAGE"}:
            return FileStorageCollector(self.context, source_type)
        if source_type == "CASSANDRA":
            return CassandraMetadataCollector(self.context)
        if source_type == "REST_API":
            return RestApiMetadataCollector(self.context)
        raise ValueError(f"Unsupported data-source type: {source_type}")


# ------------------------------- JDBC Collector -----------------------------
class JdbcMetadataCollector(BaseCollector):
    DRIVER_MAP = {
        "SQLSERVER": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
        "POSTGRESQL": "org.postgresql.Driver",
        "MARIADB": "org.mariadb.jdbc.Driver",
    }

    DIALECT = {
        "SQLSERVER": {
            "columns": "SELECT table_schema, table_name, column_name, data_type, ordinal_position, is_nullable FROM INFORMATION_SCHEMA.COLUMNS",
            "primary_keys": "SELECT ku.table_schema, ku.table_name, ku.column_name FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku ON tc.constraint_name = ku.constraint_name AND tc.table_schema = ku.table_schema WHERE tc.constraint_type = 'PRIMARY KEY'",
            "qualifier": lambda schema, table: f"[{schema}] [{table}]",
        },
        "POSTGRESQL": {
            "columns": "SELECT table_schema, table_name, column_name, data_type, ordinal_position, is_nullable FROM information_schema.columns",
            "primary_keys": "SELECT kcu.table_schema, kcu.table_name, kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.constraint_schema = kcu.constraint_schema WHERE tc.constraint_type = 'PRIMARY KEY'",
            "qualifier": lambda schema, table: f'"{schema}"."{table}"',
        },
        "MARIADB": {
            "columns": "SELECT table_schema, table_name, column_name, data_type, ordinal_position, is_nullable FROM information_schema.columns",
            "primary_keys": "SELECT kcu.table_schema, kcu.table_name, kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema WHERE tc.constraint_type = 'PRIMARY KEY'",
            "qualifier": lambda schema, table: f'`{schema}`.`{table}`',
        },
    }

    def __init__(self, context: CollectorContext, source_type: str) -> None:
        super().__init__(context)
        self.source_type = source_type.upper()

    def _collect_impl(self, config: DataSourceConfig) -> List[TableMetadata]:
        options = self._build_jdbc_options(config)
        column_rows = self._fetch_metadata_rows(options, config, "columns")
        if not column_rows:
            return []
        pk_rows = self._fetch_metadata_rows(options, config, "primary_keys")
        pk_lookup = self._build_pk_lookup(pk_rows)
        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for row in column_rows:
            key = (row["table_schema"], row["table_name"])
            grouped.setdefault(key, []).append(row)
        ct_enabled = int(config.db_details.get("is_ct_enabled", False))
        table_rows: List[TableMetadata] = []
        for (schema, table), rows in grouped.items():
            sorted_rows = sorted(rows, key=lambda item: int(item.get("ordinal_position", 0)))
            source_schema = [item["column_name"] for item in sorted_rows]
            column_details = [
                {
                    "name": item["column_name"],
                    "data_type": item.get("data_type"),
                    "nullable": (item.get("is_nullable", "YES").upper() == "YES"),
                    "metadata": {
                        "source_data_type": item.get("data_type"),
                        "is_primary_key": str(item["column_name"] in pk_lookup.get((schema, table), set())).lower(),
                    },
                }
                for item in sorted_rows
            ]
            configured_ids = _normalize_list(config.db_details.get("id_columns"))
            discovered_ids = [col for col in source_schema if col in pk_lookup.get((schema, table), set())]
            id_columns = configured_ids or discovered_ids
            row_count = self._compute_row_count(schema, table, options) if self.context.compute_row_count else None
            table_rows.append(
                TableMetadata(
                    config=config,
                    full_table_name=f"{schema}.{table}",
                    table_name=table,
                    source_schema=source_schema,
                    column_details=column_details,
                    id_columns=id_columns,
                    partition_cols=_normalize_list(config.db_details.get("partition_cols")),
                    ct_enabled=ct_enabled,
                    db_name=config.db_details.get("db_name"),
                    entity_name=config.table_name,
                    table_row_count=row_count,
                )
            )
        return table_rows

    def _build_jdbc_options(self, config: DataSourceConfig) -> Dict[str, Any]:
        details = config.db_details
        password_key = details.get("password_key")
        password = self.secret_provider.get(password_key, None) if password_key else details.get("password")
        url = self._jdbc_url(details)
        return {
            "url": url,
            "driver": self.DRIVER_MAP[self.source_type],
            "user": details.get("user_name"),
            "password": password,
            "fetchsize": "10000",
        }

    def _jdbc_url(self, details: Dict[str, Any]) -> str:
        host = details.get("db_host")
        database = details.get("db_name")
        port = details.get("db_port")
        if self.source_type == "SQLSERVER":
            return f"jdbc:sqlserver://{host}:{port};databaseName={database}"
        if self.source_type == "POSTGRESQL":
            return f"jdbc:postgresql://{host}:{port}/{database}"
        if self.source_type == "MARIADB":
            return f"jdbc:mariadb://{host}:{port}/{database}"
        raise ValueError(f"Unsupported JDBC source {self.source_type}")

    def _fetch_metadata_rows(self, options: Dict[str, Any], config: DataSourceConfig, query_type: str) -> List[Dict[str, Any]]:
        sql = self.DIALECT[self.source_type][query_type]
        schemas = _normalize_list(config.db_details.get("table_schema"))
        if schemas:
            placeholder = ",".join(f"'{schema}'" for schema in schemas)
            column_ref = self._schema_column_reference(query_type, sql)
            condition = f"{column_ref} IN ({placeholder})"
            sql = f"{sql} AND {condition}" if "WHERE" in sql.upper() else f"{sql} WHERE {condition}"
        df = (
            self.spark.read.format("jdbc")
            .options(**options)
            .option("dbtable", f"({sql}) as metadata_{query_type}")
            .load()
        )
        return [row.asDict(True) for row in df.collect()]

    def _schema_column_reference(self, query_type: str, sql: str) -> str:
        if query_type == "columns":
            return "table_schema"
        if "ku.table_schema" in sql:
            return "ku.table_schema"
        if "kcu.table_schema" in sql:
            return "kcu.table_schema"
        return "table_schema"

    def _build_pk_lookup(self, pk_rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], set]:
        lookup: Dict[Tuple[str, str], set] = {}
        for row in pk_rows:
            schema = row["table_schema"]
            table = row["table_name"]
            column = row["column_name"]
            lookup.setdefault((schema, table), set()).add(column)
        return lookup

    def _compute_row_count(self, schema: str, table: str, options: Dict[str, Any]) -> Optional[int]:
        qualifier = self.DIALECT[self.source_type]["qualifier"](schema, table)
        query = f"(SELECT COUNT(1) AS total_count FROM {qualifier}) as row_count"
        df = self.spark.read.format("jdbc").options(**options).option("dbtable", query).load()
        result = df.collect()
        return int(result[0]["total_count"]) if result else None


# ---------------------------- File & Blob Collector -------------------------
class FileStorageCollector(BaseCollector):
    def __init__(self, context: CollectorContext, source_type: str) -> None:
        super().__init__(context)
        self.source_type = source_type

    def _collect_impl(self, config: DataSourceConfig) -> List[TableMetadata]:
        details = config.db_details
        storage_path = self._build_storage_path(details)
        file_format = details.get("file_extension", "csv")
        options = details.get("file_options", {})
        df = self.spark.read.format(file_format).options(**options).load(storage_path).limit(0)
        schema = df.schema
        column_details = [
            {
                "name": field.name,
                "data_type": field.dataType.simpleString(),
                "nullable": field.nullable,
                "metadata": {"source_data_type": field.dataType.simpleString()},
            }
            for field in schema.fields
        ]
        file_stats = self._gather_file_stats(storage_path)
        table_name = config.table_name or (details.get("folder_path") or storage_path.rstrip("/").split("/")[-1])
        metadata = TableMetadata(
            config=config,
            full_table_name=storage_path,
            table_name=table_name,
            source_schema=[field.name for field in schema.fields],
            column_details=column_details,
            id_columns=_normalize_list(details.get("id_columns")),
            partition_cols=_normalize_list(details.get("partition_cols")),
            ct_enabled=int(details.get("is_ct_enabled", False)),
            db_name=details.get("storage_name"),
            entity_name=config.table_name,
            file_size_bytes=file_stats.get("size"),
            file_last_modified=file_stats.get("last_modified"),
            sample_file_paths=file_stats.get("sample_paths"),
        )
        return [metadata]

    def _build_storage_path(self, details: Dict[str, Any]) -> str:
        storage_name = details.get("storage_name")
        container = details.get("container_name")
        folder_path = (details.get("folder_path") or "").lstrip("/")
        protocol = "abfss" if "ABFSS" in self.source_type else "wasbs"
        if details.get("storage_access_key"):
            endpoint = "dfs.core.windows.net" if protocol == "abfss" else "blob.core.windows.net"
            conf_key = f"fs.azure.account.key.{storage_name}.{endpoint}"
            self.spark.conf.set(conf_key, details["storage_access_key"])
        if protocol == "abfss":
            return f"abfss://{container}@{storage_name}.dfs.core.windows.net/{folder_path}"
        return f"wasbs://{container}@{storage_name}.blob.core.windows.net/{folder_path}"

    def _gather_file_stats(self, path: str) -> Dict[str, Any]:
        if not self.fs_client:
            return {"size": None, "last_modified": None, "sample_paths": []}
        try:
            entries = self.fs_client.list(path)
        except Exception:
            self.logger.warning("Failed to list storage path %s", path, exc_info=True)
            return {"size": None, "last_modified": None, "sample_paths": []}
        if not entries:
            return {"size": None, "last_modified": None, "sample_paths": []}
        sorted_entries = sorted(entries, key=lambda item: item.get("modification_time", 0), reverse=True)
        total_size = sum(item.get("size", 0) for item in entries)
        latest_entry = sorted_entries[0]
        last_modified = datetime.fromtimestamp(latest_entry.get("modification_time", 0) / 1000, tz=timezone.utc)
        sample_paths = [entry["path"] for entry in sorted_entries[: self.context.sample_file_limit]]
        return {"size": total_size, "last_modified": last_modified, "sample_paths": sample_paths}


# ----------------------------- Cassandra Collector -------------------------
class CassandraMetadataCollector(BaseCollector):
    def _collect_impl(self, config: DataSourceConfig) -> List[TableMetadata]:
        details = config.db_details
        keyspace = details.get("keyspace_name")
        table = config.table_name or details.get("table_name")
        if not keyspace or not table:
            raise ValueError("Cassandra config must include keyspace_name and table_name")
        read_options = {
            "table": table,
            "keyspace": keyspace,
        }
        bundle_path = details.get("secure_connect_bundle_path")
        if bundle_path:
            self.spark.conf.set("spark.cassandra.connection.config.profile.path", bundle_path)
        username = details.get("user_name")
        password_key = details.get("password_key")
        if username:
            read_options["spark.cassandra.auth.username"] = username
        if password_key and self.secret_provider:
            read_options["spark.cassandra.auth.password"] = self.secret_provider.get(password_key)
        df = (
            self.spark.read.format("org.apache.spark.sql.cassandra")
            .options(**read_options)
            .load()
            .limit(0)
        )
        schema = df.schema
        column_details = [
            {
                "name": field.name,
                "data_type": field.dataType.simpleString(),
                "nullable": field.nullable,
                "metadata": {"source_data_type": field.dataType.simpleString()},
            }
            for field in schema.fields
        ]
        metadata = TableMetadata(
            config=config,
            full_table_name=f"{keyspace}.{table}",
            table_name=table,
            source_schema=[field.name for field in schema.fields],
            column_details=column_details,
            id_columns=_normalize_list(details.get("id_columns")),
            partition_cols=_normalize_list(details.get("partition_cols")),
            ct_enabled=int(details.get("is_ct_enabled", False)),
            db_name=keyspace,
            entity_name=config.table_name,
        )
        return [metadata]


# ------------------------------ REST API Collector -------------------------
class RestApiMetadataCollector(BaseCollector):
    def _collect_impl(self, config: DataSourceConfig) -> List[TableMetadata]:
        import requests  # pragma: no cover - heavy dependency

        details = config.db_details
        api_url = details.get("api_url")
        api_method = (details.get("api_method") or "get").lower()
        headers: Dict[str, str] = {}
        api_key_ref = details.get("api_parameter_id")
        if api_key_ref:
            headers["Authorization"] = self.secret_provider.get(api_key_ref)
        response = requests.request(api_method, api_url, headers=headers, timeout=60)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            payload = payload.get("data") or payload.get("items") or [payload]
        if not payload:
            raise ValueError(f"API {config.id} returned no data")
        first_row = payload[0]
        columns = details.get("select_exprs") or list(first_row.keys())
        parsed_columns = self._parse_columns(columns, first_row)
        metadata = TableMetadata(
            config=config,
            full_table_name=api_url,
            table_name=config.table_name or details.get("entity_name") or "api_payload",
            source_schema=[col["name"] for col in parsed_columns],
            column_details=[
                {
                    "name": col["name"],
                    "data_type": col.get("data_type", "string"),
                    "nullable": True,
                    "metadata": {"source": "REST_API"},
                }
                for col in parsed_columns
            ],
            id_columns=_normalize_list(details.get("id_columns")),
            partition_cols=[],
            ct_enabled=int(details.get("is_ct_enabled", False)),
            db_name=config.catalog_name,
            entity_name=config.table_name,
            table_row_count=len(payload) if self.context.compute_row_count else None,
        )
        return [metadata]

    def _parse_columns(self, select_exprs: Sequence[Any], sample_row: Dict[str, Any]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        if select_exprs and isinstance(select_exprs[0], str):
            for expr in select_exprs:
                alias = expr.split(" AS ")[-1].strip().strip("[]")
                parsed.append({"name": alias, "data_type": "string"})
        else:
            for key, value in sample_row.items():
                dtype = type(value).__name__
                parsed.append({"name": key, "data_type": dtype})
        return parsed


# ---------------------------------------------------------------------------
#  Row dedupe helpers
# ---------------------------------------------------------------------------
def dedupe_registry_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, int] = {}
    for row in rows:
        identifier = row["id"]
        count = seen.get(identifier, 0)
        if count:
            suffix = to_snake_case(row.get("catalog_name", "duplicate"))
            row["table_name"] = f"{suffix}_{row['table_name']}_{count}"
            row["id"] = f"{row['source_id']}_{row['table_name']}"
        seen[identifier] = count + 1
    return rows


def dedupe_registry_df(df: DataFrame) -> DataFrame:
    if Window is None:
        return df
    window = Window.partitionBy("id").orderBy("catalog_name", "table_name")
    renamed = df.withColumn("dup_rank", F.row_number().over(window))
    adjusted = renamed.withColumn(
        "table_name",
        F.when(
            F.col("dup_rank") > 1,
            F.concat_ws("_", F.col("catalog_name"), F.col("table_name")),
        ).otherwise(F.col("table_name")),
    ).withColumn("id", F.concat_ws("_", F.col("source_id"), F.col("table_name"))).drop("dup_rank")
    return adjusted.dropDuplicates(["id"])


# ---------------------------------------------------------------------------
#  Summary writer & orchestrator
# ---------------------------------------------------------------------------
class SummaryWriter:
    def __init__(self, spark: SparkSession, table_name: str = DEFAULT_SUMMARY_TABLE) -> None:
        self.spark = spark
        self.table_name = table_name

    def write(self, rows: List[Tuple[str, str, Optional[str]]]) -> None:
        if not rows:
            return
        schema = T.StructType(
            [
                T.StructField("source_id", T.StringType(), False),
                T.StructField("status", T.StringType(), False),
                T.StructField("error_message", T.StringType(), True),
            ]
        )
        df = self.spark.createDataFrame(rows, schema)
        write_table(df, self.table_name, partition_cols=["status"], cdc_check=False, source_delete=False)


class MetadataCollectorOrchestrator:
    def __init__(
        self,
        context: CollectorContext,
        config_repository: ConfigRepository,
        collector_factory: CollectorFactory,
        summary_writer: SummaryWriter,
        registry_table: str = DEFAULT_REGISTRY_TABLE,
        batch_size: int = 10,
        max_workers: int = 5,
    ) -> None:
        self.context = context
        self.config_repository = config_repository
        self.collector_factory = collector_factory
        self.summary_writer = summary_writer
        self.registry_table = registry_table
        self.batch_size = batch_size
        self.max_workers = max(1, max_workers)
        self.logger = _ensure_logger()

    def run(self) -> None:
        configs = self.config_repository.load()
        self.logger.info("Loaded %d source configurations", len(configs))
        registry_rows: List[Dict[str, Any]] = []
        summary_rows: List[Tuple[str, str, Optional[str]]] = []
        for batch in chunked(configs, self.batch_size):
            outputs = self._collect_batch(batch)
            for output in outputs:
                summary_rows.append(output.summary)
                if output.rows:
                    registry_rows.extend([row.to_row() for row in output.rows])
        if registry_rows:
            if REGISTRY_SCHEMA is None:
                raise RuntimeError("PySpark is required to build the registry DataFrame")
            deduped = dedupe_registry_rows(registry_rows)
            spark_df = self.context.spark.createDataFrame(deduped, schema=REGISTRY_SCHEMA)
            final_df = dedupe_registry_df(spark_df)
            write_table(
                final_df,
                self.registry_table,
                partition_cols=["source_id"],
                cdc_check=True,
                source_delete=True,
            )
            self.logger.info("Wrote %d rows to %s", final_df.count(), self.registry_table)
        else:
            self.logger.warning("No metadata collected; registry table not updated")
        self.summary_writer.write(summary_rows)

    def _collect_batch(self, batch: Sequence[DataSourceConfig]) -> List[CollectorOutput]:
        if not batch:
            return []
        outputs: List[CollectorOutput] = []
        max_workers = min(self.max_workers, len(batch))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_config = {
                executor.submit(self._collect_single, config): config for config in batch
            }
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                try:
                    outputs.append(future.result())
                except Exception as exc:  # pragma: no cover - defensive
                    outputs.append(CollectorOutput([], (config.id, "Failure", str(exc))))
        return outputs

    def _collect_single(self, config: DataSourceConfig) -> CollectorOutput:
        collector = self.collector_factory.get(config.data_source_type)
        return collector.collect(config)


# ---------------------------------------------------------------------------
#  Public entry point
# ---------------------------------------------------------------------------
def run_job(
    spark: SparkSession,
    secret_provider: SecretProvider,
    filesystem_client: Optional[FileSystemClient] = None,
    compute_row_count: bool = False,
    full_load: bool = False,
    include_inactive: bool = False,
    require_metadata_enabled: bool = False,
    summary_table: str = DEFAULT_SUMMARY_TABLE,
    registry_table: str = DEFAULT_REGISTRY_TABLE,
    batch_size: int = 10,
    max_workers: int = 5,
) -> None:
    context = CollectorContext(
        spark=spark,
        secret_provider=secret_provider,
        filesystem_client=filesystem_client,
        compute_row_count=compute_row_count,
    )
    repository = ConfigRepository(
        spark,
        include_inactive=include_inactive or full_load,
        require_metadata_enabled=require_metadata_enabled,
    )
    factory = CollectorFactory(context)
    summary_writer = SummaryWriter(spark, summary_table)
    orchestrator = MetadataCollectorOrchestrator(
        context,
        repository,
        factory,
        summary_writer,
        registry_table=registry_table,
        batch_size=batch_size,
        max_workers=max_workers,
    )
    orchestrator.run()


__all__ = [
    "run_job",
    "CollectorContext",
    "ConfigRepository",
    "CollectorFactory",
    "InclusionEvaluator",
    "dedupe_registry_rows",
    "to_snake_case",
    "to_snake_case_list",
]
