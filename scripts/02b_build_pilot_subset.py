#!/usr/bin/env python3
"""Build a deterministic multi-dataset development subset of ACDC trials."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.config import load_config
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)
from flowzone_validation.subsetting import choose_pilot_members


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/interim/acdc_trial_extract.parquet",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/interim/acdc_pilot_trial_extract.parquet",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/pilot.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/acdc_pilot_subset.md",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "reports/acdc_pilot_subset.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "reports/run_manifest.json",
    )
    return parser.parse_args()


def _read_selected_rows(
    path: Path,
    selected_members: pd.DataFrame,
) -> pd.DataFrame:
    source = ds.dataset(path, format="parquet")
    expression = None
    for (task, dataset_id), group in selected_members.groupby(
        ["task_family", "dataset_id"],
        observed=True,
        sort=True,
    ):
        participants = group["participant_id"].astype(str).tolist()
        clause = (
            (ds.field("task_family") == str(task))
            & (ds.field("dataset_id") == int(dataset_id))
            & ds.field("participant_id").isin(participants)
        )
        expression = clause if expression is None else expression | clause
    if expression is None:
        raise ValueError("Pilot member selection was empty")
    return source.to_table(filter=expression).to_pandas()


def _render_report(
    selected_members: pd.DataFrame,
    dataset_ranking: pd.DataFrame,
    subset: pd.DataFrame,
    config: object,
) -> str:
    selected_summary = (
        selected_members.groupby(["task_family", "dataset_id"], observed=True)
        .agg(
            participants=("participant_id", "nunique"),
            estimated_primary_windows=("estimated_primary_windows", "sum"),
            nonpractice_trials=("nonpractice_trials", "sum"),
        )
        .reset_index()
    )
    actual_rows = (
        subset.groupby(["task_family", "dataset_id"], observed=True)
        .size()
        .rename("extracted_rows")
        .reset_index()
    )
    selected_summary = selected_summary.merge(
        actual_rows,
        on=["task_family", "dataset_id"],
        how="left",
        validate="one_to_one",
    )
    lines = [
        "# ACDC Development Subset",
        "",
        "This subset is for pipeline development and feasibility analysis. Formal "
        "results must be rerun against the full pinned ACDC release.",
        "",
        f"- Selection seed: {config.random_seed}",
        f"- Datasets requested per task: {config.subset_datasets_per_task}",
        "- Complete participants requested per dataset: "
        f"{config.subset_participants_per_dataset}",
        f"- Extracted trial rows: {len(subset):,}",
        f"- Dataset-scoped participants: "
        f"{selected_members[list(('task_family', 'dataset_id', 'participant_id'))].drop_duplicates().shape[0]:,}",
        "",
        "## Selected Sources",
        "",
        "| Task | Dataset | Participants | Estimated 80-trial windows | Trial rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in selected_summary.itertuples(index=False):
        lines.append(
            f"| {row.task_family} | {row.dataset_id} | {row.participants} | "
            f"{row.estimated_primary_windows} | {row.extracted_rows} |"
        )
    lines.extend(
        [
            "",
            "## Selection Rule",
            "",
            "Datasets are ranked within task by the number of complete, "
            "block-bounded 80-trial windows. Participants with at least one such "
            "window are selected by a SHA-256 ordering derived from task, dataset, "
            "participant ID, and the registered seed. Every row for each selected "
            "participant is retained, including practice rows for audit purposes.",
            "",
            f"Eligible source datasets considered: {len(dataset_ranking):,}.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if not args.input.exists():
        raise FileNotFoundError(f"Full ACDC extract is missing: {args.input}")

    index = pd.read_parquet(
        args.input,
        columns=[
            "task_family",
            "dataset_id",
            "participant_id",
            "block_raw",
        ],
    )
    selected_members, dataset_ranking = choose_pilot_members(
        index,
        datasets_per_task=config.subset_datasets_per_task,
        participants_per_dataset=config.subset_participants_per_dataset,
        primary_window_size=config.primary_window_size,
        seed=config.random_seed,
    )
    subset = _read_selected_rows(args.input, selected_members)
    subset = subset.sort_values(
        [
            "task_family",
            "dataset_id",
            "participant_id",
            "block_raw",
            "trial_raw",
            "observation_id",
        ],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    write_table(subset, args.output)

    payload = {
        "development_subset": True,
        "seed": config.random_seed,
        "datasets_per_task": config.subset_datasets_per_task,
        "participants_per_dataset": config.subset_participants_per_dataset,
        "trial_rows": int(len(subset)),
        "tasks": {
            str(task): {
                "datasets": int(group["dataset_id"].nunique()),
                "participants": int(
                    group[["dataset_id", "participant_id"]]
                    .drop_duplicates()
                    .shape[0]
                ),
                "trial_rows": int(len(group)),
                "estimated_primary_windows": int(
                    selected_members[
                        selected_members["task_family"].eq(task)
                    ]["estimated_primary_windows"].sum()
                ),
            }
            for task, group in subset.groupby("task_family", observed=True)
        },
        "selected_members": selected_members.drop(
            columns=["selection_key"]
        ).to_dict(orient="records"),
    }
    write_json(payload, args.json_output)
    write_text(
        _render_report(
            selected_members,
            dataset_ranking,
            subset,
            config,
        ),
        args.report,
    )
    update_run_manifest(
        args.manifest,
        ROOT,
        "build_pilot_subset",
        {
            "input": str(args.input),
            "output": str(args.output),
            "development_subset": True,
            "selection_seed": config.random_seed,
            "datasets_per_task": config.subset_datasets_per_task,
            "participants_per_dataset": (
                config.subset_participants_per_dataset
            ),
            "trial_rows": int(len(subset)),
        },
    )
    print(
        f"Wrote {len(subset):,} trials for "
        f"{selected_members['participant_id'].nunique():,} selected participants "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
