from __future__ import annotations

import numpy as np
import pandas as pd
import mne

from flowzone_validation.cog_bci_analysis import (
    add_next_window_targets,
    fit_autonomic_dimensions,
    published_effect_replication,
    trait_state_decomposition,
)
from flowzone_validation.cog_bci_io import (
    annotation_events,
    find_participant_directory,
    flanker_trials,
    nback_trials,
)


def test_participant_directory_accepts_non_padded_archive_folder(
    tmp_path,
) -> None:
    participant = tmp_path / "sub-3"
    (participant / "ses-S1").mkdir(parents=True)

    assert find_participant_directory(tmp_path, "sub-03") == participant


def test_participant_directory_accepts_duplicate_nested_folder(
    tmp_path,
) -> None:
    participant = tmp_path / "sub-03" / "sub-03"
    (participant / "ses-S1").mkdir(parents=True)

    assert find_participant_directory(tmp_path, "sub-03") == participant


def test_annotation_events_has_schema_when_no_numeric_events() -> None:
    raw = mne.io.RawArray(
        np.zeros((1, 1000)),
        mne.create_info(["ECG1"], 500, ["ecg"]),
        verbose="ERROR",
    )
    events = annotation_events(raw)

    assert events.empty
    assert events.columns.tolist() == [
        "onset_seconds",
        "duration_seconds",
        "event_code",
    ]


def test_flanker_event_parser_preserves_congruency_and_accuracy() -> None:
    events = pd.DataFrame(
        {
            "onset_seconds": [1.0, 1.4, 2.0, 2.5, 3.0],
            "duration_seconds": 0.0,
            "event_code": [241, 2511, 242, 2522, 25322],
        }
    )
    trials = flanker_trials(events)

    assert trials["congruency"].tolist() == ["congruent", "incongruent"]
    assert trials["correct"].tolist() == [1, 0]
    assert np.allclose(trials["rt_seconds"], [0.4, 0.5])


def test_nback_event_parser_uses_level_specific_codes() -> None:
    events = pd.DataFrame(
        {
            "onset_seconds": [1.0, 1.5, 2.0, 2.4],
            "duration_seconds": 0.0,
            "event_code": [6122, 6132, 6123, 6133],
        }
    )
    trials = nback_trials(events, level=1)

    assert trials["trial_type"].tolist() == ["hit", "conflict"]
    assert trials["correct"].tolist() == [1, 0]


def test_next_window_targets_never_cross_task_or_session() -> None:
    frame = pd.DataFrame(
        {
            "participant_id": ["p1"] * 4,
            "session_id": ["s1", "s1", "s1", "s2"],
            "task": ["PVT", "PVT", "Flanker", "PVT"],
            "block_id": ["p1:s1:PVT", "p1:s1:PVT", "p1:s1:F", "p1:s2:PVT"],
            "window_label": ["120"] * 4,
            "window_index": [0, 1, 0, 0],
            "pvt_lapse_rate": [0.1, 0.2, np.nan, 0.9],
        }
    )
    result = add_next_window_targets(frame)

    assert result.loc[0, "next_pvt_lapse_rate"] == 0.2
    assert np.isnan(result.loc[1, "next_pvt_lapse_rate"])
    assert np.isnan(result.loc[3, "next_pvt_lapse_rate"])


def test_replication_gate_stops_cleanly_for_undersized_pilot() -> None:
    rows = []
    for index in range(6):
        rows.append(
            {
                "participant_id": "sub-01",
                "session_id": "ses-S1",
                "analysis_role": "replication",
                "window_label": "10",
                "task": "PVT",
                "task_family": "PVT",
                "time_on_task_fraction": index / 6,
                "pvt_median_rt_ms": 300 + index,
                "mean_hr_bpm": 65 + index,
                "log_rmssd": 4 - index / 10,
                "sdnn_ms": 50 - index,
            }
        )
    frame = pd.DataFrame(rows)
    result, gate = published_effect_replication(frame)

    assert not result.empty
    assert gate.status == "not_testable"
    assert "at least five participants" in gate.reason


def test_trait_state_decomposition_reports_both_sources() -> None:
    frame = pd.DataFrame(
        {
            "participant_id": ["p1"] * 3 + ["p2"] * 3,
            "mean_hr_bpm": [60, 62, 58, 80, 78, 82],
        }
    )
    result = trait_state_decomposition(frame, ["mean_hr_bpm"]).iloc[0]

    assert result["between_fraction"] > 0
    assert result["within_fraction"] > 0
    assert np.isclose(
        result["between_fraction"] + result["within_fraction"],
        1.0,
    )


def test_autonomic_dimensions_are_deterministic() -> None:
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(
        {
            "participant_id": np.repeat(
                [f"p{index}" for index in range(10)],
                4,
            ),
            "a": rng.normal(size=40),
            "b": rng.normal(size=40),
            "c": rng.normal(size=40),
            "d": rng.normal(size=40),
        }
    )
    first = fit_autonomic_dimensions(
        frame,
        ["a", "b", "c", "d"],
        mode="within",
        maximum_factors=4,
        seed=42,
    )[0]
    second = fit_autonomic_dimensions(
        frame,
        ["a", "b", "c", "d"],
        mode="within",
        maximum_factors=4,
        seed=42,
    )[0]

    pd.testing.assert_frame_equal(first, second)
