"""Utilities for assigning trial rows to cognitive time windows."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def assign_fixed_windows(
    trials: pd.DataFrame,
    timestamp_column: str = "timestamp",
    group_columns: Sequence[str] = ("participant_id",),
    frequency: str = "5min",
) -> pd.DataFrame:
    """Assign UTC timestamps to non-overlapping, fixed-width windows."""
    required = {timestamp_column, *group_columns}
    missing = required - set(trials.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    output = trials.copy()
    output[timestamp_column] = pd.to_datetime(
        output[timestamp_column],
        errors="coerce",
        utc=True,
    )
    if output[timestamp_column].isna().any():
        invalid = int(output[timestamp_column].isna().sum())
        raise ValueError(f"{invalid} rows have invalid timestamps")

    output["window_start"] = output[timestamp_column].dt.floor(frequency)
    offset = pd.tseries.frequencies.to_offset(frequency)
    output["window_end"] = output["window_start"] + offset
    return output.sort_values([*group_columns, timestamp_column]).reset_index(drop=True)
