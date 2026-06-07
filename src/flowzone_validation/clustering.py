"""PCA and clustering helpers for cognitive feature validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import hdbscan
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class ClusteringResult:
    assignments: pd.DataFrame
    metrics: dict[str, Any]


def _feature_columns(frame: pd.DataFrame) -> list[str]:
    excluded = {
        "n_trials",
        "elapsed_seconds",
        "participant_id",
        "session_id",
    }
    return [
        column
        for column in frame.select_dtypes(include="number").columns
        if column not in excluded and frame[column].notna().any()
    ]


def cluster_features(
    frame: pd.DataFrame,
    gmm_components: int = 4,
    min_cluster_size: int = 10,
    random_state: int = 42,
) -> ClusteringResult:
    """Transform numeric features with PCA and fit GMM and HDBSCAN labels."""
    features = _feature_columns(frame)
    if len(features) < 2:
        raise ValueError("At least two non-empty numeric features are required")
    if len(frame) < max(gmm_components, 2):
        raise ValueError("Not enough rows for the requested GMM component count")

    n_components = min(len(features), len(frame) - 1)
    transformer = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        PCA(n_components=n_components, random_state=random_state),
    )
    scores = transformer.fit_transform(frame[features])
    pca = transformer.named_steps["pca"]

    gmm = GaussianMixture(
        n_components=gmm_components,
        covariance_type="full",
        n_init=20,
        random_state=random_state,
    )
    gmm_labels = gmm.fit_predict(scores)
    density_labels = hdbscan.HDBSCAN(
        min_cluster_size=min(min_cluster_size, max(2, len(frame) // 2)),
        prediction_data=True,
    ).fit_predict(scores)

    assignments = frame.copy()
    for index in range(scores.shape[1]):
        assignments[f"pc{index + 1}"] = scores[:, index]
    assignments["gmm_cluster"] = gmm_labels
    assignments["hdbscan_cluster"] = density_labels

    metrics = {
        "features": features,
        "rows": int(len(frame)),
        "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "gmm_components": int(gmm_components),
        "gmm_bic": float(gmm.bic(scores)),
        "gmm_aic": float(gmm.aic(scores)),
        "hdbscan_cluster_count": int(
            len(set(density_labels)) - (1 if -1 in density_labels else 0)
        ),
        "hdbscan_noise_fraction": float(np.mean(density_labels == -1)),
    }
    return ClusteringResult(assignments=assignments, metrics=metrics)
