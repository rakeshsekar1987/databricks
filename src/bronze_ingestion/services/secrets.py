"""
Secret management layer to resolve credentials from Azure Key Vault / Databricks scopes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Protocol


class SecretManager(Protocol):
    def get_secret(self, secret_name: str) -> str:
        ...


@dataclass
class KeyVaultSecretManager:
    scope: str
    dbutils: object

    def get_secret(self, secret_name: str) -> str:
        return self.dbutils.secrets.get(scope=self.scope, key=secret_name)


@dataclass
class EnvironmentSecretManager:
    env: Mapping[str, str] = field(default_factory=lambda: os.environ)

    def get_secret(self, secret_name: str) -> str:
        if secret_name not in self.env:
            raise KeyError(f"Secret '{secret_name}' not found in environment variables.")
        return self.env[secret_name]


def resolve_dbutils():
    try:  # pragma: no cover - only available inside Databricks runtime
        from pyspark.dbutils import DBUtils  # type: ignore
        from pyspark.sql import SparkSession

        return DBUtils(SparkSession.getActiveSession())
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("dbutils is not available. Run within Databricks cluster.") from exc
