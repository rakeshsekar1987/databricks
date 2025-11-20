import pytest

from bronze_ingestion.exceptions import DataQualityError
from bronze_ingestion.logging_utils import StructuredLogger
from bronze_ingestion.services.data_quality import DataQualityService


def make_fake_df(count_value, schema_map):
    class FakeField:
        def __init__(self, name, dtype):
            self.name = name

            class DataType:
                def __init__(self, value):
                    self._value = value

                def simpleString(self):
                    return self._value

            self.dataType = DataType(dtype)

    class FakeSchema:
        def __init__(self, mapping):
            self.fields = [FakeField(name, dtype) for name, dtype in mapping.items()]

    class FakeDataFrame:
        def __init__(self, count_value, mapping):
            self._count = count_value
            self.schema = FakeSchema(mapping)

        def count(self):
            return self._count

    return FakeDataFrame(count_value, schema_map)


def test_row_count_validation_passes():
    service = DataQualityService(StructuredLogger("dq"))
    source_df = make_fake_df(100, {"id": "long"})
    target_df = make_fake_df(101, {"id": "long"})
    result = service.validate_row_counts(source_df, target_df, tolerance_percent=2.0)
    assert result.passed is True
    assert result.actual_count == 101


def test_row_count_validation_fails():
    service = DataQualityService(StructuredLogger("dq"))
    source_df = make_fake_df(100, {"id": "long"})
    target_df = make_fake_df(150, {"id": "long"})
    with pytest.raises(DataQualityError):
        service.validate_row_counts(source_df, target_df, tolerance_percent=2.0)


def test_schema_alignment_logs_warnings(caplog):
    service = DataQualityService(StructuredLogger("dq"))
    source_df = make_fake_df(10, {"id": "long", "value": "string"})
    target_df = make_fake_df(10, {"id": "decimal(10,0)", "extra": "string"})
    service.validate_schema_alignment(source_df, target_df)
    assert "dq.schema.mismatch" in caplog.text
