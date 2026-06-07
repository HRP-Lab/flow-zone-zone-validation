"""Trial-count windows that never cross ACDC grouping boundaries."""

from __future__ import annotations

import numpy as np
import pandas as pd
from collections.abc import Iterator


BOUNDARY_COLUMNS = ("dataset_id", "participant_id", "task_family", "block_raw")
ORDER_COLUMNS = ("trial_raw", "observation_id")


def _window_piece(
    group: pd.DataFrame,
    start: int,
    stop: int,
    size: int,
    index: int,
    kind: str,
    dynamics_eligible: bool,
) -> pd.DataFrame:
    piece = group.iloc[start:stop].copy()
    piece["window_size"] = int(size)
    piece["window_index"] = int(index)
    piece["window_kind"] = kind
    piece["dynamics_eligible"] = bool(dynamics_eligible)
    boundary = piece.iloc[0]
    piece["window_id"] = (
        boundary["task_family"].astype(str)
        if hasattr(boundary["task_family"], "astype")
        else str(boundary["task_family"])
    )
    piece["window_id"] = (
        str(boundary["task_family"])
        + ":"
        + str(int(boundary["dataset_id"]))
        + ":"
        + str(boundary["participant_id"])
        + ":"
        + str(boundary["block_raw"])
        + ":"
        + str(size)
        + ":"
        + str(index)
        + ":"
        + kind
    )
    return piece


def assign_trial_windows(
    trials: pd.DataFrame,
    primary_size: int = 80,
    sensitivity_sizes: tuple[int, ...] = (60, 120),
    minimum_remainder_trials: int = 40,
) -> pd.DataFrame:
    """Create full windows plus primary aggregate-only remainders."""
    required = {*BOUNDARY_COLUMNS, *ORDER_COLUMNS}
    missing = required - set(trials.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    pieces = list(
        iter_trial_windows(
            trials,
            primary_size=primary_size,
            sensitivity_sizes=sensitivity_sizes,
            minimum_remainder_trials=minimum_remainder_trials,
        )
    )
    if not pieces:
        columns = list(trials.columns) + [
            "window_size",
            "window_index",
            "window_kind",
            "dynamics_eligible",
            "window_id",
            "window_trial_position",
            "window_trial_fraction",
        ]
        return pd.DataFrame(columns=columns)
    return pd.concat(pieces, ignore_index=True)


def iter_trial_windows(
    trials: pd.DataFrame,
    primary_size: int = 80,
    sensitivity_sizes: tuple[int, ...] = (60, 120),
    minimum_remainder_trials: int = 40,
) -> Iterator[pd.DataFrame]:
    """Yield bounded windows without materializing duplicated trial data."""
    required = {*BOUNDARY_COLUMNS, *ORDER_COLUMNS}
    missing = required - set(trials.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    sorted_trials = trials.sort_values(
        [*BOUNDARY_COLUMNS, *ORDER_COLUMNS],
        na_position="last",
        kind="stable",
    ).reset_index(drop=True)
    sizes = (primary_size, *sensitivity_sizes)
    for _, group in sorted_trials.groupby(
        list(BOUNDARY_COLUMNS),
        dropna=False,
        sort=True,
    ):
        for size in sizes:
            full_count = len(group) // size
            for index in range(full_count):
                start = index * size
                piece = _window_piece(
                    group,
                    start,
                    start + size,
                    size,
                    index,
                    "full",
                    True,
                )
                piece["window_trial_position"] = np.arange(len(piece))
                piece["window_trial_fraction"] = (
                    piece["window_trial_position"] / max(len(piece) - 1, 1)
                )
                yield piece
            remainder = len(group) - full_count * size
            if (
                size == primary_size
                and minimum_remainder_trials <= remainder < primary_size
            ):
                start = full_count * size
                piece = _window_piece(
                    group,
                    start,
                    len(group),
                    primary_size,
                    full_count,
                    "aggregate_remainder",
                    False,
                )
                piece["window_trial_position"] = np.arange(len(piece))
                piece["window_trial_fraction"] = (
                    piece["window_trial_position"] / max(len(piece) - 1, 1)
                )
                yield piece
