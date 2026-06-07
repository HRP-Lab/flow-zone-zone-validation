from pathlib import Path

from flowzone_validation.database import (
    execute_sql_file,
    load_schema_contract,
    validate_schema,
)


ROOT = Path(__file__).resolve().parents[1]


def test_schema_contract_accepts_expected_fixture(acdc_connection):
    contract = load_schema_contract(ROOT / "config/acdc_schema.json")
    assert validate_schema(acdc_connection, contract) == []


def test_schema_contract_reports_missing_column(acdc_connection):
    contract = load_schema_contract(ROOT / "config/acdc_schema.json")
    contract["observation_table"] = [
        *contract["observation_table"],
        "invented_column",
    ]
    issues = validate_schema(acdc_connection, contract)
    assert issues == [
        "Table observation_table is missing columns: invented_column"
    ]


def test_shared_inventory_sql(acdc_connection):
    rows = execute_sql_file(
        acdc_connection,
        ROOT / "sql/acdc_inventory.sql",
    )
    assert len(rows) == 1
    assert rows[0]["task_family"] == "Stroop"
    assert rows[0]["observed_trials"] == 4
    assert rows[0]["congruent_trials"] == 2
    assert rows[0]["incongruent_trials"] == 1


def test_shared_extract_sql_normalizes_units_and_codes(acdc_connection):
    rows = execute_sql_file(
        acdc_connection,
        ROOT / "sql/acdc_trial_extract.sql",
    )
    assert len(rows) == 4
    assert rows[0]["participant_id"] == "1:7"
    assert rows[0]["block_raw"] == 1
    assert rows[0]["block_source_raw"] == "1"
    assert rows[0]["rt_ms"] == 450
    assert [row["congruency"] for row in rows] == [
        "congruent",
        "incongruent",
        "congruent",
        "neutral",
    ]
    assert rows[2]["correct"] == 0


def test_shared_extract_sql_does_not_coerce_blank_blocks_to_zero(
    acdc_connection,
):
    acdc_connection.execute(
        "UPDATE observation_table SET block = '' WHERE observation_id = 4"
    )
    rows = execute_sql_file(
        acdc_connection,
        ROOT / "sql/acdc_trial_extract.sql",
    )
    assert rows[3]["block_source_raw"] == ""
    assert rows[3]["block_raw"] is None
