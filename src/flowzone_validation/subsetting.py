"""Deterministic, boundary-preserving development subsets."""

from __future__ import annotations

import hashlib

import pandas as pd


SUBSET_KEY_COLUMNS = ("task_family", "dataset_id", "participant_id")


def _selection_key(
    task_family: object,
    dataset_id: object,
    participant_id: object,
    seed: int,
) -> str:
    value = f"{seed}|{task_family}|{dataset_id}|{participant_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def choose_pilot_members(
    trials: pd.DataFrame,
    datasets_per_task: int,
    participants_per_dataset: int,
    primary_window_size: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Choose complete participants from high-yield datasets reproducibly."""
    required = {
        "task_family",
        "dataset_id",
        "participant_id",
        "block_raw",
    }
    missing = required - set(trials.columns)
    if missing:
        raise ValueError(f"Missing subset columns: {sorted(missing)}")

    index = trials[list(required)].copy()
    index["block_raw"] = pd.to_numeric(index["block_raw"], errors="coerce")
    index = index[index["block_raw"].ge(0)].copy()
    block_counts = (
        index.groupby(
            list(SUBSET_KEY_COLUMNS) + ["block_raw"],
            observed=True,
            dropna=False,
        )
        .size()
        .rename("block_trials")
        .reset_index()
    )
    block_counts["estimated_primary_windows"] = (
        block_counts["block_trials"] // primary_window_size
    )
    participant_yield = (
        block_counts.groupby(
            list(SUBSET_KEY_COLUMNS),
            observed=True,
            dropna=False,
        )
        .agg(
            nonpractice_trials=("block_trials", "sum"),
            nonpractice_blocks=("block_raw", "nunique"),
            estimated_primary_windows=("estimated_primary_windows", "sum"),
        )
        .reset_index()
    )
    participant_yield = participant_yield[
        participant_yield["estimated_primary_windows"].gt(0)
    ].copy()
    if participant_yield.empty:
        raise ValueError("No participants support a complete primary window")

    dataset_ranking = (
        participant_yield.groupby(
            ["task_family", "dataset_id"],
            observed=True,
            dropna=False,
        )
        .agg(
            eligible_participants=("participant_id", "nunique"),
            estimated_primary_windows=("estimated_primary_windows", "sum"),
            nonpractice_trials=("nonpractice_trials", "sum"),
        )
        .reset_index()
        .sort_values(
            [
                "task_family",
                "estimated_primary_windows",
                "eligible_participants",
                "dataset_id",
            ],
            ascending=[True, False, False, True],
            kind="stable",
        )
    )
    dataset_ranking["dataset_rank"] = (
        dataset_ranking.groupby("task_family", observed=True).cumcount() + 1
    )
    dataset_ranking["selected"] = dataset_ranking["dataset_rank"].le(
        datasets_per_task
    )

    selected_datasets = dataset_ranking.loc[
        dataset_ranking["selected"],
        ["task_family", "dataset_id"],
    ]
    candidates = participant_yield.merge(
        selected_datasets,
        on=["task_family", "dataset_id"],
        how="inner",
        validate="many_to_one",
    )
    candidates["selection_key"] = [
        _selection_key(task, dataset, participant, seed)
        for task, dataset, participant in candidates[
            list(SUBSET_KEY_COLUMNS)
        ].itertuples(index=False, name=None)
    ]
    candidates = candidates.sort_values(
        ["task_family", "dataset_id", "selection_key"],
        kind="stable",
    )
    selected_members = (
        candidates.groupby(
            ["task_family", "dataset_id"],
            observed=True,
            group_keys=False,
        )
        .head(participants_per_dataset)
        .reset_index(drop=True)
    )
    selected_members["participant_rank"] = (
        selected_members.groupby(
            ["task_family", "dataset_id"],
            observed=True,
        ).cumcount()
        + 1
    )
    return selected_members, dataset_ranking.reset_index(drop=True)


def filter_selected_members(
    trials: pd.DataFrame,
    selected_members: pd.DataFrame,
) -> pd.DataFrame:
    """Return every row for selected dataset-scoped participants."""
    keys = selected_members[list(SUBSET_KEY_COLUMNS)].drop_duplicates()
    return trials.merge(
        keys,
        on=list(SUBSET_KEY_COLUMNS),
        how="inner",
        validate="many_to_one",
    )
