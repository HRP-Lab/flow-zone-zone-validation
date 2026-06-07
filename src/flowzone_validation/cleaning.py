"""Trial cleaning and defensible ACDC-specific quality flags."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PilotConfig


REQUIRED_TRIAL_COLUMNS = {
    "dataset_id",
    "participant_id",
    "task_family",
    "block_raw",
    "trial_raw",
    "observation_id",
    "congruency",
    "correct",
    "rt_ms",
}


def _median_absolute_deviation(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return np.nan
    median = float(numeric.median())
    return float((numeric - median).abs().median())


def _documented_nonresponse(frame: pd.DataFrame) -> pd.Series:
    nonresponse = pd.Series(False, index=frame.index, dtype=bool)
    for column in ("timeout", "timed_out", "non_response"):
        if column in frame:
            values = frame[column]
            if values.dtype == bool:
                nonresponse |= values.fillna(False)
            else:
                normalized = values.astype("string").str.lower()
                nonresponse |= normalized.isin({"1", "true", "yes", "timeout"})
    return nonresponse


def flag_trials(frame: pd.DataFrame, config: PilotConfig) -> pd.DataFrame:
    """Preserve rows while adding RT, response, and sensitivity flags."""
    missing = REQUIRED_TRIAL_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required trial columns: {sorted(missing)}")

    output = frame.copy()
    for column in (
        "dataset_id",
        "block_raw",
        "trial_raw",
        "observation_id",
        "correct",
        "rt_ms",
    ):
        output[column] = pd.to_numeric(output[column], errors="coerce")

    output["rt_missing"] = output["rt_ms"].isna()
    output["practice_block"] = output["block_raw"].lt(0).fillna(False)
    output["rt_below_min"] = output["rt_ms"].lt(config.rt_min_ms).fillna(False)
    output["rt_above_max"] = output["rt_ms"].gt(config.rt_max_ms).fillna(False)

    group_columns = ["dataset_id", "participant_id"]
    grouped = output.groupby(group_columns, dropna=False)["rt_ms"]
    output["participant_rt_median_ms"] = grouped.transform("median")
    output["participant_rt_mad_ms"] = grouped.transform(
        _median_absolute_deviation
    )
    robust_distance = (
        output["rt_ms"] - output["participant_rt_median_ms"]
    ).abs()
    robust_limit = config.rt_mad_multiplier * output["participant_rt_mad_ms"]
    output["rt_robust_outlier"] = (
        output["participant_rt_mad_ms"].gt(0)
        & robust_distance.gt(robust_limit)
    ).fillna(False)

    output["rt_excluded"] = output[
        ["rt_missing", "rt_below_min", "rt_above_max", "rt_robust_outlier"]
    ].any(axis=1)
    output["documented_nonresponse"] = _documented_nonresponse(output)
    output["lapse_proxy"] = (
        output["rt_missing"] | output["documented_nonresponse"]
    )

    valid_rt = output["rt_ms"].where(~output["rt_excluded"])
    output["participant_rt_q90_ms"] = valid_rt.groupby(
        [output["dataset_id"], output["participant_id"]],
        dropna=False,
    ).transform(lambda values: values.quantile(0.90))
    output["slow_tail_sensitivity"] = (
        ~output["rt_excluded"]
        & output["rt_ms"].gt(output["participant_rt_q90_ms"])
    )
    output["fast_error"] = (
        ~output["rt_excluded"]
        & output["correct"].eq(0)
        & output["rt_ms"].lt(250)
    )
    output["valid_rt"] = ~output["rt_excluded"]
    output["valid_correct_rt"] = output["valid_rt"] & output["correct"].eq(1)
    output["analysis_eligible_trial"] = ~output["practice_block"]
    return output
