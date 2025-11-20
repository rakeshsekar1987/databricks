"""
Global constants and knobs for the Bronze ingestion framework.
"""

from __future__ import annotations

DEFAULT_PARALLELISM = 16
DEFAULT_JDBC_BATCH_SIZE = 10_000
DEFAULT_JDBC_FETCH_SIZE = 5_000
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 30
DEFAULT_CDF_RETENTION_DAYS = 7
DEFAULT_LOG_ANALYTICS_WORKSPACE = "log-analytics-workspace"
DEFAULT_EMAIL_RECIPIENTS: list[str] = []

SCHEMA_DRIFT_ALERT_SUBJECT = "[Bronze][SchemaDrift] {}"
FAILURE_ALERT_SUBJECT = "[Bronze][Failure] {}"

SUPPORTED_MODES = {"full", "incremental", "mixed"}
