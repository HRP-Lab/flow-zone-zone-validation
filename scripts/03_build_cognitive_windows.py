#!/usr/bin/env python3
"""Build fixed cognitive windows and summarize trial-level features."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.cognitive_features import summarize_trials
from flowzone_validation.reporting import write_table
from flowzone_validation.windowing import assign_fixed_windows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/interim/acdc_trials.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument("--window", default="5min", help="Pandas time frequency.")
    parser.add_argument("--timestamp-column", default="timestamp")
    parser.add_argument("--participant-column", default="participant_id")
    parser.add_argument("--session-column", default="session_id")
    return parser.parse_args()


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def main() -> None:
    args = parse_args()
    trials = read_table(args.input)
    group_columns = [args.participant_column]
    if args.session_column in trials.columns:
        group_columns.append(args.session_column)

    windowed = assign_fixed_windows(
        trials,
        timestamp_column=args.timestamp_column,
        group_columns=group_columns,
        frequency=args.window,
    )
    features = summarize_trials(
        windowed,
        group_columns=[*group_columns, "window_start", "window_end"],
        timestamp_column=args.timestamp_column,
    )
    write_table(features, args.output)
    print(f"Wrote {len(features):,} cognitive windows to {args.output}")


if __name__ == "__main__":
    main()
