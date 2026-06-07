"""Cognitive dynamics and conflict-control features."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from math import factorial

import numpy as np
import pandas as pd

from .config import PilotConfig
from .windowing import iter_trial_windows


PRIMARY_CLUSTER_CANDIDATES = (
    "throughput_proxy",
    "accuracy",
    "cog_alpha1",
    "cog_lag1",
    "cog_lag2",
    "cog_roughness",
    "cog_sign_change",
    "cog_sd1_sd2",
    "cog_perm_entropy3",
    "cog_diff_entropy",
    "control_cost_rt_ms",
    "control_cost_acc",
    "post_error_slowing_ms",
    "post_error_adjustment_abs_ms",
    "rt_cv",
    "nonresponse_rate",
    "slow_tail_rate",
    "fast_error_rate",
    "rt_volatility",
    "error_burstiness",
    "rt_drift",
)


def _finite(values: pd.Series | np.ndarray) -> np.ndarray:
    numeric = np.asarray(values, dtype=float)
    return numeric[np.isfinite(numeric)]


def dfa_alpha(values: pd.Series | np.ndarray) -> float:
    series = _finite(values)
    if len(series) < 40 or np.std(series) == 0:
        return np.nan
    integrated = np.cumsum(series - np.mean(series))
    scales: list[int] = []
    fluctuations: list[float] = []
    for scale in range(4, 17):
        segment_count = len(integrated) // scale
        if segment_count < 4:
            continue
        residuals: list[np.ndarray] = []
        x = np.arange(scale, dtype=float)
        for index in range(segment_count):
            segment = integrated[index * scale : (index + 1) * scale]
            coefficients = np.polyfit(x, segment, deg=1)
            residuals.append(segment - np.polyval(coefficients, x))
        fluctuation = float(
            np.sqrt(np.mean(np.concatenate(residuals) ** 2))
        )
        if fluctuation > 0:
            scales.append(scale)
            fluctuations.append(fluctuation)
    if len(scales) < 4:
        return np.nan
    return float(
        np.polyfit(np.log(scales), np.log(fluctuations), deg=1)[0]
    )


def lag_correlation(values: pd.Series | np.ndarray, lag: int) -> float:
    series = _finite(values)
    if len(series) <= lag + 2:
        return np.nan
    left = series[lag:]
    right = series[:-lag]
    if np.std(left) == 0 or np.std(right) == 0:
        return np.nan
    return float(np.corrcoef(left, right)[0, 1])


def roughness(values: pd.Series | np.ndarray) -> float:
    series = _finite(values)
    if len(series) < 3:
        return np.nan
    standard_deviation = np.std(series, ddof=1)
    if standard_deviation == 0:
        return np.nan
    return float(np.sqrt(np.mean(np.diff(series) ** 2)) / standard_deviation)


def sign_change_rate(values: pd.Series | np.ndarray) -> float:
    differences = np.diff(_finite(values))
    signs = np.sign(differences)
    signs = signs[signs != 0]
    if len(signs) < 2:
        return np.nan
    return float(np.mean(signs[1:] != signs[:-1]))


def sd1_sd2_ratio(values: pd.Series | np.ndarray) -> float:
    series = _finite(values)
    if len(series) < 3:
        return np.nan
    rmssd = np.sqrt(np.mean(np.diff(series) ** 2))
    sdnn = np.std(series, ddof=1)
    sd1 = rmssd / np.sqrt(2)
    sd2_squared = 2 * sdnn**2 - 0.5 * rmssd**2
    if sd2_squared <= 0:
        return np.nan
    return float(sd1 / np.sqrt(sd2_squared))


def permutation_entropy_3(values: pd.Series | np.ndarray) -> float:
    series = _finite(values)
    if len(series) < 5:
        return np.nan
    patterns = [
        tuple(np.argsort(series[index : index + 3], kind="stable"))
        for index in range(len(series) - 2)
    ]
    counts = np.asarray(list(Counter(patterns).values()), dtype=float)
    probabilities = counts / counts.sum()
    entropy = -np.sum(probabilities * np.log(probabilities))
    return float(entropy / np.log(factorial(3)))


def difference_entropy(
    values: pd.Series | np.ndarray,
    bins: int = 16,
) -> float:
    differences = np.diff(_finite(values))
    if len(differences) < 4:
        return np.nan
    clip = float(np.quantile(np.abs(differences), 0.95))
    if not np.isfinite(clip) or clip <= 0:
        return np.nan
    clipped = np.clip(differences, -clip, clip)
    counts, _ = np.histogram(clipped, bins=bins, range=(-clip, clip))
    probabilities = counts[counts > 0] / counts.sum()
    entropy = -np.sum(probabilities * np.log(probabilities))
    return float(entropy / np.log(bins))


def _slope(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.notna()
    if valid.sum() < 3:
        return np.nan
    x = np.arange(len(numeric), dtype=float)[valid]
    y = numeric.loc[valid].to_numpy(dtype=float)
    if np.std(x) == 0:
        return np.nan
    return float(np.polyfit(x, y, deg=1)[0])


def _mean_absolute_temporal_difference(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    differences = np.abs(np.diff(numeric))
    finite = differences[np.isfinite(differences)]
    if len(finite) == 0:
        return np.nan
    return float(np.mean(finite))


def _control_costs(
    trials: pd.DataFrame,
    minimum_trials: int,
) -> dict[str, float | int | bool]:
    congruency = trials["congruency"].astype("string")
    correct = pd.to_numeric(trials["correct"], errors="coerce")
    rt = pd.to_numeric(trials["rt_ms"], errors="coerce")
    valid_correct = trials["valid_correct_rt"].fillna(False)
    congruent_rt = rt[valid_correct & congruency.eq("congruent")]
    incongruent_rt = rt[valid_correct & congruency.eq("incongruent")]
    congruent_acc = correct[congruency.eq("congruent")]
    incongruent_acc = correct[congruency.eq("incongruent")]
    supported = (
        congruent_rt.notna().sum() >= minimum_trials
        and incongruent_rt.notna().sum() >= minimum_trials
        and congruent_acc.notna().sum() >= minimum_trials
        and incongruent_acc.notna().sum() >= minimum_trials
    )
    return {
        "control_cost_supported": bool(supported),
        "control_cost_congruent_n": int(congruent_rt.notna().sum()),
        "control_cost_incongruent_n": int(incongruent_rt.notna().sum()),
        "control_cost_rt_ms": (
            float(incongruent_rt.mean() - congruent_rt.mean())
            if supported
            else np.nan
        ),
        "control_cost_acc": (
            float(congruent_acc.mean() - incongruent_acc.mean())
            if supported
            else np.nan
        ),
    }


def _post_error_slowing(
    trials: pd.DataFrame,
    minimum_post_error: int,
    minimum_post_correct: int,
) -> dict[str, float | int | bool]:
    ordered = trials.sort_values(
        ["trial_raw", "observation_id"],
        kind="stable",
        na_position="last",
    )
    correct = pd.to_numeric(ordered["correct"], errors="coerce")
    rt = pd.to_numeric(ordered["rt_ms"], errors="coerce")
    valid_current = ordered["valid_correct_rt"].fillna(False)
    previous_correct = correct.shift(1)
    post_error = rt[valid_current & previous_correct.eq(0)]
    post_correct = rt[valid_current & previous_correct.eq(1)]
    supported = (
        post_error.notna().sum() >= minimum_post_error
        and post_correct.notna().sum() >= minimum_post_correct
    )
    return {
        "pes_supported": bool(supported),
        "pes_post_error_n": int(post_error.notna().sum()),
        "pes_post_correct_n": int(post_correct.notna().sum()),
        "post_error_slowing_ms": (
            float(post_error.mean() - post_correct.mean())
            if supported
            else np.nan
        ),
    }


def _error_burstiness(correct: pd.Series) -> float:
    errors = pd.to_numeric(correct, errors="coerce").eq(0).to_numpy(dtype=float)
    if len(errors) < 2:
        return np.nan
    error_rate = errors.mean()
    expected_pairs = (len(errors) - 1) * error_rate**2
    observed_pairs = float(np.sum((errors[:-1] == 1) & (errors[1:] == 1)))
    if expected_pairs == 0:
        return 0.0
    return observed_pairs / expected_pairs


def summarize_window(
    trials: pd.DataFrame,
    config: PilotConfig,
) -> dict[str, object]:
    first = trials.iloc[0]
    correct = pd.to_numeric(trials["correct"], errors="coerce")
    correct_rt = pd.to_numeric(
        trials.loc[trials["valid_correct_rt"], "rt_ms"],
        errors="coerce",
    ).dropna()
    u_values = pd.to_numeric(trials["u_t"], errors="coerce")
    dynamics_eligible = bool(first["dynamics_eligible"])
    median_rt = float(correct_rt.median()) if not correct_rt.empty else np.nan
    accuracy = float(correct.mean()) if correct.notna().any() else np.nan
    mean_rt = float(correct_rt.mean()) if not correct_rt.empty else np.nan
    sd_rt = float(correct_rt.std(ddof=1)) if len(correct_rt) > 1 else np.nan

    row: dict[str, object] = {
        "window_id": first["window_id"],
        "dataset_id": first["dataset_id"],
        "participant_id": first["participant_id"],
        "task_family": first["task_family"],
        "control_cost_type": first.get("control_cost_type", pd.NA),
        "block_raw": first["block_raw"],
        "window_size": int(first["window_size"]),
        "window_index": int(first["window_index"]),
        "window_kind": first["window_kind"],
        "dynamics_eligible": dynamics_eligible,
        "n_trials": int(len(trials)),
        "n_valid_rt": int(trials["valid_rt"].sum()),
        "n_valid_correct_rt": int(trials["valid_correct_rt"].sum()),
        "accuracy": accuracy,
        "median_rt_ms": median_rt,
        "mean_rt_ms": mean_rt,
        "rt_cv": (
            float(sd_rt / mean_rt)
            if np.isfinite(sd_rt) and np.isfinite(mean_rt) and mean_rt > 0
            else np.nan
        ),
        "throughput_proxy": (
            float(accuracy / (median_rt / 1000.0))
            if np.isfinite(accuracy) and np.isfinite(median_rt) and median_rt > 0
            else np.nan
        ),
        "nonresponse_rate": float(trials["lapse_proxy"].mean()),
        "slow_tail_rate": float(trials["slow_tail_sensitivity"].mean()),
        "fast_error_rate": float(trials["fast_error"].mean()),
        "rt_volatility": _mean_absolute_temporal_difference(
            trials["log_rt_residual"]
        ),
        "error_burstiness": float(_error_burstiness(correct)),
        "rt_drift": _slope(trials["log_rt_residual"]),
        "error_drift": _slope(1 - correct),
        "rt_excluded_fraction": float(trials["rt_excluded"].mean()),
        "residualisation_ok_fraction": float(
            trials["residualisation_status"].eq("ok").mean()
        ),
    }
    row.update(
        _control_costs(trials, config.minimum_condition_trials)
    )
    row.update(
        _post_error_slowing(
            trials,
            config.minimum_pes_post_error_trials,
            config.minimum_pes_post_correct_trials,
        )
    )
    row["post_error_adjustment_abs_ms"] = (
        abs(float(row["post_error_slowing_ms"]))
        if np.isfinite(row["post_error_slowing_ms"])
        else np.nan
    )

    if dynamics_eligible:
        row.update(
            {
                "cog_alpha1": dfa_alpha(u_values),
                "cog_lag1": lag_correlation(u_values, 1),
                "cog_lag2": lag_correlation(u_values, 2),
                "cog_roughness": roughness(u_values),
                "cog_sign_change": sign_change_rate(u_values),
                "cog_sd1_sd2": sd1_sd2_ratio(u_values),
                "cog_perm_entropy3": permutation_entropy_3(u_values),
                "cog_diff_entropy": difference_entropy(u_values),
            }
        )
    else:
        row.update(
            {
                "cog_alpha1": np.nan,
                "cog_lag1": np.nan,
                "cog_lag2": np.nan,
                "cog_roughness": np.nan,
                "cog_sign_change": np.nan,
                "cog_sd1_sd2": np.nan,
                "cog_perm_entropy3": np.nan,
                "cog_diff_entropy": np.nan,
            }
        )
    return row


def summarize_windows(
    windowed_trials: pd.DataFrame,
    config: PilotConfig,
) -> pd.DataFrame:
    """Return one feature row per trial-count window."""
    if windowed_trials.empty:
        return pd.DataFrame()
    rows = [
        summarize_window(group, config)
        for _, group in windowed_trials.groupby(
            "window_id",
            sort=True,
            dropna=False,
        )
    ]
    return pd.DataFrame(rows)


def build_window_features(
    trials: pd.DataFrame,
    config: PilotConfig,
    progress_every: int = 0,
    progress_callback: Callable[[int], None] | None = None,
) -> pd.DataFrame:
    """Summarize yielded windows without triplicating the trial table."""
    rows: list[dict[str, object]] = []
    for count, window in enumerate(
        iter_trial_windows(
            trials,
            primary_size=config.primary_window_size,
            sensitivity_sizes=config.sensitivity_window_sizes,
            minimum_remainder_trials=config.minimum_remainder_trials,
        ),
        start=1,
    ):
        rows.append(summarize_window(window, config))
        if (
            progress_every > 0
            and progress_callback is not None
            and count % progress_every == 0
        ):
            progress_callback(count)
    return pd.DataFrame(rows)
