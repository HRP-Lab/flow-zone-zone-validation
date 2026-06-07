#!/usr/bin/env python3
"""Run the post-modelling ACDC Zhang-Tang follow-up analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.config import load_zhang_tang_config
from flowzone_validation.prediction import compare_prediction_models
from flowzone_validation.reporting import (
    update_run_manifest,
    write_table,
    write_text,
)
from flowzone_validation.zhang_tang import (
    MI_FEATURES,
    NEXT_OUTCOMES,
    TAIL_FEATURES,
    UPDATE_FEATURES,
    build_cluster_profiles,
    build_feature_audit,
    build_large_update_usefulness,
    build_zhang_tang_windows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trials",
        type=Path,
        default=ROOT / "data/processed/acdc_cleaned_trials.parquet",
    )
    parser.add_argument(
        "--full-extract",
        type=Path,
        default=ROOT / "data/interim/acdc_trial_extract.parquet",
    )
    parser.add_argument(
        "--windows",
        type=Path,
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument(
        "--assignments",
        type=Path,
        default=ROOT / "data/processed/cluster_assignments.parquet",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=ROOT / "reports/acdc_data_audit.md",
    )
    parser.add_argument(
        "--clusters-report",
        type=Path,
        default=ROOT / "reports/exploratory_clusters.md",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "reports/run_manifest.json",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/zhang_tang.json",
    )
    parser.add_argument(
        "--enriched-output",
        type=Path,
        default=ROOT / "data/processed/acdc_zhang_tang_windows.parquet",
    )
    parser.add_argument(
        "--reuse-enriched",
        action="store_true",
        help="Reuse an existing enriched-window checkpoint.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/zhang_tang_followup.md",
    )
    parser.add_argument(
        "--tables",
        type=Path,
        default=ROOT / "reports/tables",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=ROOT / "reports/figures",
    )
    return parser.parse_args()


def _preflight(args: argparse.Namespace) -> dict[str, Any]:
    required = {
        "full trial extract": args.full_extract,
        "cleaned residualised trials": args.trials,
        "cognitive windows": args.windows,
        "cluster assignments": args.assignments,
        "data audit": args.audit,
        "exploratory cluster report": args.clusters_report,
        "run manifest": args.manifest,
        "follow-up config": args.config,
    }
    missing = [
        f"{label}: {path}" for label, path in required.items() if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Required follow-up inputs are missing:\n- " + "\n- ".join(missing)
        )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    stages = manifest.get("stages", {})
    if "build_cognitive_windows" not in stages or "exploratory_models" not in stages:
        raise ValueError(
            "Run manifest does not document cognitive windows and clustering"
        )
    return {
        label: {
            "path": str(path),
            "size_bytes": int(path.stat().st_size),
        }
        for label, path in required.items()
    }


def _check_structural_availability(windows: pd.DataFrame) -> dict[str, Any]:
    selected = [
        *MI_FEATURES,
        *UPDATE_FEATURES,
        *TAIL_FEATURES,
        "large_update_window",
    ]
    structurally_unavailable: list[str] = []
    for feature in selected:
        if feature not in windows or windows[feature].notna().sum() == 0:
            reason_column = f"missing_reason_{feature}"
            reasons = (
                windows[reason_column].dropna().astype(str).unique().tolist()
                if reason_column in windows
                else []
            )
            if any("unavailable" in reason for reason in reasons):
                structurally_unavailable.append(feature)
    fraction = len(structurally_unavailable) / len(selected)
    if fraction > 0.20:
        raise ValueError(
            "More than 20% of selected Zhang-Tang features are structurally "
            f"unavailable: {structurally_unavailable}"
        )
    return {
        "selected_feature_count": len(selected),
        "structurally_unavailable": structurally_unavailable,
        "structurally_unavailable_fraction": fraction,
    }


def _task_availability(
    windows: pd.DataFrame,
    minimum_next_windows: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    computable_mi = [
        "mi_congruency_correct",
        "mi_prev_error_next_correct",
        "mi_condition_efficiency_bin_sens",
    ]
    for task, group in windows.groupby("task_family", observed=True, sort=True):
        mi_rates = {
            feature: float(group[feature].notna().mean())
            for feature in computable_mi
        }
        next_count = int(group["has_next_window"].sum())
        reasons: list[str] = []
        if max(mi_rates.values()) < 0.50:
            reasons.append("all computable MI features below 50% availability")
        if next_count < minimum_next_windows:
            reasons.append(
                f"{next_count} safe next windows < {minimum_next_windows}"
            )
        rows.append(
            {
                "task_family": task,
                "n_windows": int(len(group)),
                "n_subjects": int(group["participant_id"].nunique()),
                "safe_next_windows": next_count,
                **{
                    f"availability_{feature}": value
                    for feature, value in mi_rates.items()
                },
                "followup_available": not reasons,
                "unavailable_reasons": "; ".join(reasons),
            }
        )
    return pd.DataFrame(rows)


def _check_cluster_composition(
    profiles: pd.DataFrame,
    threshold: float,
) -> None:
    task_specific = profiles[profiles["analysis"].ne("Pooled")]
    pooled = profiles[profiles["analysis"].eq("Pooled")]
    dominated = task_specific[
        task_specific["max_dataset_share"].ge(threshold)
    ]["gmm_cluster_id"].tolist()
    dominated.extend(
        pooled[
            pooled["max_dataset_share"].ge(threshold)
            | pooled["max_task_share"].ge(threshold)
        ]["gmm_cluster_id"].tolist()
    )
    if dominated:
        raise ValueError(
            "Cluster profiles are source dominated at the registered threshold: "
            + ", ".join(dominated)
        )


def _prediction_features() -> dict[str, list[str]]:
    baseline = [
        "accuracy",
        "throughput_proxy",
        "rt_cv",
        "control_cost_rt_ms",
        "error_burstiness",
        "median_rt_ms",
        "nonresponse_rate",
    ]
    original_dynamics = [
        "cog_alpha1",
        "cog_lag1",
        "cog_lag2",
        "cog_roughness",
        "cog_sign_change",
        "cog_sd1_sd2",
        "cog_perm_entropy3",
        "cog_diff_entropy",
        "rt_volatility",
        "rt_drift",
    ]
    zhang_tang = [
        "mi_congruency_correct",
        "mi_prev_error_next_correct",
        "mi_condition_efficiency_bin_sens",
        "delta_throughput",
        "delta_accuracy",
        "delta_rt_cv",
        "delta_interference_rt_cost",
        "combined_update_magnitude",
        "upper_tail_rate_abs_rt_resid_z",
        "upper_tail_rate_abs_delta_u_z",
        "large_update_window",
    ]
    return {
        "Model A": baseline,
        "Model B": [*baseline, *original_dynamics],
        "Model C": [*baseline, *zhang_tang],
        "Model D": [*baseline, *original_dynamics, *zhang_tang],
        "Model E": [*baseline, *original_dynamics, *zhang_tang],
    }


def _plot_cluster_heatmap(
    profiles: pd.DataFrame,
    path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    columns = {
        "mean_task_relevant_mi": "Task MI",
        "mean_combined_update_magnitude": "Update magnitude",
        "mean_upper_tail_residual_rate": "Residual tail",
        "mean_upper_tail_delta_u_rate": "Delta-u tail",
        "large_update_window_proportion": "Large-update rate",
        "mean_next_accuracy": "Next accuracy",
        "mean_next_throughput": "Next throughput",
        "mean_next_rt_cv": "Next RT CV",
        "mean_next_interference_rt_cost": "Next cost",
        "mean_next_error_burstiness": "Next burstiness",
    }
    values = profiles[list(columns)].apply(pd.to_numeric, errors="coerce")
    standardized = (values - values.mean()) / values.std(ddof=0).replace(0, np.nan)
    standardized.index = (
        profiles["analysis"].astype(str)
        + " | "
        + profiles["gmm_cluster_id"].astype(str)
    )
    standardized = standardized.rename(columns=columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure_height = max(7, 0.36 * len(standardized))
    figure, axis = plt.subplots(figsize=(12, figure_height))
    sns.heatmap(
        standardized,
        cmap="vlag",
        center=0,
        robust=True,
        linewidths=0.25,
        ax=axis,
        cbar_kws={"label": "Across-cluster z-score"},
    )
    axis.set_title("Neutral cluster profiles on Zhang-Tang follow-up features")
    axis.set_xlabel("")
    axis.set_ylabel("")
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_large_update_effects(
    usefulness: pd.DataFrame,
    path: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    usable = usefulness[
        usefulness["standardized_useful_direction_effect"].notna()
    ].copy()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(11, 5))
    if usable.empty:
        axis.text(
            0.5,
            0.5,
            "No dataset-task contrast met minimum support.",
            ha="center",
            va="center",
        )
        axis.set_axis_off()
    else:
        summary = (
            usable.groupby(["task_family", "outcome"], observed=True)[
                "standardized_useful_direction_effect"
            ]
            .mean()
            .reset_index()
        )
        sns.barplot(
            data=summary,
            x="outcome",
            y="standardized_useful_direction_effect",
            hue="task_family",
            ax=axis,
        )
        axis.axhline(0, color="black", linewidth=1)
        axis.set_ylabel("Standardized effect in useful direction")
        axis.set_xlabel("")
        axis.tick_params(axis="x", rotation=25)
        axis.set_title("Large updates and subsequent window changes")
        axis.legend(title="Task")
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _render_report(
    inputs: dict[str, Any],
    structural: dict[str, Any],
    task_availability: pd.DataFrame,
    feature_audit: pd.DataFrame,
    profiles: pd.DataFrame,
    usefulness: pd.DataFrame,
    predictions: pd.DataFrame,
) -> str:
    lines = [
        "# Zhang-Tang Follow-Up Analysis",
        "",
        "## 1. Purpose",
        "",
        "This compact post-modelling analysis tests whether the existing neutral "
        "ACDC profiles differ in task-relevant mutual information, update "
        "magnitude, tail/spike structure, large-update usefulness, and safe "
        "next-window outcomes.",
        "",
        "## 2. Inputs checked",
        "",
    ]
    for label, details in inputs.items():
        lines.append(
            f"- {label}: `{details['path']}` "
            f"({details['size_bytes']:,} bytes)"
        )
    lines.extend(
        [
            "",
            "The requested canonical filenames were reconciled against the "
            "existing run manifest. Existing cleaned trials, cognitive windows, "
            "and neutral assignments were reused; the original pipeline was not "
            "rebuilt.",
            "",
            "## 3. Zhang-Tang feature availability",
            "",
            f"- Structurally unavailable selected features: "
            f"{', '.join(structural['structurally_unavailable']) or 'none'}",
            "- Structural-unavailability fraction: "
            f"{structural['structurally_unavailable_fraction']:.3f}",
            "- `mi_congruency_response` is unavailable because the ACDC extract "
            "does not contain response-choice identity.",
            "",
            "| Task | Windows | Subjects | Safe next windows | Congruency MI | "
            "Previous-error MI | Condition-efficiency MI | Available |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in task_availability.itertuples(index=False):
        lines.append(
            f"| {row.task_family} | {row.n_windows} | {row.n_subjects} | "
            f"{row.safe_next_windows} | "
            f"{row.availability_mi_congruency_correct:.3f} | "
            f"{row.availability_mi_prev_error_next_correct:.3f} | "
            f"{row.availability_mi_condition_efficiency_bin_sens:.3f} | "
            f"{'yes' if row.followup_available else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"The dataset-task audit contains {len(feature_audit):,} source rows. "
            "Missingness reasons are retained in the audit table; structurally "
            "unavailable features were not imputed.",
            "",
            "## 4. Cluster profiles on MI/update/tail features",
            "",
            f"- Neutral cluster profiles: {len(profiles):,}",
            f"- Profiles with sufficient data: "
            f"{int(profiles['provisional_pattern_note'].ne('insufficient_data').sum()):,}",
            "- Cluster identifiers were retained unchanged.",
            "",
            "| Analysis | Cluster | Windows | Subjects | Pattern note |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in profiles.itertuples(index=False):
        lines.append(
            f"| {row.analysis} | `{row.gmm_cluster_id}` | {row.n_windows} | "
            f"{row.n_subjects} | `{row.provisional_pattern_note}` |"
        )
    interpretation_counts = (
        usefulness["interpretation"].value_counts().to_dict()
        if not usefulness.empty
        else {}
    )
    lines.extend(
        [
            "",
            "## 5. Large-update usefulness",
            "",
            "Large updates are interpreted only where a safe next window exists. "
            "Effects compare next-minus-current changes after large versus "
            "ordinary updates within dataset and task.",
            "",
            "- " + "; ".join(
                f"{key}: {value}"
                for key, value in sorted(interpretation_counts.items())
            ),
            "",
            "## 6. Next-window prediction comparison",
            "",
            "All folds are grouped by dataset-scoped participant ID. Models use "
            "ridge regression with fold-local imputation, robust scaling, and "
            "source categorical controls. Model E is a transductive sensitivity "
            "analysis because neutral clusters were discovered on the complete "
            "pilot sample.",
            "",
            "| Target | Best model | CV R2 | Model C vs A | Model D vs B |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for target, group in predictions[predictions["status"].eq("ok")].groupby(
        "target",
        observed=True,
        sort=True,
    ):
        best = group.loc[group["r2"].idxmax()]
        model_c = group[group["model"].eq("Model C")]
        model_d = group[group["model"].eq("Model D")]
        lines.append(
            f"| {target} | {best['model']} | {best['r2']:.3f} | "
            f"{model_c['delta_r2_vs_model_a'].iloc[0]:.3f} | "
            f"{model_d['delta_r2_vs_model_b'].iloc[0]:.3f} |"
        )
    lines.extend(
        [
            "",
            "The Zhang-Tang block is considered predictively useful only where "
            "Model C improves on Model A or Model D improves on Model B. Negative "
            "or negligible increments are retained as evidence against added "
            "predictive value.",
            "",
            "## 7. Provisional interpretation",
            "",
            "IN_ZONE-like profiles should not be defined by low variability alone. "
            "The predicted adaptive pattern is strong throughput and accuracy, "
            "low lapses and burstiness, moderate structured variability, "
            "preserved task-relevant mutual information, and evidence that "
            "occasional larger deviations are followed by recovery or improved "
            "control.",
            "",
            "The descriptive mapping used here is:",
            "",
            "- `in_zone_like`: moderate structured entropy/variability, high "
            "task-relevant MI, and occasional useful update spikes.",
            "- `flat_like`: low throughput, weak MI, and low update magnitude.",
            "- `locked_in_like`: low entropy, high persistence/interference cost, "
            "and suppressed useful updating.",
            "- `spun_out_like`: high volatility/entropy, weak MI, and large "
            "updates that do not stabilise later performance.",
            "- `mixed_or_unclear` and `insufficient_data` retain uncertainty.",
            "",
            "These notes are descriptive and do not rename any neutral cluster.",
            "",
            "## 8. Limitations",
            "",
            "- ACDC is a conflict-control analogue based on a deterministic "
            "development subset, not direct MFT-M or CCC validation.",
            "- Response-choice MI is structurally unavailable.",
            "- Only consecutive full 80-trial windows within the same participant, "
            "dataset, task, and block support next-window inference.",
            "- MI estimates are bias-corrected but remain noisy in high-accuracy "
            "windows with sparse errors or invariant conditions.",
            "- Cluster-based prediction is transductive and is not production "
            "classifier evidence.",
            "",
            "## 9. Claim-safe conclusion",
            "",
            "This follow-up tests whether ACDC conflict-control profiles differ in "
            "task-relevant mutual information, update magnitude and tail/spike "
            "structure. The results may support, weaken or refine the Trident-G "
            "four-zone behavioural geometry. They do not validate discrete brain "
            "states and should not be treated as production classifier evidence.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    config = load_zhang_tang_config(args.config)
    inputs = _preflight(args)

    print("Loading existing cleaned trials and window outputs", flush=True)
    cleaned = pd.read_parquet(args.trials)
    windows = pd.read_parquet(args.windows)
    assignments = pd.read_parquet(args.assignments)

    if args.reuse_enriched:
        if not args.enriched_output.exists():
            raise FileNotFoundError(
                f"Enriched-window checkpoint is missing: {args.enriched_output}"
            )
        print(
            f"Reusing enriched windows from {args.enriched_output}",
            flush=True,
        )
        enriched = pd.read_parquet(args.enriched_output)
    else:
        enriched = build_zhang_tang_windows(cleaned, windows, config)
        write_table(enriched, args.enriched_output)
        print(
            f"Checkpointed {len(enriched):,} enriched windows to "
            f"{args.enriched_output}",
            flush=True,
        )
    if not enriched["has_next_window"].any():
        raise ValueError("Next-window outcomes cannot be constructed safely")
    structural = _check_structural_availability(enriched)
    task_availability = _task_availability(
        enriched,
        config.minimum_task_next_windows,
    )
    if not task_availability["followup_available"].any():
        raise ValueError("Zhang-Tang features are too sparse for every task")

    feature_audit = build_feature_audit(enriched)
    profiles = build_cluster_profiles(enriched, assignments, config)
    _check_cluster_composition(profiles, config.source_dominance_threshold)
    usefulness = build_large_update_usefulness(enriched, config)

    pooled_assignments = assignments[
        assignments["analysis"].eq("Pooled")
    ][["window_id", "gmm_cluster_id"]].rename(
        columns={"gmm_cluster_id": "pooled_gmm_cluster_id"}
    )
    if pooled_assignments.duplicated("window_id").any():
        raise ValueError("Pooled cluster assignments are not unique by window")
    prediction_frame = enriched.merge(
        pooled_assignments,
        on="window_id",
        how="left",
        validate="one_to_one",
    )
    if prediction_frame["pooled_gmm_cluster_id"].isna().any():
        raise ValueError("Pooled neutral cluster assignments are incomplete")
    predictions = compare_prediction_models(
        prediction_frame,
        _prediction_features(),
        list(NEXT_OUTCOMES),
        source_categoricals=["dataset_id", "task_family"],
        cluster_column="pooled_gmm_cluster_id",
        folds=config.prediction_folds,
        alpha=config.ridge_alpha,
    )
    successful = predictions[predictions["status"].eq("ok")]
    if successful.empty:
        raise ValueError("Next-window predictive comparisons were not testable")
    if successful["maximum_participant_group_overlap"].fillna(0).gt(0).any():
        raise AssertionError("Participant leakage detected in prediction folds")

    args.tables.mkdir(parents=True, exist_ok=True)
    args.figures.mkdir(parents=True, exist_ok=True)
    write_table(
        feature_audit,
        args.tables / "zhang_tang_feature_audit.csv",
    )
    write_table(
        profiles,
        args.tables / "zhang_tang_cluster_profiles.csv",
    )
    write_table(
        usefulness,
        args.tables / "large_update_usefulness.csv",
    )
    write_table(
        predictions,
        args.tables / "next_window_prediction_comparison.csv",
    )
    _plot_cluster_heatmap(
        profiles,
        args.figures / "zhang_tang_cluster_heatmap.png",
    )
    _plot_large_update_effects(
        usefulness,
        args.figures / "large_update_next_window_effects.png",
    )
    write_text(
        _render_report(
            inputs,
            structural,
            task_availability,
            feature_audit,
            profiles,
            usefulness,
            predictions,
        ),
        args.report,
    )
    update_run_manifest(
        args.manifest,
        ROOT,
        "zhang_tang_followup",
        {
            "cleaned_trials": str(args.trials),
            "cognitive_windows": str(args.windows),
            "cluster_assignments": str(args.assignments),
            "enriched_windows": str(args.enriched_output),
            "primary_windows": int(len(enriched)),
            "safe_next_windows": int(enriched["has_next_window"].sum()),
            "structurally_unavailable_features": structural[
                "structurally_unavailable"
            ],
            "available_tasks": task_availability.loc[
                task_availability["followup_available"],
                "task_family",
            ].tolist(),
            "report": str(args.report),
        },
    )
    print(f"Wrote Zhang-Tang follow-up report to {args.report}")


if __name__ == "__main__":
    main()
