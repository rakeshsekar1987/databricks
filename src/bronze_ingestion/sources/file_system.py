"""
Generic file-system adapter supporting ABFSS, WABS, Blob, and other Spark-compatible file sources.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, TYPE_CHECKING

from ..logging_utils import StructuredLogger
from .base import SourceAdapter, SourceReadContext

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyspark.sql import DataFrame


class FileSystemAdapter(SourceAdapter):
    def __init__(self, logger: StructuredLogger):
        self._logger = logger

    def read(self, context: SourceReadContext) -> "DataFrame":
        read_format = context.options.get("format", "parquet")
        paths: Iterable[str] | str = context.options.get("paths")
        if not paths:
            raise ValueError("FileSystemAdapter requires 'paths' option in metadata.")

        reader = context.spark.read.format(read_format)
        extra_options: Dict[str, Any] = context.options.get("reader_options", {})
        for key, value in extra_options.items():
            reader = reader.option(key, value)

        self._logger.info(
            "source.filesystem.read",
            {
                "format": read_format,
                "paths": paths if isinstance(paths, str) else list(paths),
                "table": context.table_metadata.table_name,
            },
        )

        return reader.load(paths)
