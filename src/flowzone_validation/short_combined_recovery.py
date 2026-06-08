"""Short paired Stroop and Flanker profile-recovery helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


def match_raw_sessions(
    raw: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    """Match only unambiguous participant-date task sessions."""
    trials = raw.copy()
    trials["session_date"] = pd.to_datetime(
        trials["date"].astype(int).astype(str).str.zfill(6),
        format="%m%d%y",
        errors="coerce",
    ).dt.normalize()
    reference = sessions.copy()
    reference["session_date"] = pd.to_datetime(
        reference["session_date"]
    ).dt.normalize()
    reference = reference[
        ~reference.duplicated(
            ["source_subject_id", "session_date"],
            keep=False,
        )
    ]
    raw_keys = trials[
        ["subjectid", "session_date", "time"]
    ].drop_duplicates()
    raw_keys = raw_keys[
        ~raw_keys.duplicated(["subjectid", "session_date"], keep=False)
    ]
    keys = raw_keys.merge(
        reference,
        left_on=["subjectid", "session_date"],
        right_on=["source_subject_id", "session_date"],
        how="inner",
        validate="one_to_one",
    )
    columns = [
        "subjectid",
        "session_date",
        "time",
        "session_id",
        "participant_id",
        "dataset_id",
        "control_profile",
    ]
    return trials.merge(
        keys[columns],
        on=["subjectid", "session_date", "time"],
        validate="many_to_one",
    )


def prepare_task_trials(
    raw: pd.DataFrame,
    sessions: pd.DataFrame,
    task: str,
) -> pd.DataFrame:
    """Prepare ordered scored trials and modelled Stroop elapsed time."""
    trials = match_raw_sessions(raw, sessions)
    if task == "stroop":
        trials = trials.sort_values(["session_id", "trialnum"])
        trials["condition"] = trials["values.congruency"]
        latency = pd.to_numeric(trials["latency"], errors="coerce").fillna(
            3000
        )
        trials["modelled_duration_ms"] = (
            latency + 400 + 400 * trials["correct"].eq(0)
        )
        trials["modelled_elapsed_ms"] = trials.groupby(
            "session_id"
        )["modelled_duration_ms"].cumsum()
    elif task == "flanker":
        trials = trials[
            trials["values.practice"].eq(0)
            & trials["trialcode"].astype("string").str.startswith("target")
            & trials["values.congruence"].isin([1, 2])
        ].sort_values(["session_id", "values.trialcount"])
        trials["condition"] = trials["values.congruence"]
    else:
        raise ValueError(f"Unsupported task: {task}")
    trials["trial_order"] = trials.groupby("session_id").cumcount() + 1
    return trials


def summarize_prefix(
    trials: pd.DataFrame,
    task: str,
    selector: Callable[[pd.DataFrame], pd.Series],
) -> pd.DataFrame:
    """Summarize selected trial prefixes without crossing sessions."""
    selected = trials[selector(trials)].copy()
    rows: list[dict[str, Any]] = []
    for session_id, group in selected.groupby("session_id", sort=False):
        correct = group["correct"].eq(1)
        rt = pd.to_numeric(group["latency"], errors="coerce")
        row: dict[str, Any] = {
            "session_id": session_id,
            "parent_window_id": session_id,
            "participant_id": group["participant_id"].iloc[0],
            "dataset_id": group["dataset_id"].iloc[0],
            "control_profile": group["control_profile"].iloc[0],
            f"{task}_n": len(group),
            f"{task}_accuracy": correct.mean(),
            f"{task}_mean_rt": rt[correct].mean(),
            f"{task}_median_rt": rt[correct].median(),
            f"{task}_rt_cv": rt[correct].std(ddof=1) / rt[correct].mean(),
        }
        row[f"{task}_throughput"] = row[f"{task}_accuracy"] / (
            row[f"{task}_mean_rt"] / 1000
        )
        for condition, name in ((1, "congruent"), (2, "incongruent")):
            mask = group["condition"].eq(condition)
            row[f"{task}_{name}_accuracy"] = correct[mask].mean()
            row[f"{task}_{name}_rt"] = rt[correct & mask].mean()
        row[f"{task}_cost_rt"] = (
            row[f"{task}_incongruent_rt"]
            - row[f"{task}_congruent_rt"]
        )
        row[f"{task}_cost_accuracy"] = (
            row[f"{task}_congruent_accuracy"]
            - row[f"{task}_incongruent_accuracy"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def merge_task_prefixes(
    stroop: pd.DataFrame,
    flanker: pd.DataFrame,
) -> pd.DataFrame:
    """Join paired task prefixes while retaining one reference label."""
    metadata = {
        "participant_id",
        "dataset_id",
        "control_profile",
        "parent_window_id",
    }
    return stroop.merge(
        flanker.drop(columns=list(metadata)),
        on="session_id",
        validate="one_to_one",
    )


def feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return numeric task features, excluding trial-count metadata."""
    return [
        column
        for column in frame.columns
        if (
            column.startswith("stroop_")
            or column.startswith("flanker_")
        )
        and column not in {"stroop_n", "flanker_n"}
    ]


def trial_yield_by_profile(stroop_two_minute: pd.DataFrame) -> pd.DataFrame:
    """Summarize fixed-duration Stroop evidence by full-session profile."""
    rows: list[dict[str, Any]] = []
    for profile, group in stroop_two_minute.groupby(
        "control_profile",
        sort=True,
    ):
        counts = group["stroop_n"]
        rows.append(
            {
                "control_profile": profile,
                "n_sessions": len(group),
                "mean_trials": counts.mean(),
                "median_trials": counts.median(),
                "p10_trials": counts.quantile(0.10),
                "p90_trials": counts.quantile(0.90),
                "below_60_rate": counts.lt(60).mean(),
                "below_80_rate": counts.lt(80).mean(),
                "at_least_100_rate": counts.ge(100).mean(),
            }
        )
    return pd.DataFrame(rows)


def flanker_two_minute_trials(trial_duration_ms: int = 2700) -> int:
    """Conservative trial yield under the source task's maximum duration."""
    if trial_duration_ms <= 0:
        raise ValueError("trial_duration_ms must be positive")
    return int(np.floor(120_000 / trial_duration_ms))
