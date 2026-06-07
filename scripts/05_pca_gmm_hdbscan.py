#!/usr/bin/env python3
"""Run gated task-specific models, then eligible pooled sensitivity models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.audit import median_impute_selected
from flowzone_validation.clustering import fit_exploratory_models
from flowzone_validation.confounds import grouped_confound_test
from flowzone_validation.config import load_config
from flowzone_validation.reporting import (
    plot_model_diagnostics,
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)
from flowzone_validation.residualisation import robust_scale_within_sources
from flowzone_validation.zone_alignment import align_clusters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data/processed/cognitive_windows.parquet",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=ROOT / "reports/acdc_data_audit.json",
    )
    parser.add_argument(
        "--assignments-output",
        type=Path,
        default=ROOT / "data/processed/cluster_assignments.parquet",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=ROOT / "reports/exploratory_cluster_metrics.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/exploratory_clusters.md",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=ROOT / "reports/figures",
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


def _model_one(
    frame: pd.DataFrame,
    features: list[str],
    analysis_name: str,
    config: Any,
    figures: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    print(f"{analysis_name}: minimal feature imputation", flush=True)
    imputed, imputation_rates = median_impute_selected(frame, features)
    print(f"{analysis_name}: dataset confound test before adjustment", flush=True)
    confound_before = grouped_confound_test(
        imputed,
        features,
        "dataset_id",
        permutations=config.confound_permutations,
        seed=config.random_seed,
    )
    adjusted = robust_scale_within_sources(
        imputed,
        features,
        source_columns=("dataset_id", "task_family"),
    )
    adjusted_features = [f"{feature}__source_adjusted" for feature in features]
    print(f"{analysis_name}: dataset confound test after adjustment", flush=True)
    confound_after = grouped_confound_test(
        adjusted,
        adjusted_features,
        "dataset_id",
        permutations=config.confound_permutations,
        seed=config.random_seed,
    )
    print(f"{analysis_name}: PCA, GMM, HDBSCAN, and stability", flush=True)
    result = fit_exploratory_models(
        adjusted,
        adjusted_features,
        analysis_name=analysis_name,
        k_min=config.gmm_k_min,
        k_max=config.gmm_k_max,
        n_init=config.gmm_initializations,
        bootstrap_repetitions=config.bootstrap_repetitions,
        seed=config.random_seed,
    )
    print(f"{analysis_name}: neutral prototype alignment", flush=True)
    alignment = align_clusters(
        result.assignments,
        result.standardized_features,
        bootstraps=config.zone_alignment_bootstraps,
        seed=config.random_seed,
    )
    figure_paths = plot_model_diagnostics(
        result.assignments,
        result.metrics,
        figures,
    )
    metrics = {
        **result.metrics,
        "model_feature_space": "robust-scaled within dataset and task",
        "imputation_fraction": imputation_rates,
        "dataset_confound_before_source_adjustment": confound_before,
        "dataset_confound_after_source_adjustment": confound_after,
        "zone_alignment": alignment,
        "figures": figure_paths,
    }
    return result.assignments, metrics


def _render_report(
    audit: dict[str, Any],
    analyses: dict[str, Any],
    skipped: dict[str, list[str]],
) -> str:
    lines = [
        "# Exploratory ACDC Cluster Profiles",
        "",
        "> Cluster identifiers are neutral. Similarity to zone prototypes is "
        "post hoc and is not direct validation of MFT-M, CCC, or brain states.",
        "",
    ]
    for task, reasons in skipped.items():
        lines.extend(
            [
                f"## {task}: modelling skipped",
                "",
                "- " + "; ".join(reasons),
                "",
            ]
        )
    for name, metrics in analyses.items():
        best = metrics["best_gmm"]
        lines.extend(
            [
                f"## {name}",
                "",
                f"- Windows: {metrics['rows']:,}",
                f"- Participants: {metrics['participants']:,}",
                f"- Datasets: {metrics['datasets']:,}",
                f"- Model feature space: `{metrics['model_feature_space']}`",
                f"- Selected GMM: `{best['covariance']}`, `k={best['k']}` by BIC "
                "among component-size-valid solutions",
                f"- Median grouped bootstrap ARI: "
                f"{metrics['gmm_bootstrap_ari_median']}",
                f"- HDBSCAN status: `{metrics['hdbscan']['status']}`",
                "",
                "### Neutral cluster alignment",
                "",
                "| Cluster | Closest prototype | Similarity | 95% CI | Lead | Strong alignment |",
                "|---|---|---:|---:|---:|---|",
            ]
        )
        for row in metrics["zone_alignment"]:
            lines.append(
                f"| {row['cluster_id']} | {row['closest_prototype']} | "
                f"{row['similarity']:.3f} | "
                f"{row['similarity_ci_lower']:.3f} to "
                f"{row['similarity_ci_upper']:.3f} | "
                f"{row['lead_over_next']:.3f} | "
                f"{'yes' if row['strong_alignment'] else 'no'} |"
            )
        after = metrics["dataset_confound_after_source_adjustment"]
        before = metrics.get("dataset_confound_before_source_adjustment")
        if before and before.get("status") == "ok":
            lines.extend(
                [
                    "",
                    "- Dataset confounding before source adjustment: "
                    f"`{'substantial' if before['substantial_confounding'] else 'not substantial'}` "
                    f"(normalized improvement={before['normalized_improvement_over_chance']:.3f}, "
                    f"permutation p={before['permutation_p_value']:.4f}).",
                ]
            )
        if after.get("status") == "ok":
            lines.extend(
                [
                    "",
                    "- Dataset confounding after source adjustment: "
                    f"`{'substantial' if after['substantial_confounding'] else 'not substantial'}` "
                    f"(normalized improvement={after['normalized_improvement_over_chance']:.3f}, "
                    f"permutation p={after['permutation_p_value']:.4f}).",
                ]
            )
        task_before = metrics.get("task_confound_before_source_adjustment")
        task_after = metrics.get("task_confound_after_source_adjustment")
        if task_before and task_before.get("status") == "ok":
            lines.extend(
                [
                    "- Task confounding before source adjustment: "
                    f"`{'substantial' if task_before['substantial_confounding'] else 'not substantial'}` "
                    f"(normalized improvement={task_before['normalized_improvement_over_chance']:.3f}, "
                    f"permutation p={task_before['permutation_p_value']:.4f}).",
                ]
            )
        if task_after and task_after.get("status") == "ok":
            lines.extend(
                [
                    "- Task confounding after source adjustment: "
                    f"`{'substantial' if task_after['substantial_confounding'] else 'not substantial'}` "
                    f"(normalized improvement={task_after['normalized_improvement_over_chance']:.3f}, "
                    f"permutation p={task_after['permutation_p_value']:.4f}).",
                ]
            )
        lines.append("")
    if not analyses:
        lines.extend(
            [
                "No task passed all modelling gates. This is a valid negative "
                "pipeline outcome; no exploratory model was forced.",
                "",
            ]
        )
    lines.extend(
        [
            "## Scientific boundary",
            "",
            "A one- or two-component solution, unstable components, source-dominated "
            "clusters, or a continuous geometry is informative evidence against a "
            "four-discrete-zone interpretation in ACDC.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    windows = pd.read_parquet(args.input)
    primary = windows[
        windows["window_size"].eq(config.primary_window_size)
        & windows["window_kind"].eq("full")
        & windows["dynamics_eligible"].eq(True)
    ].copy()

    analyses: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    assignments: list[pd.DataFrame] = []
    skipped: dict[str, list[str]] = {}
    eligible_tasks: list[str] = []
    for task, gate in audit["task_gates"].items():
        if not gate["eligible"]:
            skipped[task] = gate["gate_reasons"]
            print(f"{task}: skipped by audit gate", flush=True)
            continue
        eligible_tasks.append(task)
        task_frame = primary[primary["task_family"].eq(task)].reset_index(drop=True)
        task_assignments, metrics = _model_one(
            task_frame,
            gate["selected_features"],
            task,
            config,
            args.figures,
        )
        task_assignments["analysis"] = task
        assignments.append(task_assignments)
        analyses[task] = metrics

    if len(eligible_tasks) >= 2:
        print("Pooled: evaluating common feature set and confounds", flush=True)
        common_features = sorted(
            set.intersection(
                *[
                    set(audit["task_gates"][task]["selected_features"])
                    for task in eligible_tasks
                ]
            )
        )
        if len(common_features) >= config.minimum_clustering_features:
            pooled = primary[
                primary["task_family"].isin(eligible_tasks)
            ].reset_index(drop=True)
            pooled, rates = median_impute_selected(pooled, common_features)
            print("Pooled: dataset confound test before adjustment", flush=True)
            dataset_confound_before = grouped_confound_test(
                pooled,
                common_features,
                "dataset_id",
                permutations=config.confound_permutations,
                seed=config.random_seed,
            )
            print("Pooled: task confound test before adjustment", flush=True)
            task_confound_before = grouped_confound_test(
                pooled,
                common_features,
                "task_family",
                permutations=config.confound_permutations,
                seed=config.random_seed,
            )
            adjusted = robust_scale_within_sources(
                pooled,
                common_features,
                source_columns=("dataset_id", "task_family"),
            )
            adjusted_features = [
                f"{feature}__source_adjusted" for feature in common_features
            ]
            print("Pooled: dataset confound test after adjustment", flush=True)
            dataset_confound = grouped_confound_test(
                adjusted,
                adjusted_features,
                "dataset_id",
                permutations=config.confound_permutations,
                seed=config.random_seed,
            )
            print("Pooled: task confound test after adjustment", flush=True)
            task_confound = grouped_confound_test(
                adjusted,
                adjusted_features,
                "task_family",
                permutations=config.confound_permutations,
                seed=config.random_seed,
            )
            substantial = any(
                result.get("substantial_confounding", False)
                for result in (dataset_confound, task_confound)
            )
            if substantial:
                print(
                    "Pooled: skipped because substantial confounding remains",
                    flush=True,
                )
                skipped["Pooled"] = [
                    "substantial dataset/task confounding remained after source adjustment"
                ]
                diagnostics["Pooled confound check"] = {
                    "imputation_fraction": rates,
                    "dataset_confound_before": dataset_confound_before,
                    "task_confound_before": task_confound_before,
                    "dataset_confound": dataset_confound,
                    "task_confound": task_confound,
                }
            else:
                print(
                    "Pooled: PCA, GMM, HDBSCAN, and stability",
                    flush=True,
                )
                pooled_result = fit_exploratory_models(
                    adjusted,
                    adjusted_features,
                    analysis_name="Pooled",
                    k_min=config.gmm_k_min,
                    k_max=config.gmm_k_max,
                    n_init=config.gmm_initializations,
                    bootstrap_repetitions=config.bootstrap_repetitions,
                    seed=config.random_seed,
                )
                pooled_assignments = pooled_result.assignments
                pooled_assignments["analysis"] = "Pooled"
                assignments.append(pooled_assignments)
                print("Pooled: neutral prototype alignment", flush=True)
                alignment = align_clusters(
                    pooled_result.assignments,
                    pooled_result.standardized_features,
                    bootstraps=config.zone_alignment_bootstraps,
                    seed=config.random_seed,
                )
                pooled_metrics = {
                    **pooled_result.metrics,
                    "model_feature_space": (
                        "robust-scaled within dataset and task"
                    ),
                    "imputation_fraction": rates,
                    "dataset_confound_before_source_adjustment": (
                        dataset_confound_before
                    ),
                    "task_confound_before_source_adjustment": (
                        task_confound_before
                    ),
                    "dataset_confound_after_source_adjustment": dataset_confound,
                    "task_confound_after_source_adjustment": task_confound,
                    "zone_alignment": alignment,
                    "figures": plot_model_diagnostics(
                        pooled_result.assignments,
                        pooled_result.metrics,
                        args.figures,
                    ),
                }
                analyses["Pooled"] = pooled_metrics
        else:
            skipped["Pooled"] = [
                f"only {len(common_features)} common eligible features"
            ]

    if assignments:
        write_table(pd.concat(assignments, ignore_index=True), args.assignments_output)
    write_json(
        {
            "analyses": analyses,
            "diagnostics": diagnostics,
            "skipped": skipped,
        },
        args.metrics_output,
    )
    write_text(_render_report(audit, analyses, skipped), args.report)
    update_run_manifest(
        args.manifest,
        ROOT,
        "exploratory_models",
        {
            "input": str(args.input),
            "analyses_run": list(analyses),
            "analyses_skipped": skipped,
            "assignments_output": (
                str(args.assignments_output) if assignments else None
            ),
            "metrics_output": str(args.metrics_output),
            "report": str(args.report),
        },
    )
    print(f"Wrote exploratory report to {args.report}")


if __name__ == "__main__":
    main()
