import numpy as np
import pandas as pd

from flowzone_validation.stroop_zone_count import (
    compare_continuous_and_mixture_models,
    compare_stroop_zone_counts,
    summarize_density_comparison,
)


def _stroop_frame(seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    centers = [
        (-2.0, -1.5, 0.5, 1.0, 1.5),
        (0, 0, 0, 0, 0),
        (2, 1.5, -0.5, -1, -1.5),
    ]
    for dataset in range(4):
        for participant in range(8):
            component = participant % 3
            for window in range(3):
                values = np.asarray(centers[component]) + rng.normal(0, 0.25, 5)
                rows.append(
                    {
                        "window_id": f"{dataset}:{participant}:{window}",
                        "participant_id": f"{dataset}:{participant}",
                        "dataset_id": dataset,
                        "throughput_proxy": values[0] + dataset,
                        "accuracy": values[1],
                        "rt_cv": values[2],
                        "rt_volatility": values[3],
                        "error_burstiness": values[4],
                    }
                )
    return pd.DataFrame(rows)


def test_constrained_comparison_is_deterministic_and_neutral():
    frame = _stroop_frame()
    features = [
        "throughput_proxy",
        "accuracy",
        "rt_cv",
        "rt_volatility",
        "error_burstiness",
    ]
    first = compare_stroop_zone_counts(
        frame,
        features,
        n_init=3,
        bootstrap_repetitions=2,
        seed=42,
    )
    second = compare_stroop_zone_counts(
        frame,
        features,
        n_init=3,
        bootstrap_repetitions=2,
        seed=42,
    )
    pd.testing.assert_frame_equal(first.model_comparison, second.model_comparison)
    assert set(first.model_comparison["k"]) == {2, 3, 4}
    cluster_columns = [
        column for column in first.assignments if column.endswith("_cluster_id")
    ]
    assert cluster_columns
    assert all(
        value.startswith("Stroop-GMM")
        for column in cluster_columns
        for value in first.assignments[column]
    )


def test_density_comparison_has_no_participant_leakage():
    frame = _stroop_frame()
    features = [
        "throughput_proxy",
        "accuracy",
        "rt_cv",
        "rt_volatility",
        "error_burstiness",
    ]
    folds = compare_continuous_and_mixture_models(
        frame,
        features,
        factor_counts=(1, 2),
        repetitions=2,
        n_init=2,
        seed=42,
    )
    summary = summarize_density_comparison(folds)
    assert set(folds["model_family"]) == {
        "continuous_factor",
        "discrete_mixture",
    }
    assert folds["participant_overlap"].eq(0).all()
    assert not summary["participant_leakage_detected"].any()
