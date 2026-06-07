"""Exploratory PCA, GMM, HDBSCAN, and grouped stability analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import RobustScaler


@dataclass(frozen=True)
class ClusteringResult:
    assignments: pd.DataFrame
    standardized_features: pd.DataFrame
    metrics: dict[str, Any]


def _gmm_parameter_count(k: int, dimensions: int, covariance: str) -> int:
    covariance_parameters = (
        dimensions if covariance == "diag" else dimensions * (dimensions + 1) // 2
    )
    return k * (dimensions + covariance_parameters) + (k - 1)


def _minimum_component_ok(labels: np.ndarray) -> bool:
    counts = np.bincount(labels)
    return bool(np.all(counts >= 20) and np.all(counts / len(labels) >= 0.05))


def _posterior_entropy(probabilities: np.ndarray) -> float:
    if probabilities.shape[1] <= 1:
        return 0.0
    clipped = np.clip(probabilities, 1e-12, 1.0)
    entropy = -np.sum(clipped * np.log(clipped), axis=1)
    return float(np.mean(entropy / np.log(probabilities.shape[1])))


def _full_covariance_well_conditioned(model: GaussianMixture) -> bool:
    if model.covariance_type != "full":
        return True
    condition_numbers = [
        np.linalg.cond(covariance) for covariance in model.covariances_
    ]
    return bool(
        condition_numbers
        and np.all(np.isfinite(condition_numbers))
        and max(condition_numbers) < 1e8
    )


def _partition_jaccard(
    reference: np.ndarray,
    candidate: np.ndarray,
) -> float:
    reference_clusters = sorted(set(reference) - {-1})
    candidate_clusters = sorted(set(candidate) - {-1})
    if not reference_clusters or not candidate_clusters:
        return np.nan
    scores: list[float] = []
    for reference_cluster in reference_clusters:
        reference_members = reference == reference_cluster
        best = 0.0
        for candidate_cluster in candidate_clusters:
            candidate_members = candidate == candidate_cluster
            union = np.sum(reference_members | candidate_members)
            if union:
                best = max(
                    best,
                    float(
                        np.sum(reference_members & candidate_members) / union
                    ),
                )
        scores.append(best)
    return float(np.mean(scores))


def _bootstrap_hdbscan_stability(
    scores: np.ndarray,
    labels: np.ndarray,
    groups: pd.Series,
    minimum_cluster_size: int,
    repetitions: int,
    seed: int,
) -> list[float]:
    import hdbscan

    if not (set(labels) - {-1}):
        return []
    rng = np.random.default_rng(seed)
    group_values = groups.astype("string").to_numpy()
    unique_groups = np.unique(group_values)
    group_indices = {
        group: np.flatnonzero(group_values == group) for group in unique_groups
    }
    values: list[float] = []
    for index in range(repetitions):
        sampled_groups = rng.choice(
            unique_groups,
            size=len(unique_groups),
            replace=True,
        )
        sampled_indices = np.concatenate(
            [group_indices[group] for group in sampled_groups]
        )
        model = hdbscan.HDBSCAN(
            min_cluster_size=minimum_cluster_size,
            prediction_data=True,
        )
        try:
            model.fit(scores[sampled_indices])
            if not (set(model.labels_) - {-1}):
                continue
            predicted, _ = hdbscan.approximate_predict(model, scores)
            value = _partition_jaccard(labels, predicted)
            if np.isfinite(value):
                values.append(value)
        except ValueError:
            continue
    return values


def _select_pca(x: np.ndarray, seed: int) -> tuple[PCA, np.ndarray]:
    maximum = min(6, x.shape[1], x.shape[0] - 1)
    full = PCA(n_components=maximum, random_state=seed).fit(x)
    cumulative = np.cumsum(full.explained_variance_ratio_)
    count = int(np.searchsorted(cumulative, 0.80) + 1)
    count = min(maximum, max(1, count))
    pca = PCA(n_components=count, random_state=seed)
    return pca, pca.fit_transform(x)


def _bootstrap_gmm_stability(
    scores: np.ndarray,
    labels: np.ndarray,
    groups: pd.Series,
    k: int,
    covariance: str,
    repetitions: int,
    seed: int,
) -> list[float]:
    if k <= 1:
        return [1.0]
    rng = np.random.default_rng(seed)
    unique_groups = groups.astype("string").unique()
    group_indices = {
        group: np.flatnonzero(groups.astype("string").to_numpy() == group)
        for group in unique_groups
    }
    values: list[float] = []
    for index in range(repetitions):
        sampled_groups = rng.choice(
            unique_groups,
            size=len(unique_groups),
            replace=True,
        )
        sampled_indices = np.concatenate(
            [group_indices[group] for group in sampled_groups]
        )
        model = GaussianMixture(
            n_components=k,
            covariance_type=covariance,
            n_init=5,
            random_state=seed + index + 1,
        )
        try:
            model.fit(scores[sampled_indices])
            values.append(
                float(adjusted_rand_score(labels, model.predict(scores)))
            )
        except ValueError:
            continue
    return values


def _leave_dataset_out_stability(
    scores: np.ndarray,
    base_labels: np.ndarray,
    datasets: pd.Series,
    k: int,
    covariance: str,
    seed: int,
) -> dict[str, float]:
    values: dict[str, float] = {}
    if k <= 1:
        return {str(value): 1.0 for value in datasets.unique()}
    for offset, dataset in enumerate(sorted(datasets.unique())):
        held_out = datasets.eq(dataset).to_numpy()
        if held_out.sum() < 2 or (~held_out).sum() <= k:
            continue
        model = GaussianMixture(
            n_components=k,
            covariance_type=covariance,
            n_init=10,
            random_state=seed + offset + 1,
        )
        try:
            model.fit(scores[~held_out])
            predicted = model.predict(scores[held_out])
            values[str(dataset)] = float(
                adjusted_rand_score(base_labels[held_out], predicted)
            )
        except ValueError:
            continue
    return values


def fit_exploratory_models(
    frame: pd.DataFrame,
    feature_columns: list[str],
    analysis_name: str,
    k_min: int = 1,
    k_max: int = 8,
    n_init: int = 20,
    bootstrap_repetitions: int = 50,
    seed: int = 42,
) -> ClusteringResult:
    """Fit eligible model variants and retain neutral cluster identifiers."""
    if len(frame) < 2:
        raise ValueError("At least two windows are required")
    numeric = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        raise ValueError("Features must be minimally imputed before modelling")

    scaler = RobustScaler()
    standardized_array = scaler.fit_transform(numeric)
    standardized = pd.DataFrame(
        standardized_array,
        columns=feature_columns,
        index=frame.index,
    )
    pca, scores = _select_pca(standardized_array, seed)
    dimensions = scores.shape[1]

    comparison: list[dict[str, Any]] = []
    fitted: dict[tuple[str, int], tuple[GaussianMixture, np.ndarray]] = {}
    maximum_k = min(k_max, len(frame) - 1)
    for covariance in ("diag", "full"):
        for k in range(k_min, maximum_k + 1):
            parameter_count = _gmm_parameter_count(k, dimensions, covariance)
            if covariance == "full" and len(frame) <= 10 * parameter_count:
                continue
            model = GaussianMixture(
                n_components=k,
                covariance_type=covariance,
                n_init=n_init,
                random_state=seed,
                reg_covar=1e-6,
            )
            try:
                labels = model.fit_predict(scores)
            except ValueError:
                continue
            valid_components = k == 1 or _minimum_component_ok(labels)
            well_conditioned = _full_covariance_well_conditioned(model)
            valid_components = valid_components and well_conditioned
            probabilities = model.predict_proba(scores)
            comparison.append(
                {
                    "covariance": covariance,
                    "k": k,
                    "parameter_count": parameter_count,
                    "bic": float(model.bic(scores)),
                    "aic": float(model.aic(scores)),
                    "silhouette": (
                        float(silhouette_score(scores, labels))
                        if k > 1 and len(np.unique(labels)) > 1
                        else None
                    ),
                    "posterior_entropy": _posterior_entropy(probabilities),
                    "minimum_component_size": int(
                        np.bincount(labels).min()
                    ),
                    "valid_component_sizes": valid_components,
                    "well_conditioned": well_conditioned,
                }
            )
            fitted[(covariance, k)] = (model, labels)

    valid = [row for row in comparison if row["valid_component_sizes"]]
    if not valid:
        raise ValueError("No GMM solution passed minimum component-size rules")
    best = min(valid, key=lambda row: row["bic"])
    best_model, best_labels = fitted[(best["covariance"], best["k"])]

    assignments = frame.copy()
    assignments["gmm_component"] = best_labels
    assignments["gmm_cluster_id"] = [
        f"{analysis_name}-GMM{best['k']}-C{label + 1}"
        for label in best_labels
    ]
    probabilities = best_model.predict_proba(scores)
    assignments["gmm_max_posterior"] = probabilities.max(axis=1)
    for index in range(scores.shape[1]):
        assignments[f"pc{index + 1}"] = scores[:, index]

    hdbscan_metrics: dict[str, Any]
    try:
        import hdbscan

        minimum_cluster_size = max(20, int(np.ceil(0.05 * len(frame))))
        density_model = hdbscan.HDBSCAN(
            min_cluster_size=minimum_cluster_size,
            prediction_data=True,
        )
        density_labels = density_model.fit_predict(scores)
        density_cluster_count = int(
            len(set(density_labels)) - (1 if -1 in density_labels else 0)
        )
        assignments["hdbscan_component"] = density_labels
        assignments["hdbscan_cluster_id"] = [
            (
                f"{analysis_name}-HDBSCAN-C{label + 1}"
                if label >= 0
                else f"{analysis_name}-HDBSCAN-NOISE"
            )
            for label in density_labels
        ]
        hdbscan_metrics = {
            "status": "ok" if density_cluster_count > 0 else "no_clusters",
            "minimum_cluster_size": minimum_cluster_size,
            "cluster_count": density_cluster_count,
            "noise_fraction": float(np.mean(density_labels == -1)),
            "silhouette_non_noise": (
                float(
                    silhouette_score(
                        scores[density_labels >= 0],
                        density_labels[density_labels >= 0],
                    )
                )
                if len(set(density_labels[density_labels >= 0])) > 1
                else None
            ),
        }
        density_stability = _bootstrap_hdbscan_stability(
            scores,
            density_labels,
            frame["participant_id"],
            minimum_cluster_size,
            bootstrap_repetitions,
            seed,
        )
        hdbscan_metrics["bootstrap_jaccard"] = density_stability
        hdbscan_metrics["bootstrap_jaccard_median"] = (
            float(np.median(density_stability)) if density_stability else None
        )
    except ImportError:
        assignments["hdbscan_component"] = pd.NA
        assignments["hdbscan_cluster_id"] = pd.NA
        hdbscan_metrics = {
            "status": "unavailable",
            "reason": "hdbscan package is not installed",
        }

    bootstrap_values = _bootstrap_gmm_stability(
        scores,
        best_labels,
        frame["participant_id"],
        best["k"],
        best["covariance"],
        bootstrap_repetitions,
        seed,
    )
    leave_dataset_out = _leave_dataset_out_stability(
        scores,
        best_labels,
        frame["dataset_id"],
        best["k"],
        best["covariance"],
        seed,
    )
    metrics = {
        "analysis_name": analysis_name,
        "rows": int(len(frame)),
        "participants": int(frame["participant_id"].nunique()),
        "datasets": int(frame["dataset_id"].nunique()),
        "features": feature_columns,
        "pca_components": int(scores.shape[1]),
        "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "pca_loadings": {
            f"pc{index + 1}": dict(zip(feature_columns, values, strict=True))
            for index, values in enumerate(pca.components_)
        },
        "gmm_comparison": comparison,
        "best_gmm": best,
        "gmm_bootstrap_ari": bootstrap_values,
        "gmm_bootstrap_ari_median": (
            float(np.median(bootstrap_values)) if bootstrap_values else None
        ),
        "leave_one_dataset_out_ari": leave_dataset_out,
        "hdbscan": hdbscan_metrics,
    }
    return ClusteringResult(
        assignments=assignments,
        standardized_features=standardized,
        metrics=metrics,
    )
