import numpy as np
import pandas as pd

from flowzone_validation.profile_recoverability import (
    grouped_profile_recovery,
    one_way_icc,
    profile_repeatability,
)


def _repeated_frame(seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    labels = ["C1", "C2", "C3"]
    for dataset in range(3):
        for participant in range(12):
            label = labels[participant % 3]
            center = labels.index(label) * 3
            for window in range(4):
                rows.append(
                    {
                        "parent_window_id": f"{dataset}:{participant}:{window}",
                        "window_id": f"{dataset}:{participant}:{window}",
                        "participant_id": f"{dataset}:{participant}",
                        "dataset_id": dataset,
                        "task_family": "Stroop",
                        "block_raw": 1,
                        "window_index": window,
                        "profile": label,
                        "feature_a": center + rng.normal(0, 0.3),
                        "feature_b": -center + rng.normal(0, 0.3),
                    }
                )
    return pd.DataFrame(rows)


def test_grouped_profile_recovery_has_no_participant_leakage():
    frame = _repeated_frame()
    metrics, predictions = grouped_profile_recovery(
        frame,
        ["feature_a", "feature_b"],
        "profile",
        folds=3,
    )
    assert metrics["maximum_participant_overlap"] == 0
    assert metrics["balanced_accuracy"] > 0.9
    assert predictions["fold"].gt(0).all()


def test_repeatability_and_icc_detect_stable_participant_profiles():
    frame = _repeated_frame()
    metrics, occupancy, transitions = profile_repeatability(
        frame,
        "profile",
        permutations=20,
        seed=42,
    )
    icc = one_way_icc(frame, ["feature_a", "feature_b"])
    assert metrics["within_participant_pair_agreement"] == 1.0
    assert metrics["adjacent_same_profile_rate"] == 1.0
    assert occupancy["modal_share"].eq(1.0).all()
    assert transitions["count"].sum() > 0
    assert icc["icc_1"].min() > 0.5
