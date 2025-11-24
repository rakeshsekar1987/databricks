# Databricks notebook source
# MAGIC %run ../../Utils/DPCommonFunctions

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import reduce
from operator import and_, or_
from typing import Any, Callable, Dict, List, Optional, Sequence
from uuid import uuid4

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.column import Column
from pyspark.sql.functions import (
    broadcast,
    col,
    collect_list,
    collect_set,
    expr,
    lead,
    lit,
    lower,
    row_number,
    struct,
    sum as f_sum,
)
from pyspark.sql.window import Window

logger = logging.getLogger("silver_nxt_pipeline")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

dbutils.widgets.text("full_load", "True", "Full Load?")
dbutils.widgets.text("job_run_id", "", "Job Run ID")
dbutils.widgets.text("max_workers", "5", "Max Workers")
full_load = eval(dbutils.widgets.get("full_load"))
max_workers = int(dbutils.widgets.get("max_workers"))
run_id = dbutils.widgets.get("job_run_id")
if not run_id:
    run_id = str(uuid4())
print("The run ID : " + run_id)

DEFAULT_DROP_COLUMNS = ["idp_id", "idp_cdc_hash", "idp_created_date"]


def configure_spark_for_ingestion(
    spark_session: SparkSession, extra_conf: Optional[Dict[str, Any]] = None
) -> None:
    default_shuffle = max(spark_session.sparkContext.defaultParallelism * 2, 64)
    base_conf = {
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.sql.adaptive.skewJoin.enabled": "true",
        "spark.sql.optimizer.dynamicPartitionPruning": "true",
        "spark.sql.shuffle.partitions": default_shuffle,
        "spark.sql.execution.arrow.maxRecordsPerBatch": "500000",
        "spark.databricks.optimizer.autoBroadcastJoinThreshold": "67108864",
        "spark.sql.autoBroadcastJoinThreshold": "67108864",
        "spark.databricks.delta.optimizeWrite.enabled": "true",
        "spark.databricks.delta.autoCompact.enabled": "true",
    }
    final_conf = {**base_conf, **(extra_conf or {})}
    for key, value in final_conf.items():
        spark_session.conf.set(key, value)


configure_spark_for_ingestion(spark)


class FilterBuilder:
    """Converts configuration-driven filter definitions into Spark Column expressions."""

    @staticmethod
    def build(filters: Optional[Sequence[Any]]) -> Optional[Column]:
        if not filters:
            return None
        expressions: List[Column] = []
        for item in filters:
            if isinstance(item, str):
                expressions.append(expr(item))
                continue
            if isinstance(item, dict):
                for column_name, value in item.items():
                    expressions.append(FilterBuilder._parse_condition(column_name, value))
                continue
            raise ValueError(f"Unsupported filter definition: {item}")
        return reduce(and_, expressions) if expressions else None

    @staticmethod
    def _parse_condition(column_name: str, raw_value: Any) -> Column:
        column_ref = col(column_name)
        if isinstance(raw_value, Column):
            return raw_value
        if raw_value is None:
            return column_ref.isNull()
        if isinstance(raw_value, bool):
            return column_ref == lit(raw_value)
        if isinstance(raw_value, (int, float)):
            return column_ref == lit(raw_value)
        if isinstance(raw_value, (list, tuple, set)):
            values = [FilterBuilder._coerce_literal(v) for v in raw_value]
            return column_ref.isin(*values)
        if isinstance(raw_value, str):
            value = raw_value.strip()
            upper_value = value.upper()
            if upper_value == "IS NOT NULL":
                return column_ref.isNotNull()
            if upper_value == "IS NULL":
                return column_ref.isNull()
            if upper_value.startswith("IN (") and value.endswith(")"):
                payload = value[value.find("(") + 1 : -1]
                tokens = [
                    FilterBuilder._coerce_literal(FilterBuilder._clean_literal(token))
                    for token in payload.split(",")
                ]
                return column_ref.isin(*tokens)
            for operator in (">=", "<=", "!=", "<>", ">", "<"):
                if value.startswith(operator):
                    operand = FilterBuilder._coerce_literal(
                        FilterBuilder._clean_literal(value[len(operator) :])
                    )
                    return FilterBuilder._apply_operator(column_ref, operator, lit(operand))
            literal_value = FilterBuilder._coerce_literal(FilterBuilder._clean_literal(value))
            return column_ref == lit(literal_value)
        return column_ref == lit(raw_value)

    @staticmethod
    def _apply_operator(column_ref: Column, operator: str, literal_value: Column) -> Column:
        if operator == ">=":
            return column_ref >= literal_value
        if operator == "<=":
            return column_ref <= literal_value
        if operator == ">":
            return column_ref > literal_value
        if operator == "<":
            return column_ref < literal_value
        if operator in ("!=", "<>"):
            return column_ref != literal_value
        raise ValueError(f"Unsupported operator {operator}")

    @staticmethod
    def _clean_literal(value: str) -> str:
        trimmed = value.strip()
        if (trimmed.startswith("'") and trimmed.endswith("'")) or (
            trimmed.startswith('"') and trimmed.endswith('"')
        ):
            return trimmed[1:-1]
        return trimmed

    @staticmethod
    def _coerce_literal(value: Any) -> Any:
        if isinstance(value, str):
            lower_value = value.lower()
            if lower_value == "true":
                return True
            if lower_value == "false":
                return False
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
        return value


class ColumnMutationApplier:
    """Applies add/update column instructions expressed as dictionaries."""

    @staticmethod
    def apply(df: DataFrame, mutations: Optional[Sequence[Dict[str, Any]]]) -> DataFrame:
        for mutation in mutations or []:
            for name, expression in mutation.items():
                df = df.withColumn(name, ColumnMutationApplier._as_column(expression))
        return df

    @staticmethod
    def _as_column(expression: Any) -> Column:
        if isinstance(expression, Column):
            return expression
        if isinstance(expression, dict):
            if "sql" in expression:
                return expr(expression["sql"])
            if "expression" in expression:
                return expr(expression["expression"])
            if "literal" in expression:
                return lit(expression["literal"])
            if "value" in expression:
                return lit(expression["value"])
            if "column" in expression:
                return col(expression["column"])
        if isinstance(expression, (int, float, bool)):
            return lit(expression)
        if expression is None:
            return lit(None)
        return expr(str(expression))


