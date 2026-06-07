#!/usr/bin/env python3
"""Clean ACDC trials and build block-bounded cognitive feature windows."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.cleaning import flag_trials
from flowzone_validation.cognitive_features import build_window_features
from flowzone_validation.config import load_config
from flowzone_validation.reporting import update_run_manifest, write_table
from flowzone_validation.residualisation import residualise_trial_rt


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
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument(
        "--cleaned-trials-output",
        type=Path,
        default=ROOT / "data/processed/acdc_cleaned_trials.parquet",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/pilot.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "reports/run_manifest.json",
    )
    return parser.parse_args()


ANALYSIS_COLUMNS = [
    "observation_id",
    "dataset_id",
    "participant_id",
    "task_family",
    "control_cost_type",
    "block_raw",
    "trial_raw",
    "within_id",
    "congruency",
    "correct",
    "rt_ms",
]


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        import pyarrow.parquet as parquet

        available = set(parquet.ParquetFile(path).schema.names)
        columns = [column for column in ANALYSIS_COLUMNS if column in available]
        return pd.read_parquet(path, columns=columns)
    return pd.read_csv(
        path,
        usecols=lambda column: column in ANALYSIS_COLUMNS,
        compression="infer",
    )


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if not args.input.exists() and args.input.suffix.lower() == ".parquet":
        csv_fallbacks = [
            args.input.with_suffix(".csv"),
            args.input.with_suffix(".csv.gz"),
        ]
        for csv_fallback in csv_fallbacks:
            if csv_fallback.exists():
                args.input = csv_fallback
                break
    trials = read_table(args.input)
    print(f"Loaded {len(trials):,} trial rows from {args.input}", flush=True)
    flagged = flag_trials(trials, config)
    print("RT and response flags complete", flush=True)
    residualized = residualise_trial_rt(flagged)
    write_table(residualized, args.cleaned_trials_output)
    print(
        f"Wrote cleaned trials to {args.cleaned_trials_output}",
        flush=True,
    )

    features = build_window_features(
        residualized[residualized["analysis_eligible_trial"]].copy(),
        config,
        progress_every=250,
        progress_callback=lambda count: print(
            f"Summarized {count:,} windows",
            flush=True,
        ),
    )
    write_table(features, args.output)
    if ".csv" in args.input.suffixes:
        write_table(
            trials,
            ROOT / "data/interim/acdc_trial_extract.parquet",
        )
    update_run_manifest(
        args.manifest,
        ROOT,
        "build_cognitive_windows",
        {
            "input": str(args.input),
            "cleaned_trials_output": str(args.cleaned_trials_output),
            "window_output": str(args.output),
            "primary_window_size": config.primary_window_size,
            "sensitivity_window_sizes": list(config.sensitivity_window_sizes),
            "trial_rows": int(len(trials)),
            "window_rows": int(len(features)),
        },
    )
    print(f"Wrote {len(features):,} cognitive windows to {args.output}")


if __name__ == "__main__":
    main()
