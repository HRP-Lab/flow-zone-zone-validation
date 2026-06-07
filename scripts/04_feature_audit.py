#!/usr/bin/env python3
"""Audit processed cognitive features for missingness and low variance."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.reporting import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/feature_audit.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = pd.read_parquet(args.input)
    numeric = frame.select_dtypes(include="number")
    audit = {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_fraction": frame.isna().mean().sort_values(ascending=False).to_dict(),
        "numeric_summary": numeric.describe().to_dict(),
        "constant_numeric_features": [
            column for column in numeric if numeric[column].nunique(dropna=True) <= 1
        ],
    }
    write_json(audit, args.output)
    print(f"Wrote feature audit to {args.output}")


if __name__ == "__main__":
    main()
