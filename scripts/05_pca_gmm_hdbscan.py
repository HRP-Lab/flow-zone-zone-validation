#!/usr/bin/env python3
"""Fit PCA, Gaussian mixture, and HDBSCAN models to cognitive windows."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.clustering import cluster_features
from flowzone_validation.reporting import write_json, write_table


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
        default=ROOT / "data/processed/cluster_assignments.parquet",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/clustering_metrics.json",
    )
    parser.add_argument("--gmm-components", type=int, default=4)
    parser.add_argument("--min-cluster-size", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = pd.read_parquet(args.input)
    result = cluster_features(
        frame,
        gmm_components=args.gmm_components,
        min_cluster_size=args.min_cluster_size,
    )
    write_table(result.assignments, args.output)
    write_json(result.metrics, args.report)
    print(f"Wrote {len(result.assignments):,} cluster assignments to {args.output}")


if __name__ == "__main__":
    main()
