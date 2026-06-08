"""Helpers for validating abbreviated SART prefixes against full sessions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score

from .paired_vigilance import build_sart_dimensions


FINGERPRINT_RAW_COLUMNS = [
    "sart_commission_percent_raw",
    "sart_omission_percent_raw",
    "sart_anticipatory_count_raw",
    "sart_go_mean_rt_ms_raw",
    "sart_go_rt_cv_raw",
]
FINGERPRINT_SUMMARY_COLUMNS = [
    "sart_commission_percent",
    "sart_omission_percent",
    "sart_anticipatory_count",
    "sart_go_mean_rt_ms",
    "sart_go_rt_cv",
]
FINGERPRINT_SCALES = np.asarray([4.0, 0.5, 1.0, 5.0, 0.01])


@dataclass(frozen=True)
class SartMatchResult:
    trials: pd.DataFrame
    assignments: pd.DataFrame
    audit: pd.DataFrame


def prepare_sart_trials(raw: pd.DataFrame) -> pd.DataFrame:
    """Return ordered main-block SART rows with stable raw-session IDs."""
    required = {
        "subjectid",
        "date",
        "time",
        "blockcode",
        "expressions.trialcount",
        "values.trialtype",
        "values.responsetype",
        "values.RT",
    }
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing raw SART columns: {sorted(missing)}")
    trials = raw[raw["blockcode"].eq("SART")].copy()
    trials["raw_session_id"] = (
        trials["subjectid"].astype("Int64").astype(str)
        + ":"
        + trials["date"].astype("Int64").astype(str)
        + ":"
        + trials["time"].astype(str)
    )
    trials["trial_order"] = pd.to_numeric(
        trials["expressions.trialcount"],
        errors="coerce",
    )
    trials = trials.sort_values(
        ["raw_session_id", "trial_order"],
        kind="stable",
    )
    counts = trials.groupby("raw_session_id").size()
    if not counts.eq(225).all():
        raise ValueError("Every raw SART main block must contain 225 trials")
    expected = np.arange(1, 226)
    for _, group in trials.groupby("raw_session_id", sort=False):
        if not np.array_equal(group["trial_order"].to_numpy(), expected):
            raise ValueError("SART trial order must be complete and contiguous")
    return trials


def summarize_sart_trials(
    trials: pd.DataFrame,
    *,
    prefix_trials: int,
) -> pd.DataFrame:
    """Summarize a bounded SART prefix for every raw session."""
    if prefix_trials <= 0 or prefix_trials > 225:
        raise ValueError("prefix_trials must be between 1 and 225")
    selected = trials[trials["trial_order"].le(prefix_trials)].copy()
    rows = []
    for raw_session_id, group in selected.groupby(
        "raw_session_id",
        sort=False,
    ):
        response_type = group["values.responsetype"].astype(str)
        go = group["values.trialtype"].eq("Go")
        nogo = group["values.trialtype"].eq("NoGo")
        valid_go = response_type.eq("Go Success")
        rt = pd.to_numeric(group["values.RT"], errors="coerce")
        go_n = int(go.sum())
        nogo_n = int(nogo.sum())
        commission_count = int(response_type.eq("NoGo Failure").sum())
        omission_count = int(response_type.eq("Omission").sum())
        anticipatory_count = int(response_type.eq("Go Anticipatory").sum())
        go_mean = float(rt[valid_go].mean())
        go_sd = float(rt[valid_go].std(ddof=1))
        rows.append(
            {
                "raw_session_id": raw_session_id,
                "source_subject_id": int(group["subjectid"].iloc[0]),
                "raw_date": int(group["date"].iloc[0]),
                "raw_time": str(group["time"].iloc[0]),
                "prefix_trials": prefix_trials,
                "sart_trial_count_raw": len(group),
                "sart_go_count_raw": go_n,
                "sart_nogo_count_raw": nogo_n,
                "sart_valid_go_count_raw": int(valid_go.sum()),
                "sart_commission_count_raw": commission_count,
                "sart_commission_rate_raw": (
                    commission_count / nogo_n if nogo_n else np.nan
                ),
                "sart_commission_percent_raw": (
                    100 * commission_count / nogo_n if nogo_n else np.nan
                ),
                "sart_omission_count_raw": omission_count,
                "sart_omission_rate_raw": (
                    omission_count / go_n if go_n else np.nan
                ),
                "sart_omission_percent_raw": (
                    100 * omission_count / go_n if go_n else np.nan
                ),
                "sart_anticipatory_count_raw": anticipatory_count,
                "sart_anticipatory_rate_raw": (
                    anticipatory_count / go_n if go_n else np.nan
                ),
                "sart_go_mean_rt_ms_raw": go_mean,
                "sart_go_sd_rt_ms_raw": go_sd,
                "sart_go_rt_cv_raw": (
                    go_sd / go_mean
                    if np.isfinite(go_sd) and go_mean > 0
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def match_sart_sessions(
    full_raw: pd.DataFrame,
    sessions: pd.DataFrame,
    *,
    maximum_cost: float = 0.01,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match raw bouts to paired sessions using participant-bound fingerprints."""
    required = {
        "source_subject_id",
        "session_id",
        "session_type",
        *FINGERPRINT_SUMMARY_COLUMNS,
    }
    missing = required - set(sessions.columns)
    if missing:
        raise ValueError(f"Missing paired-session columns: {sorted(missing)}")
    assignments = []
    for participant, summary_group in sessions.groupby(
        "source_subject_id",
        sort=True,
    ):
        raw_group = full_raw[
            full_raw["source_subject_id"].eq(participant)
        ]
        if raw_group.empty:
            continue
        raw_values = raw_group[FINGERPRINT_RAW_COLUMNS].to_numpy(float)
        summary_values = summary_group[
            FINGERPRINT_SUMMARY_COLUMNS
        ].to_numpy(float)
        cost = np.mean(
            np.abs(
                raw_values[:, np.newaxis, :]
                - summary_values[np.newaxis, :, :]
            )
            / FINGERPRINT_SCALES,
            axis=2,
        )
        raw_indices, summary_indices = linear_sum_assignment(cost)
        for raw_index, summary_index in zip(
            raw_indices,
            summary_indices,
            strict=True,
        ):
            assignments.append(
                {
                    "raw_session_id": raw_group.iloc[raw_index][
                        "raw_session_id"
                    ],
                    "session_id": summary_group.iloc[summary_index][
                        "session_id"
                    ],
                    "source_subject_id": int(participant),
                    "fingerprint_cost": float(
                        cost[raw_index, summary_index]
                    ),
                }
            )
    candidates = pd.DataFrame(assignments)
    candidates["accepted"] = candidates["fingerprint_cost"].le(maximum_cost)
    accepted = candidates[candidates["accepted"]].copy()
    if accepted["raw_session_id"].duplicated().any():
        raise ValueError("A raw SART bout matched more than one paired session")
    if accepted["session_id"].duplicated().any():
        raise ValueError("A paired session matched more than one raw SART bout")
    return accepted, candidates


