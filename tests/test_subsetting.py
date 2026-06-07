import pandas as pd

from flowzone_validation.subsetting import (
    choose_pilot_members,
    filter_selected_members,
)


def test_subset_is_deterministic_and_keeps_complete_participants(
    synthetic_trials,
):
    selected_a, ranking_a = choose_pilot_members(
        synthetic_trials,
        datasets_per_task=2,
        participants_per_dataset=2,
        primary_window_size=80,
        seed=42,
    )
    selected_b, ranking_b = choose_pilot_members(
        synthetic_trials,
        datasets_per_task=2,
        participants_per_dataset=2,
        primary_window_size=80,
        seed=42,
    )
    pd.testing.assert_frame_equal(selected_a, selected_b)
    pd.testing.assert_frame_equal(ranking_a, ranking_b)

    subset = filter_selected_members(synthetic_trials, selected_a)
    expected_counts = (
        synthetic_trials.merge(
            selected_a[["task_family", "dataset_id", "participant_id"]],
            on=["task_family", "dataset_id", "participant_id"],
            how="inner",
        )
        .groupby(["task_family", "dataset_id", "participant_id"])
        .size()
        .sort_index()
    )
    actual_counts = (
        subset.groupby(["task_family", "dataset_id", "participant_id"])
        .size()
        .sort_index()
    )
    pd.testing.assert_series_equal(actual_counts, expected_counts)
    assert selected_a["dataset_id"].nunique() == 2
    assert (
        selected_a.groupby(["task_family", "dataset_id"]).size().eq(2).all()
    )


def test_subset_rejects_data_without_complete_primary_windows():
    trials = pd.DataFrame(
        {
            "task_family": ["Stroop"] * 20,
            "dataset_id": [1] * 20,
            "participant_id": ["1:1"] * 20,
            "block_raw": [1] * 20,
        }
    )
    try:
        choose_pilot_members(
            trials,
            datasets_per_task=1,
            participants_per_dataset=1,
            primary_window_size=80,
            seed=42,
        )
    except ValueError as error:
        assert "complete primary window" in str(error)
    else:
        raise AssertionError("Expected an explicit short-data failure")