class JoinConditionBuilder:
    """Builds arbitrary join expressions from flexible configuration payloads."""

    LOGICAL_OPERATORS = {
        "AND": and_,
        "OR": or_,
    }

    @classmethod
    def build(
        cls,
        condition: Any,
        *,
        left_df: DataFrame,
        right_df: DataFrame,
    ) -> Optional[Column]:
        if condition is None:
            return None
        if isinstance(condition, Column):
            return condition
        if isinstance(condition, str):
            return expr(condition)
        if isinstance(condition, list):
            expressions: List[Column] = []
            for entry in condition:
                if isinstance(entry, str):
                    expressions.append(cls._column_match(left_df, right_df, entry))
                else:
                    built = cls.build(entry, left_df=left_df, right_df=right_df)
                    if built is not None:
                        expressions.append(built)
            return cls._combine(expressions, and_)
        if isinstance(condition, dict):
            if "sql" in condition or "expression" in condition:
                return expr(condition.get("sql") or condition.get("expression"))
            if "conditions" in condition:
                logical_operator = condition.get("logical_operator", "AND").upper()
                combinator = cls.LOGICAL_OPERATORS.get(logical_operator, and_)
                nested = [
                    cls.build(item, left_df=left_df, right_df=right_df)
                    for item in condition.get("conditions", [])
                ]
                return cls._combine(nested, combinator)
            left_expression = condition.get("left") or condition.get("left_column")
            right_expression = condition.get("right") or condition.get("right_column")
            operator_symbol = (condition.get("operator") or "=").upper()
            null_safe = bool(condition.get("null_safe", False))
            left_column = cls._operand_to_column(left_expression, left_df, right_df)
            right_column = cls._operand_to_column(right_expression, left_df, right_df)
            return cls._apply_operator(
                left_column,
                right_column,
                operator_symbol,
                null_safe=null_safe,
                raw_right=condition.get("right"),
                options=condition,
                left_df=left_df,
                right_df=right_df,
            )
        return expr(str(condition))

    @staticmethod
    def _column_match(left_df: DataFrame, right_df: DataFrame, descriptor: Any) -> Column:
        if isinstance(descriptor, str):
            return left_df[descriptor] == right_df[descriptor]
        if isinstance(descriptor, dict):
            left_key = descriptor.get("left") or descriptor.get("column") or descriptor.get(
                "left_column"
            )
            right_key = descriptor.get("right") or descriptor.get("right_column") or left_key
            if left_key is None:
                raise ValueError(f"Invalid join column descriptor: {descriptor}")
            return left_df[left_key] == right_df[right_key]
        raise ValueError(f"Unsupported join column descriptor: {descriptor}")

    @staticmethod
    def _combine(
        expressions: List[Column], operator_func: Callable[[Column, Column], Column]
    ) -> Optional[Column]:
        filtered = [expr for expr in expressions if expr is not None]
        if not filtered:
            return None
        if len(filtered) == 1:
            return filtered[0]
        return reduce(operator_func, filtered)

    @staticmethod
    def _operand_to_column(
        operand: Any, left_df: DataFrame, right_df: DataFrame
    ) -> Optional[Column]:
        if operand is None:
            return None
        if isinstance(operand, Column):
            return operand
        if isinstance(operand, dict):
            if "sql" in operand or "expression" in operand:
                return expr(operand.get("sql") or operand.get("expression"))
            if "literal" in operand or "value" in operand:
                return lit(operand.get("literal", operand.get("value")))
            if "column" in operand:
                column_name = operand["column"]
                side = operand.get("side")
                if side:
                    target_df = left_df if side.lower() in {"left", "l"} else right_df
                    return target_df[column_name]
                return col(column_name)
        if isinstance(operand, (int, float, bool)):
            return lit(operand)
        if isinstance(operand, str):
            return expr(operand)
        return lit(operand)

    @staticmethod
    def _apply_operator(
        left_column: Optional[Column],
        right_column: Optional[Column],
        operator_symbol: str,
        *,
        null_safe: bool,
        raw_right: Any,
        options: Dict[str, Any],
        left_df: DataFrame,
        right_df: DataFrame,
    ) -> Column:
        if left_column is None:
            raise ValueError("Left operand is required for join conditions.")
        operator_symbol = operator_symbol.upper()

        if operator_symbol in {"=", "==", "EQ"}:
            if right_column is None:
                raise ValueError("Right operand is required for equality joins.")
            return left_column.eqNullSafe(right_column) if null_safe else left_column == right_column
        if operator_symbol in {"!=", "<>", "NE"}:
            if right_column is None:
                raise ValueError("Right operand is required for inequality joins.")
            return left_column != right_column
        if operator_symbol == ">":
            return left_column > right_column
        if operator_symbol == "<":
            return left_column < right_column
        if operator_symbol == ">=":
            return left_column >= right_column
        if operator_symbol == "<=":
            return left_column <= right_column
        if operator_symbol in {"<=>", "NULLSAFE"}:
            if right_column is None:
                raise ValueError("Right operand is required for null-safe joins.")
            return left_column.eqNullSafe(right_column)
        if operator_symbol == "BETWEEN":
            bounds = options.get("bounds") or raw_right
            lower, upper = JoinConditionBuilder._prepare_bounds(bounds, left_df, right_df)
            return left_column.between(lower, upper)
        if operator_symbol == "IN":
            values = JoinConditionBuilder._prepare_values(options.get("values") or raw_right)
            return left_column.isin(*values)
        if operator_symbol == "NOT IN":
            values = JoinConditionBuilder._prepare_values(options.get("values") or raw_right)
            return ~left_column.isin(*values)
        if operator_symbol in {"LIKE", "ILIKE", "RLIKE"}:
            pattern = JoinConditionBuilder._prepare_pattern(right_column, raw_right, operator_symbol)
            if operator_symbol == "LIKE":
                return left_column.like(pattern)
            if operator_symbol == "ILIKE":
                return left_column.ilike(pattern)
            return left_column.rlike(pattern)
        if operator_symbol == "IS NULL":
            return left_column.isNull()
        if operator_symbol == "IS NOT NULL":
            return left_column.isNotNull()

        raise ValueError(f"Unsupported join operator: {operator_symbol}")

    @staticmethod
    def _prepare_bounds(bounds: Any, left_df: DataFrame, right_df: DataFrame) -> Sequence[Any]:
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("Bounds for BETWEEN joins must be a two-element sequence.")
        lower = JoinConditionBuilder._operand_to_column(bounds[0], left_df, right_df)
        upper = JoinConditionBuilder._operand_to_column(bounds[1], left_df, right_df)
        if lower is None or upper is None:
            raise ValueError("Bounds for BETWEEN joins cannot be null.")
        return lower, upper

    @staticmethod
    def _prepare_values(values: Any) -> List[Any]:
        if values is None:
            raise ValueError("Values must be supplied for IN/NOT IN joins.")
        if isinstance(values, (list, tuple, set)):
            if not values:
                raise ValueError("Values for IN/NOT IN joins cannot be empty.")
            return list(values)
        return [values]

    @staticmethod
    def _prepare_pattern(
        right_column: Optional[Column], raw_right: Any, operator_symbol: str
    ) -> Any:
        if isinstance(right_column, Column):
            return right_column
        if raw_right is None:
            raise ValueError(f"A pattern must be supplied for {operator_symbol} joins.")
        return raw_right


