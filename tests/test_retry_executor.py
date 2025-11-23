import random

import pytest

from bronze_ingestion.logging_utils import StructuredLogger
from bronze_ingestion.metadata.models import RetryPolicy
from bronze_ingestion.services.retry import RetryExecutor


def test_retry_executor_succeeds_after_retry(monkeypatch):
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("transient")
        return "ok"

    # Avoid random jitter for deterministic tests
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)

    executor = RetryExecutor(
        policy=RetryPolicy(attempts=3, initial_backoff_seconds=0),
        logger=StructuredLogger("test"),
        table_name="sample",
    )

    result = executor.run(flaky)
    assert result == "ok"
    assert attempts["count"] == 2


def test_retry_executor_exhausts_attempts(monkeypatch):
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    executor = RetryExecutor(
        policy=RetryPolicy(attempts=2, initial_backoff_seconds=0),
        logger=StructuredLogger("test"),
        table_name="sample",
    )

    def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        executor.run(always_fail)
