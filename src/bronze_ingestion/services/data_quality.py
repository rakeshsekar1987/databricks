"""
Data quality utilities (row counts, type checks).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyspark.sql import DataFrame

from ..exceptions import DataQualityError
from ..logging_utils import StructuredLogger


@dataclass(frozen=True)
class DataQualityResult:
    passed: bool
    expected_count: int
    actual_count: int
    tolerance_percent: float


class DataQualityService:
    def __init__(self, logger: StructuredLogger):
        self._logger = logger

    def validate_row_counts(
        self,
        source_df: "DataFrame",
        target_df: "DataFrame",
        tolerance_percent: float = 1.0,
    ) -> DataQualityResult:
        expected = source_df.count()
        actual = target_df.count()
        difference = abs(expected - actual)
        allowed_difference = max(1, int(expected * (tolerance_percent / 100)))

        passed = difference <= allowed_difference
        result = DataQualityResult(
            passed=passed,
            expected_count=expected,
            actual_count=actual,
            tolerance_percent=tolerance_percent,
        )

        payload = {
            "expected": expected,
            "actual": actual,
            "tolerance_percent": tolerance_percent,
            "passed": passed,
        }
        if passed:
            self._logger.info("dq.rowcount.passed", payload)
        else:
            self._logger.error("dq.rowcount.failed", payload)
            raise DataQualityError(f"Row count validation failed: {payload}")

        return result

    def validate_schema_alignment(
        self,
        source_df: "DataFrame",
        target_df: "DataFrame",
        allow_additive_only: bool = True,
    ) -> None:
        source_schema = {field.name: field.dataType.simpleString() for field in source_df.schema.fields}
        target_schema = {field.name: field.dataType.simpleString() for field in target_df.schema.fields}
        violations = []

        for column, dtype in source_schema.items():
            target_dtype = target_schema.get(column)
            if not target_dtype:
                continue  # new column - handled by schema evolution service
            if target_dtype != dtype:
                violations.append(
                    {
                        "column": column,
                        "source_dtype": dtype,
                        "target_dtype": target_dtype,
                    }
                )

        if allow_additive_only:
            for column in target_schema:
                if column not in source_schema:
                    violations.append({"column": column, "issue": "missing_in_source"})

        if violations:
            self._logger.warning(
                "dq.schema.mismatch",
                {"violations": violations[:10], "count": len(violations)},
            )
            # Log only; do not raise unless critical
