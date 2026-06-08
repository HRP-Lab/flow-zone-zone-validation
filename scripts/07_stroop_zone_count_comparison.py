#!/usr/bin/env python3
"""Compare two-, three-, and four-profile Stroop solutions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)
from flowzone_validation.stroop_zone_count import (
    compare_continuous_and_mixture_models,
    compare_stroop_zone_counts,
    summarize_density_comparison,
)
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
        "--zhang-tang-input",
        type=Path,
        default=ROOT / "data/processed/acdc_zhang_tang_windows.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports/tables",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "reports/stroop_zone_count_comparison.md",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=ROOT / "reports/stroop_zone_count_metrics.json",
    )
    parser.add_argument(
        "--assignments",
        type=Path,
        default=ROOT / "data/processed/stroop_zone_count_assignments.parquet",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=ROOT / "reports/figures/stroop_zone_count_comparison.png",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "reports/run_manifest.json",
    )
    parser.add_argument("--bootstrap-repetitions", type=int, default=50)
    parser.add_argument("--density-repetitions", type=int, default=20)
    parser.add_argument("--alignment-bootstraps", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _plot(
    models: pd.DataFrame,
    density: pd.DataFrame,
    output: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = models[models["valid"].fillna(False)].copy()
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for covariance, group in valid.groupby("covariance"):
        axes[0].plot(group["k"], group["bic"], marker="o", label=covariance)
        axes[1].plot(
            group["k"],
            group["bootstrap_ari_median"],
            marker="o",
            label=covariance,
        )
    axes[0].set(title="In-sample BIC", xlabel="GMM components", ylabel="BIC")
    axes[1].set(
        title="Participant-bootstrap stability",
        xlabel="GMM components",
        ylabel="Median ARI",
        ylim=(-0.05, 1.05),
    )
    axes[0].legend()
    axes[1].legend()

    ordered = density.sort_values("mean_test_log_likelihood", ascending=True)
    colors = [
        "#4472C4" if family == "continuous_factor" else "#C55A11"
        for family in ordered["model_family"]
    ]
    axes[2].barh(
        ordered["model_id"],
        ordered["mean_test_log_likelihood"],
        xerr=ordered["sd_test_log_likelihood"],
        color=colors,
        alpha=0.85,
    )
    axes[2].set(
        title="Participant-grouped held-out density",
        xlabel="Mean test log likelihood",
    )
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _render_report(
    stroop: pd.DataFrame,
    models: pd.DataFrame,
    holdout: pd.DataFrame,
    density: pd.DataFrame,
    alignment: pd.DataFrame,
    profiles: pd.DataFrame,
    pca_metrics: dict[str, Any],
) -> str:
    valid = models[models["valid"].fillna(False)].copy()
    bic_best = valid.loc[valid["bic"].idxmin()]
    stable_best = valid.loc[valid["bootstrap_ari_median"].idxmax()]
    best_factor = density[density["model_family"].eq("continuous_factor")].iloc[0]
    eligible_mixtures = density[
        density["model_family"].eq("discrete_mixture")
        & density["valid_component_split_fraction"].ge(0.80)
    ]
    best_mixture = eligible_mixtures.iloc[0]
    likelihood_delta = (
        best_mixture["mean_test_log_likelihood"]
        - best_factor["mean_test_log_likelihood"]
    )
    lines = [
        "# Stroop Zone-Count Comparison",
        "",
        "> This is a focused exploratory comparison of neutral behavioural "
        "profiles. It does not validate named zones or discrete brain states.",
        "",
        "## Analysis set",
        "",
        f"- Primary 80-trial Stroop windows: {len(stroop):,}",
        f"- Dataset-scoped participants: {stroop['participant_id'].nunique():,}",
        f"- Datasets: {stroop['dataset_id'].nunique():,}",
        f"- Selected features: {len(pca_metrics['loadings']['pc1']):,}",
        f"- PCA components: {pca_metrics['components']} "
        f"({pca_metrics['cumulative_explained_variance']:.1%} variance under "
        "the six-component cap)",
        "",
        "## Constrained mixture comparison",
        "",
        "| Model | Valid | BIC | Silhouette | Bootstrap ARI | "
        "LODO median/min ARI | Components |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in models.sort_values(["k", "covariance"]).itertuples():
        if not bool(row.valid):
            lines.append(
                f"| {row.model_id} | no: {row.invalid_reason} | | | | | |"
            )
            continue
        lines.append(
            f"| {row.model_id} | yes | {row.bic:.1f} | "
            f"{row.silhouette:.3f} | {row.bootstrap_ari_median:.3f} | "
            f"{row.lodo_ari_median:.3f}/{row.lodo_ari_minimum:.3f} | "
            f"{row.component_sizes} |"
        )
    lines.extend(
        [
            "",
            f"- Lowest valid BIC: `{bic_best['model_id']}`.",
            f"- Highest median participant-bootstrap ARI: "
            f"`{stable_best['model_id']}`.",
            "- Leave-one-dataset-out ARI compares held-out predictions with the "
            "corresponding full-sample neutral partition.",
            "",
            "## Continuous versus discrete geometry",
            "",
            "All models below were scored in the same full feature space using "
            "identical participant-grouped holdouts.",
            "",
            "| Model | Family | Mean test log likelihood | SD | Valid-size splits |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in density.itertuples():
        lines.append(
            f"| {row.model_id} | {row.model_family} | "
            f"{row.mean_test_log_likelihood:.3f} | "
            f"{row.sd_test_log_likelihood:.3f} | "
            f"{row.valid_component_split_fraction:.0%} |"
        )
    lines.extend(
        [
            "",
            f"- Best continuous model: `{best_factor['model_id']}`.",
            f"- Best component-size-eligible discrete model: "
            f"`{best_mixture['model_id']}`.",
            f"- Discrete-minus-continuous held-out log-likelihood difference: "
            f"{likelihood_delta:.3f} per window.",
            "",
            "A positive difference favours a mixture density; it does not by "
            "itself establish psychologically discrete states. Mixtures passing "
            "the minimum-size rule in fewer than 80% of held-out splits are not "
            "used as the preferred discrete result.",
            "",
            "## Stroop interpretation rubric",
            "",
            "| Provisional pattern | Observable Stroop signature | Caution |",
            "|---|---|---|",
            "| In-zone-like | High accuracy and throughput, manageable interference "
            "cost, moderate structured variability, and preserved task-relevant "
            "MI | Post-error adjustment and MI are supporting features, not "
            "requirements |",
            "| Flat-like | Slow responses, weak throughput, non-response or slow-tail "
            "signatures, low updates, and weak conflict/non-conflict "
            "differentiation | Low interference cost can also reflect poor task "
            "engagement |",
            "| Locked-in-like | Large interference cost, incongruent slowing, high "
            "persistence, low entropy, and exaggerated or inflexible post-error "
            "adjustment | PES is frequently unavailable and adaptive caution "
            "must not be labelled rigidity automatically |",
            "| Spun-out-like | Fast errors, high RT variability, volatility and error "
            "burstiness, with weak task-relevant MI | Conflict adaptation is not "
            "directly estimated in this pipeline |",
            "",
            "This rubric tests the useful distinction between disengaged slowing, "
            "over-controlled slowing, structured variability and unstable "
            "variability. ACDC records task responses; it does not always verify "
            "spoken colour naming.",
            "",
            "## Prototype alignment",
            "",
            "| Model | Cluster | Closest prototype | Similarity | Lower 95% | "
            "Lead | Strong |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in alignment.itertuples():
        lines.append(
            f"| {row.model_id} | {row.cluster_id} | {row.closest_prototype} | "
            f"{row.similarity:.3f} | {row.similarity_ci_lower:.3f} | "
            f"{row.lead_over_next:.3f} | "
            f"{'yes' if row.strong_alignment else 'no'} |"
        )
    three_profiles = profiles[
        profiles["model_id"].eq("Stroop-GMM3-full")
    ].copy()
    lines.extend(
        [
            "",
            "## Three-profile descriptive check",
            "",
            "Missing PES and MI values are not imputed. Their availability is "
            "reported because these metrics cannot safely define every profile.",
            "",
            "| Neutral cluster | Windows | Accuracy | Throughput | Median RT | "
            "Interference RT | RT CV | Error burstiness | PES avail. | MI avail. |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in three_profiles.itertuples():
        lines.append(
            f"| {row.cluster_id} | {row.n_windows} | {row.mean_accuracy:.3f} | "
            f"{row.mean_throughput_proxy:.3f} | {row.mean_median_rt_ms:.1f} | "
            f"{row.mean_control_cost_rt_ms:.1f} | {row.mean_rt_cv:.3f} | "
            f"{row.mean_error_burstiness:.3f} | "
            f"{row.availability_post_error_slowing_ms:.1%} | "
            f"{row.availability_mi_congruency_correct:.1%} |"
        )
    stable = three_profiles.loc[
        (
            three_profiles["mean_accuracy"].rank(pct=True)
            + three_profiles["mean_throughput_proxy"].rank(pct=True)
            - three_profiles["mean_rt_cv"].rank(pct=True)
            - three_profiles["mean_error_burstiness"].rank(pct=True)
        ).idxmax()
    ]
    slow = three_profiles.loc[three_profiles["mean_median_rt_ms"].idxmax()]
    bursty = three_profiles.loc[
        three_profiles["mean_error_burstiness"].idxmax()
    ]
    lines.extend(
        [
            "",
            "### Observed neutral structure",
            "",
            f"- `{stable['cluster_id']}` is the high-performing stable profile: "
            f"accuracy {stable['mean_accuracy']:.3f}, throughput "
            f"{stable['mean_throughput_proxy']:.3f}, RT CV "
            f"{stable['mean_rt_cv']:.3f}, and error burstiness "
            f"{stable['mean_error_burstiness']:.3f}. It is broadly "
            "in-zone-like, but sparse MI/PES support and its interference cost "
            "prevent a validated mapping.",
            f"- `{slow['cluster_id']}` is the slow low-throughput variable "
            f"profile: median RT {slow['mean_median_rt_ms']:.1f} ms, accuracy "
            f"{slow['mean_accuracy']:.3f}, and RT CV "
            f"{slow['mean_rt_cv']:.3f}. It is not cleanly flat-like because "
            "non-response is low and update magnitude is not suppressed.",
            f"- `{bursty['cluster_id']}` is the fast error-bursty persistent "
            f"profile: median RT {bursty['mean_median_rt_ms']:.1f} ms, "
            f"error burstiness {bursty['mean_error_burstiness']:.3f}, and "
            f"lag-1 persistence {bursty['mean_cog_lag1']:.3f}. It mixes "
            "spun-out-like instability with locked-in-like persistence rather "
            "than cleanly matching either prototype.",
            "",
            "The three-profile result therefore separates a stable central "
            "profile from two different dysregulated profiles. It does not "
            "separately recover all four proposed zones.",
        ]
    )
    sensitive = holdout.groupby("model_id")["assignment_ari"].min().sort_values()
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The preferred profile count should balance BIC, separation, "
            "participant-bootstrap stability, held-out-dataset stability and "
            "out-of-sample density. No single statistic is decisive.",
            "",
            f"The most dataset-sensitive candidate was `{sensitive.index[0]}` "
            f"(minimum leave-one-dataset-out ARI {sensitive.iloc[0]:.3f}).",
            "",
            "Strong evidence for three zones would require the three-component "
            "solution to be stable across datasets, outperform the two- and "
            "four-component alternatives out of sample, and yield distinct, "
            "replicable profiles. Otherwise the safer interpretation is "
            "continuous dimensions or a broad central profile with tails.",
            "",
            "There is no registered support for four Stroop zones. The "
            "four-component diagonal GMM improves unconstrained density fit but "
            "fails the full-sample minimum-component rule and passes that rule "
            "in only 55% of participant-held-out splits. The full-covariance "
            "four-component model is not estimable under the sample-size rule.",
            "",
            "## Claim-safe conclusion",
            "",
            "This analysis compares whether Stroop conflict-control dynamics are "
            "better summarized by two, three or four neutral mixtures, or by a "
            "continuous latent-factor distribution. It is exploratory evidence "
            "about behavioural geometry and not validation of discrete zones or "
            "brain states.",
        ]
    )
    return "\n".join(lines)


def _json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")


def _build_cluster_profiles(
    windows: pd.DataFrame,
    assignments: pd.DataFrame,
    models: pd.DataFrame,
) -> pd.DataFrame:
    measures = [
        "accuracy",
        "throughput_proxy",
        "median_rt_ms",
        "control_cost_rt_ms",
        "control_cost_acc",
        "cog_lag1",
        "cog_diff_entropy",
        "cog_perm_entropy3",
        "rt_cv",
        "rt_volatility",
        "fast_error_rate",
        "error_burstiness",
        "nonresponse_rate",
        "slow_tail_rate",
        "post_error_slowing_ms",
        "mi_congruency_correct",
        "combined_update_magnitude",
    ]
    available = [measure for measure in measures if measure in windows]
    base = windows[["window_id", *available]].copy()
    rows: list[dict[str, Any]] = []
    for model in models.itertuples():
        if not bool(model.valid):
            continue
        cluster_column = f"{model.model_id}_cluster_id"
        merged = base.merge(
            assignments[
                ["window_id", "participant_id", "dataset_id", cluster_column]
            ],
            on="window_id",
            how="inner",
            validate="one_to_one",
        )
        for cluster_id, group in merged.groupby(cluster_column, sort=True):
            row: dict[str, Any] = {
                "model_id": model.model_id,
                "cluster_id": cluster_id,
                "n_windows": len(group),
                "n_subjects": group["participant_id"].nunique(),
                "n_datasets": group["dataset_id"].nunique(),
                "dataset_composition": "|".join(
                    f"{dataset}:{count}"
                    for dataset, count in group["dataset_id"]
                    .value_counts()
                    .sort_index()
                    .items()
                ),
                "maximum_dataset_share": float(
                    group["dataset_id"].value_counts(normalize=True).max()
                ),
            }
            for measure in available:
                numeric = pd.to_numeric(group[measure], errors="coerce")
                row[f"mean_{measure}"] = float(numeric.mean())
                row[f"median_{measure}"] = float(numeric.median())
                row[f"availability_{measure}"] = float(numeric.notna().mean())
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    missing = [path for path in (args.input, args.audit) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Required inputs are missing: " + ", ".join(str(path) for path in missing)
        )
    windows = pd.read_parquet(args.input)
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    gate = audit["task_gates"].get("Stroop")
    if not gate or not gate["eligible"]:
        raise RuntimeError("Stroop did not pass the existing modelling gates")
    features = list(gate["selected_features"])
    stroop = windows[
        windows["task_family"].eq("Stroop")
        & windows["window_kind"].eq("full")
        & windows["window_size"].eq(80)
    ].copy()
    if stroop.empty:
        raise RuntimeError("No primary full Stroop windows were found")

    print("Comparing constrained Stroop GMMs", flush=True)
    result = compare_stroop_zone_counts(
        stroop,
        features,
        bootstrap_repetitions=args.bootstrap_repetitions,
        seed=args.seed,
    )
    print("Comparing continuous factors with discrete mixtures", flush=True)
    density_folds = compare_continuous_and_mixture_models(
        stroop,
        features,
        repetitions=args.density_repetitions,
        seed=args.seed,
    )
    density_summary = summarize_density_comparison(density_folds)
    if args.zhang_tang_input.exists():
        profile_windows = pd.read_parquet(args.zhang_tang_input)
    else:
        profile_windows = stroop
    profiles = _build_cluster_profiles(
        profile_windows,
        result.assignments,
        result.model_comparison,
    )

    alignments: list[dict[str, Any]] = []
    for row in result.model_comparison.itertuples():
        if not bool(row.valid):
            continue
        cluster_column = f"{row.model_id}_cluster_id"
        assignment = result.assignments[
            ["window_id", "participant_id", "dataset_id", cluster_column]
        ].rename(columns={cluster_column: "gmm_cluster_id"})
        for aligned in align_clusters(
            assignment,
            result.standardized_features,
            bootstraps=args.alignment_bootstraps,
            seed=args.seed,
        ):
            alignments.append({"model_id": row.model_id, **aligned})
    alignment_frame = pd.DataFrame(alignments)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_table(
        result.model_comparison,
        args.output_dir / "stroop_zone_count_models.csv",
    )
    write_table(
        result.dataset_holdout,
        args.output_dir / "stroop_zone_count_dataset_holdout.csv",
    )
    write_table(
        density_folds,
        args.output_dir / "stroop_density_comparison_folds.csv",
    )
    write_table(
        density_summary,
        args.output_dir / "stroop_continuous_vs_mixture.csv",
    )
    write_table(
        alignment_frame,
        args.output_dir / "stroop_zone_count_alignment.csv",
    )
    write_table(
        profiles,
        args.output_dir / "stroop_zone_count_profiles.csv",
    )
    write_table(result.assignments, args.assignments)
    _plot(result.model_comparison, density_summary, args.figure)
    report = _render_report(
        stroop,
        result.model_comparison,
        result.dataset_holdout,
        density_summary,
        alignment_frame,
        profiles,
        result.pca_metrics,
    )
    write_text(report, args.report)
    write_json(
        {
            "analysis_rows": len(stroop),
            "participants": stroop["participant_id"].nunique(),
            "datasets": stroop["dataset_id"].nunique(),
            "features": features,
            "pca": result.pca_metrics,
            "models": _json_records(result.model_comparison),
            "density_summary": _json_records(density_summary),
            "alignment": _json_records(alignment_frame),
            "profiles": _json_records(profiles),
        },
        args.metrics,
    )
    update_run_manifest(
        args.manifest,
        ROOT,
        "stroop_zone_count_comparison",
        {
            "input": str(args.input),
            "audit": str(args.audit),
            "zhang_tang_input": str(args.zhang_tang_input),
            "k_values": [2, 3, 4],
            "bootstrap_repetitions": args.bootstrap_repetitions,
            "density_repetitions": args.density_repetitions,
            "participant_grouped": True,
            "seed": args.seed,
            "report": str(args.report),
        },
    )
    print(f"Wrote {args.report}", flush=True)


if __name__ == "__main__":
    main()
