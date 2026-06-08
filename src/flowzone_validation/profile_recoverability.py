"""Short-window profile recovery and repeated-measures diagnostics."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    log_loss,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

from .cognitive_features import summarize_window
from .config import PilotConfig
from .windowing import iter_trial_windows


SHORT_TEST_FEATURES = (
    "accuracy",
    "throughput_proxy",
    "median_rt_ms",
    "rt_cv",
    "control_cost_rt_ms",
    "control_cost_acc",
    "cog_lag1",
    "cog_lag2",
    "cog_roughness",
    "cog_sign_change",
    "cog_sd1_sd2",
    "cog_perm_entropy3",
    "cog_diff_entropy",
    "nonresponse_rate",
    "slow_tail_rate",
    "fast_error_rate",
    "rt_volatility",
    "error_burstiness",
    "rt_drift",
)


def build_prefix_features(
    trials: pd.DataFrame,
    target_window_ids: set[str],
    config: PilotConfig,
    trial_counts: Iterable[int] = (20, 30, 40, 50, 60, 80),
) -> pd.DataFrame:
    """Summarize prefixes of the exact primary windows used for clustering."""
    counts = sorted(set(int(value) for value in trial_counts))
    if not counts or counts[-1] > config.primary_window_size:
        raise ValueError("Trial counts must be within the primary window size")
    eligible = trials[
        trials["analysis_eligible_trial"] & trials["task_family"].eq("Stroop")
    ].copy()
    rows: list[dict[str, Any]] = []
    observed: set[str] = set()
    for window in iter_trial_windows(
        eligible,
        primary_size=config.primary_window_size,
        sensitivity_sizes=(),
        minimum_remainder_trials=config.minimum_remainder_trials,
    ):
        parent_id = str(window["window_id"].iloc[0])
        if (
            parent_id not in target_window_ids
            or window["window_kind"].iloc[0] != "full"
        ):
            continue
        observed.add(parent_id)
        for trial_count in counts:
            prefix = window.iloc[:trial_count].copy()
            prefix["window_id"] = f"{parent_id}:prefix:{trial_count}"
            prefix["window_size"] = trial_count
            prefix["window_index"] = window["window_index"].iloc[0]
            prefix["window_kind"] = "prefix"
            prefix["dynamics_eligible"] = True
            row = summarize_window(prefix, config)
            row["parent_window_id"] = parent_id
            row["trial_count"] = trial_count
            rows.append(row)
    missing = target_window_ids - observed
    if missing:
        raise ValueError(
            f"Could not reconstruct {len(missing)} target primary windows"
        )
    return pd.DataFrame(rows)


def grouped_profile_recovery(
    frame: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    *,
    group_column: str = "participant_id",
    folds: int = 5,
    confidence_threshold: float = 0.60,
    seed: int = 42,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Recover full-window neutral profiles without participant leakage."""
    required = {target_column, group_column, *feature_columns}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing profile recovery columns: {sorted(missing)}")
    usable_features = [
        column
        for column in feature_columns
        if frame[column].notna().any() and frame[column].nunique(dropna=True) > 1
    ]
    if not usable_features:
        raise ValueError("No usable short-test features")
    usable = frame.dropna(subset=[target_column, group_column]).reset_index(drop=True)
    groups = usable[group_column].astype("string")
    labels = sorted(usable[target_column].astype(str).unique())
    y = usable[target_column].astype(str).to_numpy()
    splitter = StratifiedGroupKFold(
        n_splits=min(folds, groups.nunique()),
        shuffle=True,
        random_state=seed,
    )
    probabilities = np.full((len(usable), len(labels)), np.nan)
    predictions = np.full(len(usable), "", dtype=object)
    fold_ids = np.full(len(usable), -1, dtype=int)
    maximum_overlap = 0

    for fold, (train_index, test_index) in enumerate(
        splitter.split(usable, y, groups),
        start=1,
    ):
        overlap = set(groups.iloc[train_index]) & set(groups.iloc[test_index])
        maximum_overlap = max(maximum_overlap, len(overlap))
        numeric = make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            RobustScaler(),
        )
        model = make_pipeline(
            ColumnTransformer(
                [("numeric", numeric, usable_features)],
                remainder="drop",
            ),
            LogisticRegression(
                class_weight="balanced",
                max_iter=3000,
                random_state=seed,
            ),
        )
        model.fit(usable.iloc[train_index], y[train_index])
        fold_model = model[-1]
        fold_probabilities = model.predict_proba(usable.iloc[test_index])
        class_positions = {
            label: index for index, label in enumerate(fold_model.classes_)
        }
        for label_index, label in enumerate(labels):
            probabilities[test_index, label_index] = fold_probabilities[
                :, class_positions[label]
            ]
        predictions[test_index] = np.asarray(labels)[
            probabilities[test_index].argmax(axis=1)
        ]
        fold_ids[test_index] = fold

    confidence = probabilities.max(axis=1)
    confident = confidence >= confidence_threshold
    metrics: dict[str, Any] = {
        "status": "ok",
        "n_windows": len(usable),
        "n_subjects": groups.nunique(),
        "folds": int(fold_ids.max()),
        "maximum_participant_overlap": maximum_overlap,
        "features": usable_features,
        "feature_count": len(usable_features),
        "accuracy": float(accuracy_score(y, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predictions)),
        "macro_f1": float(f1_score(y, predictions, average="macro")),
        "log_loss": float(log_loss(y, probabilities, labels=labels)),
        "mean_confidence": float(confidence.mean()),
        "confidence_threshold": confidence_threshold,
        "confident_coverage": float(confident.mean()),
        "confident_accuracy": (
            float(accuracy_score(y[confident], predictions[confident]))
            if confident.any()
            else np.nan
        ),
        "per_class_recall": dict(
            zip(
                labels,
                recall_score(
                    y,
                    predictions,
                    labels=labels,
                    average=None,
                    zero_division=0,
                ),
                strict=True,
            )
        ),
    }
    prediction_frame = usable[
        ["parent_window_id", "participant_id", "dataset_id", target_column]
    ].copy()
    prediction_frame["predicted_profile"] = predictions
    prediction_frame["prediction_confidence"] = confidence
    prediction_frame["confident_prediction"] = confident
    prediction_frame["fold"] = fold_ids
    for index, label in enumerate(labels):
        prediction_frame[f"probability_{label}"] = probabilities[:, index]
    return metrics, prediction_frame


