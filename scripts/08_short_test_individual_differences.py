#!/usr/bin/env python3
"""Test short Stroop profile recovery and individual differences."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.config import load_config
from flowzone_validation.profile_recoverability import (
    SHORT_TEST_FEATURES,
    build_prefix_features,
    grouped_profile_recovery,
    one_way_icc,
    profile_repeatability,
)
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)
from flowzone_validation.residualisation import robust_scale_within_sources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trials",
        type=Path,
        default=ROOT / "data/processed/acdc_cleaned_trials.parquet",
    )
    parser.add_argument(
        "--windows",
        type=Path,
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument(
        "--assignments",
        type=Path,
        default=ROOT / "data/processed/stroop_zone_count_assignments.parquet",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/pilot.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/stroop_short_test_individual_differences.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports/tables",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=ROOT / "reports/figures/stroop_trial_count_recovery.png",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "reports/run_manifest.json",
    )
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _plot_recovery(results: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(
        results["trial_count"],
        results["balanced_accuracy"],
        marker="o",
        label="Balanced accuracy",
    )
    axis.plot(
        results["trial_count"],
        results["macro_f1"],
        marker="s",
        label="Macro F1",
    )
    axis.plot(
        results["trial_count"],
        results["confident_coverage"],
        marker="^",
        label="Coverage at p >= 0.60",
    )
    axis.axhline(1 / 3, color="grey", linestyle="--", label="3-class chance")
    axis.set(
        xlabel="Trials used from each 80-trial window",
        ylabel="Score",
        ylim=(0, 1.02),
        title="Participant-grouped Stroop profile recovery",
    )
    axis.legend()
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _render_report(
    recovery: pd.DataFrame,
    repeatability: dict[str, Any],
    transitions: pd.DataFrame,
    icc: pd.DataFrame,
) -> str:
    best_short = recovery[recovery["trial_count"].lt(80)].sort_values(
        "balanced_accuracy",
        ascending=False,
    ).iloc[0]
    earliest_usable = recovery[
        recovery["balanced_accuracy"].ge(0.70)
        & recovery["confident_coverage"].ge(0.60)
    ]
    lines = [
        "# Stroop Short-Test and Individual-Differences Analysis",
        "",
        "> Full-window GMM assignments are treated as provisional reference "
        "profiles, not validated ground truth.",
        "",
        "## Shorter trial counts",
        "",
        "Each row uses the first trials from the exact original 80-trial window. "
        "Prediction uses participant-isolated five-fold validation.",
        "",
        "| Trials | Features | Balanced accuracy | Macro F1 | Mean confidence | "
        "Coverage p>=0.60 | Confident accuracy |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in recovery.itertuples():
        lines.append(
            f"| {row.trial_count} | {row.feature_count} | "
            f"{row.balanced_accuracy:.3f} | {row.macro_f1:.3f} | "
            f"{row.mean_confidence:.3f} | {row.confident_coverage:.3f} | "
            f"{row.confident_accuracy:.3f} |"
        )
    lines.extend(
        [
            "",
            "### Profile-specific recall",
            "",
            "| Trials | Slow overloaded (C1) | Efficient regulated (C2) | "
            "Fast brittle (C3) |",
            "|---:|---:|---:|---:|",
        ]
    )
    for row in recovery.itertuples():
        recalls = row.per_class_recall
        lines.append(
            f"| {row.trial_count} | "
            f"{recalls['Stroop-GMM3-full-C1']:.3f} | "
            f"{recalls['Stroop-GMM3-full-C2']:.3f} | "
            f"{recalls['Stroop-GMM3-full-C3']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"The strongest sub-80-trial result used {int(best_short['trial_count'])} "
            f"trials (balanced accuracy {best_short['balanced_accuracy']:.3f}).",
        ]
    )
    if not earliest_usable.empty:
        earliest = earliest_usable.sort_values("trial_count").iloc[0]
        lines.append(
            f"The first trial count meeting the provisional 0.70 balanced-accuracy "
            f"and 0.60 coverage thresholds was {int(earliest['trial_count'])}."
        )
    else:
        lines.append(
            "No shortened condition met both provisional deployment thresholds."
        )
    lines.extend(
        [
            "",
            "## Individual differences",
            "",
            f"- Participants: {repeatability['n_subjects']}",
            f"- Median windows per participant: "
            f"{repeatability['median_windows_per_subject']:.1f}",
            f"- Median modal-profile share: "
            f"{repeatability['median_modal_share']:.3f}",
            f"- Participants showing more than one profile: "
            f"{repeatability['participants_with_multiple_profiles_fraction']:.1%}",
            f"- Within-participant pair agreement: "
            f"{repeatability['within_participant_pair_agreement']:.3f}",
            f"- Dataset-preserving permutation expectation: "
            f"{repeatability['permutation_pair_agreement_mean']:.3f} "
            f"(p={repeatability['permutation_pair_agreement_p_value']:.4f})",
            f"- Adjacent same-profile rate: "
            f"{repeatability['adjacent_same_profile_rate']:.3f}",
            f"- Marginal chance same-profile rate: "
            f"{repeatability['marginal_chance_same_profile_rate']:.3f}",
            "",
            "### Adjacent-window transitions",
            "",
            "| From | To | Count | Probability |",
            "|---|---|---:|---:|",
        ]
    )
    for row in transitions.itertuples():
        lines.append(
            f"| {row.from_profile} | {row.to_profile} | {row.count} | "
            f"{row.row_probability:.3f} |"
        )
    lines.extend(
        [
            "",
            "The efficient regulated profile is the most persistent. The fast "
            "brittle profile is comparatively transient and most often moves to "
            "the regulated profile in the next adjacent window. This pattern is "
            "consistent with a mixed trait-state account, although it does not "
            "establish causal recovery.",
            "",
            "High modal consistency and ICC indicate stable individual "
            "differences. Frequent within-person transitions and low ICC indicate "
            "state-like variation. Evidence for both implies a mixed trait-state "
            "structure.",
            "",
            "## Source-adjusted feature ICC",
            "",
            "| Feature | ICC(1) | Interpretation | Windows | Participants |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for row in icc.itertuples():
        lines.append(
            f"| {row.feature} | {row.icc_1:.3f} | {row.interpretation} | "
            f"{row.n_windows} | {row.n_subjects} |"
        )
    lines.extend(
        [
            "",
            "## App implication",
            "",
            "A short app should return calibrated profile probabilities and an "
            "uncertain result rather than force a label. App-specific timing, "
            "instructions and normative data must be validated independently. "
            "This analysis measures recovery of an exploratory ACDC partition, "
            "not clinical or production classification validity.",
        ]
    )
    return "\n".join(lines)


def _json_safe(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")


def main() -> None:
    args = parse_args()
    required = [args.trials, args.windows, args.assignments, args.config]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Required inputs are missing: " + ", ".join(str(path) for path in missing)
        )
    config = load_config(args.config)
    trials = pd.read_parquet(args.trials)
    windows = pd.read_parquet(args.windows)
    assignments = pd.read_parquet(args.assignments)
    target = "Stroop-GMM3-full_cluster_id"
    reference = windows.merge(
        assignments[["window_id", target]],
        on="window_id",
        how="inner",
        validate="one_to_one",
    )
    target_ids = set(reference["window_id"].astype(str))

    print("Building 20-80 trial prefix features", flush=True)
    prefixes = build_prefix_features(trials, target_ids, config)
    prefixes = prefixes.merge(
        assignments[["window_id", target]].rename(
            columns={"window_id": "parent_window_id"}
        ),
        on="parent_window_id",
        how="inner",
        validate="many_to_one",
    )
    recovery_rows: list[dict[str, Any]] = []
    predictions: list[pd.DataFrame] = []
    for trial_count, group in prefixes.groupby("trial_count", sort=True):
        print(f"Testing {trial_count} trials", flush=True)
        metrics, prediction = grouped_profile_recovery(
            group,
            list(SHORT_TEST_FEATURES),
            target,
            seed=args.seed,
        )
        recovery_rows.append({"trial_count": trial_count, **metrics})
        prediction["trial_count"] = trial_count
        predictions.append(prediction)
    recovery = pd.DataFrame(recovery_rows)
    recall_rows = []
    for row in recovery.itertuples():
        for profile, recall in row.per_class_recall.items():
            recall_rows.append(
                {
                    "trial_count": row.trial_count,
                    "profile": profile,
                    "recall": recall,
                }
            )
    class_recall = pd.DataFrame(recall_rows)

    print("Estimating participant repeatability", flush=True)
    repeatability, occupancy, transitions = profile_repeatability(
        reference,
        target,
        permutations=args.permutations,
        seed=args.seed,
    )
    selected = [
        feature
        for feature in SHORT_TEST_FEATURES
        if feature in reference and reference[feature].notna().any()
    ]
    adjusted = robust_scale_within_sources(
        reference,
        selected,
        source_columns=("dataset_id", "task_family"),
    )
    icc = one_way_icc(
        adjusted,
        [f"{feature}__source_adjusted" for feature in selected],
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_table(
        recovery.drop(columns=["per_class_recall", "features"]),
        args.output_dir / "stroop_trial_count_recovery.csv",
    )
    write_table(
        class_recall,
        args.output_dir / "stroop_trial_count_class_recall.csv",
    )
    write_table(
        pd.concat(predictions, ignore_index=True),
        args.output_dir / "stroop_trial_count_predictions.csv",
    )
    write_table(
        occupancy,
        args.output_dir / "stroop_participant_profile_occupancy.csv",
    )
    write_table(
        transitions,
        args.output_dir / "stroop_profile_transitions.csv",
    )
    write_table(icc, args.output_dir / "stroop_feature_icc.csv")
    _plot_recovery(recovery, args.figure)
    write_text(
        _render_report(recovery, repeatability, transitions, icc),
        args.report,
    )
    write_json(
        {
            "trial_count_recovery": _json_safe(recovery),
            "repeatability": repeatability,
            "feature_icc": _json_safe(icc),
        },
        args.report.with_suffix(".json"),
    )
    update_run_manifest(
        args.manifest,
        ROOT,
        "stroop_short_test_individual_differences",
        {
            "trial_counts": sorted(recovery["trial_count"].astype(int).tolist()),
            "reference_profile": target,
            "participant_grouped": True,
            "permutations": args.permutations,
            "seed": args.seed,
            "report": str(args.report),
        },
    )
    print(f"Wrote {args.report}", flush=True)


if __name__ == "__main__":
    main()