def project_columns(df: DataFrame, columns: Sequence[str]) -> DataFrame:
    select_exprs = [col(column) if isinstance(column, str) else column for column in columns]
    return df.select(*select_exprs)


@dataclass
class RuntimeHooks:
    resolve_source: Callable[[str, str, str], str]
    resolve_target: Callable[[str], str]
    write_table: Callable[..., None]
    cdc_hash: Callable[[DataFrame], DataFrame]


class TablePlanBuilder:
    """Translates table configuration dictionaries into executable Spark plans."""

    def __init__(
        self,
        spark_session: SparkSession,
        table_resolver: Callable[[str, str, str], str],
        *,
        drop_columns: Optional[Sequence[str]] = None,
    ) -> None:
        self.spark = spark_session
        self.table_resolver = table_resolver
        self.drop_columns = list(drop_columns or DEFAULT_DROP_COLUMNS)

    def build(self, config: Dict[str, Any]) -> DataFrame:
        joined_df: Optional[DataFrame] = None
        for table_step in config["table_map"]:
            current_df = self._load_step(table_step)
            if joined_df is None:
                joined_df = ColumnMutationApplier.apply(current_df, table_step.get("update_columns"))
                continue
            join_type = table_step.get("join_type")
            if join_type == "union":
                joined_df = joined_df.unionByName(current_df, allowMissingColumns=True)
                joined_df = ColumnMutationApplier.apply(joined_df, table_step.get("update_columns"))
                continue
            joined_df = self._join(joined_df, current_df, table_step)
            joined_df = ColumnMutationApplier.apply(joined_df, table_step.get("update_columns"))
        if joined_df is None:
            raise ValueError(f"No table map defined for {config['table_name']}")
        joined_df = self._apply_aggregation(joined_df, config.get("aggregation"))
        joined_df = ColumnMutationApplier.apply(joined_df, config.get("update_columns"))
        order_by = config.get("order_by")
        if order_by:
            joined_df = joined_df.orderBy(*order_by)
        return joined_df

    def _load_step(self, table_step: Dict[str, Any]) -> DataFrame:
        table_name = self.table_resolver(
            table_step.get("source"), table_step.get("schema"), table_step["table"]
        )
        df = self.spark.table(table_name).alias(table_step["alias"])
        select_cols = table_step.get("select_cols")
        if select_cols:
            df = df.select(*select_cols)
        drop_targets = [
            column_name
            for column_name in self.drop_columns + table_step.get("drop_cols", [])
            if column_name in df.columns
        ]
        if drop_targets:
            df = df.drop(*drop_targets)
        filter_expr = FilterBuilder.build(table_step.get("filter_cols"))
        if filter_expr is not None:
            df = df.filter(filter_expr)
        df = ColumnMutationApplier.apply(df, table_step.get("add_columns"))
        if table_step.get("repartition"):
            df = df.repartition(table_step["repartition"])
        if table_step.get("cache", False):
            df = df.cache()
        return df

    @staticmethod
    def _build_join_expr(
        join_condition: Any, left_df: DataFrame, right_df: DataFrame
    ) -> Optional[Column]:
        return JoinConditionBuilder.build(
            join_condition, left_df=left_df, right_df=right_df
        )

    def _join(self, left_df: DataFrame, right_df: DataFrame, table_step: Dict[str, Any]) -> DataFrame:
        join_condition = table_step.get("join_condition")
        join_expr = (
            self._build_join_expr(join_condition, left_df, right_df)
            if join_condition is not None
            else None
        )
        join_type_value = table_step.get("join_type") or "inner"
        normalized_join_type = join_type_value.lower()

        if normalized_join_type in {"cross", "cross_join"}:
            if table_step.get("broadcast_hint"):
                right_df = broadcast(right_df)
            return left_df.crossJoin(right_df)

        if join_expr is None:
            raise ValueError(f"Join condition missing or invalid for {table_step['alias']}")

        if table_step.get("broadcast_hint"):
            right_df = broadcast(right_df)

        return left_df.join(right_df, join_expr, join_type_value)

    def _apply_aggregation(self, df: DataFrame, aggregation: Optional[Dict[str, Any]]) -> DataFrame:
        if not aggregation:
            return df
        group_by = aggregation.get("group_by") or []
        agg_exprs = aggregation.get("agg_exprs") or []
        if group_by and agg_exprs:
            df = df.groupBy(*group_by).agg(*agg_exprs)
        for post_step in aggregation.get("post_agg", []):
            df = ColumnMutationApplier.apply(df, [post_step])
        return df