def _pair_agreement(frame: pd.DataFrame, label_column: str) -> float:
    same = 0
    total = 0
    for _, group in frame.groupby("participant_id", sort=False):
        counts = group[label_column].value_counts().to_numpy()
        size = int(counts.sum())
        same += int(np.sum(counts * (counts - 1) // 2))
        total += size * (size - 1) // 2
    return float(same / total) if total else np.nan


def profile_repeatability(
    frame: pd.DataFrame,
    label_column: str,
    *,
    permutations: int = 1000,
    seed: int = 42,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Quantify participant occupancy and adjacent profile persistence."""
    required = {
        "participant_id",
        "dataset_id",
        "block_raw",
        "window_index",
        label_column,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing repeatability columns: {sorted(missing)}")
    ordered = frame.sort_values(
        ["dataset_id", "participant_id", "block_raw", "window_index"],
        kind="stable",
    ).reset_index(drop=True)
    labels = sorted(ordered[label_column].astype(str).unique())
    occupancy_rows: list[dict[str, Any]] = []
    for participant, group in ordered.groupby("participant_id", sort=True):
        counts = group[label_column].value_counts()
        probabilities = counts / counts.sum()
        entropy = float(
            -(probabilities * np.log(probabilities)).sum() / np.log(len(labels))
        )
        row: dict[str, Any] = {
            "participant_id": participant,
            "dataset_id": group["dataset_id"].iloc[0],
            "n_windows": len(group),
            "modal_profile": counts.index[0],
            "modal_share": float(counts.iloc[0] / len(group)),
            "normalized_profile_entropy": entropy,
            "profiles_observed": int(len(counts)),
        }
        for label in labels:
            row[f"share_{label}"] = float(counts.get(label, 0) / len(group))
        occupancy_rows.append(row)
    occupancy = pd.DataFrame(occupancy_rows)

    observed_pair_agreement = _pair_agreement(ordered, label_column)
    rng = np.random.default_rng(seed)
    permutation_values: list[float] = []
    for _ in range(permutations):
        shuffled = ordered.copy()
        shuffled[label_column] = (
            shuffled.groupby("dataset_id", sort=False)[label_column]
            .transform(lambda values: rng.permutation(values.to_numpy()))
            .to_numpy()
        )
        permutation_values.append(_pair_agreement(shuffled, label_column))
    permutation_array = np.asarray(permutation_values)

    transition_counts = pd.DataFrame(0, index=labels, columns=labels, dtype=int)
    adjacent_pairs = 0
    adjacent_same = 0
    for _, group in ordered.groupby(
        ["participant_id", "block_raw"],
        dropna=False,
        sort=False,
    ):
        group = group.sort_values("window_index")
        current = group.iloc[:-1]
        following = group.iloc[1:]
        for (_, left), (_, right) in zip(
            current.iterrows(),
            following.iterrows(),
            strict=True,
        ):
            if int(right["window_index"]) != int(left["window_index"]) + 1:
                continue
            source = str(left[label_column])
            destination = str(right[label_column])
            transition_counts.loc[source, destination] += 1
            adjacent_pairs += 1
            adjacent_same += int(source == destination)
    transition_rows: list[dict[str, Any]] = []
    for source in labels:
        total = int(transition_counts.loc[source].sum())
        for destination in labels:
            count = int(transition_counts.loc[source, destination])
            transition_rows.append(
                {
                    "from_profile": source,
                    "to_profile": destination,
                    "count": count,
                    "row_probability": float(count / total) if total else np.nan,
                }
            )
    transitions = pd.DataFrame(transition_rows)
    global_probabilities = ordered[label_column].value_counts(normalize=True)
    chance_adjacent_same = float(np.sum(global_probabilities.to_numpy() ** 2))
    metrics = {
        "n_windows": len(ordered),
        "n_subjects": ordered["participant_id"].nunique(),
        "median_windows_per_subject": float(
            ordered.groupby("participant_id").size().median()
        ),
        "mean_modal_share": float(occupancy["modal_share"].mean()),
        "median_modal_share": float(occupancy["modal_share"].median()),
        "mean_normalized_profile_entropy": float(
            occupancy["normalized_profile_entropy"].mean()
        ),
        "participants_with_multiple_profiles_fraction": float(
            occupancy["profiles_observed"].gt(1).mean()
        ),
        "within_participant_pair_agreement": observed_pair_agreement,
        "permutation_pair_agreement_mean": float(permutation_array.mean()),
        "permutation_pair_agreement_p_value": float(
            (1 + np.sum(permutation_array >= observed_pair_agreement))
            / (permutations + 1)
        ),
        "adjacent_pairs": adjacent_pairs,
        "adjacent_same_profile_rate": (
            float(adjacent_same / adjacent_pairs) if adjacent_pairs else np.nan
        ),
        "marginal_chance_same_profile_rate": chance_adjacent_same,
    }
    return metrics, occupancy, transitions


def one_way_icc(
    frame: pd.DataFrame,
    feature_columns: list[str],
    group_column: str = "participant_id",
) -> pd.DataFrame:
    """Estimate unbalanced one-way random-effects ICC(1) per feature."""
    rows: list[dict[str, Any]] = []
    for feature in feature_columns:
        usable = frame[[group_column, feature]].copy()
        usable[feature] = pd.to_numeric(usable[feature], errors="coerce")
        usable = usable.dropna()
        group_sizes = usable.groupby(group_column).size()
        usable = usable[
            usable[group_column].isin(group_sizes[group_sizes >= 2].index)
        ]
        n = len(usable)
        k = usable[group_column].nunique()
        if k < 2 or n <= k:
            continue
        grand = float(usable[feature].mean())
        grouped = usable.groupby(group_column)[feature]
        means = grouped.mean()
        sizes = grouped.size()
        ss_between = float(np.sum(sizes * (means - grand) ** 2))
        centered = usable[feature] - usable[group_column].map(means)
        ss_within = float(np.sum(centered**2))
        ms_between = ss_between / (k - 1)
        ms_within = ss_within / (n - k)
        n0 = float((n - np.sum(sizes.to_numpy() ** 2) / n) / (k - 1))
        denominator = ms_between + (n0 - 1) * ms_within
        icc = (ms_between - ms_within) / denominator if denominator else np.nan
        rows.append(
            {
                "feature": feature,
                "icc_1": float(icc),
                "n_windows": n,
                "n_subjects": k,
                "mean_windows_per_subject": float(n / k),
                "interpretation": (
                    "mostly_between_person"
                    if icc >= 0.50
                    else "mixed"
                    if icc >= 0.25
                    else "mostly_within_person"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("icc_1", ascending=False)
