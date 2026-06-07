"""Feature extraction from trial-level cognitive task data."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"rt_ms", "correct"}


def _safe_mean(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce")
    return float(numeric.mean()) if numeric.notna().any() else np.nan


def _summarize_group(
    trials: pd.DataFrame,
    timestamp_column: str,
) -> dict[str, float | int]:
    correct = pd.to_numeric(trials["correct"], errors="coerce")
    rt = pd.to_numeric(trials["rt_ms"], errors="coerce")
    valid_rt = rt[(rt > 0) & correct.eq(1)]

    elapsed_seconds = np.nan
    if timestamp_column in trials:
        timestamps = pd.to_datetime(trials[timestamp_column], errors="coerce", utc=True)
        if timestamps.notna().sum() >= 2:
            elapsed_seconds = (timestamps.max() - timestamps.min()).total_seconds()

    result: dict[str, float | int] = {
        "n_trials": int(len(trials)),
        "accuracy": _safe_mean(correct),
        "mean_rt_ms": _safe_mean(valid_rt),
        "median_rt_ms": float(valid_rt.median()) if valid_rt.notna().any() else np.nan,
        "rt_sd_ms": float(valid_rt.std(ddof=1)) if valid_rt.notna().sum() > 1 else np.nan,
        "elapsed_seconds": float(elapsed_seconds),
    }
    result["rt_cv"] = (
        result["rt_sd_ms"] / result["mean_rt_ms"]
        if result["mean_rt_ms"] and np.isfinite(result["mean_rt_ms"])
        else np.nan
    )
    result["correct_per_minute"] = (
        float(correct.eq(1).sum()) * 60.0 / elapsed_seconds
        if np.isfinite(elapsed_seconds) and elapsed_seconds > 0
        else np.nan
    )

    if "n_choices" in trials:
        choices = pd.to_numeric(trials["n_choices"], errors="coerce")
        information_bits = np.where(
            correct.eq(1) & choices.gt(1),
            np.log2(choices),
            0.0,
        ).sum()
        result["bits_per_second"] = (
            float(information_bits / elapsed_seconds)
            if np.isfinite(elapsed_seconds) and elapsed_seconds > 0
            else np.nan
        )
    else:
        result["bits_per_second"] = np.nan

    if "is_switch" in trials:
        switch = trials["is_switch"].astype("boolean")
        switch_rt = rt[switch.eq(True) & correct.eq(1)]
        repeat_rt = rt[switch.eq(False) & correct.eq(1)]
        result["switch_cost_ms"] = (
            _safe_mean(switch_rt) - _safe_mean(repeat_rt)
            if switch_rt.notna().any() and repeat_rt.notna().any()
            else np.nan
        )
    else:
        result["switch_cost_ms"] = np.nan

    result["perseveration_rate"] = (
        _safe_mean(trials["perseverative_error"])
        if "perseverative_error" in trials
        else np.nan
    )
    return result


def summarize_trials(
    trials: pd.DataFrame,
    group_columns: Sequence[str],
    timestamp_column: str = "timestamp",
) -> pd.DataFrame:
    """Summarize trial rows into one cognitive feature row per group."""
    missing = (REQUIRED_COLUMNS | set(group_columns)) - set(trials.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    grouper = group_columns[0] if len(group_columns) == 1 else list(group_columns)
    for key, group in trials.groupby(grouper, dropna=False, sort=True):
        keys = key if isinstance(key, tuple) else (key,)
        row = dict(zip(group_columns, keys, strict=True))
        row.update(_summarize_group(group, timestamp_column))
        rows.append(row)
    return pd.DataFrame(rows)
