#!/usr/bin/env python3
"""Test two-minute Stroop and Flanker recovery of four control profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.profile_recoverability import grouped_profile_recovery
from flowzone_validation.reporting import write_table, write_text
from flowzone_validation.short_combined_recovery import (
    feature_columns,
    flanker_two_minute_trials,
    merge_task_prefixes,
    prepare_task_trials,
    summarize_prefix,
    trial_yield_by_profile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sessions",
        type=Path,
        default=(
            ROOT
            / "data/processed/paired_vigilance_session_features.parquet"
        ),
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/raw/stroop_sart_flanker",
    )
    parser.add_argument(
        "--interim-dir",
        type=Path,
        default=ROOT / "data/interim",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/short_combined_task_recovery.md",
    )
    parser.add_argument(
        "--table",
        type=Path,
        default=(
            ROOT
            / "reports/tables/short_combined_task_recovery.csv"
        ),
    )
    parser.add_argument(
        "--yield-table",
        type=Path,
        default=(
            ROOT
            / "reports/tables/short_stroop_trial_yield_by_profile.csv"
        ),
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=(
            ROOT
            / "reports/figures/short_combined_task_recovery.png"
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _load_raw(args: argparse.Namespace, task: str) -> pd.DataFrame:
    cache = args.interim_dir / f"paired_raw_{task}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    if task == "stroop":
        source = args.raw_dir / "Raw_Stroop.xlsx"
        columns = [
            "subjectid",
            "date",
            "time",
            "trialnum",
            "values.congruency",
            "response",
            "correct",
            "latency",
        ]
    else:
        source = args.raw_dir / "Raw_Flanker.xlsx"
        columns = [
            "subjectid",
            "date",
            "time",
            "values.practice",
            "blockcode",
            "trialcode",
            "trialnum",
            "values.trialcount",
            "values.congruence",
            "response",
            "correct",
            "latency",
        ]
    if not source.exists():
        raise FileNotFoundError(f"Missing raw {task} workbook: {source}")
    frame = pd.read_excel(source, sheet_name="Inquisit Data", usecols=columns)
    write_table(frame, cache)
    return frame


def _evaluate(
    name: str,
    frame: pd.DataFrame,
    seed: int,
) -> dict[str, Any]:
    metrics, _ = grouped_profile_recovery(
        frame,
        feature_columns(frame),
        "control_profile",
        group_column="participant_id",
        folds=5,
        confidence_threshold=0.60,
        seed=seed,
    )
    return {
        "variant": name,
        "n_sessions": metrics["n_windows"],
        "n_subjects": metrics["n_subjects"],
        "feature_count": metrics["feature_count"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "macro_f1": metrics["macro_f1"],
        "mean_confidence": metrics["mean_confidence"],
        "confident_coverage": metrics["confident_coverage"],
        "confident_accuracy": metrics["confident_accuracy"],
        "median_stroop_trials": (
            frame["stroop_n"].median() if "stroop_n" in frame else None
        ),
        "median_flanker_trials": (
            frame["flanker_n"].median() if "flanker_n" in frame else None
        ),
        "per_class_recall": json.dumps(
            metrics["per_class_recall"],
            sort_keys=True,
        ),
    }


def _plot(results: pd.DataFrame, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    combined = results[results["variant"].str.contains(r"\+")].sort_values(
        "balanced_accuracy"
    )
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.barh(
        combined["variant"],
        combined["balanced_accuracy"],
        color="#4472C4",
    )
    axis.axvline(0.70, color="grey", linestyle="--", label="0.70 threshold")
    axis.set(
        xlim=(0.5, 0.8),
        xlabel="Participant-grouped balanced accuracy",
        ylabel="Prefix configuration",
        title="Recovery of four full-session control profiles",
    )
    axis.legend()
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _render_report(
    results: pd.DataFrame,
    yields: pd.DataFrame,
    common_sessions: int,
    common_subjects: int,
) -> str:
    two_minute = results[
        results["variant"].eq("stroop_2min+flanker_44")
    ].iloc[0]
    recalls = json.loads(two_minute["per_class_recall"])
    lines = [
        "# Two-Minute Stroop and Flanker Recovery",
        "",
        "> This analysis tests recovery of the exploratory four-component "
        "full-session partition. The partition is not validated ground truth.",
        "",
        "## Analysis set",
        "",
        f"- Matched paired sessions: {common_sessions:,}.",
        f"- Dataset-scoped participants: {common_subjects:,}.",
        "- Five-fold validation isolated participants across train and test.",
        "- Stroop elapsed time was modelled as RT + 400 ms interval + 400 ms "
        "error feedback.",
        "- The conservative two-minute Flanker prefix used 44 trials, based on "
        "the source protocol's maximum 2700 ms trial duration.",
        "",
        "## Recovery results",
        "",
        "| Variant | Stroop trials | Flanker trials | Balanced accuracy | "
        "Macro F1 | Coverage p>=0.60 | Accuracy when confident |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results.sort_values(
        ["balanced_accuracy", "variant"],
        ascending=[False, True],
    ).itertuples():
        lines.append(
            f"| {row.variant} | "
            f"{'' if pd.isna(row.median_stroop_trials) else int(row.median_stroop_trials)} | "
            f"{'' if pd.isna(row.median_flanker_trials) else int(row.median_flanker_trials)} | "
            f"{row.balanced_accuracy:.3f} | {row.macro_f1:.3f} | "
            f"{row.confident_coverage:.3f} | "
            f"{row.confident_accuracy:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Conservative six-minute configuration",
            "",
            "The operational candidate is approximately:",
            "",
            "```text",
            "2-minute source-prefix SART",
            "+ 2-minute Stroop",
            "+ 2-minute Flanker",
            "= approximately 6 minutes",
            "```",
            "",
            f"Its four-profile balanced accuracy was "
            f"`{two_minute['balanced_accuracy']:.3f}` with macro F1 "
            f"`{two_minute['macro_f1']:.3f}`. It returned predictions above "
            f"`0.60` confidence for {two_minute['confident_coverage']:.1%} of "
            f"sessions; accuracy within those sessions was "
            f"{two_minute['confident_accuracy']:.1%}.",
            "",
            "| Full-session neutral profile | Recall |",
            "|---|---:|",
        ]
    )
    for profile, recall in recalls.items():
        lines.append(f"| {profile} | {recall:.3f} |")
    lines.extend(
        [
            "",
            "The globally overloaded component had the weakest recall. This "
            "component is also the smallest and produces fewer Stroop trials "
            "within a fixed two-minute period.",
            "",
            "## Fixed-duration Stroop evidence bias",
            "",
            "| Full-session profile | Median trials | P10-P90 | Below 60 | "
            "Below 80 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in yields.itertuples():
        lines.append(
            f"| {row.control_profile} | {row.median_trials:.0f} | "
            f"{row.p10_trials:.0f}-{row.p90_trials:.0f} | "
            f"{row.below_60_rate:.1%} | {row.below_80_rate:.1%} |"
        )
    lines.extend(
        [
            "",
            "A fixed-duration Stroop yields less evidence for slow and "
            "overloaded sessions. Trial count must therefore be an explicit "
            "model input and quality variable; fewer than 60 scored trials "
            "should normally trigger abstention.",
            "",
            "## Interpretation",
            "",
            "The six-minute protocol is feasible for a research prototype. "
            "Combined prefixes materially outperform either task alone and "
            "cross the provisional 0.70 balanced-accuracy threshold. However, "
            "the result is an internal recovery analysis because full-session "
            "profiles and shortened features come from the same dataset.",
            "",
            "A redesigned response-contingent Flanker could deliver more than "
            "44 trials in two minutes, but changing stimulus duration or "
            "response termination changes the task and requires fresh "
            "validation. The present result should not be used to claim "
            "production classifier validity.",
            "",
            "## Recommended next protocol",
            "",
            "```text",
            "20-30 second context check",
            "2-minute source-prefix SART; use 3 minutes when higher "
            "single-session fidelity is required",
            "2-minute Stroop, target >=80 and minimum 60 scored trials",
            "2-minute Flanker, conservative target 44 scored trials",
            "probabilistic four-profile control output",
            "continuous vigilance output",
            "abstain when evidence or confidence is insufficient",
            "```",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    sessions = pd.read_parquet(args.sessions)
    stroop = prepare_task_trials(
        _load_raw(args, "stroop"),
        sessions,
        "stroop",
    )
    flanker = prepare_task_trials(
        _load_raw(args, "flanker"),
        sessions,
        "flanker",
    )
    flanker_two_minute = flanker_two_minute_trials()

    prefixes = {
        "stroop_60": summarize_prefix(
            stroop,
            "stroop",
            lambda frame: frame["trial_order"].le(60),
        ),
        "stroop_80": summarize_prefix(
            stroop,
            "stroop",
            lambda frame: frame["trial_order"].le(80),
        ),
        "stroop_100": summarize_prefix(
            stroop,
            "stroop",
            lambda frame: frame["trial_order"].le(100),
        ),
        "stroop_2min": summarize_prefix(
            stroop,
            "stroop",
            lambda frame: frame["modelled_elapsed_ms"].le(120_000),
        ),
        "flanker_44": summarize_prefix(
            flanker,
            "flanker",
            lambda frame: frame["trial_order"].le(flanker_two_minute),
        ),
        "flanker_60": summarize_prefix(
            flanker,
            "flanker",
            lambda frame: frame["trial_order"].le(60),
        ),
        "flanker_80": summarize_prefix(
            flanker,
            "flanker",
            lambda frame: frame["trial_order"].le(80),
        ),
    }
    variants = {
        "stroop_2min": prefixes["stroop_2min"],
        "stroop_80": prefixes["stroop_80"],
        "stroop_100": prefixes["stroop_100"],
        "flanker_44": prefixes["flanker_44"],
        "flanker_60": prefixes["flanker_60"],
        "flanker_80": prefixes["flanker_80"],
    }
    for stroop_name, flanker_name in (
        ("stroop_2min", "flanker_44"),
        ("stroop_60", "flanker_44"),
        ("stroop_80", "flanker_44"),
        ("stroop_100", "flanker_44"),
        ("stroop_80", "flanker_60"),
        ("stroop_80", "flanker_80"),
    ):
        name = f"{stroop_name}+{flanker_name}"
        variants[name] = merge_task_prefixes(
            prefixes[stroop_name],
            prefixes[flanker_name],
        )

    results = pd.DataFrame(
        [
            _evaluate(name, frame, args.seed)
            for name, frame in variants.items()
        ]
    )
    common = variants["stroop_2min+flanker_44"]
    yields = trial_yield_by_profile(prefixes["stroop_2min"])
    write_table(results, args.table)
    write_table(yields, args.yield_table)
    _plot(results, args.figure)
    write_text(
        _render_report(
            results,
            yields,
            len(common),
            common["participant_id"].nunique(),
        ),
        args.report,
    )
    print(
        json.dumps(
            {
                "report": str(args.report),
                "table": str(args.table),
                "sessions": len(common),
                "participants": common["participant_id"].nunique(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
