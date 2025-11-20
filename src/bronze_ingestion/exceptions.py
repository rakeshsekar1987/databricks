"""
Custom exception hierarchy for the Bronze ingestion framework.
"""

from __future__ import annotations


class BronzeFrameworkError(Exception):
    """Base error for the ingestion framework."""


class MetadataNotFoundError(BronzeFrameworkError):
    """Raised when mandatory metadata is missing."""


class SourceAdapterError(BronzeFrameworkError):
    """Raised when a source adapter fails to read data."""


class StrategySelectionError(BronzeFrameworkError):
    """Raised when the orchestrator cannot resolve a load strategy."""


class SchemaDriftError(BronzeFrameworkError):
    """Raised for schema drift conditions that cannot be auto-handled."""


class DataQualityError(BronzeFrameworkError):
    """Raised when row counts or DQ checks fail."""
