from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from flowzone_validation.healthy_rr_replication import (
    REPLICATION_FEATURES,
    deterministic_window_indices,
    fit_fixed_components,
    loading_subspace_similarity,
    match_loading_components,
    read_rr_file,
    rr_window_slices,
    time_domain_features_from_rr,
)


def test_rr_reader_audits_nonnumeric_rows(tmp_path: Path) -> None:
    source = tmp_path / "p01.txt"
    source.write_text("800\n810\n@\n\n790\n", encoding="utf-8")

    result = read_rr_file(source)

    assert result.participant_id == "p01"
    assert result.rr_ms.tolist() == [800, 810, 790]
    assert result.nonnumeric_rows == 1
    assert result.blank_rows == 1


def test_rr_windows_are_contained_and_evenly_subsampled() -> None:
    rr = np.full(900, 1000.0)
    slices = rr_window_slices(rr, 120, maximum_windows=3)

    assert [row[0] for row in slices] == [0, 3, 6]
    assert all(stop_seconds - start_seconds == 120 for *_, start_seconds, stop_seconds in slices)
    assert all(stop_index > start_index for _, start_index, stop_index, *_ in slices)
    assert deterministic_window_indices(7, 3).tolist() == [0, 3, 6]


def test_time_domain_features_match_regular_rr_sequence() -> None:
    result = time_domain_features_from_rr(np.full(120, 1000.0))

    assert result["quality_pass"]
    assert result["mean_hr_bpm"] == 60.0
    assert result["mean_nn_ms"] == 1000.0
    assert result["sdnn_ms"] == 0.0
    assert np.isnan(result["log_rmssd"])


def test_component_matching_recovers_permutation_and_sign() -> None:
    reference_rows = []
    candidate_rows = []
    rng = np.random.default_rng(42)
    matrix = rng.normal(size=(len(REPLICATION_FEATURES), 3))
    candidate = np.column_stack((-matrix[:, 2], matrix[:, 0], matrix[:, 1]))
    for feature_index, feature in enumerate(REPLICATION_FEATURES):
        for component in range(3):
            reference_rows.append(
                {
                    "feature": feature,
                    "component": component + 1,
                    "loading": matrix[feature_index, component],
                }
            )
            candidate_rows.append(
                {
                    "feature": feature,
                    "component": component + 1,
                    "loading": candidate[feature_index, component],
                }
            )

    matched, aligned = match_loading_components(
        pd.DataFrame(reference_rows),
        pd.DataFrame(candidate_rows),
    )

    assert np.allclose(matched["absolute_tucker_congruence"], 1.0)
    aligned_matrix = aligned.pivot(
        index="feature",
        columns="component",
        values="loading",
    ).loc[REPLICATION_FEATURES]
    assert np.allclose(aligned_matrix.to_numpy(), matrix)


def test_subspace_similarity_is_rotation_invariant() -> None:
    rng = np.random.default_rng(7)
    basis, _ = np.linalg.qr(rng.normal(size=(len(REPLICATION_FEATURES), 3)))
    angle = np.pi / 4
    rotation = np.array(
        [
            [1, 0, 0],
            [0, np.cos(angle), -np.sin(angle)],
            [0, np.sin(angle), np.cos(angle)],
        ]
    )
    candidate = basis @ rotation
    rows = []
    candidate_rows = []
    for feature_index, feature in enumerate(REPLICATION_FEATURES):
        for component in range(3):
            rows.append(
                {
                    "feature": feature,
                    "component": component + 1,
                    "loading": basis[feature_index, component],
                }
            )
            candidate_rows.append(
                {
                    "feature": feature,
                    "component": component + 1,
                    "loading": candidate[feature_index, component],
                }
            )

    result = loading_subspace_similarity(
        pd.DataFrame(rows),
        pd.DataFrame(candidate_rows),
    )

    assert np.allclose(result["minimum_canonical_similarity"], 1.0)


def test_fixed_component_solution_is_deterministic() -> None:
    rng = np.random.default_rng(42)
    rows = []
    for participant in range(6):
        for window in range(20):
            latent = rng.normal(size=3)
            row = {
                "participant_id": f"p{participant}",
                "window_seconds": 120,
                "window_index": window,
                "start_seconds": window * 120,
            }
            for index, feature in enumerate(REPLICATION_FEATURES):
                row[feature] = (
                    latent[index % 3]
                    + participant * 0.1
                    + rng.normal(scale=0.1)
                )
            rows.append(row)
    frame = pd.DataFrame(rows)

    first = fit_fixed_components(frame, seed=42)[0]
    second = fit_fixed_components(frame, seed=42)[0]

    pd.testing.assert_frame_equal(first, second)