@dataclass
class TableResult:
    table_name: str
    status: str
    duration: float
    error: Optional[str] = None


class TableTaskRunner:
    """Runs a single table configuration end-to-end."""

    def __init__(
        self,
        builder: TablePlanBuilder,
        hooks: RuntimeHooks,
        *,
        full_load: bool,
        writer_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.builder = builder
        self.hooks = hooks
        self.full_load = full_load
        self.writer_options = writer_options or {}

    def __call__(self, config: Dict[str, Any]) -> TableResult:
        table_name = config["table_name"]
        thread_id = threading.current_thread().name
        start_time = time.perf_counter()
        try:
            logger.info("[%s] Starting %s", thread_id, table_name)
            df = self.builder.build(config)
            df = project_columns(df, config["columns_to_keep"])
            dedup_subset = config.get("id_columns") or None
            df = df.dropDuplicates(dedup_subset) if dedup_subset else df.dropDuplicates()
            df = self.hooks.cdc_hash(df)
            target_table = self.hooks.resolve_target(table_name)
            writer_kwargs = dict(self.writer_options)
            if self.full_load:
                writer_kwargs["enable_cdf"] = True
            else:
                writer_kwargs.pop("enable_cdf", None)
            id_columns = None if self.full_load else config.get("id_columns")
            self.hooks.write_table(df, target_table, id_columns, **writer_kwargs)
            duration = time.perf_counter() - start_time
            logger.info("[%s] Completed %s in %.2fs", thread_id, table_name, duration)
            return TableResult(table_name=table_name, status="success", duration=duration)
        except Exception as exc:  # pylint: disable=broad-except
            duration = time.perf_counter() - start_time
            logger.exception("[%s] Error processing %s", thread_id, table_name)
            return TableResult(
                table_name=table_name,
                status="failed",
                duration=duration,
                error=str(exc),
            )


class ParallelTableOrchestrator:
    """Coordinates parallel execution of multiple table tasks."""

    def __init__(
        self,
        builder: TablePlanBuilder,
        hooks: RuntimeHooks,
        *,
        full_load: bool,
        max_workers: int,
        writer_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.builder = builder
        self.hooks = hooks
        self.full_load = full_load
        self.max_workers = max_workers
        self.writer_options = writer_options or {}

    def run(self, table_configs: Sequence[Dict[str, Any]]) -> List[TableResult]:
        runner = TableTaskRunner(
            self.builder,
            self.hooks,
            full_load=self.full_load,
            writer_options=self.writer_options,
        )
        results: List[TableResult] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_config = {executor.submit(runner, config): config for config in table_configs}
            for future in as_completed(future_to_config):
                results.append(future.result())
        return results

    @staticmethod
    def summarize(results: Sequence[TableResult]) -> Dict[str, Any]:
        failures = [result for result in results if result.status == "failed"]
        return {
            "total": len(results),
            "success": len(results) - len(failures),
            "failed": len(failures),
            "failures": failures,
        }

    @staticmethod
    def log_summary(results: Sequence[TableResult]) -> None:
        summary = ParallelTableOrchestrator.summarize(results)
        print("\n" + "=" * 80)
        print("PROCESSING SUMMARY")
        print("=" * 80)
        print(f"Total tables: {summary['total']}")
        print(f"Successful: {summary['success']}")
        print(f"Failed: {summary['failed']}")
        if summary["failed"]:
            print("\nFailed tables:")
            for failure in summary["failures"]:
                print(f"  - {failure.table_name}: {failure.error}")


table_configurations = [
    {
        "table_name": "invoice_tax",
        "table_map": [
            {
                "table": "tbl_invoice_items",
                "alias": "tii",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["invoice_item_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["invoice_item_id"],
            },
            {
                "table": "tbl_invoice_taxrequest_itemtaxes",
                "alias": "titrit",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "tii.invoice_item_id = titrit.invoice_item_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": [
                    "invoice_item_id",
                    "tax_request_item_tax_id",
                    "authority_name",
                    "tax_name",
                    "tax_rate",
                    "taxable_amount",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["invoice_item_id"],
            },
        ],
        "aggregation": {
            "group_by": ["tii.invoice_item_id"],
            "agg_exprs": [
                collect_list(
                    struct(
                        col("titrit.tax_request_item_tax_id").alias("tax_request_item_tax_id"),
                        col("titrit.authority_name").alias("authority_name"),
                        col("titrit.tax_name").alias("tax_name"),
                        col("titrit.tax_rate").alias("tax_rate"),
                        col("titrit.taxable_amount").alias("taxable_amount"),
                    )
                ).alias("tax"),
            ],
        },
        "order_by": ["invoice_item_id"],
        "id_columns": ["invoice_item_id"],
        "auto_generate_id": "False",
        "columns_to_keep": ["invoice_item_id", "tax"],
    },
    {
        "table_name": "invoice_discounts",
        "table_map": [
            {
                "table": "tbl_invoice_discounts",
                "alias": "tid",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "invoice_id",
                    "discount_id",
                    "discount_title",
                    "discount_value",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["invoice_id"],
            }
        ],
        "aggregation": {
            "group_by": ["tid.invoice_id"],
            "agg_exprs": [
                collect_list(
                    struct(
                        col("tid.discount_id").alias("discount_id"),
                        col("tid.discount_title").alias("discount_title"),
                        col("tid.discount_value").alias("discount_value"),
                    )
                ).alias("discounts"),
            ],
        },
        "order_by": ["invoice_id"],
        "id_columns": ["invoice_id"],
        "auto_generate_id": "False",
        "columns_to_keep": ["invoice_id", "discounts"],
    },
    {
        "table_name": "job_versions",
        "table_map": [
            {
                "table": "tbl_job_versions",
                "alias": "v",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "job_id",
                    "job_version_id",
                    "job_version",
                    "job_status",
                    "booked_date_time",
                    "retailer",
                    "brand",
                    "variety",
                    "promotion",
                    "weight",
                    "language_desc",
                    "plate_size_unit_id",
                    "priority",
                    "legacy_design_no",
                    "packaging_reference",
                    "order_type_id",
                    "job_range_id",
                    "project_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["job_id", "job_version_id"],
            },
            {
                "table": "job_status",
                "alias": "job_status",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.job_status = job_status.id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["id", "status"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [
                    {
                        "version_status": col("job_status.status"),
                    }
                ],
                "id_columns": [],
            },
            {
                "table": "tbl_projects",
                "alias": "p",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.project_id = p.project_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["project_id", "project_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_order_type",
                "alias": "tbl_order_type",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.order_type_id = tbl_order_type.id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["id", "name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [
                    {
                        "order_type": col("tbl_order_type.name"),
                    }
                ],
                "id_columns": [],
            },
            {
                "table": "tbl_plate_size_units",
                "alias": "tbl_plate_size_units",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.plate_size_unit_id = tbl_plate_size_units.unit_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["unit_id", "unit_desc", "unit_conversion_factor"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [
                    {
                        "plate_size_unit_description": col("tbl_plate_size_units.unit_desc"),
                    }
                ],
                "id_columns": [],
            },
            {
                "table": "tbl_job_ranges",
                "alias": "tbl_job_ranges",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.job_range_id = tbl_job_ranges.range_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["range_id", "range_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [
                    {
                        "ranger_name": col("tbl_job_ranges.range_name"),
                    }
                ],
                "id_columns": [],
            },
        ],
        "update_columns": [
            {
                "version_details": struct(
                    col("v.retailer").alias("retailer"),
                    col("v.brand").alias("brand"),
                    col("v.variety").alias("variety"),
                    col("v.promotion").alias("promotion"),
                    col("v.weight").alias("weight"),
                    col("v.language_desc").alias("language_desc"),
                    col("v.plate_size_unit_id").alias("plate_size_unit_id"),
                    col("v.priority").alias("priority"),
                    col("p.project_name").alias("project_name"),
                    col("v.legacy_design_no").alias("legacy_design_no"),
                    col("v.packaging_reference").alias("packaging_reference"),
                    col("v.order_type_id").alias("order_type_id"),
                    col("order_type").alias("order_type"),
                    col("v.job_range_id").alias("job_range_id"),
                    col("ranger_name").alias("ranger_name"),
                    col("plate_size_unit_description").alias("plate_size_unit_description"),
                    col("tbl_plate_size_units.unit_conversion_factor").alias(
                        "unit_conversion_factor"
                    ),
                ),
            }
        ],
        "order_by": ["v.job_id", "v.job_version_id", "v.job_version"],
        "id_columns": ["job_id", "job_version_id", "job_version"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "v.job_id",
            "v.job_version_id",
            "v.job_version",
            "version_status",
            "v.booked_date_time",
            "version_details",
        ],
    },
    {
        "table_name": "logins",
        "table_map": [
            {
                "table": "tbl_logins",
                "alias": "l",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["login_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["login_id"],
            },
            {
                "table": "tbl_login_profiles",
                "alias": "p",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "l.login_id = p.login_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": [
                    "login_id",
                    "profile_id",
                    "first_name",
                    "last_name",
                    "site_id",
                    "time_zone_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_sites",
                "alias": "s",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "p.site_id = s.site_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": ["site_id", "site_name", "company_legal_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_time_zones",
                "alias": "tz",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "p.time_zone_id = tz.time_zone_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": ["time_zone_id", "iana_time_zone_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
        ],
        "order_by": ["l.login_id"],
        "id_columns": ["login_id"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "l.login_id",
            "p.profile_id",
            "p.first_name",
            "p.last_name",
            "s.site_id",
            "s.site_name",
            "s.company_legal_name",
            "tz.iana_time_zone_id",
        ],
    },
    {
        "table_name": "job_contacts",
        "table_map": [
            {
                "table": "tbl_job_versions",
                "alias": "v",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["job_version_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["job_version_id"],
            },
            {
                "table": "tbl_job_contacts",
                "alias": "jc",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.job_version_id = jc.job_version_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": ["job_version_id", "customer_id", "primary_contact"],
                "filter_cols": [{"primary_contact": "true"}],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_customers",
                "alias": "c",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "jc.customer_id = c.customer_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": [
                    "customer_id",
                    "customer_name",
                    "customer_type",
                    "portfolio_group_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "customer_types",
                "alias": "ct",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "c.customer_type = ct.customer_type_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": ["customer_type_id", "customer_type_description"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_customer_portfolio_groups",
                "alias": "pg",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "c.portfolio_group_id = pg.portfolio_group_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": [
                    "portfolio_group_id",
                    "portfolio_group_name",
                    "simplified_group_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_customer_simplified_groups",
                "alias": "sp",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "pg.simplified_group_id = sp.simplified_group_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["simplified_group_id", "simplified_group_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
        ],
        "update_columns": [
            {
                "row_rank": row_number().over(
                    Window.partitionBy("v.job_version_id").orderBy(col("c.customer_id").desc())
                ),
            }
        ],
        "order_by": ["v.job_version_id", "c.customer_id", "row_rank"],
        "id_columns": ["job_version_id", "customer_id", "row_rank"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "v.job_version_id",
            "c.customer_id",
            "c.customer_name",
            "c.customer_type",
            "ct.customer_type_description",
            "pg.portfolio_group_name",
            "sp.simplified_group_name",
            "row_rank",
        ],
    },
    {
        "table_name": "item_patch",
        "table_map": [
            {
                "table": "tbl_job_items_patches",
                "alias": "jip",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "job_item_id",
                    "height",
                    "width",
                    "quantity",
                    "unit_price",
                    "apply_handling",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["job_item_id"],
            }
        ],
        "aggregation": {
            "group_by": ["job_item_id"],
            "agg_exprs": [
                f_sum(
                    ((col("height") / 2.54) / 10)
                    * ((col("width") / 2.54) / 10)
                    * col("quantity")
                ).alias("total_patch_area"),
                collect_set(col("unit_price")).alias("patch_unit_prices"),
                collect_list(
                    struct(
                        col("height").alias("height_original"),
                        col("width").alias("width_original"),
                        (col("height") / 2.54 / 10).alias("heigh_inches"),
                        (col("width") / 2.54 / 10).alias("width_inches"),
                        ((col("height") / 2.54 / 10) * (col("width") / 2.54 / 10)).alias(
                            "patch_area"
                        ),
                        col("quantity").alias("quantity"),
                        col("unit_price").alias("unit_price"),
                        col("apply_handling").alias("apply_handling"),
                    )
                ).alias("patch_details"),
            ],
        },
        "order_by": ["job_item_id"],
        "id_columns": ["job_item_id"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "job_item_id",
            "total_patch_area",
            "patch_unit_prices",
            "patch_details",
        ],
    },
    {
        "table_name": "item_merge",
        "table_map": [
            {
                "table": "tbl_job_versions",
                "alias": "v",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "job_id",
                    "job_version",
                    "job_version_id",
                    "job_status",
                    "booked_date_time",
                    "brand",
                    "variety",
                ],
                "filter_cols": [{"booked_date_time": ">='2024-01-01'"}],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["job_version_id"],
            },
            {
                "table": "tbl_job_stages",
                "alias": "s",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.job_version_id = s.job_version_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": ["job_version_id", "job_stage_id", "job_stage"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_job_items",
                "alias": "i",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "s.job_stage_id = i.job_stage_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": [
                    "job_stage_id",
                    "job_item_id",
                    "price_matrix_item_id",
                    "price_matrix_multiplier_id",
                    "job_item_status",
                    "job_item_description",
                    "quantity",
                    "cost",
                    "plate_type",
                    "item_due_date_time",
                    "item_due_reason",
                    "item_booked_date_time",
                    "item_kpi",
                    "item_kpi_duration",
                    "item_completed_date_time",
                    "target_deadline",
                    "currency_id",
                    "exchange_rate_value",
                    "account_manager_login_id",
                    "assigned_to",
                    "price_matrix_variant_item_id",
                    "item_order",
                    "created_by_invoice_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
        ],
        "order_by": ["v.job_version_id", "s.job_stage_id", "i.job_item_id"],
        "id_columns": ["job_version_id", "job_stage_id", "job_item_id"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "v.job_id",
            "v.job_version",
            "v.job_version_id",
            "v.job_status",
            "v.booked_date_time",
            "v.brand",
            "v.variety",
            "s.job_stage_id",
            "s.job_stage",
            "i.job_item_id",
            "i.price_matrix_item_id",
            "i.price_matrix_multiplier_id",
            "i.job_item_status",
            "i.job_item_description",
            "i.quantity",
            "i.cost",
            "i.plate_type",
            "i.item_due_date_time",
            "i.item_due_reason",
            "i.item_booked_date_time",
            "i.item_kpi",
            "i.item_kpi_duration",
            "i.item_completed_date_time",
            "i.target_deadline",
            "i.currency_id",
            "i.exchange_rate_value",
            "i.account_manager_login_id",
            "i.assigned_to",
            "i.price_matrix_variant_item_id",
            "i.item_order",
            "i.created_by_invoice_id",
        ],
    },
    {
        "table_name": "qcp_outcome",
        "table_map": [
            {
                "table": "qcp_outcome",
                "alias": "qcp",
                "source": "datascience",
                "schema": "bronze",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "JobTaskId",
                    "uuid",
                    "QcStep",
                    "decision",
                    "result",
                    "threshold",
                    "ModelConfidence",
                    "SampleQuality",
                    "timeofcall",
                    "calltype",
                    "message_sent",
                ],
                "update_columns": [
                    {
                        "job_task_id": col("qcp.JobTaskId"),
                    }
                ],
                "id_columns": [],
            },
        ],
        "aggregation": {
            "group_by": ["job_task_id"],
            "agg_exprs": [
                collect_list(
                    struct(
                        col("uuid").alias("uuid"),
                        col("QcStep").alias("qc_step"),
                        col("decision").alias("decision"),
                        col("result").alias("result"),
                        col("threshold").alias("threshold"),
                        col("ModelConfidence").alias("model_confidence"),
                        col("SampleQuality").alias("sample_quality"),
                        col("timeofcall").alias("time_of_call"),
                        col("calltype").alias("call_type"),
                        col("message_sent").alias("message_sent"),
                    )
                ).alias("qcp"),
            ],
        },
        "order_by": ["job_task_id"],
        "id_columns": ["job_task_id"],
        "auto_generate_id": "False",
        "columns_to_keep": ["job_task_id", "qcp"],
    },
    {
        "table_name": "stages",
        "table_map": [
            {
                "table": "tbl_job_versions",
                "alias": "v",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["job_id", "job_version_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["job_id", "job_version_id"],
            },
            {
                "table": "tbl_job_stages",
                "alias": "s",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "v.job_version_id = s.job_version_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": [
                    "job_version_id",
                    "job_stage_id",
                    "job_stage",
                    "creation_date_time",
                    "workflow_template_id",
                    "workflow_variant_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_job_stage_reason",
                "alias": "b",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "s.job_stage_id = b.stage_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": [
                    "stage_id",
                    "reason_id",
                    "reason_code",
                    "fault_of",
                    "added_by",
                    "found_on",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_job_stage_reason_categories",
                "alias": "cat",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "b.reason_id = cat.reason_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["reason_id", "category_id", "amend_type_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_job_stage_reason_faults",
                "alias": "faults",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "b.reason_id = faults.reason_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["reason_id", "task_history_at_fault", "person_at_fault_id"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "pma_fault_of",
                "alias": "pma_fault_of",
                "source": "masterdata",
                "schema": "silver",
                "join_condition": "b.fault_of = pma_fault_of.code",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["code", "fault_of"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_new_stage_reason_codes",
                "alias": "reason_codes",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "b.reason_code = reason_codes.reason_code_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": [
                    "reason_code_id",
                    "reason_code_desc",
                    "reason_code_requires_fault_code",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_new_stage_categories",
                "alias": "reason_categories",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "cat.category_id = reason_categories.category_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["category_id", "category_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
            {
                "table": "tbl_new_stage_amendtypes",
                "alias": "reason_amends",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "cat.amend_type_id = reason_amends.amend_type_id",
                "join_type": "left_outer",
                "drop_cols": [],
                "select_cols": ["amend_type_id", "amend_type_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
        ],
        "aggregation": {
            "group_by": [
                "v.job_id",
                "v.job_version_id",
                "s.job_stage_id",
                "s.job_stage",
                "s.creation_date_time",
                "s.workflow_template_id",
                "s.workflow_variant_id",
            ],
            "agg_exprs": [
                collect_list(
                    struct(
                        col("b.reason_id").alias("reason_id"),
                        col("b.reason_code").alias("reason_code_id"),
                        col("reason_codes.reason_code_desc").alias("reason_code"),
                        col("reason_codes.reason_code_requires_fault_code").alias(
                            "reason_code_requires_fault_code"
                        ),
                        col("b.fault_of").alias("fault_of_id"),
                        col("pma_fault_of.fault_of").alias("fault_of"),
                        col("b.added_by").alias("added_by"),
                        col("b.found_on").alias("found_on"),
                        col("cat.category_id").alias("category_id"),
                        col("reason_categories.category_name").alias("category_name"),
                        col("cat.amend_type_id").alias("amend_type_id"),
                        col("reason_amends.amend_type_name").alias("amend_type_name"),
                        col("faults.task_history_at_fault").alias("task_history_at_fault"),
                        col("faults.person_at_fault_id").alias("person_at_fault_id"),
                    )
                ).alias("stage_reasons"),
            ],
        },
        "order_by": ["v.job_id", "v.job_version_id", "s.job_stage_id"],
        "id_columns": ["job_id", "job_version_id", "job_stage_id"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "v.job_id",
            "v.job_version_id",
            "s.job_stage_id",
            "s.job_stage",
            "s.creation_date_time",
            "s.workflow_template_id",
            "s.workflow_variant_id",
            "stage_reasons",
        ],
    },
    {
        "table_name": "login_profiles_distinct",
        "table_map": [
            {
                "table": "tbl_login_profiles",
                "alias": "lp",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "login_id",
                    "ultipro_id",
                    "site_id",
                    "active_directory_id",
                    "idp_modified_date",
                ],
                "filter_cols": [{"ultipro_id": "IS NOT NULL"}],
                "add_columns": [
                    {
                        "tbl_login_profiles_idp_modified_date": col("idp_modified_date"),
                    }
                ],
                "update_columns": [],
                "id_columns": ["login_id"],
            }
        ],
        "update_columns": [
            {
                "rn_lp": row_number()
                .over(Window.partitionBy("ultipro_id").orderBy(col("idp_modified_date").desc()))
            }
        ],
        "order_by": ["ultipro_id"],
        "id_columns": ["login_id", "ultipro_id"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "login_id",
            "ultipro_id",
            "site_id",
            "active_directory_id",
            "tbl_login_profiles_idp_modified_date",
            "rn_lp",
        ],
    },
    {
        "table_name": "logins_distinct",
        "table_map": [
            {
                "table": "tbl_logins",
                "alias": "l",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["login_id", "email", "user_level", "idp_modified_date"],
                "filter_cols": [],
                "add_columns": [
                    {
                        "tbl_logins_idp_modified_date": col("idp_modified_date"),
                    }
                ],
                "update_columns": [],
                "id_columns": ["login_id"],
            }
        ],
        "update_columns": [
            {
                "rn_l": row_number()
                .over(Window.partitionBy("login_id").orderBy(col("idp_modified_date").desc()))
            }
        ],
        "order_by": ["login_id"],
        "id_columns": ["login_id"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "login_id",
            "email",
            "user_level",
            "tbl_logins_idp_modified_date",
            "rn_l",
        ],
    },
    {
        "table_name": "workfront_login_combined",
        "table_map": [
            {
                "table": "exported_users",
                "alias": "eu",
                "source": "workfront",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["id", "email_addr"],
                "filter_cols": [{"email_addr": "IS NOT NULL"}],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["id"],
            },
            {
                "table": "user_data",
                "alias": "ud",
                "source": "workfront",
                "schema": "silver",
                "join_condition": [],
                "join_type": "union",
                "drop_cols": [],
                "select_cols": ["id", "email_addr"],
                "filter_cols": [{"email_addr": "IS NOT NULL"}],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["id"],
            },
        ],
        "update_columns": [
            {
                "workfront_id": col("id"),
                "rn_wf": row_number()
                .over(Window.partitionBy(lower(col("email_addr"))).orderBy(col("workfront_id").desc())),
            }
        ],
        "order_by": ["workfront_id", "rn_wf"],
        "id_columns": ["workfront_id", "rn_wf"],
        "auto_generate_id": "False",
        "columns_to_keep": ["workfront_id", "email_addr", "rn_wf"],
    },
    {
        "table_name": "tech_colours",
        "table_map": [
            {
                "table": "tbl_job_tech_spec_colours",
                "alias": "a",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "job_tech_spec_id",
                    "colour_order",
                    "client_plate_colour_ref",
                    "new_colour",
                    "cust_carrier_id_no",
                    "mcg_colour_id",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["job_tech_spec_id"],
            },
            {
                "table": "tbl_mcg_colours",
                "alias": "b",
                "source": "mysgs",
                "schema": "silver",
                "join_condition": "a.mcg_colour_id = b.colour_id",
                "join_type": "inner",
                "drop_cols": [],
                "select_cols": ["colour_id", "colour_name"],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": [],
            },
        ],
        "aggregation": {
            "group_by": ["job_tech_spec_id"],
            "agg_exprs": [
                collect_list(
                    struct(
                        col("a.colour_order").alias("colour_order"),
                        col("a.client_plate_colour_ref").alias("client_plate_colour_ref"),
                        col("b.colour_name").alias("colour_name"),
                        col("a.new_colour").alias("new_colour"),
                        col("a.cust_carrier_id_no").alias("cust_carrier_id_no"),
                    )
                ).alias("colours"),
            ],
        },
        "order_by": ["job_tech_spec_id"],
        "id_columns": ["job_tech_spec_id"],
        "auto_generate_id": "False",
        "columns_to_keep": ["job_tech_spec_id", "colours"],
    },
    {
        "table_name": "profile_audit",
        "table_map": [
            {
                "table": "audit_category",
                "alias": "ac",
                "source": "pricematrix",
                "schema": "bronze",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": ["EntityId", "ProfileStatusId", "ModifiedDate"],
                "filter_cols": [{"ProfileStatusId": [5, 6]}],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["EntityId"],
            }
        ],
        "update_columns": [
            {
                "entity_id": col("ac.EntityId"),
                "profile_status_id": col("ac.ProfileStatusId"),
                "modified_date": col("ac.ModifiedDate"),
                "next_status": lead("ProfileStatusId").over(
                    Window.partitionBy("EntityId").orderBy("ModifiedDate")
                ),
                "next_modified": lead("ModifiedDate").over(
                    Window.partitionBy("EntityId").orderBy("ModifiedDate")
                ),
                "rn": row_number()
                .over(
                    Window.partitionBy("EntityId", "ProfileStatusId").orderBy("ModifiedDate")
                ),
            }
        ],
        "order_by": [],
        "id_columns": ["entity_id", "profile_status_id", "rn"],
        "auto_generate_id": "False",
        "columns_to_keep": [
            "entity_id",
            "profile_status_id",
            "modified_date",
            "next_status",
            "next_modified",
            "rn",
        ],
    },
    {
        "table_name": "price_profile_currency",
        "table_map": [
            {
                "table": "price_profile_item_currency",
                "alias": "ppic",
                "source": "pricematrix",
                "schema": "bronze",
                "join_condition": None,
                "join_type": None,
                "drop_cols": [],
                "select_cols": [
                    "PriceProfileItemId",
                    "Id",
                    "Cost",
                    "ExchangeRate",
                    "CurrencyId",
                    "CurrencyName",
                    "Symbol",
                    "Code",
                    "CreatedDate",
                    "CreatedBy",
                    "ModifiedDate",
                    "ModifiedBy",
                    "Active",
                    "ItemCurrencyNumber",
                ],
                "filter_cols": [],
                "add_columns": [],
                "update_columns": [],
                "id_columns": ["PriceProfileItemId"],
            }
        ],
        "aggregation": {
            "group_by": ["PriceProfileItemId"],
            "agg_exprs": [
                collect_set(
                    struct(
                        col("Id").alias("id"),
                        col("Cost").alias("cost"),
                        col("ExchangeRate").alias("exchange_rate"),
                        col("CurrencyId").alias("currency_id"),
                        col("CurrencyName").alias("currency_name"),
                        col("Symbol").alias("symbol"),
                        col("Code").alias("code"),
                        col("CreatedDate").alias("created_date"),
                        col("CreatedBy").alias("created_by"),
                        col("ModifiedDate").alias("modified_date"),
                        col("ModifiedBy").alias("modified_by"),
                        col("Active").alias("active"),
                        col("ItemCurrencyNumber").alias("item_currency_code"),
                    )
                ).alias("price_profile_currency_array"),
            ],
        },
        "update_columns": [
            {
                "price_profile_item_id": col("PriceProfileItemId"),
            }
        ],
        "order_by": ["price_profile_item_id"],
        "id_columns": ["price_profile_item_id"],
        "auto_generate_id": "False",
        "columns_to_keep": ["price_profile_item_id", "price_profile_currency_array"],
    },
]


runtime_hooks = RuntimeHooks(
    resolve_source=resolve_table_name,
    resolve_target=lambda table_name: resolve_table_name(
        Catalog.MYSGS.value, Schema.SILVER_NXT, table_name
    ),
    write_table=write_table,
    cdc_hash=lambda dataframe: cdc_hash(dataframe, convert_complex_to_json=True),
)

builder = TablePlanBuilder(
    spark,
    runtime_hooks.resolve_source,
    drop_columns=DEFAULT_DROP_COLUMNS,
)

orchestrator = ParallelTableOrchestrator(
    builder=builder,
    hooks=runtime_hooks,
    full_load=full_load,
    max_workers=max_workers,
    writer_options={"cdc_check": True, "source_delete": True},
)

print(f"Starting parallel processing with {max_workers} workers for {len(table_configurations)} tables")
results = orchestrator.run(table_configurations)
ParallelTableOrchestrator.log_summary(results)

failed_tables = [result for result in results if result.status == "failed"]
if failed_tables:
    dbutils.notebook.exit(f"PARTIAL_FAILURE: {len(failed_tables)} table(s) failed")
else:
    dbutils.notebook.exit(Constants.SUCCESS)
