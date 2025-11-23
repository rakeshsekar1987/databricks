from bronze_ingestion.logging_utils import StructuredLogger
from bronze_ingestion.metadata.models import SourceConnectionMetadata
from bronze_ingestion.sources.cassandra import CassandraAdapter
from bronze_ingestion.sources.file_system import FileSystemAdapter
from bronze_ingestion.sources.factory import SourceAdapterFactory
from bronze_ingestion.sources.rest_api import RestApiAdapter
from bronze_ingestion.sources.sql_server import SqlServerAdapter


class DummySecretManager:
    def get_secret(self, name: str) -> str:
        return "secret"


def make_metadata(source_type: str, metadata: dict | None = None) -> SourceConnectionMetadata:
    return SourceConnectionMetadata(
        id=f"{source_type}-id",
        data_source_type=source_type,
        catalog_name="cat",
        logical_name="table",
        db_details={
            "db_host": "host",
            "db_name": "db",
            "user_name": "user",
            "password_key": "pwd",
            "db_port": "1433",
        },
        is_active=True,
        include_list=[],
        exclude_list=[],
        is_ct_enabled=True,
        metadata=metadata or {},
    )


def test_factory_returns_sql_adapter():
    factory = SourceAdapterFactory(DummySecretManager(), StructuredLogger("test"))
    adapter = factory.get_adapter(make_metadata("SQLSERVER"))
    assert isinstance(adapter, SqlServerAdapter)


def test_factory_returns_rest_adapter():
    factory = SourceAdapterFactory(DummySecretManager(), StructuredLogger("test"))
    adapter = factory.get_adapter(make_metadata("REST"))
    assert isinstance(adapter, RestApiAdapter)


def test_factory_returns_filesystem_adapter():
    factory = SourceAdapterFactory(DummySecretManager(), StructuredLogger("test"))
    adapter = factory.get_adapter(make_metadata("ABFSS"))
    assert isinstance(adapter, FileSystemAdapter)


def test_factory_returns_cassandra_adapter():
    factory = SourceAdapterFactory(DummySecretManager(), StructuredLogger("test"))
    adapter = factory.get_adapter(make_metadata("CASSANDRA"))
    assert isinstance(adapter, CassandraAdapter)


def test_build_source_options_merges_metadata():
    factory = SourceAdapterFactory(DummySecretManager(), StructuredLogger("test"))
    metadata = make_metadata("SQLSERVER", {"custom_option": "value"})
    options = factory.build_source_options(metadata)
    assert options["db_details"]["db_host"] == "host"
    assert options["custom_option"] == "value"
