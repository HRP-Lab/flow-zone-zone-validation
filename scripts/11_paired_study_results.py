#!/usr/bin/env python3
"""Generate joint and repeat-session results for the paired-task study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.paired_study import (
    control_vigilance_association,
    profile_repeatability,
)
from flowzone_validation.reporting import write_json, write_table, write_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=(
            ROOT
            / "data/processed/paired_vigilance_session_features.parquet"
        ),
    )
    parser.add_argument(
        "--profile-table",
        type=Path,
        default=ROOT / "reports/tables/paired_control_cluster_profiles.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports/tables",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/paired_study_supplement.md",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=ROOT / "reports/paired_study_supplement.json",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=ROOT / "reports/figures/control_vigilance_joint.png",
    )
    parser.add_argument("--engagement-threshold", type=float, default=-0.5)
    parser.add_argument("--bootstrap-repetitions", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _plot_joint(
    rates: pd.DataFrame,
    label_map: dict[str, str],
    output: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plot = rates.copy()
    plot["label"] = plot["control_profile"].map(label_map).fillna(
        plot["control_profile"]
    )
    plot = plot.sort_values("low_engagement_rate")
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.barh(
        plot["label"],
        plot["low_engagement_rate"],
        color="#C55A11",
    )
    overall = (
        plot["low_engagement_sessions"].sum()
        / plot["total_sessions"].sum()
    )
    axis.axvline(
        overall,
        color="grey",
        linestyle="--",
        label=f"Overall rate ({overall:.1%})",
    )
    axis.set(
        xlim=(0, 0.8),
        xlabel="Low-engagement session rate",
        ylabel="Neutral control profile",
        title="Control profiles are associated with SART engagement",
    )
    axis.legend()
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _render_report(
    joint_statistics: dict,
    rates: pd.DataFrame,
    odds: pd.DataFrame,
    repeat_statistics: dict,
    repeat_profiles: pd.DataFrame,
    binary_icc: pd.DataFrame,
    label_map: dict[str, str],
) -> str:
    lines = [
        "# Paired-Study Joint and Repeat-Session Results",
        "",
        "> Profile names below are descriptive interpretations of neutral "
        "mixture components. They are not validated cognitive states.",
        "",
        "## Control and engagement association",
        "",
        f"- Sessions: {joint_statistics['n_sessions']:,}.",
        f"- Participants: {joint_statistics['n_participants']:,}.",
        f"- Low-engagement threshold: SART engagement index <= "
        f"`{joint_statistics['engagement_threshold']:.2f}`.",
        f"- Chi-square: `{joint_statistics['chi_square']:.3f}`, "
        f"df `{joint_statistics['degrees_freedom']}`, "
        f"p `{joint_statistics['p_value']:.3g}`.",
        f"- Cramer's V: `{joint_statistics['cramers_v']:.3f}`.",
        "",
        "| Neutral profile | Interpretation | Sessions | Low engagement | "
        "Rate | Observed/expected |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rates.itertuples():
        lines.append(
            f"| {row.control_profile} | "
            f"{label_map.get(row.control_profile, 'unmapped')} | "
            f"{row.total_sessions} | {row.low_engagement_sessions} | "
            f"{row.low_engagement_rate:.1%} | "
            f"{row.low_engagement_observed_expected_ratio:.2f} |"
        )
    lines.extend(
        [
            "",
            "Participant-clustered bootstrap intervals:",
            "",
            "| Interpretation | Low-engagement rate, 95% CI | "
            "One-vs-rest OR, 95% CI |",
            "|---|---:|---:|",
        ]
    )
    for row in odds.itertuples():
        lines.append(
            f"| {label_map.get(row.control_profile, row.control_profile)} | "
            f"{row.low_engagement_rate:.1%} "
            f"[{row.low_engagement_rate_ci_lower:.1%}, "
            f"{row.low_engagement_rate_ci_upper:.1%}] | "
            f"{row.one_vs_rest_odds_ratio:.2f} "
            f"[{row.odds_ratio_ci_lower:.2f}, "
            f"{row.odds_ratio_ci_upper:.2f}] |"
        )
    lines.extend(
        [
            "",
            "The dimensions are associated but not deterministic. Every control "
            "profile contains both preserved- and low-engagement sessions.",
            "",
            "## Repeat-session profile structure",
            "",
            f"- Repeated-session participants: "
            f"{repeat_statistics['n_repeated_participants']:,}.",
            f"- Repeated sessions: "
            f"{repeat_statistics['n_repeated_sessions']:,}.",
            f"- Participants showing multiple profiles: "
            f"{repeat_statistics['participants_with_multiple_profiles_rate']:.1%}.",
            f"- Overall adjacent-session persistence: "
            f"{repeat_statistics['overall_adjacent_persistence']:.1%}.",
            "",
            "| Interpretation | Sessions | Participants | Adjacent persistence | "
            "Always profile among ever-profile participants |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in repeat_profiles.itertuples():
        lines.append(
            f"| {label_map.get(row.control_profile, row.control_profile)} | "
            f"{row.n_sessions} | {row.n_participants} | "
            f"{row.adjacent_persistence:.1%} | "
            f"{row.ever_profile_always_profile_rate:.1%} |"
        )
    lines.extend(
        [
            "",
            "### Binary profile ICC",
            "",
            "| Profile indicator | ICC(1) | Interpretation |",
            "|---|---:|---|",
        ]
    )
    for row in binary_icc.itertuples():
        lines.append(
            f"| {row.feature} | {row.icc_1:.3f} | {row.interpretation} |"
        )
    lines.extend(
        [
            "",
            "The control profiles therefore show mixed trait-state structure. "
            "The regulated and slow-compensatory components are more persistent, "
            "whereas the globally overloaded component is comparatively "
            "transient in the repeated-session subset.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    frame = pd.read_parquet(args.input)
    profiles = pd.read_csv(args.profile_table)
    label_map = dict(
        zip(
            profiles["control_profile"],
            profiles["provisional_pattern_note"],
            strict=True,
        )
    )
    joint = control_vigilance_association(
        frame,
        threshold=args.engagement_threshold,
        bootstrap_repetitions=args.bootstrap_repetitions,
        seed=args.seed,
    )
    repeatability = profile_repeatability(frame)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_table(
        joint.counts,
        args.output_dir / "control_vigilance_joint_counts.csv",
    )
    write_table(
        joint.rates,
        args.output_dir / "control_vigilance_joint_rates.csv",
    )
    write_table(
        joint.odds_ratios,
        args.output_dir / "control_vigilance_odds_ratios.csv",
    )
    write_table(
        repeatability.transitions,
        args.output_dir / "control_profile_transitions.csv",
    )
    write_table(
        repeatability.profiles,
        args.output_dir / "control_profile_repeatability.csv",
    )
    write_table(
        repeatability.binary_icc,
        args.output_dir / "control_profile_binary_icc.csv",
    )
    _plot_joint(joint.rates, label_map, args.figure)
    write_text(
        _render_report(
            joint.statistics,
            joint.rates,
            joint.odds_ratios,
            repeatability.statistics,
            repeatability.profiles,
            repeatability.binary_icc,
            label_map,
        ),
        args.report,
    )
    metrics = {
        "joint_association": joint.statistics,
        "profile_repeatability": repeatability.statistics,
        "parameters": {
            "seed": args.seed,
            "engagement_threshold": args.engagement_threshold,
            "bootstrap_repetitions": args.bootstrap_repetitions,
        },
    }
    write_json(metrics, args.metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
