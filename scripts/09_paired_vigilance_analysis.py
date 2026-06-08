#!/usr/bin/env python3
"""Test whether SART engagement adds a dimension beyond task-active control."""

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

from flowzone_validation.paired_vigilance import (
    build_session_features,
    decompose_associations,
    fit_control_mixtures,
    grouped_control_prediction,
    grouped_profile_prediction,
    overloaded_engagement_check,
    reshape_paired_summary,
    summarize_control_profiles,
)
from flowzone_validation.profile_recoverability import one_way_icc
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=(
            ROOT
            / "data/raw/stroop_sart_flanker"
            / "STROOP_FLANKERS_SART_web_and_lab.xls"
        ),
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=(
            ROOT
            / "data/processed/paired_vigilance_session_features.parquet"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/paired_vigilance_followup.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports/tables",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=ROOT / "reports/figures",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=ROOT / "reports/paired_vigilance_metrics.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "reports/run_manifest.json",
    )
    parser.add_argument("--bootstrap-repetitions", type=int, default=50)
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


def _plot_dimensions(frame: pd.DataFrame, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    sns.scatterplot(
        data=frame,
        x="sart_engagement_index",
        y="task_active_efficacy",
        hue="control_profile",
        alpha=0.65,
        s=30,
        ax=axes[0],
    )
    axes[0].axvline(-0.5, color="grey", linestyle="--", linewidth=1)
    axes[0].set(
        title="SART engagement and task-active efficacy",
        xlabel="SART engagement-vigilance index",
        ylabel="Stroop/Flanker task-active efficacy",
    )
    axes[0].legend(fontsize=7, title="Neutral profile")

    sns.scatterplot(
        data=frame,
        x="sart_engagement_index",
        y="sart_inhibitory_stability_index",
        hue="control_profile",
        alpha=0.65,
        s=30,
        legend=False,
        ax=axes[1],
    )
    axes[1].axvline(-0.5, color="grey", linestyle="--", linewidth=1)
    axes[1].set(
        title="Two SART dimensions",
        xlabel="Engagement-vigilance index",
        ylabel="Inhibitory-stability index",
    )
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _plot_overloaded(
    frame: pd.DataFrame,
    profiles: pd.DataFrame,
    output: Path,
) -> bool:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    match = profiles[
        profiles["provisional_pattern_note"].eq(
            "overloaded_control_candidate"
        )
    ]
    if match.empty:
        return False
    profile = match.iloc[0]["control_profile"]
    subset = frame[frame["control_profile"].eq(profile)]
    if subset.empty:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    sns.histplot(
        data=subset,
        x="sart_engagement_index",
        bins=20,
        kde=True,
        ax=axes[0],
    )
    axes[0].axvline(-0.5, color="grey", linestyle="--")
    axes[0].set(title=f"{profile}: engagement distribution")
    sns.scatterplot(
        data=subset,
        x="sart_engagement_index",
        y="sart_inhibitory_stability_index",
        hue="session_type",
        ax=axes[1],
    )
    axes[1].set(title="Engagement versus inhibitory stability")
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return True


def _fmt(value: object, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return "" if not np.isfinite(number) else f"{number:.{digits}f}"


def _render_report(
    frame: pd.DataFrame,
    loadings: pd.DataFrame,
    mixtures: pd.DataFrame,
    selected_model_id: str,
    profiles: pd.DataFrame,
    associations: pd.DataFrame,
    icc: pd.DataFrame,
    prediction: pd.DataFrame,
    profile_prediction: pd.DataFrame,
    overloaded: pd.DataFrame,
    input_hash: str,
) -> str:
    session_counts = frame["session_type"].value_counts()
    repeated = frame.groupby("participant_id").size()
    selected = mixtures[mixtures["model_id"].eq(selected_model_id)].iloc[0]
    model3 = mixtures[
        mixtures["model_id"].str.contains("GMM3")
        & mixtures["valid"].fillna(False)
    ].sort_values("bic")
    overloaded_profile = profiles[
        profiles["provisional_pattern_note"].eq(
            "overloaded_control_candidate"
        )
    ]
    overloaded_bic = np.nan
    if len(overloaded) >= 2 and overloaded["status"].eq("ok").all():
        one = overloaded[overloaded["k"].eq(1)]
        two = overloaded[overloaded["k"].eq(2)]
        if not one.empty and not two.empty:
            overloaded_bic = float(one.iloc[0]["bic"] - two.iloc[0]["bic"])

    lines = [
        "# Paired Vigilance and Task-Active Control Follow-Up",
        "",
        "> This analysis tests whether SART engagement/vigilance is a useful "
        "dimension beyond Stroop/Flanker task-active control. It does not "
        "diagnose under-arousal, disengagement, sleepiness, or a brain state.",
        "",
        "## 1. Purpose",
        "",
        "This secondary analysis uses participant-linked Stroop, Flanker, and "
        "SART sessions to identify neutral task-active control profiles and "
        "test whether vigilance-sensitive SART dimensions add information that "
        "conflict tasks do not measure directly.",
        "",
        "## 2. Data and integrity",
        "",
        "- Source: Barzykowski et al. (2022), paired online and laboratory "
        "Stroop, Flanker, and SART data.",
        f"- Published summary workbook SHA-256: `{input_hash}`.",
        f"- Participants: {frame['participant_id'].nunique():,}.",
        f"- Paired sessions: {len(frame):,}.",
        f"- Online sessions: {int(session_counts.get('online', 0)):,}.",
        f"- First laboratory sessions: {int(session_counts.get('lab1', 0)):,}.",
        f"- Second laboratory sessions: {int(session_counts.get('lab2', 0)):,}.",
        f"- Participants with at least two sessions: "
        f"{int(repeated.ge(2).sum()):,}.",
        "",
        "The published participant-level session table was used because it "
        "provides explicit cross-task and repeat-session linkage. Raw trial "
        "workbooks remain available for a later time-on-task analysis.",
        "",
        "## 3. Constructed dimensions",
        "",
        "The SART engagement-vigilance index is oriented so higher values mean "
        "fewer Go omissions and lower Go RT variability. The inhibitory-"
        "stability index is oriented so higher values mean fewer NoGo "
        "commissions and fewer anticipatory responses.",
        "",
        "| Score | Indicator | Direction | Weight | Diagnostic PC1 variance |",
        "|---|---|---:|---:|---:|",
    ]
    for row in loadings.itertuples():
        lines.append(
            f"| {row.score} | {row.indicator} | {row.direction:+d} | "
            f"{row.equal_weight:.3f} | "
            f"{row.diagnostic_pc1_variance:.1%} |"
        )
    lines.extend(
        [
            "",
            "These are behavioural dimensions. A low engagement-vigilance score "
            "is a candidate lapse/instability signal, not proof of low arousal.",
            "",
            "## 4. Neutral task-active profiles",
            "",
            "Mixtures used three context-adjusted dimensions: control accuracy, "
            "response speed, and conflict resilience. Component count was "
            "selected by BIC subject to minimum component sizes; component "
            "counts from one through five were compared and four profiles were "
            "not forced.",
            "",
            "| Model | Valid | BIC | Posterior entropy | Bootstrap ARI | Sizes |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in mixtures.sort_values(["k", "covariance"]).itertuples():
        lines.append(
            f"| {row.model_id} | {'yes' if bool(row.valid) else 'no'} | "
            f"{_fmt(getattr(row, 'bic', np.nan), 1)} | "
            f"{_fmt(getattr(row, 'posterior_entropy', np.nan))} | "
            f"{_fmt(getattr(row, 'bootstrap_ari_median', np.nan))} | "
            f"{getattr(row, 'component_sizes', '')} |"
        )
    lines.extend(
        [
            "",
            f"- Selected neutral model: `{selected_model_id}` "
            f"(BIC {_fmt(selected['bic'], 1)}; bootstrap ARI "
            f"{_fmt(selected['bootstrap_ari_median'])}).",
        ]
    )
    if not model3.empty:
        lines.append(
            f"- Best valid three-component comparison: "
            f"`{model3.iloc[0]['model_id']}` "
            f"(BIC {_fmt(model3.iloc[0]['bic'], 1)})."
        )
    lines.extend(
        [
            "",
            "| Neutral profile | Sessions | Efficacy | Accuracy index | "
            "Speed index | Conflict resilience | SART engagement | "
            "SART inhibition | Descriptive note |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in profiles.itertuples():
        lines.append(
            f"| {row.control_profile} | {row.n_sessions} | "
            f"{row.mean_task_active_efficacy:.3f} | "
            f"{row.mean_control_accuracy_index:.3f} | "
            f"{row.mean_control_speed_index:.3f} | "
            f"{row.mean_conflict_resilience_index:.3f} | "
            f"{row.mean_sart_engagement_index:.3f} | "
            f"{row.mean_sart_inhibitory_stability_index:.3f} | "
            f"{row.provisional_pattern_note} |"
        )
    lines.extend(
        [
            "",
            "## 5. Is engagement a separate dimension?",
            "",
            "Correlations are shown at the session level, between participant "
            "means, and within participants after person-mean centring. The "
            "within-person estimate uses only participants with repeated "
            "sessions.",
            "",
            "| Predictor | Outcome | Level | Correlation | N |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in associations.itertuples():
        lines.append(
            f"| {row.predictor} | {row.outcome} | {row.level} | "
            f"{_fmt(row.correlation)} | {row.n} |"
        )
    lines.extend(
        [
            "",
            "Low-to-moderate correlations support treating SART engagement and "
            "task-active control as related but non-identical dimensions. A "
            "large correlation would instead suggest that the SART score mostly "
            "relabels general performance.",
            "",
            "## 6. Trait-state structure",
            "",
            "| Feature | ICC(1) | Interpretation | Repeated sessions | "
            "Participants |",
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
            "ICC describes repeat-session consistency, not causation. Stable "
            "differences may reflect capacity, strategy, motor speed, or other "
            "person-level factors; session deviations may reflect time, fatigue, "
            "practice, context, or measurement noise.",
            "",
            "## 7. Incremental prediction",
            "",
            "All folds isolate dataset-scoped participants.",
            "",
            "| Model | Features | CV R2 | MAE | RMSE | Participant overlap |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in prediction.itertuples():
        lines.append(
            f"| {row.model} | {row.features or 'none'} | {row.r2:.3f} | "
            f"{row.mae:.3f} | {row.rmse:.3f} | "
            f"{row.maximum_participant_overlap} |"
        )
    lines.extend(
        [
            "",
            "| SART profile model | Balanced accuracy | Chance | "
            "Participant overlap |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in profile_prediction.itertuples():
        lines.append(
            f"| {row.model} | {row.balanced_accuracy:.3f} | "
            f"{row.chance_accuracy:.3f} | "
            f"{row.maximum_participant_overlap} |"
        )
    lines.extend(
        [
            "",
            "Prediction above chance indicates cross-task association. Weak "
            "prediction alongside reliable SART measurement is also meaningful: "
            "it favours a separate readiness/vigilance layer rather than a "
            "duplicate control classifier.",
            "",
            "## 8. Does the overloaded candidate split by engagement?",
            "",
        ]
    )
    if overloaded_profile.empty or overloaded.empty:
        lines.append("No overloaded candidate was available for this check.")
    else:
        profile = overloaded_profile.iloc[0]
        lines.extend(
            [
                f"The descriptive overloaded candidate was "
                f"`{profile['control_profile']}`. Its low-engagement candidate "
                f"rate was "
                f"{profile['low_engagement_candidate_rate']:.1%}.",
                "",
                "| SART mixture | BIC | AIC | Sizes | Valid sizes |",
                "|---|---:|---:|---|---|",
            ]
        )
        for row in overloaded.itertuples():
            if row.status != "ok":
                continue
            lines.append(
                f"| {row.model} | {row.bic:.1f} | {row.aic:.1f} | "
                f"{row.component_sizes} | "
                f"{'yes' if row.valid_components else 'no'} |"
            )
        lines.extend(
            [
                "",
                f"The two-subgroup BIC improvement over one subgroup was "
                f"{_fmt(overloaded_bic, 1)}. A positive value favours two "
                "descriptive SART subgroups, but does not prove categorical "
                "under-activation.",
            ]
        )
    lines.extend(
        [
            "",
            "## 9. Interpretation",
            "",
            "The defensible architecture is layered:",
            "",
            "```text",
            "SART engagement/vigilance",
            "  -> lapse-proneness and response-timing stability",
            "",
            "SART inhibitory stability",
            "  -> NoGo suppression and premature response control",
            "",
            "Stroop/Flanker task-active control",
            "  -> accuracy, speed policy, and conflict resilience",
            "```",
            "",
            "A slow or inefficient conflict-task profile should therefore not be "
            "called under-activated without convergent SART, subjective, sleep, "
            "context, or physiological evidence. Conversely, low SART "
            "engagement can occur without the same conflict-control profile.",
            "",
            "The SART is an executive-vigilance and response-inhibition task, not "
            "a pure Psychomotor Vigilance Test. A future app should use a short "
            "PVT-like probe if the primary target is arousal vigilance and "
            "sleep-loss sensitivity.",
            "",
            "## 10. Claim-safe conclusion",
            "",
            "This paired follow-up tests whether vigilance-sensitive SART "
            "behaviour adds a dimension beyond conflict-task performance. It can "
            "support a multi-layer readiness model if engagement and inhibitory "
            "stability show distinct repeat-session and cross-task patterns. It "
            "does not validate under-activation, clinical states, intervention "
            "routing, or production classification.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Required paired summary is missing: {args.input}")

    summary = pd.read_excel(args.input, engine="xlrd")
    sessions = reshape_paired_summary(summary)
    frame, loadings = build_session_features(sessions)
    complete = frame.dropna(
        subset=[
            "task_active_efficacy",
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
        ]
    ).copy()

    mixture_result = fit_control_mixtures(
        complete,
        bootstrap_repetitions=args.bootstrap_repetitions,
        seed=args.seed,
    )
    complete = complete.merge(
        mixture_result.assignments[
            ["session_id", "control_profile", "control_profile_probability"]
        ],
        on="session_id",
        how="left",
        validate="one_to_one",
    )
    profiles = summarize_control_profiles(complete)
    pairs = [
        ("sart_engagement_index", "task_active_efficacy"),
        ("sart_engagement_index", "control_accuracy_index"),
        ("sart_engagement_index", "control_speed_index"),
        ("sart_engagement_index", "conflict_resilience_index"),
        ("sart_inhibitory_stability_index", "task_active_efficacy"),
        ("sart_inhibitory_stability_index", "control_accuracy_index"),
        ("sart_inhibitory_stability_index", "control_speed_index"),
        ("sart_inhibitory_stability_index", "conflict_resilience_index"),
    ]
    associations = decompose_associations(complete, pairs)
    icc = one_way_icc(
        complete,
        [
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
            "task_active_efficacy",
            "control_accuracy_index",
            "control_speed_index",
            "conflict_resilience_index",
        ],
    )
    prediction = grouped_control_prediction(complete, seed=args.seed)
    profile_prediction = grouped_profile_prediction(complete, seed=args.seed)
    overloaded = overloaded_engagement_check(
        complete,
        profiles,
        seed=args.seed,
    )
    input_hash = _sha256(args.input)

    inventory = (
        complete.groupby("session_type")
        .agg(
            n_sessions=("session_id", "size"),
            n_participants=("participant_id", "nunique"),
            complete_stroop=("stroop_accuracy", "count"),
            complete_flanker=("flanker_accuracy", "count"),
            complete_sart_engagement=("sart_engagement_index", "count"),
        )
        .reset_index()
    )
    write_table(complete, args.features)
    write_table(
        inventory,
        args.output_dir / "paired_vigilance_inventory.csv",
    )
    write_table(
        loadings,
        args.output_dir / "paired_vigilance_factor_loadings.csv",
    )
    write_table(
        mixture_result.comparison,
        args.output_dir / "paired_control_mixture_comparison.csv",
    )
    write_table(
        profiles,
        args.output_dir / "paired_control_cluster_profiles.csv",
    )
    write_table(
        associations,
        args.output_dir / "paired_vigilance_associations.csv",
    )
    write_table(
        icc,
        args.output_dir / "paired_vigilance_icc.csv",
    )
    write_table(
        prediction,
        args.output_dir / "paired_vigilance_prediction.csv",
    )
    write_table(
        profile_prediction,
        args.output_dir / "paired_vigilance_profile_prediction.csv",
    )
    write_table(
        overloaded,
        args.output_dir / "paired_overloaded_engagement_check.csv",
    )
    _plot_dimensions(
        complete,
        args.figure_dir / "paired_vigilance_dimensions.png",
    )
    overloaded_figure = _plot_overloaded(
        complete,
        profiles,
        args.figure_dir / "paired_overloaded_engagement.png",
    )
    report = _render_report(
        complete,
        loadings,
        mixture_result.comparison,
        mixture_result.selected_model_id,
        profiles,
        associations,
        icc,
        prediction,
        profile_prediction,
        overloaded,
        input_hash,
    )
    write_text(report, args.report)

    metrics: dict[str, Any] = {
        "input": _portable_path(args.input),
        "input_sha256": input_hash,
        "n_sessions": len(complete),
        "n_participants": complete["participant_id"].nunique(),
        "selected_control_model": mixture_result.selected_model_id,
        "figures": {
            "dimensions": _portable_path(
                args.figure_dir / "paired_vigilance_dimensions.png"
            ),
            "overloaded": (
                _portable_path(
                    args.figure_dir / "paired_overloaded_engagement.png"
                )
                if overloaded_figure
                else None
            ),
        },
        "outputs": {
            "features": _portable_path(args.features),
            "report": _portable_path(args.report),
            "tables": _portable_path(args.output_dir),
        },
    }
    write_json(metrics, args.metrics)
    update_run_manifest(
        args.manifest,
        ROOT,
        "paired_vigilance_followup",
        {
            "input": _portable_path(args.input),
            "input_sha256": input_hash,
            "seed": args.seed,
            "bootstrap_repetitions": args.bootstrap_repetitions,
            "selected_control_model": mixture_result.selected_model_id,
            "n_sessions": len(complete),
            "n_participants": complete["participant_id"].nunique(),
        },
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
