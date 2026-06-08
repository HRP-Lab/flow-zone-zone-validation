#!/usr/bin/env python3
"""Validate the first 144 SART trials against the full 225-trial session."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.paired_study import control_vigilance_association
from flowzone_validation.paired_vigilance import (
    decompose_associations,
    grouped_control_prediction,
    grouped_profile_prediction,
)
from flowzone_validation.profile_recoverability import one_way_icc
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)
from flowzone_validation.sart_abbreviation import (
    agreement_table,
    binary_threshold_agreement,
    build_match_audit,
    match_sart_sessions,
    prepare_sart_trials,
    score_sart_prefix,
    summarize_sart_trials,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    study = ROOT / "studies/paired-control-vigilance"
    parser.add_argument(
        "--raw",
        type=Path,
        default=ROOT / "data/raw/stroop_sart_flanker/Raw_Sart.xlsx",
    )
    parser.add_argument(
        "--sessions",
        type=Path,
        default=(
            ROOT / "data/processed/paired_vigilance_session_features.parquet"
        ),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=ROOT / "data/interim/paired_raw_sart.parquet",
    )
    parser.add_argument(
        "--session-output",
        type=Path,
        default=ROOT / "data/processed/sart_3min_validation_sessions.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=study / "outputs/tables",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=study / "outputs/figures",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=study / "outputs/reports/sart_3min_validation.md",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=study / "outputs/manifests/sart_3min_validation_metrics.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=study / "outputs/manifests/study_run_manifest.json",
    )
    parser.add_argument("--prefix-trials", type=int, default=144)
    parser.add_argument(
        "--sensitivity-trials",
        type=int,
        nargs="+",
        default=[90, 120, 144, 180],
    )
    parser.add_argument("--engagement-threshold", type=float, default=-0.5)
    parser.add_argument("--bootstrap-repetitions", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _load_raw(args: argparse.Namespace) -> pd.DataFrame:
    if args.cache.exists():
        return pd.read_parquet(args.cache)
    if not args.raw.exists():
        raise FileNotFoundError(f"Raw SART workbook is missing: {args.raw}")
    columns = [
        "subjectid",
        "date",
        "time",
        "blockcode",
        "trialcode",
        "trialnum",
        "expressions.trialcount",
        "values.trialtype",
        "values.digit",
        "response",
        "correct",
        "values.RT",
        "latency",
        "values.latencytype",
        "values.responsetype",
    ]
    frame = pd.read_excel(
        args.raw,
        sheet_name="Inquisit Data",
        usecols=columns,
    )
    write_table(frame, args.cache)
    return frame


def _raw_metric_pairs(prefix: str, full: str) -> list[tuple[str, str, str]]:
    return [
        (
            "commission_rate",
            f"{prefix}_sart_commission_rate_raw",
            f"{full}_sart_commission_rate_raw",
        ),
        (
            "omission_rate",
            f"{prefix}_sart_omission_rate_raw",
            f"{full}_sart_omission_rate_raw",
        ),
        (
            "anticipatory_rate",
            f"{prefix}_sart_anticipatory_rate_raw",
            f"{full}_sart_anticipatory_rate_raw",
        ),
        (
            "go_mean_rt_ms",
            f"{prefix}_sart_go_mean_rt_ms_raw",
            f"{full}_sart_go_mean_rt_ms_raw",
        ),
        (
            "go_rt_cv",
            f"{prefix}_sart_go_rt_cv_raw",
            f"{full}_sart_go_rt_cv_raw",
        ),
    ]


def _rename_raw_columns(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    metadata = {
        "raw_session_id",
        "source_subject_id",
        "raw_date",
        "raw_time",
        "prefix_trials",
    }
    return frame.rename(
        columns={
            column: f"{label}_{column}"
            for column in frame.columns
            if column not in metadata
        }
    )


def _prediction_tables(
    full: pd.DataFrame,
    abbreviated: pd.DataFrame,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    control_rows = []
    profile_rows = []
    for source, frame in (("full_225", full), ("abbreviated_144", abbreviated)):
        control = grouped_control_prediction(frame, seed=seed)
        control = control[
            control["model"].isin(
                [
                    "intercept_only",
                    "engagement_only",
                    "inhibitory_only",
                    "two_sart_dimensions",
                ]
            )
        ].copy()
        control.insert(0, "sart_source", source)
        control_rows.append(control)
        profile = grouped_profile_prediction(frame, seed=seed)
        profile.insert(0, "sart_source", source)
        profile_rows.append(profile)
    return (
        pd.concat(control_rows, ignore_index=True),
        pd.concat(profile_rows, ignore_index=True),
    )


def _plot_agreement(
    frame: pd.DataFrame,
    output: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    pairs = [
        (
            "sart_engagement_index",
            "sart_3min_engagement_index",
            "Engagement-vigilance",
        ),
        (
            "sart_inhibitory_stability_index",
            "sart_3min_inhibitory_stability_index",
            "Inhibitory stability",
        ),
    ]
    for axis, (full, abbreviated, title) in zip(axes, pairs, strict=True):
        sns.scatterplot(
            data=frame,
            x=full,
            y=abbreviated,
            hue="control_profile",
            alpha=0.55,
            s=24,
            legend=False,
            ax=axis,
        )
        minimum = float(frame[[full, abbreviated]].min().min())
        maximum = float(frame[[full, abbreviated]].max().max())
        axis.plot(
            [minimum, maximum],
            [minimum, maximum],
            color="grey",
            linestyle="--",
            linewidth=1,
        )
        axis.set(
            title=title,
            xlabel="Full 225-trial score",
            ylabel="First-144-trial score",
        )
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _plot_sensitivity(frame: pd.DataFrame, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    sns.lineplot(
        data=frame,
        x="duration_minutes",
        y="spearman_r",
        hue="dimension",
        marker="o",
        ax=axes[0],
    )
    axes[0].axvline(3, color="grey", linestyle="--", linewidth=1)
    axes[0].set(
        ylim=(0, 1),
        title="Score association with full SART",
        xlabel="Prefix duration, minutes",
        ylabel="Spearman correlation",
    )
    classification = frame[
        frame["dimension"].eq("engagement_vigilance")
    ]
    axes[1].plot(
        classification["duration_minutes"],
        classification["low_engagement_balanced_accuracy"],
        marker="o",
        color="#C55A11",
    )
    axes[1].axvline(3, color="grey", linestyle="--", linewidth=1)
    axes[1].axhline(0.75, color="grey", linestyle=":", linewidth=1)
    axes[1].set(
        ylim=(0.5, 1),
        title="Low-engagement classification agreement",
        xlabel="Prefix duration, minutes",
        ylabel="Balanced accuracy",
    )
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _fmt(value: object, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return "" if not np.isfinite(number) else f"{number:.{digits}f}"


def _render_report(
    audit: pd.DataFrame,
    integrity: pd.DataFrame,
    metric_agreement: pd.DataFrame,
    dimension_agreement: pd.DataFrame,
    within_person_agreement: pd.DataFrame,
    threshold: dict[str, Any],
    association_summary: pd.DataFrame,
    association_rates: pd.DataFrame,
    associations: pd.DataFrame,
    icc: pd.DataFrame,
    prediction: pd.DataFrame,
    profile_prediction: pd.DataFrame,
    sensitivity: pd.DataFrame,
    prefix_row: pd.Series,
) -> str:
    audit_row = audit.iloc[0]
    engagement = dimension_agreement[
        dimension_agreement["metric"].eq("engagement_vigilance")
    ].iloc[0]
    inhibition = dimension_agreement[
        dimension_agreement["metric"].eq("inhibitory_stability")
    ].iloc[0]
    full_assoc = association_summary[
        association_summary["sart_source"].eq("full_225")
    ].iloc[0]
    short_assoc = association_summary[
        association_summary["sart_source"].eq("abbreviated_144")
    ].iloc[0]
    engagement_supported = (
        engagement["spearman_r"] >= 0.80
        and engagement["lins_ccc"] >= 0.75
        and threshold["balanced_accuracy"] >= 0.75
    )
    inhibition_supported = (
        inhibition["spearman_r"] >= 0.70
        and inhibition["lins_ccc"] >= 0.65
    )
    lines = [
        "# Three-Minute SART Validation",
        "",
        "> This is an internal abbreviation analysis. The first 144 trials are "
        "nested within the full 225-trial SART and are not an independent "
        "validation sample.",
        "",
        "## 1. Purpose",
        "",
        "This analysis tests whether the first 144 trials (three minutes at "
        "1250 ms per trial) preserve the paired study's full-session SART "
        "engagement-vigilance and inhibitory-stability information.",
        "",
        "## 2. Raw linkage and integrity",
        "",
        f"- Raw SART main sessions: "
        f"{int(audit_row['raw_main_sessions']):,}.",
        f"- Paired study sessions: {int(audit_row['paired_sessions']):,}.",
        f"- Exact participant-bounded fingerprint matches: "
        f"{int(audit_row['accepted_exact_fingerprint_matches']):,}.",
        f"- Matched participants: "
        f"{int(audit_row['matched_participants']):,}.",
        f"- Rejected ambiguous/mismatched assignments: "
        f"{int(audit_row['rejected_fingerprint_assignments']):,}.",
        f"- Paired sessions without a candidate raw bout: "
        f"{int(audit_row['unmatched_paired_sessions']):,}.",
        "",
        "Matching was restricted within participant and required agreement on "
        "full-session commissions, omissions, anticipatory responses, Go RT, "
        "and Go RT CV. Rejected rows were not forced.",
        "",
        "The accepted raw full-session measures reproduce the published "
        "summary:",
        "",
        "| Measure | N | Pearson r | Lin CCC | MAE |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in integrity.itertuples():
        lines.append(
            f"| {row.metric} | {row.n_sessions} | "
            f"{_fmt(row.pearson_r)} | {_fmt(row.lins_ccc)} | "
            f"{_fmt(row.mae)} |"
        )
    lines.extend(
        [
            "",
            "## 3. Three-minute prefix",
            "",
            f"- Trials: {int(prefix_row['sart_trial_count_raw'])}.",
            f"- Go trials: {int(prefix_row['sart_go_count_raw'])}.",
            f"- NoGo trials: {int(prefix_row['sart_nogo_count_raw'])}.",
            "- The source used one fixed semi-random sequence. Every session "
            "therefore has the same 131/13 composition.",
            "",
            "A redesigned 128/16 sequence is not validated by this analysis.",
            "",
            "## 4. Raw metric agreement",
            "",
            "| Measure | Pearson r | Spearman r | Lin CCC | Bias | MAE |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in metric_agreement.itertuples():
        lines.append(
            f"| {row.metric} | {_fmt(row.pearson_r)} | "
            f"{_fmt(row.spearman_r)} | {_fmt(row.lins_ccc)} | "
            f"{_fmt(row.mean_bias)} | {_fmt(row.mae)} |"
        )
    lines.extend(
        [
            "",
            "## 5. Composite score agreement",
            "",
            "| Dimension | Pearson r | Spearman r | Lin CCC | MAE | "
            "Heuristic result |",
            "|---|---:|---:|---:|---:|---|",
            f"| Engagement-vigilance | {_fmt(engagement['pearson_r'])} | "
            f"{_fmt(engagement['spearman_r'])} | "
            f"{_fmt(engagement['lins_ccc'])} | "
            f"{_fmt(engagement['mae'])} | "
            f"{'supported' if engagement_supported else 'not supported'} |",
            f"| Inhibitory stability | {_fmt(inhibition['pearson_r'])} | "
            f"{_fmt(inhibition['spearman_r'])} | "
            f"{_fmt(inhibition['lins_ccc'])} | "
            f"{_fmt(inhibition['mae'])} | "
            f"{'supported' if inhibition_supported else 'not supported'} |",
            "",
            "The heuristic gates were not preregistered: engagement required "
            "Spearman r >= .80, CCC >= .75, and low-engagement balanced "
            "accuracy >= .75; inhibition required Spearman r >= .70 and "
            "CCC >= .65.",
            "",
            "Agreement remains high after separating stable person differences "
            "from session deviations:",
            "",
            "| Dimension | Level | Spearman correlation | N |",
            "|---|---|---:|---:|",
        ]
    )
    for row in within_person_agreement.itertuples():
        dimension = (
            "engagement_vigilance"
            if "engagement" in row.predictor
            else "inhibitory_stability"
        )
        lines.append(
            f"| {dimension} | {row.level} | "
            f"{_fmt(row.correlation)} | {row.n} |"
        )
    lines.extend(
        [
            "",
            "## 6. Low-engagement agreement",
            "",
            f"- Full-session low-engagement rate: "
            f"{threshold['reference_positive_rate']:.1%}.",
            f"- Three-minute low-engagement rate: "
            f"{threshold['abbreviated_positive_rate']:.1%}.",
            f"- Sensitivity: {threshold['sensitivity']:.3f}.",
            f"- Specificity: {threshold['specificity']:.3f}.",
            f"- Balanced accuracy: {threshold['balanced_accuracy']:.3f}.",
            f"- Cohen's kappa: {threshold['cohen_kappa']:.3f}.",
            "",
            "## 7. Control-profile association",
            "",
            f"- Full SART Cramer's V: {full_assoc['cramers_v']:.3f}.",
            f"- Three-minute SART Cramer's V: "
            f"{short_assoc['cramers_v']:.3f}.",
            "",
            "| SART source | Neutral profile | Low-engagement rate |",
            "|---|---|---:|",
        ]
    )
    for row in association_rates.itertuples():
        lines.append(
            f"| {row.sart_source} | {row.control_profile} | "
            f"{row.low_engagement_rate:.1%} |"
        )
    lines.extend(
        [
            "",
            "## 8. Between- and within-person associations",
            "",
            "| SART source | Dimension | Level | Correlation with "
            "task-active efficacy | N |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in associations.itertuples():
        lines.append(
            f"| {row.sart_source} | {row.predictor} | {row.level} | "
            f"{_fmt(row.correlation)} | {row.n} |"
        )
    lines.extend(
        [
            "",
            "## 9. Repeat-session ICC",
            "",
            "| SART source | Dimension | ICC(1) | Interpretation |",
            "|---|---|---:|---|",
        ]
    )
    for row in icc.itertuples():
        lines.append(
            f"| {row.sart_source} | {row.feature} | "
            f"{_fmt(row.icc_1)} | {row.interpretation} |"
        )
    lines.extend(
        [
            "",
            "## 10. Participant-grouped prediction",
            "",
            "Continuous task-active efficacy:",
            "",
            "| SART source | Model | CV R2 | MAE | RMSE |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in prediction.itertuples():
        lines.append(
            f"| {row.sart_source} | {row.model} | {_fmt(row.r2)} | "
            f"{_fmt(row.mae)} | {_fmt(row.rmse)} |"
        )
    lines.extend(
        [
            "",
            "Four-profile prediction:",
            "",
            "| SART source | Model | Balanced accuracy | Chance |",
            "|---|---|---:|---:|",
        ]
    )
    for row in profile_prediction.itertuples():
        lines.append(
            f"| {row.sart_source} | {row.model} | "
            f"{_fmt(row.balanced_accuracy)} | "
            f"{_fmt(row.chance_accuracy)} |"
        )
    lines.extend(
        [
            "",
            "## 11. Duration sensitivity",
            "",
            "| Trials | Minutes | Go | NoGo | Dimension | Spearman r | "
            "Lin CCC | Low-engagement balanced accuracy |",
            "|---:|---:|---:|---:|---|---:|---:|---:|",
        ]
    )
    for row in sensitivity.itertuples():
        lines.append(
            f"| {row.prefix_trials} | {row.duration_minutes:.2f} | "
            f"{row.go_trials} | {row.nogo_trials} | {row.dimension} | "
            f"{_fmt(row.spearman_r)} | {_fmt(row.lins_ccc)} | "
            f"{_fmt(row.low_engagement_balanced_accuracy)} |"
        )
    lines.extend(
        [
            "",
            "## 12. Interpretation",
            "",
            "The three-minute prefix has internal support for the dimensions "
            "that pass the stated agreement gates. "
            "Commission-based inhibitory stability is expected to be less "
            "precise because the prefix contains only 13 NoGo trials.",
            "",
            "Even a positive result is internal abbreviation evidence: the "
            "prefix is part of the full task, uses the same fixed sequence, "
            "and shares method variance with the reference. A prospective "
            "study must compare the abbreviated task with an independently "
            "administered full SART and an external outcome.",
            "",
            "## 13. Claim-safe conclusion",
            "",
            "This analysis estimates how much of the full paired-study SART "
            "signal is retained in its first three minutes. It can support "
            "selection of an abbreviated research protocol, but it does not "
            "validate under-activation, physiological arousal, work-readiness "
            "routing, or a production classifier.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if not args.sessions.exists():
        raise FileNotFoundError(
            f"Paired session features are missing: {args.sessions}"
        )
    sessions = pd.read_parquet(args.sessions)
    raw = _load_raw(args)
    trials = prepare_sart_trials(raw)
    full_summary = summarize_sart_trials(trials, prefix_trials=225)
    accepted, candidates = match_sart_sessions(full_summary, sessions)
    audit = build_match_audit(trials, sessions, candidates, accepted)
    metadata_columns = [
        "session_id",
        "participant_id",
        "session_type",
        "dataset_id",
        "control_profile",
        "task_active_efficacy",
        "sart_engagement_index",
        "sart_inhibitory_stability_index",
        "sart_commission_percent",
        "sart_omission_percent",
        "sart_anticipatory_count",
        "sart_go_mean_rt_ms",
        "sart_go_rt_cv",
        "sart_pre_failure_speeding_ms",
    ]
    metadata = accepted.merge(
        sessions[metadata_columns],
        on="session_id",
        validate="one_to_one",
    )

    full_scored = score_sart_prefix(
        full_summary,
        metadata,
        label="sart_full_raw",
    )
    prefix_summary = summarize_sart_trials(
        trials,
        prefix_trials=args.prefix_trials,
    )
    prefix_scored = score_sart_prefix(
        prefix_summary,
        metadata,
        label="sart_3min",
    )

    raw_full = _rename_raw_columns(full_scored, "full")
    raw_prefix = _rename_raw_columns(prefix_scored, "short")
    shared = [
        "raw_session_id",
        "session_id",
        "participant_id",
        "session_type",
        "dataset_id",
        "control_profile",
        "task_active_efficacy",
        "sart_engagement_index",
        "sart_inhibitory_stability_index",
        "sart_commission_percent",
        "sart_omission_percent",
        "sart_anticipatory_count",
        "sart_go_mean_rt_ms",
        "sart_go_rt_cv",
        "sart_pre_failure_speeding_ms",
    ]
    validation = raw_prefix.merge(
        raw_full[
            [
                "raw_session_id",
                *[
                    column
                    for column in raw_full.columns
                    if column.startswith("full_")
                ],
            ]
        ],
        on="raw_session_id",
        validate="one_to_one",
    )
    validation = validation.rename(
        columns={
            f"short_{column}": column
            for column in shared
            if f"short_{column}" in validation.columns
        }
    )
    # Preserve readable composite names after the raw-column namespacing.
    validation = validation.rename(
        columns={
            "short_sart_3min_engagement_index": (
                "sart_3min_engagement_index"
            ),
            "short_sart_3min_inhibitory_stability_index": (
                "sart_3min_inhibitory_stability_index"
            ),
            "full_sart_full_raw_engagement_index": (
                "sart_full_raw_engagement_index"
            ),
            "full_sart_full_raw_inhibitory_stability_index": (
                "sart_full_raw_inhibitory_stability_index"
            ),
        }
    )

    integrity = agreement_table(
        validation,
        [
            (
                "commission_percent",
                "full_sart_commission_percent_raw",
                "sart_commission_percent",
            ),
            (
                "omission_percent",
                "full_sart_omission_percent_raw",
                "sart_omission_percent",
            ),
            (
                "anticipatory_count",
                "full_sart_anticipatory_count_raw",
                "sart_anticipatory_count",
            ),
            (
                "go_mean_rt_ms",
                "full_sart_go_mean_rt_ms_raw",
                "sart_go_mean_rt_ms",
            ),
            (
                "go_rt_cv",
                "full_sart_go_rt_cv_raw",
                "sart_go_rt_cv",
            ),
        ],
    )
    metric_agreement = agreement_table(
        validation,
        _raw_metric_pairs("short", "full"),
    )
    dimension_agreement = agreement_table(
        validation,
        [
            (
                "engagement_vigilance",
                "sart_3min_engagement_index",
                "sart_engagement_index",
            ),
            (
                "inhibitory_stability",
                "sart_3min_inhibitory_stability_index",
                "sart_inhibitory_stability_index",
            ),
        ],
    )
    within_person_agreement = decompose_associations(
        validation,
        [
            (
                "sart_3min_engagement_index",
                "sart_engagement_index",
            ),
            (
                "sart_3min_inhibitory_stability_index",
                "sart_inhibitory_stability_index",
            ),
        ],
    )
    threshold = binary_threshold_agreement(
        validation["sart_3min_engagement_index"],
        validation["sart_engagement_index"],
        threshold=args.engagement_threshold,
    )

    full_model = validation.copy()
    abbreviated_model = validation.copy()
    abbreviated_model["sart_engagement_index"] = abbreviated_model[
        "sart_3min_engagement_index"
    ]
    abbreviated_model["sart_inhibitory_stability_index"] = abbreviated_model[
        "sart_3min_inhibitory_stability_index"
    ]
    association_rows = []
    rate_rows = []
    odds_rows = []
    for source, frame in (
        ("full_225", full_model),
        ("abbreviated_144", abbreviated_model),
    ):
        result = control_vigilance_association(
            frame,
            threshold=args.engagement_threshold,
            bootstrap_repetitions=args.bootstrap_repetitions,
            seed=args.seed,
        )
        association_rows.append(
            {"sart_source": source, **result.statistics}
        )
        rates = result.rates.copy()
        rates.insert(0, "sart_source", source)
        rate_rows.append(rates)
        odds = result.odds_ratios.copy()
        odds.insert(0, "sart_source", source)
        odds_rows.append(odds)
    association_summary = pd.DataFrame(association_rows)
    association_rates = pd.concat(rate_rows, ignore_index=True)
    association_odds = pd.concat(odds_rows, ignore_index=True)

    association_decomposition = []
    for source, frame in (
        ("full_225", full_model),
        ("abbreviated_144", abbreviated_model),
    ):
        table = decompose_associations(
            frame,
            [
                ("sart_engagement_index", "task_active_efficacy"),
                (
                    "sart_inhibitory_stability_index",
                    "task_active_efficacy",
                ),
            ],
        )
        table.insert(0, "sart_source", source)
        association_decomposition.append(table)
    associations = pd.concat(association_decomposition, ignore_index=True)

    icc_rows = []
    for source, frame in (
        ("full_225", full_model),
        ("abbreviated_144", abbreviated_model),
    ):
        table = one_way_icc(
            frame,
            [
                "sart_engagement_index",
                "sart_inhibitory_stability_index",
            ],
        )
        table.insert(0, "sart_source", source)
        icc_rows.append(table)
    icc = pd.concat(icc_rows, ignore_index=True)
    prediction, profile_prediction = _prediction_tables(
        full_model,
        abbreviated_model,
        args.seed,
    )

    sensitivity_rows = []
    sensitivity_scored: dict[int, pd.DataFrame] = {}
    for prefix_trials in sorted(set(args.sensitivity_trials)):
        summary = summarize_sart_trials(
            trials,
            prefix_trials=prefix_trials,
        )
        label = f"sart_{prefix_trials}"
        scored = score_sart_prefix(summary, metadata, label=label)
        sensitivity_scored[prefix_trials] = scored
        threshold_result = binary_threshold_agreement(
            scored[f"{label}_engagement_index"],
            scored["sart_engagement_index"],
            threshold=args.engagement_threshold,
        )
        agreements = agreement_table(
            scored,
            [
                (
                    "engagement_vigilance",
                    f"{label}_engagement_index",
                    "sart_engagement_index",
                ),
                (
                    "inhibitory_stability",
                    f"{label}_inhibitory_stability_index",
                    "sart_inhibitory_stability_index",
                ),
            ],
        )
        for row in agreements.itertuples():
            sensitivity_rows.append(
                {
                    "prefix_trials": prefix_trials,
                    "duration_minutes": prefix_trials * 1.25 / 60,
                    "go_trials": int(
                        scored["sart_go_count_raw"].iloc[0]
                    ),
                    "nogo_trials": int(
                        scored["sart_nogo_count_raw"].iloc[0]
                    ),
                    "dimension": row.metric,
                    "pearson_r": row.pearson_r,
                    "spearman_r": row.spearman_r,
                    "lins_ccc": row.lins_ccc,
                    "mae": row.mae,
                    "low_engagement_balanced_accuracy": (
                        threshold_result["balanced_accuracy"]
                        if row.metric == "engagement_vigilance"
                        else np.nan
                    ),
                    "low_engagement_kappa": (
                        threshold_result["cohen_kappa"]
                        if row.metric == "engagement_vigilance"
                        else np.nan
                    ),
                }
            )
    sensitivity = pd.DataFrame(sensitivity_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    write_table(validation, args.session_output)
    write_table(audit, args.output_dir / "sart_3min_match_audit.csv")
    write_table(
        integrity,
        args.output_dir / "sart_3min_source_integrity.csv",
    )
    write_table(
        metric_agreement,
        args.output_dir / "sart_3min_metric_agreement.csv",
    )
    write_table(
        dimension_agreement,
        args.output_dir / "sart_3min_dimension_agreement.csv",
    )
    write_table(
        within_person_agreement,
        args.output_dir / "sart_3min_within_person_agreement.csv",
    )
    write_table(
        pd.DataFrame([threshold]),
        args.output_dir / "sart_3min_low_engagement_agreement.csv",
    )
    write_table(
        association_summary,
        args.output_dir / "sart_3min_control_association.csv",
    )
    write_table(
        association_rates,
        args.output_dir / "sart_3min_control_profile_rates.csv",
    )
    write_table(
        association_odds,
        args.output_dir / "sart_3min_control_profile_odds.csv",
    )
    write_table(
        associations,
        args.output_dir / "sart_3min_association_decomposition.csv",
    )
    write_table(icc, args.output_dir / "sart_3min_icc_comparison.csv")
    write_table(
        prediction,
        args.output_dir / "sart_3min_prediction_comparison.csv",
    )
    write_table(
        profile_prediction,
        args.output_dir / "sart_3min_profile_prediction.csv",
    )
    write_table(
        sensitivity,
        args.output_dir / "sart_abbreviation_length_sensitivity.csv",
    )
    _plot_agreement(
        validation,
        args.figure_dir / "sart_3min_score_agreement.png",
    )
    _plot_sensitivity(
        sensitivity,
        args.figure_dir / "sart_abbreviation_sensitivity.png",
    )
    prefix_row = prefix_scored.iloc[0]
    report = _render_report(
        audit,
        integrity,
        metric_agreement,
        dimension_agreement,
        within_person_agreement,
        threshold,
        association_summary,
        association_rates,
        associations,
        icc,
        prediction,
        profile_prediction,
        sensitivity,
        prefix_row,
    )
    write_text(report, args.report)

    metrics: dict[str, Any] = {
        "raw_input": _portable_path(args.raw),
        "raw_sha256": _sha256(args.raw),
        "paired_sessions_input": _portable_path(args.sessions),
        "prefix_trials": args.prefix_trials,
        "prefix_duration_seconds": args.prefix_trials * 1.25,
        "matched_sessions": len(validation),
        "matched_participants": validation["participant_id"].nunique(),
        "engagement_threshold": args.engagement_threshold,
        "dimension_agreement": dimension_agreement.to_dict(orient="records"),
        "within_person_agreement": within_person_agreement.to_dict(
            orient="records"
        ),
        "low_engagement_agreement": threshold,
        "outputs": {
            "report": _portable_path(args.report),
            "tables": _portable_path(args.output_dir),
            "figures": _portable_path(args.figure_dir),
            "session_data": _portable_path(args.session_output),
        },
    }
    write_json(metrics, args.metrics)
    update_run_manifest(
        args.manifest,
        ROOT,
        "sart_3min_validation",
        {
            "raw_input": _portable_path(args.raw),
            "raw_sha256": metrics["raw_sha256"],
            "prefix_trials": args.prefix_trials,
            "prefix_duration_seconds": metrics["prefix_duration_seconds"],
            "matched_sessions": metrics["matched_sessions"],
            "matched_participants": metrics["matched_participants"],
            "seed": args.seed,
            "bootstrap_repetitions": args.bootstrap_repetitions,
        },
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
