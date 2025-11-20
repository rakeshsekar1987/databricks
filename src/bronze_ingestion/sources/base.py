"""
Source adapters convert metadata into Spark DataFrames ready for Bronze ingestion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING

from ..metadata.models import TableMetadata

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyspark.sql import DataFrame, SparkSession


@dataclass(frozen=True, slots=True)
class SourceReadContext:
    spark: "SparkSession"
    table_metadata: TableMetadata
    options: Dict[str, str]
    incremental_filter: Optional[str] = None


class SourceAdapter(ABC):
    """Contract for reading from arbitrary sources into Spark DataFrames."""

    @abstractmethod
    def read(self, context: SourceReadContext) -> "DataFrame":
        ...
