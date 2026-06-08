import pandas as pd

from flowzone_validation.short_combined_recovery import (
    flanker_two_minute_trials,
    prepare_task_trials,
    summarize_prefix,
    trial_yield_by_profile,
)


def test_flanker_two_minute_yield_is_conservative():
    assert flanker_two_minute_trials() == 44


def test_flanker_preparation_excludes_prefatory_rows():
    raw = pd.DataFrame(
        {
            "subjectid": [1, 1, 1],
            "date": [10120, 10120, 10120],
            "time": ["10:00:00"] * 3,
            "values.practice": [0, 0, 0],
            "trialcode": [
                "prefatory",
                "targetleft_congruent",
                "targetright_incongruent",
            ],
            "values.congruence": [1, 1, 2],
            "values.trialcount": [11, 12, 13],
        }
    )
    sessions = pd.DataFrame(
        {
            "source_subject_id": [1],
            "session_date": [pd.Timestamp("2020-01-01")],
            "session_id": ["S1"],
            "participant_id": ["P1"],
            "dataset_id": ["D1"],
            "control_profile": ["C1"],
        }
    )
    prepared = prepare_task_trials(raw, sessions, "flanker")
    assert prepared["trialcode"].tolist() == [
        "targetleft_congruent",
        "targetright_incongruent",
    ]
    assert prepared["trial_order"].tolist() == [1, 2]


def test_prefix_summary_does_not_cross_sessions():
    trials = pd.DataFrame(
        {
            "session_id": ["A"] * 4 + ["B"] * 4,
            "participant_id": ["P1"] * 4 + ["P2"] * 4,
            "dataset_id": ["D"] * 8,
            "control_profile": ["C1"] * 4 + ["C2"] * 4,
            "trial_order": [1, 2, 3, 4] * 2,
            "condition": [1, 2, 1, 2] * 2,
            "correct": [1, 1, 0, 1, 1, 0, 1, 1],
            "latency": [500, 600, 550, 650, 400, 450, 500, 550],
        }
    )
    summary = summarize_prefix(
        trials,
        "stroop",
        lambda frame: frame["trial_order"].le(3),
    )
    assert len(summary) == 2
    assert summary["stroop_n"].eq(3).all()
    assert summary.set_index("session_id").loc["A", "participant_id"] == "P1"


def test_trial_yield_reports_profile_specific_shortfalls():
    frame = pd.DataFrame(
        {
            "control_profile": ["C1", "C1", "C2", "C2"],
            "stroop_n": [50, 70, 100, 110],
        }
    )
    result = trial_yield_by_profile(frame).set_index("control_profile")
    assert result.loc["C1", "below_60_rate"] == 0.5
    assert result.loc["C2", "at_least_100_rate"] == 1.0
