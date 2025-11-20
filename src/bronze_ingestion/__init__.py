"""
Bronze ingestion framework for Azure Databricks.

Exposes orchestration helpers for full and incremental (CT/CDF) loads into the Bronze Delta layer.
"""

from importlib import metadata


def __getattr__(name: str):
    if name == "__version__":
        try:
            return metadata.version("bronze-ingestion-framework")
        except metadata.PackageNotFoundError:  # pragma: no cover - dev installs
            return "0.0.0"
    raise AttributeError(name)


__all__ = ["__version__"]