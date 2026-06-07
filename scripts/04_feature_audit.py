#!/usr/bin/env python3
"""Audit ACDC trials/windows and enforce modelling quality gates."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from flowzone_validation.audit import evaluate_audit, render_audit_markdown
from flowzone_validation.config import load_config
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument(
        "--trials",
        type=Path,
        default=ROOT / "data/processed/acdc_cleaned_trials.parquet",
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=ROOT / "data/interim/acdc_task_inventory.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/acdc_data_audit.md",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "reports/acdc_data_audit.json",
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


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    windows = pd.read_parquet(args.input)
    trials = pd.read_parquet(args.trials) if args.trials.exists() else None
    inventory = pd.read_csv(args.inventory) if args.inventory.exists() else None
    audit = evaluate_audit(windows, config, trials=trials, inventory=inventory)
    write_json(audit, args.json_output)
    write_text(render_audit_markdown(audit), args.output)
    update_run_manifest(
        args.manifest,
        ROOT,
        "feature_audit",
        {
            "window_input": str(args.input),
            "audit_markdown": str(args.output),
            "audit_json": str(args.json_output),
            "eligible_tasks": [
                task
                for task, gate in audit["task_gates"].items()
                if gate["eligible"]
            ],
        },
    )
    print(f"Wrote feature audit to {args.output}")


if __name__ == "__main__":
    main()
