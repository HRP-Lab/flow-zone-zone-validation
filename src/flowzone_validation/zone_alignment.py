"""Post hoc alignment of neutral clusters with directional zone prototypes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


ZONE_PROTOTYPES: dict[str, dict[str, float]] = {
    "In Zone": {
        "throughput_proxy": 1,
        "accuracy": 1,
        "rt_cv": -1,
        "nonresponse_rate": -1,
        "error_burstiness": -1,
    },
    "Flat": {
        "throughput_proxy": -1,
        "nonresponse_rate": 1,
        "slow_tail_rate": 1,
        "rt_drift": 1,
    },
    "Locked In": {
        "cog_lag1": 1,
        "cog_lag2": 1,
        "control_cost_rt_ms": 1,
        "post_error_adjustment_abs_ms": 1,
        "median_rt_ms": 1,
        "rt_volatility": -1,
    },
    "Spun Out": {
        "rt_cv": 1,
        "rt_volatility": 1,
        "fast_error_rate": 1,
        "error_burstiness": 1,
    },
}


def _cosine_for_prototype(
    centroid: pd.Series,
    prototype: dict[str, float],
) -> float:
    resolved: list[tuple[str, str]] = []
    for feature in prototype:
        if feature in centroid.index:
            resolved.append((feature, feature))
        elif f"{feature}__source_adjusted" in centroid.index:
            resolved.append((feature, f"{feature}__source_adjusted"))
    if len(resolved) < 2:
        return np.nan
    left = np.asarray(
        [centroid[resolved_feature] for _, resolved_feature in resolved],
        dtype=float,
    )
    right = np.asarray(
        [prototype[feature] for feature, _ in resolved],
        dtype=float,
    )
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    if denominator == 0:
        return np.nan
    return float(np.dot(left, right) / denominator)


def align_clusters(
    assignments: pd.DataFrame,
    standardized_features: pd.DataFrame,
    bootstraps: int = 500,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Return neutral cluster-to-prototype similarities and uncertainty."""
    rng = np.random.default_rng(seed)
    feature_frame = standardized_features.reset_index(drop=True)
    labels = assignments["gmm_cluster_id"].reset_index(drop=True)
    groups = assignments["participant_id"].astype("string").reset_index(drop=True)
    results: list[dict[str, Any]] = []

    for cluster_id in sorted(labels.unique()):
        cluster_mask = labels.eq(cluster_id)
        cluster_features = feature_frame.loc[cluster_mask]
        cluster_groups = groups.loc[cluster_mask]
        centroid = cluster_features.mean()
        similarities = {
            zone: _cosine_for_prototype(centroid, prototype)
            for zone, prototype in ZONE_PROTOTYPES.items()
        }
        unique_groups = cluster_groups.unique()
        samples: dict[str, list[float]] = {zone: [] for zone in ZONE_PROTOTYPES}
        group_indices = {
            group: cluster_groups.index[cluster_groups.eq(group)].to_numpy()
            for group in unique_groups
        }
        for _ in range(bootstraps):
            sampled_groups = rng.choice(
                unique_groups,
                size=len(unique_groups),
                replace=True,
            )
            sampled_indices = np.concatenate(
                [group_indices[group] for group in sampled_groups]
            )
            sampled_centroid = feature_frame.loc[sampled_indices].mean()
            for zone, prototype in ZONE_PROTOTYPES.items():
                similarity = _cosine_for_prototype(
                    sampled_centroid,
                    prototype,
                )
                if np.isfinite(similarity):
                    samples[zone].append(similarity)

        ordered = sorted(
            similarities.items(),
            key=lambda item: -item[1] if np.isfinite(item[1]) else np.inf,
        )
        best_zone, best_similarity = ordered[0]
        next_similarity = ordered[1][1] if len(ordered) > 1 else np.nan
        best_samples = samples[best_zone]
        lower = (
            float(np.quantile(best_samples, 0.025)) if best_samples else np.nan
        )
        upper = (
            float(np.quantile(best_samples, 0.975)) if best_samples else np.nan
        )
        margin = (
            float(best_similarity - next_similarity)
            if np.isfinite(best_similarity) and np.isfinite(next_similarity)
            else np.nan
        )
        strong = bool(
            np.isfinite(best_similarity)
            and best_similarity >= 0.70
            and np.isfinite(lower)
            and lower >= 0.50
            and np.isfinite(margin)
            and margin >= 0.15
        )
        results.append(
            {
                "cluster_id": cluster_id,
                "windows": int(cluster_mask.sum()),
                "participants": int(cluster_groups.nunique()),
                "closest_prototype": best_zone,
                "similarity": best_similarity,
                "similarity_ci_lower": lower,
                "similarity_ci_upper": upper,
                "lead_over_next": margin,
                "strong_alignment": strong,
                "all_similarities": similarities,
            }
        )
    return results
