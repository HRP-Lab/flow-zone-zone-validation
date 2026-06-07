import numpy as np
import pandas as pd

from flowzone_validation.clustering import fit_exploratory_models
from flowzone_validation.zone_alignment import align_clusters


def _cluster_frame(seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    centers = [
        (2, 2, -1, -1, -1),
        (-2, -1, 1, 1, 0),
        (0, 1, -1, -1, 2),
        (0, -1, 2, 2, -1),
    ]
    for component, center in enumerate(centers):
        for index in range(30):
            values = np.asarray(center) + rng.normal(0, 0.25, len(center))
            rows.append(
                {
                    "participant_id": f"{component}:{index // 2}",
                    "dataset_id": component % 2,
                    "task_family": "Stroop",
                    "throughput_proxy": values[0],
                    "accuracy": values[1],
                    "rt_cv": values[2],
                    "rt_volatility": values[3],
                    "error_burstiness": values[4],
                }
            )
    return pd.DataFrame(rows)


def test_gmm_is_deterministic_and_neutral():
    frame = _cluster_frame()
    features = [
        "throughput_proxy",
        "accuracy",
        "rt_cv",
        "rt_volatility",
        "error_burstiness",
    ]
    first = fit_exploratory_models(
        frame,
        features,
        "Stroop",
        k_min=1,
        k_max=5,
        bootstrap_repetitions=2,
        seed=42,
    )
    second = fit_exploratory_models(
        frame,
        features,
        "Stroop",
        k_min=1,
        k_max=5,
        bootstrap_repetitions=2,
        seed=42,
    )
    assert first.assignments["gmm_cluster_id"].tolist() == second.assignments[
        "gmm_cluster_id"
    ].tolist()
    assert all(
        value.startswith("Stroop-GMM")
        for value in first.assignments["gmm_cluster_id"]
    )
    assert 1 <= first.metrics["best_gmm"]["k"] <= 5


def test_zone_alignment_does_not_rename_clusters():
    frame = _cluster_frame()
    features = [
        "throughput_proxy",
        "accuracy",
        "rt_cv",
        "rt_volatility",
        "error_burstiness",
    ]
    result = fit_exploratory_models(
        frame,
        features,
        "Stroop",
        k_min=4,
        k_max=4,
        bootstrap_repetitions=1,
        seed=42,
    )
    alignment = align_clusters(
        result.assignments,
        result.standardized_features,
        bootstraps=10,
        seed=42,
    )
    assert len(alignment) == 4
    assert all("closest_prototype" in row for row in alignment)
    assert all(
        row["cluster_id"].startswith("Stroop-GMM4-C") for row in alignment
    )
