"""
Structured logging utilities compatible with Azure Log Analytics.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests


class LogAnalyticsEmitter:
    def __init__(self, workspace_id: str, shared_key: str, log_type: str = "BronzeIngestion"):
        self._workspace_id = workspace_id
        self._shared_key = shared_key
        self._log_type = log_type

    @staticmethod
    def from_env() -> Optional["LogAnalyticsEmitter"]:
        workspace_id = os.environ.get("LOG_ANALYTICS_WORKSPACE_ID")
        shared_key = os.environ.get("LOG_ANALYTICS_SHARED_KEY")
        log_type = os.environ.get("LOG_ANALYTICS_LOG_TYPE", "BronzeIngestion")
        if workspace_id and shared_key:
            return LogAnalyticsEmitter(workspace_id, shared_key, log_type)
        return None

    def _build_signature(self, date: str, content_length: int) -> str:
        string_to_hash = f"POST\n{content_length}\napplication/json\nx-ms-date:{date}\n/api/logs"
        bytes_to_hash = bytes(string_to_hash, encoding="utf-8")
        decoded_key = base64.b64decode(self._shared_key)
        encoded_hash = base64.b64encode(
            hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()
        ).decode()
        return f"SharedKey {self._workspace_id}:{encoded_hash}"

    def send(self, record: Dict[str, Any]) -> None:
        body = json.dumps(record)
        rfc1123date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        signature = self._build_signature(rfc1123date, len(body))
        uri = f"https://{self._workspace_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"
        headers = {
            "content-type": "application/json",
            "Authorization": signature,
            "Log-Type": self._log_type,
            "x-ms-date": rfc1123date,
        }
        try:
            response = requests.post(uri, data=body, headers=headers, timeout=3)
            response.raise_for_status()
        except Exception:
            # Swallow telemetry failures silently to avoid impacting ingestion jobs.
            logging.getLogger("bronze-ingestion").debug("Log Analytics emit failed", exc_info=True)


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
        self._analytics = LogAnalyticsEmitter.from_env()

    def _emit(self, level: int, event: str, payload: Optional[Dict[str, Any]] = None):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **(payload or {}),
        }
        self._logger.log(level, json.dumps(record))
        if self._analytics:
            self._analytics.send(record)

    def info(self, event: str, payload: Optional[Dict[str, Any]] = None):
        self._emit(logging.INFO, event, payload)

    def warning(self, event: str, payload: Optional[Dict[str, Any]] = None):
        self._emit(logging.WARNING, event, payload)

    def error(self, event: str, payload: Optional[Dict[str, Any]] = None):
        self._emit(logging.ERROR, event, payload)

    def exception(self, event: str, payload: Optional[Dict[str, Any]] = None):
        combined_payload = {"level": "exception", **(payload or {})}
        self._emit(logging.ERROR, event, combined_payload)
