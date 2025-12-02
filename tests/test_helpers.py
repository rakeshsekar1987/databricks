import pytest

from IDP_Metadata_Collector_Framework import (
    InclusionEvaluator,
    dedupe_registry_rows,
    to_snake_case,
    to_snake_case_list,
)


def test_to_snake_case_basic_variants():
    assert to_snake_case("CamelCase") == "camel_case"
    assert to_snake_case("already_snake") == "already_snake"
    assert to_snake_case("spaces and-hyphen") == "spaces_and_hyphen"
    assert to_snake_case("") == ""


def test_to_snake_case_list_handles_none_and_values():
    assert to_snake_case_list(["Id", "CreatedDate"]) == ["id", "created_date"]
    assert to_snake_case_list(None) == []


def test_inclusion_evaluator_includes_and_excludes():
    include = ["Orders", "Invoices"]
    exclude = ["Invoices"]
    assert InclusionEvaluator.evaluate("Orders", include, exclude) is True
    assert InclusionEvaluator.evaluate("Invoices", include, exclude) is False
    assert InclusionEvaluator.evaluate("Unknown", include, exclude) is False


def test_dedupe_registry_rows_updates_duplicate_ids():
    rows = [
        {
            "id": "SRC_Table",
            "source_id": "SRC",
            "catalog_name": "Catalog",
            "table_name": "Table",
        },
        {
            "id": "SRC_Table",
            "source_id": "SRC",
            "catalog_name": "Catalog",
            "table_name": "Table",
        },
    ]
    deduped = dedupe_registry_rows(rows)
    unique_ids = {row["id"] for row in deduped}
    assert len(unique_ids) == 2
    assert any("catalog_table_1" in row["table_name"] for row in deduped)
