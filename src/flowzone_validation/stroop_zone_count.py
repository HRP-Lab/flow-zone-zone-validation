"""Focused Stroop comparison of discrete mixtures and continuous factors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.decomposition import FactorAnalysis, PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import RobustScaler


@dataclass(frozen=True)
class StroopZoneCountResult:
    model_comparison: pd.DataFrame
    dataset_holdout: pd.DataFrame
    assignments: pd.DataFrame
    standardized_features: pd.DataFrame
    pca_metrics: dict[str, Any]


def _posterior_entropy(probabilities: np.ndarray) -> float:
    clipped = np.clip(probabilities, 1e-12, 1.0)
    entropy = -np.sum(clipped * np.log(clipped), axis=1)
    return float(np.mean(entropy / np.log(probabilities.shape[1])))


def _parameter_count(k: int, dimensions: int, covariance: str) -> int:
    covariance_parameters = (
        dimensions if covariance == "diag" else dimensions * (dimensions + 1) // 2
    )
    return k * (dimensions + covariance_parameters) + (k - 1)


def _valid_component_sizes(labels: np.ndarray) -> bool:
    counts = np.bincount(labels)
    return bool(np.all(counts >= 20) and np.all(counts / len(labels) >= 0.05))


def _well_conditioned(model: GaussianMixture) -> bool:
    if model.covariance_type != "full":
        return True
    conditions = [np.linalg.cond(covariance) for covariance in model.covariances_]
    return bool(
        conditions
        and np.all(np.isfinite(conditions))
        and max(conditions) < 1e8
    )


def _select_pca(
    training: np.ndarray,
    seed: int,
) -> tuple[PCA, np.ndarray]:
    maximum = min(6, training.shape[1], training.shape[0] - 1)
    initial = PCA(n_components=maximum, random_state=seed).fit(training)
    cumulative = np.cumsum(initial.explained_variance_ratio_)
    count = min(maximum, max(1, int(np.searchsorted(cumulative, 0.80) + 1)))
    pca = PCA(n_components=count, random_state=seed)
    return pca, pca.fit_transform(training)


def _source_adjust(
    training: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    train_values = training[features].apply(pd.to_numeric, errors="coerce").copy()
    test_values = test[features].apply(pd.to_numeric, errors="coerce").copy()
    train_datasets = training["dataset_id"].astype("string")
    test_datasets = test["dataset_id"].astype("string")

    for feature in features:
        global_median = float(train_values[feature].median())
        train_values[feature] = train_values[feature].fillna(global_median)
        test_values[feature] = test_values[feature].fillna(global_median)
        global_q25 = float(train_values[feature].quantile(0.25))
        global_q75 = float(train_values[feature].quantile(0.75))
        global_iqr = global_q75 - global_q25
        if not np.isfinite(global_iqr) or global_iqr <= 0:
            global_iqr = 1.0

        for dataset in test_datasets.unique():
            train_mask = train_datasets.eq(dataset)
            test_mask = test_datasets.eq(dataset)
            if train_mask.any():
                median = float(train_values.loc[train_mask, feature].median())
                q25 = float(train_values.loc[train_mask, feature].quantile(0.25))
                q75 = float(train_values.loc[train_mask, feature].quantile(0.75))
                iqr = q75 - q25
                if not np.isfinite(iqr) or iqr <= 0:
                    iqr = global_iqr
            else:
                # Match the pilot's within-source adjustment for dataset holdout.
                median = float(test_values.loc[test_mask, feature].median())
                q25 = float(test_values.loc[test_mask, feature].quantile(0.25))
                q75 = float(test_values.loc[test_mask, feature].quantile(0.75))
                iqr = q75 - q25
                if not np.isfinite(iqr) or iqr <= 0:
                    median = global_median
                    iqr = global_iqr
            test_values.loc[test_mask, feature] = (
                test_values.loc[test_mask, feature] - median
            ) / iqr

        for dataset in train_datasets.unique():
            mask = train_datasets.eq(dataset)
            median = float(train_values.loc[mask, feature].median())
            q25 = float(train_values.loc[mask, feature].quantile(0.25))
            q75 = float(train_values.loc[mask, feature].quantile(0.75))
            iqr = q75 - q25
            if not np.isfinite(iqr) or iqr <= 0:
                iqr = global_iqr
            train_values.loc[mask, feature] = (
                train_values.loc[mask, feature] - median
            ) / iqr

    return train_values.to_numpy(dtype=float), test_values.to_numpy(dtype=float)


def _participant_bootstrap_ari(
    scores: np.ndarray,
    reference_labels: np.ndarray,
    participants: pd.Series,
    k: int,
    covariance: str,
    repetitions: int,
    seed: int,
) -> list[float]:
    rng = np.random.default_rng(seed)
    groups = participants.astype("string").to_numpy()
    unique_groups = np.unique(groups)
    indices = {group: np.flatnonzero(groups == group) for group in unique_groups}
    values: list[float] = []
    for repetition in range(repetitions):
        sampled = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        sampled_indices = np.concatenate([indices[group] for group in sampled])
        model = GaussianMixture(
            n_components=k,
            covariance_type=covariance,
            n_init=5,
            random_state=seed + repetition + 1,
            reg_covar=1e-6,
        )
        try:
            model.fit(scores[sampled_indices])
            values.append(
                float(adjusted_rand_score(reference_labels, model.predict(scores)))
            )
        except ValueError:
            continue
    return values


def compare_stroop_zone_counts(
    frame: pd.DataFrame,
    features: list[str],
    *,
    k_values: Iterable[int] = (2, 3, 4),
    covariances: Iterable[str] = ("diag", "full"),
    n_init: int = 20,
    bootstrap_repetitions: int = 50,
    seed: int = 42,
) -> StroopZoneCountResult:
    """Compare constrained GMMs in the established source-adjusted PCA space."""
    required = {"window_id", "participant_id", "dataset_id", *features}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing Stroop comparison columns: {sorted(missing)}")
    if frame["dataset_id"].nunique() < 3:
        raise ValueError("At least three Stroop datasets are required")

    adjusted, _ = _source_adjust(frame, frame, features)
    scaler = RobustScaler()
    standardized_array = scaler.fit_transform(adjusted)
    adjusted_names = [f"{feature}__source_adjusted" for feature in features]
    standardized = pd.DataFrame(
        standardized_array,
        columns=adjusted_names,
        index=frame.index,
    )
    pca, scores = _select_pca(standardized_array, seed)

    comparison_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    assignments = frame[
        ["window_id", "participant_id", "dataset_id"]
    ].reset_index(drop=True)
    for covariance in covariances:
        for k in k_values:
            model_id = f"Stroop-GMM{k}-{covariance}"
            parameter_count = _parameter_count(k, scores.shape[1], covariance)
            if covariance == "full" and len(frame) <= 10 * parameter_count:
                comparison_rows.append(
                    {
                        "model_id": model_id,
                        "k": k,
                        "covariance": covariance,
                        "valid": False,
                        "invalid_reason": "insufficient_rows_for_full_covariance",
                        "parameter_count": parameter_count,
                    }
                )
                continue
            model = GaussianMixture(
                n_components=k,
                covariance_type=covariance,
                n_init=n_init,
                random_state=seed,
                reg_covar=1e-6,
            )
            labels = model.fit_predict(scores)
            component_valid = _valid_component_sizes(labels)
            conditioned = _well_conditioned(model)
            valid = component_valid and conditioned
            probabilities = model.predict_proba(scores)
            bootstrap = _participant_bootstrap_ari(
                scores,
                labels,
                frame["participant_id"],
                k,
                covariance,
                bootstrap_repetitions,
                seed,
            )

            lodo_ari: list[float] = []
            lodo_log_likelihood: list[float] = []
            for offset, dataset in enumerate(sorted(frame["dataset_id"].unique())):
                held_out = frame["dataset_id"].eq(dataset).to_numpy()
                train_frame = frame.loc[~held_out]
                test_frame = frame.loc[held_out]
                train_adjusted, test_adjusted = _source_adjust(
                    train_frame,
                    test_frame,
                    features,
                )
                fold_scaler = RobustScaler()
                train_standardized = fold_scaler.fit_transform(train_adjusted)
                test_standardized = fold_scaler.transform(test_adjusted)
                fold_pca, train_scores = _select_pca(train_standardized, seed)
                test_scores = fold_pca.transform(test_standardized)
                fold_model = GaussianMixture(
                    n_components=k,
                    covariance_type=covariance,
                    n_init=n_init,
                    random_state=seed + offset + 1,
                    reg_covar=1e-6,
                )
                try:
                    fold_model.fit(train_scores)
                    predicted = fold_model.predict(test_scores)
                    ari = float(adjusted_rand_score(labels[held_out], predicted))
                    log_likelihood = float(fold_model.score(test_scores))
                except ValueError:
                    ari = np.nan
                    log_likelihood = np.nan
                holdout_rows.append(
                    {
                        "model_id": model_id,
                        "k": k,
                        "covariance": covariance,
                        "held_out_dataset": dataset,
                        "n_train": int((~held_out).sum()),
                        "n_test": int(held_out.sum()),
                        "assignment_ari": ari,
                        "mean_log_likelihood": log_likelihood,
                    }
                )
                if np.isfinite(ari):
                    lodo_ari.append(ari)
                if np.isfinite(log_likelihood):
                    lodo_log_likelihood.append(log_likelihood)

            counts = np.bincount(labels, minlength=k)
            comparison_rows.append(
                {
                    "model_id": model_id,
                    "k": k,
                    "covariance": covariance,
                    "valid": valid,
                    "invalid_reason": (
                        ""
                        if valid
                        else (
                            "component_size_rule"
                            if not component_valid
                            else "ill_conditioned_covariance"
                        )
                    ),
                    "parameter_count": parameter_count,
                    "bic": float(model.bic(scores)),
                    "aic": float(model.aic(scores)),
                    "silhouette": float(silhouette_score(scores, labels)),
                    "posterior_entropy": _posterior_entropy(probabilities),
                    "mean_max_posterior": float(probabilities.max(axis=1).mean()),
                    "minimum_component_size": int(counts.min()),
                    "minimum_component_fraction": float(counts.min() / len(labels)),
                    "component_sizes": "|".join(str(value) for value in counts),
                    "bootstrap_ari_median": (
                        float(np.median(bootstrap)) if bootstrap else np.nan
                    ),
                    "bootstrap_ari_lower": (
                        float(np.quantile(bootstrap, 0.025)) if bootstrap else np.nan
                    ),
                    "bootstrap_ari_upper": (
                        float(np.quantile(bootstrap, 0.975)) if bootstrap else np.nan
                    ),
                    "lodo_ari_median": (
                        float(np.median(lodo_ari)) if lodo_ari else np.nan
                    ),
                    "lodo_ari_minimum": min(lodo_ari) if lodo_ari else np.nan,
                    "lodo_mean_log_likelihood": (
                        float(np.mean(lodo_log_likelihood))
                        if lodo_log_likelihood
                        else np.nan
                    ),
                }
            )
            assignments[f"{model_id}_cluster_id"] = [
                f"{model_id}-C{label + 1}" for label in labels
            ]
            assignments[f"{model_id}_max_posterior"] = probabilities.max(axis=1)

    return StroopZoneCountResult(
        model_comparison=pd.DataFrame(comparison_rows),
        dataset_holdout=pd.DataFrame(holdout_rows),
        assignments=assignments,
        standardized_features=standardized.reset_index(drop=True),
        pca_metrics={
            "components": int(scores.shape[1]),
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
            "cumulative_explained_variance": float(
                pca.explained_variance_ratio_.sum()
            ),
            "loadings": {
                f"pc{index + 1}": dict(zip(adjusted_names, values, strict=True))
                for index, values in enumerate(pca.components_)
            },
        },
    )


def compare_continuous_and_mixture_models(
    frame: pd.DataFrame,
    features: list[str],
    *,
    k_values: Iterable[int] = (2, 3, 4),
    factor_counts: Iterable[int] = (1, 2, 3, 4, 5, 6),
    repetitions: int = 20,
    test_size: float = 0.20,
    n_init: int = 20,
    seed: int = 42,
) -> pd.DataFrame:
    """Compare same-space density models on participant-grouped holdouts."""
    groups = frame["participant_id"].astype("string")
    splitter = GroupShuffleSplit(
        n_splits=repetitions,
        test_size=test_size,
        random_state=seed,
    )
    rows: list[dict[str, Any]] = []
    for split, (train_index, test_index) in enumerate(
        splitter.split(frame, groups=groups),
        start=1,
    ):
        train = frame.iloc[train_index]
        test = frame.iloc[test_index]
        if set(train["participant_id"]) & set(test["participant_id"]):
            raise AssertionError("Participant leakage in grouped density split")
        train_array, test_array = _source_adjust(train, test, features)
        scaler = RobustScaler()
        train_array = scaler.fit_transform(train_array)
        test_array = scaler.transform(test_array)

        for factors in factor_counts:
            if factors >= min(train_array.shape):
                continue
            model = FactorAnalysis(
                n_components=factors,
                random_state=seed + split,
                max_iter=1000,
            )
            model.fit(train_array)
            rows.append(
                {
                    "split": split,
                    "model_family": "continuous_factor",
                    "model_id": f"FactorAnalysis-{factors}",
                    "complexity": factors,
                    "covariance": "factor",
                    "n_train": len(train),
                    "n_test": len(test),
                    "train_participants": train["participant_id"].nunique(),
                    "test_participants": test["participant_id"].nunique(),
                    "participant_overlap": 0,
                    "component_size_valid": True,
                    "minimum_component_size": np.nan,
                    "minimum_component_fraction": np.nan,
                    "mean_test_log_likelihood": float(model.score(test_array)),
                }
            )

        for k in k_values:
            model = GaussianMixture(
                n_components=k,
                covariance_type="diag",
                n_init=n_init,
                random_state=seed + split,
                reg_covar=1e-6,
            )
            labels = model.fit_predict(train_array)
            counts = np.bincount(labels, minlength=k)
            rows.append(
                {
                    "split": split,
                    "model_family": "discrete_mixture",
                    "model_id": f"GMM-{k}-diag",
                    "complexity": k,
                    "covariance": "diag",
                    "n_train": len(train),
                    "n_test": len(test),
                    "train_participants": train["participant_id"].nunique(),
                    "test_participants": test["participant_id"].nunique(),
                    "participant_overlap": 0,
                    "component_size_valid": _valid_component_sizes(labels),
                    "minimum_component_size": int(counts.min()),
                    "minimum_component_fraction": float(
                        counts.min() / len(labels)
                    ),
                    "mean_test_log_likelihood": float(model.score(test_array)),
                }
            )
    return pd.DataFrame(rows)


def summarize_density_comparison(fold_results: pd.DataFrame) -> pd.DataFrame:
    """Summarize grouped held-out likelihoods without participant leakage."""
    rows: list[dict[str, Any]] = []
    for (family, model_id), group in fold_results.groupby(
        ["model_family", "model_id"],
        sort=False,
    ):
        values = group["mean_test_log_likelihood"].to_numpy(dtype=float)
        rows.append(
            {
                "model_family": family,
                "model_id": model_id,
                "complexity": int(group["complexity"].iloc[0]),
                "covariance": group["covariance"].iloc[0],
                "splits": len(group),
                "n_windows": int(group["n_train"].iloc[0] + group["n_test"].iloc[0]),
                "n_participants": int(
                    group["train_participants"].iloc[0]
                    + group["test_participants"].iloc[0]
                ),
                "mean_test_log_likelihood": float(values.mean()),
                "sd_test_log_likelihood": float(values.std(ddof=1)),
                "median_test_log_likelihood": float(np.median(values)),
                "minimum_test_log_likelihood": float(values.min()),
                "maximum_test_log_likelihood": float(values.max()),
                "participant_leakage_detected": bool(
                    group["participant_overlap"].gt(0).any()
                ),
                "valid_component_split_fraction": float(
                    group["component_size_valid"].mean()
                ),
                "minimum_component_size_across_splits": (
                    float(group["minimum_component_size"].min())
                    if group["minimum_component_size"].notna().any()
                    else np.nan
                ),
                "minimum_component_fraction_across_splits": (
                    float(group["minimum_component_fraction"].min())
                    if group["minimum_component_fraction"].notna().any()
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        "mean_test_log_likelihood",
        ascending=False,
        ignore_index=True,
    )