def attach_sart_sessions(
    trials: pd.DataFrame,
    assignments: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    """Attach paired metadata without crossing raw SART session boundaries."""
    metadata = sessions[
        [
            "session_id",
            "participant_id",
            "source_subject_id",
            "session_type",
            "dataset_id",
            "control_profile",
            "task_active_efficacy",
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
        ]
    ]
    linked = trials.merge(
        assignments[["raw_session_id", "session_id"]],
        on="raw_session_id",
        how="inner",
        validate="many_to_one",
    ).merge(
        metadata,
        on="session_id",
        how="left",
        validate="many_to_one",
    )
    if linked["participant_id"].isna().any():
        raise ValueError("Matched SART rows are missing paired metadata")
    boundaries = linked.groupby("raw_session_id").agg(
        sessions=("session_id", "nunique"),
        participants=("participant_id", "nunique"),
    )
    if not boundaries.eq(1).all().all():
        raise ValueError("SART rows crossed a session or participant boundary")
    return linked


def score_sart_prefix(
    summary: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    label: str,
) -> pd.DataFrame:
    """Attach metadata and build abbreviated SART dimensions."""
    frame = summary.merge(
        metadata,
        on="raw_session_id",
        how="inner",
        validate="one_to_one",
    )
    frame, _ = build_sart_dimensions(
        frame,
        omission_column="sart_omission_rate_raw",
        rt_cv_column="sart_go_rt_cv_raw",
        commission_column="sart_commission_rate_raw",
        anticipatory_column="sart_anticipatory_rate_raw",
        engagement_name=f"{label}_engagement_index",
        inhibition_name=f"{label}_inhibitory_stability_index",
    )
    return frame


def lins_concordance(left: pd.Series, right: pd.Series) -> float:
    """Return Lin's concordance correlation coefficient."""
    complete = pd.concat([left, right], axis=1).dropna().to_numpy(float)
    if len(complete) < 2:
        return np.nan
    left_values = complete[:, 0]
    right_values = complete[:, 1]
    covariance = np.mean(
        (left_values - left_values.mean())
        * (right_values - right_values.mean())
    )
    denominator = (
        left_values.var()
        + right_values.var()
        + (left_values.mean() - right_values.mean()) ** 2
    )
    return float(2 * covariance / denominator) if denominator > 0 else np.nan


def agreement_table(
    frame: pd.DataFrame,
    pairs: list[tuple[str, str, str]],
) -> pd.DataFrame:
    """Summarize association and absolute agreement for paired measures."""
    rows = []
    for metric, abbreviated_column, full_column in pairs:
        complete = frame[[abbreviated_column, full_column]].dropna()
        abbreviated = complete[abbreviated_column]
        full = complete[full_column]
        difference = abbreviated - full
        rows.append(
            {
                "metric": metric,
                "abbreviated_column": abbreviated_column,
                "full_column": full_column,
                "n_sessions": len(complete),
                "pearson_r": (
                    float(pearsonr(abbreviated, full).statistic)
                    if abbreviated.nunique() > 1 and full.nunique() > 1
                    else np.nan
                ),
                "spearman_r": (
                    float(spearmanr(abbreviated, full).statistic)
                    if abbreviated.nunique() > 1 and full.nunique() > 1
                    else np.nan
                ),
                "lins_ccc": lins_concordance(abbreviated, full),
                "mean_bias": float(difference.mean()),
                "mae": float(difference.abs().mean()),
                "rmse": float(np.sqrt(np.mean(difference**2))),
            }
        )
    return pd.DataFrame(rows)


def binary_threshold_agreement(
    abbreviated: pd.Series,
    full: pd.Series,
    *,
    threshold: float = -0.5,
) -> dict[str, float | int]:
    """Compare abbreviated and full low-engagement classifications."""
    complete = pd.concat([abbreviated, full], axis=1).dropna()
    predicted = complete.iloc[:, 0].le(threshold)
    reference = complete.iloc[:, 1].le(threshold)
    true_positive = int((predicted & reference).sum())
    true_negative = int((~predicted & ~reference).sum())
    false_positive = int((predicted & ~reference).sum())
    false_negative = int((~predicted & reference).sum())
    return {
        "n_sessions": len(complete),
        "threshold": threshold,
        "reference_positive_rate": float(reference.mean()),
        "abbreviated_positive_rate": float(predicted.mean()),
        "sensitivity": (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else np.nan
        ),
        "specificity": (
            true_negative / (true_negative + false_positive)
            if true_negative + false_positive
            else np.nan
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(reference, predicted)
        ),
        "cohen_kappa": float(cohen_kappa_score(reference, predicted)),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def project_average_reliability(
    icc: pd.DataFrame,
    session_counts: tuple[int, ...] = (1, 3, 5, 7, 10),
) -> pd.DataFrame:
    """Project reliability of an average across repeated comparable sessions."""
    required = {"sart_source", "feature", "icc_1"}
    missing = required - set(icc.columns)
    if missing:
        raise ValueError(f"Missing ICC columns: {sorted(missing)}")
    if not session_counts or any(count <= 0 for count in session_counts):
        raise ValueError("session_counts must contain positive integers")
    rows = []
    for row in icc.itertuples():
        for sessions in session_counts:
            single_session_icc = float(row.icc_1)
            denominator = 1 + (sessions - 1) * single_session_icc
            projected = (
                sessions * single_session_icc / denominator
                if denominator > 0
                else np.nan
            )
            rows.append(
                {
                    "sart_source": row.sart_source,
                    "feature": row.feature,
                    "single_session_icc": single_session_icc,
                    "baseline_sessions": sessions,
                    "projected_average_reliability": projected,
                    "assumption": (
                        "Spearman-Brown projection under comparable "
                        "independent session error"
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_match_audit(
    trials: pd.DataFrame,
    sessions: pd.DataFrame,
    candidates: pd.DataFrame,
    accepted: pd.DataFrame,
) -> pd.DataFrame:
    """Return a compact audit of raw-to-summary SART linkage."""
    return pd.DataFrame(
        [
            {
                "raw_main_sessions": trials["raw_session_id"].nunique(),
                "paired_sessions": sessions["session_id"].nunique(),
                "candidate_assignments": len(candidates),
                "accepted_exact_fingerprint_matches": len(accepted),
                "rejected_fingerprint_assignments": int(
                    (~candidates["accepted"]).sum()
                ),
                "unmatched_paired_sessions": int(
                    sessions["session_id"].nunique() - len(candidates)
                ),
                "unmatched_or_unused_raw_sessions": int(
                    trials["raw_session_id"].nunique() - len(accepted)
                ),
                "matched_participants": accepted[
                    "source_subject_id"
                ].nunique(),
                "maximum_accepted_fingerprint_cost": float(
                    accepted["fingerprint_cost"].max()
                ),
            }
        ]
    )
