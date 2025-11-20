"""
Data quality utilities (row counts, type checks).
"""

from __future__ import annotations

from dataclasses import dataclass

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
        source_df: DataFrame,
        target_df: DataFrame,
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
