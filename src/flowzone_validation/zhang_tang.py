"""Zhang-Tang-style mutual information, update, and tail analyses."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any

import numpy as np
import pandas as pd

from .config import ZhangTangConfig
from .windowing import BOUNDARY_COLUMNS, iter_trial_windows


MI_FEATURES = (
    "mi_congruency_correct",
    "mi_congruency_response",
    "mi_prev_error_next_correct",
    "mi_condition_efficiency_bin_sens",
)
UPDATE_FEATURES = (
    "delta_throughput",
    "delta_accuracy",
    "delta_rt_cv",
    "delta_interference_rt_cost",
    "combined_update_magnitude",
)
TAIL_FEATURES = (
    "upper_tail_rate_abs_rt_resid_z",
    "upper_tail_rate_abs_delta_u_z",
)
NEXT_OUTCOMES = (
    "next_accuracy",
    "next_throughput",
    "next_rt_cv",
    "next_interference_rt_cost",
    "next_error_burstiness",
)
CHANGE_OUTCOMES = {
    "next_accuracy": "change_next_accuracy",
    "next_throughput": "change_next_throughput",
    "next_rt_cv": "change_next_rt_cv",
    "next_interference_rt_cost": "change_next_interference_rt_cost",
    "next_error_burstiness": "change_next_error_burstiness",
}


def _safe_float(value: object) -> float:
    if value is pd.NA or pd.isna(value):
        return np.nan
    return float(value)


def _stable_seed(seed: int, *values: object) -> int:
    text = "|".join([str(seed), *(str(value) for value in values)])
    return int.from_bytes(
        hashlib.sha256(text.encode("utf-8")).digest()[:8],
        "little",
    ) % (2**32 - 1)


def discrete_mutual_information_bits(
    left: pd.Series | np.ndarray,
    right: pd.Series | np.ndarray,
) -> float:
    """Compute discrete mutual information in bits."""
    frame = pd.DataFrame({"left": left, "right": right}).dropna()
    if frame.empty:
        return np.nan
    left_codes, left_values = pd.factorize(frame["left"], sort=True)
    right_codes, right_values = pd.factorize(frame["right"], sort=True)
    if len(left_values) < 2 or len(right_values) < 2:
        return np.nan
    counts = np.zeros((len(left_values), len(right_values)), dtype=float)
    np.add.at(counts, (left_codes, right_codes), 1)
    probabilities = counts / counts.sum()
    left_probabilities = probabilities.sum(axis=1, keepdims=True)
    right_probabilities = probabilities.sum(axis=0, keepdims=True)
    expected = left_probabilities @ right_probabilities
    positive = probabilities > 0
    return float(
        np.sum(
            probabilities[positive]
            * np.log2(probabilities[positive] / expected[positive])
        )
    )


def bias_corrected_mutual_information(
    left: pd.Series,
    right: pd.Series,
    config: ZhangTangConfig,
    seed: int,
) -> tuple[float, str | None]:
    """Return permutation-bias-corrected MI and an explicit missing reason."""
    frame = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(frame) < config.minimum_mi_observations:
        return np.nan, "insufficient_observations"
    for column in ("left", "right"):
        counts = frame[column].value_counts()
        if len(counts) < 2:
            return np.nan, f"invariant_{column}"
        if int(counts.min()) < config.minimum_mi_class_count:
            return np.nan, f"sparse_{column}_class"
    observed = discrete_mutual_information_bits(frame["left"], frame["right"])
    if not np.isfinite(observed):
        return np.nan, "mi_not_estimable"
    rng = np.random.default_rng(seed)
    permuted: list[float] = []
    right_values = frame["right"].to_numpy()
    for _ in range(config.mi_permutations):
        value = discrete_mutual_information_bits(
            frame["left"],
            rng.permutation(right_values),
        )
        if np.isfinite(value):
            permuted.append(value)
    bias = float(np.mean(permuted)) if permuted else 0.0
    return max(0.0, float(observed - bias)), None


def _zscore(values: pd.Series | np.ndarray) -> np.ndarray:
    numeric = np.asarray(values, dtype=float)
    output = np.full(len(numeric), np.nan, dtype=float)
    valid = np.isfinite(numeric)
    if valid.sum() < 2:
        return output
    deviation = float(np.std(numeric[valid], ddof=0))
    if not np.isfinite(deviation) or deviation == 0:
        output[valid] = 0.0
        return output
    output[valid] = (numeric[valid] - np.mean(numeric[valid])) / deviation
    return output


def upper_tail_rate(
    values: pd.Series | np.ndarray,
    threshold: float,
    minimum_observations: int,
) -> tuple[float, str | None]:
    numeric = np.asarray(values, dtype=float)
    finite = numeric[np.isfinite(numeric)]
    if len(finite) < minimum_observations:
        return np.nan, "insufficient_observations"
    return float(np.mean(np.abs(finite) >= threshold)), None


def _efficiency_condition_mi(
    trials: pd.DataFrame,
    config: ZhangTangConfig,
    seed: int,
) -> tuple[float, str | None]:
    frame = trials[["within_id", "efficiency_t"]].dropna()
    if len(frame) < config.minimum_mi_observations:
        return np.nan, "insufficient_observations"
    if frame["within_id"].nunique() < 2:
        return np.nan, "invariant_condition"
    estimates: list[float] = []
    reasons: list[str] = []
    for bins in config.efficiency_bin_counts:
        try:
            labels = pd.qcut(
                frame["efficiency_t"],
                q=bins,
                labels=False,
                duplicates="drop",
            )
        except ValueError:
            reasons.append(f"binning_failed_{bins}")
            continue
        value, reason = bias_corrected_mutual_information(
            frame["within_id"],
            labels,
            config,
            _stable_seed(seed, "efficiency", bins),
        )
        if np.isfinite(value):
            estimates.append(value)
        elif reason:
            reasons.append(reason)
    if not estimates:
        return np.nan, (
            Counter(reasons).most_common(1)[0][0]
            if reasons
            else "mi_not_estimable"
        )
    return float(np.median(estimates)), None


def summarize_trial_window(
    trials: pd.DataFrame,
    config: ZhangTangConfig,
) -> dict[str, Any]:
    """Summarize trial-level MI and spike features for one primary window."""
    first = trials.iloc[0]
    window_id = str(first["window_id"])
    base_seed = _stable_seed(config.random_seed, window_id)
    row: dict[str, Any] = {"window_id": window_id}

    value, reason = bias_corrected_mutual_information(
        trials["congruency"].where(trials["congruency"].ne("unknown")),
        pd.to_numeric(trials["correct"], errors="coerce"),
        config,
        _stable_seed(base_seed, "congruency_correct"),
    )
    row["mi_congruency_correct"] = value
    row["missing_reason_mi_congruency_correct"] = reason
    row["mi_congruency_response"] = np.nan
    row["missing_reason_mi_congruency_response"] = (
        "response_choice_unavailable_in_acdc"
    )

    ordered = trials.sort_values(
        ["trial_raw", "observation_id"],
        kind="stable",
        na_position="last",
    )
    correctness = pd.to_numeric(ordered["correct"], errors="coerce")
    value, reason = bias_corrected_mutual_information(
        1 - correctness.shift(1),
        correctness,
        config,
        _stable_seed(base_seed, "previous_error"),
    )
    row["mi_prev_error_next_correct"] = value
    row["missing_reason_mi_prev_error_next_correct"] = reason

    value, reason = _efficiency_condition_mi(ordered, config, base_seed)
    row["mi_condition_efficiency_bin_sens"] = value
    row["missing_reason_mi_condition_efficiency_bin_sens"] = reason

    value, reason = upper_tail_rate(
        pd.to_numeric(ordered["log_rt_residual_z"], errors="coerce"),
        config.tail_z_threshold,
        config.minimum_tail_observations,
    )
    row["upper_tail_rate_abs_rt_resid_z"] = value
    row["missing_reason_upper_tail_rate_abs_rt_resid_z"] = reason

    delta_u = np.diff(
        pd.to_numeric(ordered["u_t"], errors="coerce").to_numpy(dtype=float)
    )
    value, reason = upper_tail_rate(
        _zscore(delta_u),
        config.tail_z_threshold,
        config.minimum_tail_observations,
    )
    row["upper_tail_rate_abs_delta_u_z"] = value
    row["missing_reason_upper_tail_rate_abs_delta_u_z"] = reason
    return row


def _robust_z_within_sources(
    frame: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    output = frame.copy()
    grouped = output.groupby(
        ["dataset_id", "task_family"],
        observed=True,
        dropna=False,
    )
    for column in columns:
        numeric = pd.to_numeric(output[column], errors="coerce")
        median = grouped[column].transform("median")
        q25 = grouped[column].transform(lambda values: values.quantile(0.25))
        q75 = grouped[column].transform(lambda values: values.quantile(0.75))
        iqr = q75 - q25
        fallback = grouped[column].transform("std")
        scale = iqr.where(iqr.gt(0), fallback)
        output[f"{column}_z"] = (numeric - median) / scale.where(scale.gt(0))
    return output


def add_window_transitions(
    windows: pd.DataFrame,
    config: ZhangTangConfig,
) -> pd.DataFrame:
    """Add safe previous-window deltas, update magnitude, and next outcomes."""
    output = windows.sort_values(
        [*BOUNDARY_COLUMNS, "window_index"],
        kind="stable",
    ).reset_index(drop=True)
    grouped = output.groupby(
        list(BOUNDARY_COLUMNS),
        observed=True,
        dropna=False,
        sort=False,
    )
    previous_index = grouped["window_index"].shift(1)
    next_index = grouped["window_index"].shift(-1)
    safe_previous = previous_index.eq(output["window_index"] - 1)
    safe_next = next_index.eq(output["window_index"] + 1)
    output["has_previous_window"] = safe_previous
    output["has_next_window"] = safe_next

    delta_sources = {
        "delta_throughput": "throughput_proxy",
        "delta_accuracy": "accuracy",
        "delta_rt_cv": "rt_cv",
        "delta_interference_rt_cost": "control_cost_rt_ms",
    }
    for destination, source in delta_sources.items():
        previous = grouped[source].shift(1)
        output[destination] = (output[source] - previous).where(safe_previous)
        output[f"missing_reason_{destination}"] = np.where(
            safe_previous,
            np.where(
                output[destination].notna(),
                None,
                "source_metric_unavailable",
            ),
            "no_previous_window",
        )

    output = _robust_z_within_sources(output, list(delta_sources))
    standardized = [f"{column}_z" for column in delta_sources]
    available_count = output[standardized].notna().sum(axis=1)
    output["combined_update_magnitude"] = np.sqrt(
        output[standardized].pow(2).mean(axis=1, skipna=True)
    ).where(available_count.ge(config.minimum_update_components))
    output["missing_reason_combined_update_magnitude"] = np.where(
        output["combined_update_magnitude"].notna(),
        None,
        np.where(
            safe_previous,
            "insufficient_update_components",
            "no_previous_window",
        ),
    )

    source_groups = output.groupby(
        ["dataset_id", "task_family"],
        observed=True,
        dropna=False,
    )
    thresholds = source_groups["combined_update_magnitude"].transform(
        lambda values: values.quantile(config.large_update_quantile)
    )
    output["large_update_window"] = pd.array(
        np.where(
            output["combined_update_magnitude"].notna(),
            output["combined_update_magnitude"].ge(thresholds).astype(int),
            np.nan,
        ),
        dtype="Int64",
    )
    output["missing_reason_large_update_window"] = np.where(
        output["large_update_window"].notna(),
        None,
        output["missing_reason_combined_update_magnitude"],
    )

    next_sources = {
        "next_accuracy": "accuracy",
        "next_throughput": "throughput_proxy",
        "next_rt_cv": "rt_cv",
        "next_interference_rt_cost": "control_cost_rt_ms",
        "next_error_burstiness": "error_burstiness",
    }
    output["next_window_id"] = grouped["window_id"].shift(-1).where(safe_next)
    for destination, source in next_sources.items():
        shifted = grouped[source].shift(-1)
        output[destination] = shifted.where(safe_next)
        output[f"missing_reason_{destination}"] = np.where(
            safe_next,
            np.where(
                output[destination].notna(),
                None,
                "next_metric_unavailable",
            ),
            "no_next_window",
        )
        change_column = CHANGE_OUTCOMES[destination]
        output[change_column] = (output[destination] - output[source]).where(
            safe_next
        )
    return output


def build_zhang_tang_windows(
    cleaned_trials: pd.DataFrame,
    cognitive_windows: pd.DataFrame,
    config: ZhangTangConfig,
    progress_every: int = 250,
) -> pd.DataFrame:
    """Reconstruct and enrich the registered primary full windows."""
    primary = cognitive_windows[
        cognitive_windows["window_size"].eq(config.primary_window_size)
        & cognitive_windows["window_kind"].eq("full")
        & cognitive_windows["dynamics_eligible"].eq(True)
    ].copy()
    eligible_trials = cleaned_trials[
        cleaned_trials["analysis_eligible_trial"].fillna(False)
    ].copy()
    rows: list[dict[str, Any]] = []
    for count, window in enumerate(
        iter_trial_windows(
            eligible_trials,
            primary_size=config.primary_window_size,
            sensitivity_sizes=(),
            minimum_remainder_trials=config.primary_window_size,
        ),
        start=1,
    ):
        if not (
            int(window.iloc[0]["window_size"]) == config.primary_window_size
            and str(window.iloc[0]["window_kind"]) == "full"
        ):
            continue
        rows.append(summarize_trial_window(window, config))
        if progress_every and count % progress_every == 0:
            print(f"Zhang-Tang features: {count:,} windows", flush=True)
    trial_features = pd.DataFrame(rows)
    expected_ids = set(primary["window_id"].astype(str))
    observed_ids = set(trial_features["window_id"].astype(str))
    if expected_ids != observed_ids:
        missing = sorted(expected_ids - observed_ids)[:5]
        extra = sorted(observed_ids - expected_ids)[:5]
        raise ValueError(
            "Primary window reconstruction mismatch; "
            f"missing={missing}, extra={extra}"
        )
    enriched = primary.merge(
        trial_features,
        on="window_id",
        how="left",
        validate="one_to_one",
    )
    return add_window_transitions(enriched, config)


def build_feature_audit(windows: pd.DataFrame) -> pd.DataFrame:
    """Return dataset-task availability and explicit missingness summaries."""
    features = [
        *MI_FEATURES,
        *UPDATE_FEATURES,
        *TAIL_FEATURES,
        "large_update_window",
        *NEXT_OUTCOMES,
    ]
    rows: list[dict[str, Any]] = []
    for (dataset_id, task), group in windows.groupby(
        ["dataset_id", "task_family"],
        observed=True,
        sort=True,
    ):
        row: dict[str, Any] = {
            "dataset_id": dataset_id,
            "task_family": task,
            "n_windows": int(len(group)),
            "n_subjects": int(group["participant_id"].nunique()),
            "large_update_window_rate": _safe_float(
                pd.to_numeric(
                    group["large_update_window"],
                    errors="coerce",
                )
                .astype(float)
                .mean()
            ),
        }
        for feature in features:
            row[f"availability_rate_{feature}"] = float(
                group[feature].notna().mean()
            )
            reason_column = f"missing_reason_{feature}"
            if reason_column in group:
                counts = (
                    group.loc[group[feature].isna(), reason_column]
                    .fillna("unspecified")
                    .value_counts()
                    .to_dict()
                )
                row[f"missing_reasons_{feature}"] = json.dumps(
                    {str(key): int(value) for key, value in counts.items()},
                    sort_keys=True,
                )
        rows.append(row)
    return pd.DataFrame(rows)


def _composition_json(group: pd.DataFrame, column: str) -> str:
    counts = group[column].astype("string").value_counts(normalize=True)
    return json.dumps(
        {str(key): round(float(value), 6) for key, value in counts.items()},
        sort_keys=True,
    )


def _robust_profile_z(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = frame.copy()
    for column in columns:
        numeric = pd.to_numeric(output[column], errors="coerce")
        median = numeric.median()
        iqr = numeric.quantile(0.75) - numeric.quantile(0.25)
        scale = iqr if np.isfinite(iqr) and iqr > 0 else numeric.std()
        output[f"{column}_profile_z"] = (
            (numeric - median) / scale
            if np.isfinite(scale) and scale > 0
            else 0.0
        )
    return output


def _provisional_note(row: pd.Series, config: ZhangTangConfig) -> str:
    if (
        row["n_windows"] < config.minimum_cluster_windows
        or row["n_subjects"] < config.minimum_cluster_subjects
        or row["n_next_windows"] < 10
    ):
        return "insufficient_data"
    throughput = row.get("mean_throughput_proxy_profile_z", 0.0)
    accuracy = row.get("mean_accuracy_profile_z", 0.0)
    mi = row.get("mean_task_relevant_mi_profile_z", 0.0)
    update = row.get("mean_combined_update_magnitude_profile_z", 0.0)
    tails = row.get("mean_tail_rate_profile_z", 0.0)
    volatility = row.get("mean_rt_volatility_profile_z", 0.0)
    entropy = row.get("mean_cog_perm_entropy3_profile_z", 0.0)
    lag = row.get("mean_cog_lag1_profile_z", 0.0)
    cost = row.get("mean_control_cost_rt_ms_profile_z", 0.0)
    next_utility = row.get("mean_next_utility_profile_z", 0.0)
    if (
        throughput > 0.35
        and accuracy >= 0
        and mi > 0.20
        and tails < 0.50
        and next_utility >= 0
    ):
        return "in_zone_like"
    if throughput < -0.35 and mi < 0 and update < -0.20:
        return "flat_like"
    if entropy < -0.35 and lag > 0.20 and cost > 0.20 and update <= 0:
        return "locked_in_like"
    if (
        (volatility > 0.35 or entropy > 0.35)
        and mi < 0
        and tails > 0.20
        and next_utility <= 0
    ):
        return "spun_out_like"
    return "mixed_or_unclear"


def build_cluster_profiles(
    windows: pd.DataFrame,
    assignments: pd.DataFrame,
    config: ZhangTangConfig,
) -> pd.DataFrame:
    """Profile every neutral task-specific and pooled GMM assignment."""
    change_columns = list(CHANGE_OUTCOMES.values())
    profile_windows = _robust_z_within_sources(windows, change_columns)
    assignment_columns = [
        "analysis",
        "window_id",
        "gmm_cluster_id",
        "gmm_component",
    ]
    selected = assignments[assignment_columns].drop_duplicates()
    if selected.duplicated(["analysis", "window_id"]).any():
        raise ValueError("Cluster assignments are not unique within analysis")
    joined = selected.merge(
        profile_windows,
        on="window_id",
        how="left",
        validate="many_to_one",
    )
    if joined["dataset_id"].isna().any():
        raise ValueError("Cluster assignments could not be joined to windows")

    rows: list[dict[str, Any]] = []
    for (analysis, cluster_id), group in joined.groupby(
        ["analysis", "gmm_cluster_id"],
        observed=True,
        sort=True,
    ):
        task_mi = group[
            [
                "mi_congruency_correct",
                "mi_prev_error_next_correct",
                "mi_condition_efficiency_bin_sens",
            ]
        ].mean(axis=1, skipna=True)
        next_utility = pd.concat(
            [
                group["change_next_accuracy_z"],
                group["change_next_throughput_z"],
                -group["change_next_rt_cv_z"],
                -group["change_next_interference_rt_cost_z"],
                -group["change_next_error_burstiness_z"],
            ],
            axis=1,
        ).mean(axis=1, skipna=True)
        row = {
            "analysis": analysis,
            "gmm_cluster_id": cluster_id,
            "n_windows": int(len(group)),
            "n_subjects": int(group["participant_id"].nunique()),
            "n_datasets": int(group["dataset_id"].nunique()),
            "n_tasks": int(group["task_family"].nunique()),
            "n_next_windows": int(group["has_next_window"].sum()),
            "dataset_composition": _composition_json(group, "dataset_id"),
            "task_composition": _composition_json(group, "task_family"),
            "max_dataset_share": float(
                group["dataset_id"].value_counts(normalize=True).max()
            ),
            "max_task_share": float(
                group["task_family"].value_counts(normalize=True).max()
            ),
            "mean_task_relevant_mi": float(task_mi.mean()),
            "median_task_relevant_mi": float(task_mi.median()),
            "mean_combined_update_magnitude": float(
                group["combined_update_magnitude"].mean()
            ),
            "median_combined_update_magnitude": float(
                group["combined_update_magnitude"].median()
            ),
            "mean_upper_tail_residual_rate": float(
                group["upper_tail_rate_abs_rt_resid_z"].mean()
            ),
            "mean_upper_tail_delta_u_rate": float(
                group["upper_tail_rate_abs_delta_u_z"].mean()
            ),
            "large_update_window_proportion": _safe_float(
                pd.to_numeric(
                    group["large_update_window"],
                    errors="coerce",
                )
                .astype(float)
                .mean()
            ),
            "mean_next_accuracy": float(group["next_accuracy"].mean()),
            "mean_next_throughput": float(group["next_throughput"].mean()),
            "mean_next_rt_cv": float(group["next_rt_cv"].mean()),
            "mean_next_interference_rt_cost": float(
                group["next_interference_rt_cost"].mean()
            ),
            "mean_next_error_burstiness": float(
                group["next_error_burstiness"].mean()
            ),
            "mean_throughput_proxy": float(group["throughput_proxy"].mean()),
            "mean_accuracy": float(group["accuracy"].mean()),
            "mean_rt_volatility": float(group["rt_volatility"].mean()),
            "mean_cog_perm_entropy3": float(
                group["cog_perm_entropy3"].mean()
            ),
            "mean_cog_lag1": float(group["cog_lag1"].mean()),
            "mean_control_cost_rt_ms": float(
                group["control_cost_rt_ms"].mean()
            ),
            "mean_tail_rate": float(
                group[
                    [
                        "upper_tail_rate_abs_rt_resid_z",
                        "upper_tail_rate_abs_delta_u_z",
                    ]
                ]
                .mean(axis=1)
                .mean()
            ),
            "mean_next_utility": float(next_utility.mean()),
        }
        rows.append(row)
    profiles = pd.DataFrame(rows)
    z_columns = [
        "mean_throughput_proxy",
        "mean_accuracy",
        "mean_task_relevant_mi",
        "mean_combined_update_magnitude",
        "mean_tail_rate",
        "mean_rt_volatility",
        "mean_cog_perm_entropy3",
        "mean_cog_lag1",
        "mean_control_cost_rt_ms",
        "mean_next_utility",
    ]
    adjusted: list[pd.DataFrame] = []
    for _, group in profiles.groupby("analysis", observed=True, sort=False):
        adjusted.append(_robust_profile_z(group, z_columns))
    profiles = pd.concat(adjusted, ignore_index=True)
    profiles["provisional_pattern_note"] = profiles.apply(
        _provisional_note,
        axis=1,
        config=config,
    )
    return profiles


def _bootstrap_effect(
    group: pd.DataFrame,
    outcome: str,
    repetitions: int,
    seed: int,
) -> tuple[float, float]:
    participants = group["participant_id"].astype("string").unique()
    if len(participants) < 2:
        return np.nan, np.nan
    indices = {
        participant: group.index[
            group["participant_id"].astype("string").eq(participant)
        ].to_numpy()
        for participant in participants
    }
    rng = np.random.default_rng(seed)
    effects: list[float] = []
    for _ in range(repetitions):
        sampled = rng.choice(participants, size=len(participants), replace=True)
        sample_indices = np.concatenate([indices[value] for value in sampled])
        sample = group.loc[sample_indices]
        means = sample.groupby("large_update_window")[outcome].mean()
        if 0 in means and 1 in means:
            effects.append(float(means.loc[1] - means.loc[0]))
    if not effects:
        return np.nan, np.nan
    return (
        float(np.quantile(effects, 0.025)),
        float(np.quantile(effects, 0.975)),
    )


def build_large_update_usefulness(
    windows: pd.DataFrame,
    config: ZhangTangConfig,
) -> pd.DataFrame:
    """Compare next-window changes after large versus ordinary updates."""
    orientations = {
        "change_next_accuracy": 1,
        "change_next_throughput": 1,
        "change_next_rt_cv": -1,
        "change_next_interference_rt_cost": -1,
        "change_next_error_burstiness": -1,
    }
    rows: list[dict[str, Any]] = []
    for (dataset_id, task), source in windows.groupby(
        ["dataset_id", "task_family"],
        observed=True,
        sort=True,
    ):
        for outcome, orientation in orientations.items():
            usable = source.dropna(
                subset=["large_update_window", outcome, "participant_id"]
            ).copy()
            counts = usable["large_update_window"].value_counts()
            subjects = usable.groupby("large_update_window")[
                "participant_id"
            ].nunique()
            testable = (
                int(counts.get(1, 0)) >= 5
                and int(counts.get(0, 0)) >= 10
                and int(subjects.get(1, 0)) >= 3
                and int(subjects.get(0, 0)) >= 5
            )
            effect = np.nan
            lower = np.nan
            upper = np.nan
            standardized = np.nan
            interpretation = "insufficient_data"
            if testable:
                means = usable.groupby("large_update_window")[outcome].mean()
                effect = float(means.loc[1] - means.loc[0])
                lower, upper = _bootstrap_effect(
                    usable,
                    outcome,
                    config.bootstrap_repetitions,
                    _stable_seed(
                        config.random_seed,
                        dataset_id,
                        task,
                        outcome,
                    ),
                )
                change_sd = float(usable[outcome].std(ddof=0))
                standardized = (
                    orientation * effect / change_sd
                    if np.isfinite(change_sd) and change_sd > 0
                    else np.nan
                )
                useful_lower = orientation * lower
                useful_upper = orientation * upper
                if min(useful_lower, useful_upper) > 0:
                    interpretation = (
                        "improvement"
                        if outcome
                        in {
                            "change_next_accuracy",
                            "change_next_throughput",
                        }
                        else "stabilisation"
                    )
                elif max(useful_lower, useful_upper) < 0:
                    interpretation = "destabilisation"
                else:
                    interpretation = "no clear difference"
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "task_family": task,
                    "outcome": outcome.replace("change_", ""),
                    "n_windows": int(len(usable)),
                    "n_subjects": int(usable["participant_id"].nunique()),
                    "n_large_update": int(counts.get(1, 0)),
                    "n_ordinary_update": int(counts.get(0, 0)),
                    "mean_change_large_update": float(
                        usable.loc[
                            usable["large_update_window"].eq(1),
                            outcome,
                        ].mean()
                    ),
                    "mean_change_ordinary_update": float(
                        usable.loc[
                            usable["large_update_window"].eq(0),
                            outcome,
                        ].mean()
                    ),
                    "large_minus_ordinary_effect": effect,
                    "effect_ci_lower": lower,
                    "effect_ci_upper": upper,
                    "standardized_useful_direction_effect": standardized,
                    "interpretation": interpretation,
                }
            )
    return pd.DataFrame(rows)
