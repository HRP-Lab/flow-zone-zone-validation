"""SQLite schema checks shared by tests and diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Mapping, Sequence


def load_schema_contract(path: Path | str) -> dict[str, list[str]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {table: list(columns) for table, columns in payload.items()}


def validate_schema(
    connection: sqlite3.Connection,
    contract: Mapping[str, Sequence[str]],
) -> list[str]:
    """Return schema discrepancies without guessing replacements."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    issues: list[str] = []
    for table, required_columns in contract.items():
        if table not in tables:
            issues.append(f"Missing table: {table}")
            continue
        columns = {
            row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        missing = sorted(set(required_columns) - columns)
        if missing:
            issues.append(f"Table {table} is missing columns: {', '.join(missing)}")
    return issues


def execute_sql_file(
    connection: sqlite3.Connection,
    path: Path | str,
) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    sql = Path(path).read_text(encoding="utf-8")
    return list(connection.execute(sql))
