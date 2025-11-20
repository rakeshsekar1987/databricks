"""
REST API adapter placeholder to demonstrate extensibility.
"""

from __future__ import annotations

from typing import Dict

import requests
from pyspark.sql import DataFrame

from ..logging_utils import StructuredLogger
from .base import SourceAdapter, SourceReadContext


class RestApiAdapter(SourceAdapter):
    """
    Simple adapter that pulls from a REST endpoint and parallelizes ingestion via Spark.
    Not production-ready but illustrates how new sources can plug into the framework.
    """

    def __init__(self, logger: StructuredLogger):
        self._logger = logger

    def _fetch_payload(self, url: str, headers: Dict[str, str]) -> Dict[str, object]:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def read(self, context: SourceReadContext) -> DataFrame:
        url = context.options["url"]
        headers = context.options.get("headers", {})
        payload = self._fetch_payload(url, headers)
        self._logger.info(
            "source.rest.fetch",
            {
                "table": context.table_metadata.table_name,
                "url": url,
                "payload_keys": list(payload.keys())[:5],
            },
        )
        return context.spark.read.json(context.spark.sparkContext.parallelize([payload]))
