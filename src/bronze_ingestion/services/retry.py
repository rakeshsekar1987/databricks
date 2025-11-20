"""
Retry utilities with exponential backoff per-table.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from ..logging_utils import StructuredLogger
from ..metadata.models import RetryPolicy

T = TypeVar("T")


@dataclass
class RetryExecutor:
    policy: RetryPolicy
    logger: StructuredLogger
    table_name: str

    def run(self, func: Callable[[], T]) -> T:
        attempt = 0
        backoff = self.policy.initial_backoff_seconds
        while True:
            try:
                return func()
            except Exception as exc:  # pragma: no cover - runtime logic
                attempt += 1
                if attempt >= self.policy.attempts:
                    self.logger.error(
                        "retry.exhausted",
                        {"table": self.table_name, "attempt": attempt, "error": str(exc)},
                    )
                    raise
                jitter = random.uniform(0, backoff)
                self.logger.warning(
                    "retry.backoff",
                    {"table": self.table_name, "attempt": attempt, "sleep_seconds": backoff + jitter},
                )
                time.sleep(backoff + jitter)
                backoff *= self.policy.backoff_multiplier
