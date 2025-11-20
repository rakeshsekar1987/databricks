"""
Factory responsible for returning the correct SourceAdapter based on metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..logging_utils import StructuredLogger
from ..metadata.models import SourceConnectionMetadata
from ..services.secrets import SecretManager
from .base import SourceAdapter
from .cassandra import CassandraAdapter
from .file_system import FileSystemAdapter
from .rest_api import RestApiAdapter
from .sql_server import SqlServerAdapter


@dataclass
class SourceAdapterFactory:
    secret_manager: SecretManager
    logger: StructuredLogger

    def get_adapter(self, source_metadata: SourceConnectionMetadata) -> SourceAdapter:
        source_type = source_metadata.data_source_type.upper()
        if source_type in {"SQLSERVER", "MSSQL"}:
            return SqlServerAdapter(self.secret_manager, self.logger)
        if source_type in {"REST", "RESTAPI", "ODATA"}:
            return RestApiAdapter(self.logger)
        if source_type in {"ABFSS", "WABS", "BLOB", "WASBS", "AZURE_BLOB"}:
            return FileSystemAdapter(self.logger)
        if source_type in {"CASSANDRA"}:
            return CassandraAdapter(self.logger)

        self.logger.warning(
            "source.factory.default",
            {"source_type": source_type, "message": "Falling back to SQL Server adapter"},
        )
        return SqlServerAdapter(self.secret_manager, self.logger)

    def build_source_options(self, source_metadata: SourceConnectionMetadata) -> Dict[str, str]:
        """
        Helper to merge static source metadata with per-table overrides.
        """
        return {
            "db_details": source_metadata.db_details,
            **source_metadata.metadata,
        }
