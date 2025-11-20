"""
Structured logging utilities compatible with Azure Log Analytics.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredLogger:
    """
    Thin wrapper on top of the standard logging library that guarantees JSON payloads.
    Intended to be consumed by Azure Log Analytics and Databricks cluster logs.
    """

    def __init__(self, name: str = "bronze-ingestion", level: int = logging.INFO):
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        self._logger.setLevel(level)

    def _emit(self, level: int, event: str, payload: Optional[Dict[str, Any]] = None):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **(payload or {}),
        }
        self._logger.log(level, json.dumps(record))

    def info(self, event: str, payload: Optional[Dict[str, Any]] = None):
        self._emit(logging.INFO, event, payload)

    def warning(self, event: str, payload: Optional[Dict[str, Any]] = None):
        self._emit(logging.WARNING, event, payload)

    def error(self, event: str, payload: Optional[Dict[str, Any]] = None):
        self._emit(logging.ERROR, event, payload)

    def exception(self, event: str, payload: Optional[Dict[str, Any]] = None):
        combined_payload = {"level": "exception", **(payload or {})}
        self._emit(logging.ERROR, event, combined_payload)
