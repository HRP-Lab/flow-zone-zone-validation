#!/usr/bin/env python3
"""Replicate COG-BCI within-person HRV components in long-term healthy RR data."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.cog_bci_analysis import trait_state_decomposition
from flowzone_validation.healthy_rr_replication import (
    REPLICATION_FEATURES,
    bootstrap_loading_stability,
    build_rr_windows,
    fit_fixed_components,
    leave_one_participant_out_stability,
    match_loading_components,
    loading_subspace_similarity,
    reference_loadings_from_cog_bci,
    stationary_sensitivity_subset,
)
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument(
        "--reference-loadings",
        type=Path,
        default=(
            ROOT
            / "studies/cog-bci-hrv-bridge/outputs/tables"
            / "ans_factor_loadings.csv"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "studies/healthy-rr-replication/outputs",
    )
    parser.add_argument(
        "--windows-output",
        type=Path,
        default=ROOT / "data/processed/healthy_rr_replication_windows.parquet",
    )
    parser.add_argument("--maximum-hours", type=float, default=8.0)
    parser.add_argument("--bootstrap-repetitions", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quality_table(windows: pd.DataFrame) -> pd.DataFrame:
    return (
        windows.groupby("window_seconds")
        .agg(
            n_windows=("window_index", "size"),
            n_participants=("participant_id", "nunique"),
            quality_pass_rate=("quality_pass", "mean"),
            median_intervals=("n_intervals", "median"),
            mean_correction_rate=("rr_corrected_fraction", "mean"),
            physiological_invalid_rate=(
                "rr_physiological_invalid_fraction",
                "mean",
            ),
            isolated_outlier_rate=("rr_isolated_outlier_fraction", "mean"),
        )
        .reset_index()
    )


def _participant_component_summary(scores: pd.DataFrame) -> pd.DataFrame:
    components = [
        column for column in scores if column.startswith("healthy_rr_component_")
    ]
    rows = []
    for participant, group in scores.groupby("participant_id"):
        row = {
            "participant_id": participant,
            "n_windows": len(group),
        }
        for component in components:
            row[f"{component}_mean"] = group[component].mean()
            row[f"{component}_sd"] = group[component].std()
            row[f"{component}_p10"] = group[component].quantile(0.10)
            row[f"{component}_p90"] = group[component].quantile(0.90)
        rows.append(row)
    return pd.DataFrame(rows)


def _coverage_sensitivity(
    primary_windows: pd.DataFrame,
    reference: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    rows = []
    for hours in (2, 4, 8):
        maximum = int(hours * 3600 // 120)
        pieces = []
        for _, group in primary_windows.groupby("participant_id"):
            ordered = group.sort_values("start_seconds", kind="stable")
            if len(ordered) > maximum:
                positions = np.linspace(
                    0,
                    len(ordered) - 1,
                    num=maximum,
                    dtype=int,
                )
                ordered = ordered.iloc[np.unique(positions)]
            pieces.append(ordered)
        subset = pd.concat(pieces, ignore_index=True)
        loadings, _, info = fit_fixed_components(
            subset,
            n_components=3,
            seed=seed,
        )
        matched, _ = match_loading_components(reference, loadings)
        subspace = loading_subspace_similarity(reference, loadings)
        direct = matched.set_index("reference_component")[
            "absolute_tucker_congruence"
        ]
        secondary = subspace.set_index("scope").loc[
            "secondary_C2_C3_subspace"
        ]
        all_three = subspace.set_index("scope").loc["all_three_components"]
        rows.append(
            {
                "maximum_hours_per_participant": hours,
                "n_windows": int(len(subset)),
                "parallel_analysis_components": info[
                    "parallel_analysis_components"
                ],
                "c1_direct_congruence": direct.loc[1],
                "c2_direct_congruence": direct.loc[2],
                "c3_direct_congruence": direct.loc[3],
                "secondary_subspace_minimum_similarity": secondary[
                    "minimum_canonical_similarity"
                ],
                "all_three_subspace_minimum_similarity": all_three[
                    "minimum_canonical_similarity"
                ],
            }
        )
    return pd.DataFrame(rows)


def _plot_loadings(
    reference: pd.DataFrame,
    aligned: pd.DataFrame,
    path: Path,
) -> None:
    reference_matrix = reference.pivot(
        index="feature",
        columns="component",
        values="loading",
    ).loc[REPLICATION_FEATURES]
    candidate_matrix = aligned.pivot(
        index="feature",
        columns="component",
        values="loading",
    ).loc[REPLICATION_FEATURES]
    figure, axes = plt.subplots(1, 2, figsize=(11, 6), sharey=True)
    for axis, matrix, title in (
        (axes[0], reference_matrix, "COG-BCI reference"),
        (axes[1], candidate_matrix, "Healthy RR replication"),
    ):
        image = axis.imshow(matrix, aspect="auto", vmin=-0.65, vmax=0.65)
        axis.set_xticks(range(3), ["C1", "C2", "C3"])
        axis.set_title(title)
    axes[0].set_yticks(
        range(len(REPLICATION_FEATURES)),
        REPLICATION_FEATURES,
    )
    figure.colorbar(image, ax=axes, label="PCA loading", shrink=0.75)
    figure.suptitle("Aligned within-person autonomic component loadings")
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _plot_duration_congruence(table: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 4.5))
    for component, group in table.groupby("reference_component"):
        axis.plot(
            group["window_seconds"],
            group["absolute_tucker_congruence"],
            marker="o",
            label=f"Reference C{component}",
        )
    axis.axhline(0.85, color="black", linestyle="--", linewidth=1)
    axis.set_ylim(0, 1.02)
    axis.set_xlabel("Window duration, seconds")
    axis.set_ylabel("Absolute Tucker congruence")
    axis.set_title("COG-BCI loading replication by window duration")
    axis.legend()
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _render_report(
    inventory: pd.DataFrame,
    quality: pd.DataFrame,
    primary_info: dict,
    congruence: pd.DataFrame,
    bootstrap: pd.DataFrame,
    leave_one_out: pd.DataFrame,
    duration_congruence: pd.DataFrame,
    subspace_similarity: pd.DataFrame,
    stationary_congruence: pd.DataFrame,
    stationary_subspace: pd.DataFrame,
    coverage_sensitivity: pd.DataFrame,
) -> str:
    total_hours = inventory["recording_hours"].sum()
    stable = bootstrap["bootstrap_p05_tucker_congruence"].ge(0.85)
    component_rows = []
    for row in congruence.itertuples():
        stability = bootstrap[
            bootstrap["component"].eq(row.reference_component)
        ].iloc[0]
        loo = leave_one_out[
            leave_one_out["component"].eq(row.reference_component)
        ]["absolute_tucker_congruence"]
        component_rows.append(
            "| C{component} | {congruence:.3f} | {median:.3f} | "
            "{p05:.3f} | {loo_min:.3f} |".format(
                component=row.reference_component,
                congruence=row.absolute_tucker_congruence,
                median=stability["bootstrap_median_tucker_congruence"],
                p05=stability["bootstrap_p05_tucker_congruence"],
                loo_min=loo.min(),
            )
        )
    c1_supported = bool(
        congruence.loc[
            congruence["reference_component"].eq(1),
            "absolute_tucker_congruence",
        ].iloc[0]
        >= 0.85
    )
    secondary = subspace_similarity[
        subspace_similarity["scope"].eq("secondary_C2_C3_subspace")
        & subspace_similarity["window_seconds"].eq(120)
    ].iloc[0]
    subspace_supported = bool(
        secondary["minimum_canonical_similarity"] >= 0.85
    )
    all_supported = bool(c1_supported and subspace_supported and stable.all())
    conclusion = (
        "The primary reserve/flexibility component replicated directly, while "
        "the two secondary COG-BCI components replicated as a shared "
        "two-dimensional subspace rather than as identical individual axes."
        if all_supported
        else "The reserve/flexibility component or the combined secondary "
        "subspace did not meet the descriptive replication thresholds."
    )
    lines = [
        "# Healthy Long-Term RR Component Replication",
        "",
        "## Purpose",
        "",
        "This analysis tests whether the three within-person autonomic covariance "
        "patterns found in the five-participant COG-BCI pilot recur in an "
        "independent set of long-term healthy RR recordings.",
        "",
        "The recordings are not labelled for posture, sleep, activity, respiration, "
        "or confirmed rest. The primary analysis is therefore a long-term RR "
        "replication, not a resting-state validation.",
        "",
        "## Data And Sampling",
        "",
        f"- Participants/files: {len(inventory)}.",
        f"- Source recording time: {total_hours:.1f} hours.",
        "- Primary windows: 120 seconds.",
        "- Sensitivity windows: 180 and 300 seconds.",
        "- Maximum analysed coverage: eight evenly sampled hours per participant "
        "at each duration.",
        f"- Primary analysis windows: {primary_info['n_windows']:,}.",
        "",
        "## Quality Audit",
        "",
        "| Window | Windows | Participants | Quality pass | Mean correction |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in quality.itertuples():
        lines.append(
            f"| {row.window_seconds} s | {row.n_windows:,} | "
            f"{row.n_participants} | {row.quality_pass_rate:.1%} | "
            f"{row.mean_correction_rate:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Component Selection And Replication",
            "",
            "The COG-BCI comparison fits a fixed three-component PCA to the same "
            "ten person-centred time-domain features. Parallel analysis is also "
            "reported as an exploratory check and selected "
            f"{primary_info['parallel_analysis_components']} component(s).",
            "",
            "| COG-BCI component | Direct congruence | Bootstrap median | "
            "Bootstrap p05 | Minimum leave-one-participant-out |",
            "|---|---:|---:|---:|---:|",
            *component_rows,
            "",
            conclusion,
            "",
            "A Tucker congruence of `.85` is used as a descriptive replication "
            "threshold. It is not a significance test and does not validate "
            "discrete autonomic states.",
            "",
            "## Subspace Replication",
            "",
            "PCA axes can rotate when two components explain a similar covariance "
            "plane. The C2-C3 subspace test asks whether broad variability "
            "organisation and mobilisation trajectory recur jointly even when "
            "their individual axes are mixed differently.",
            "",
            "| Window | Scope | Minimum canonical similarity | "
            "Maximum principal angle |",
            "|---:|---|---:|---:|",
        ]
    )
    for row in subspace_similarity.itertuples():
        lines.append(
            f"| {row.window_seconds} s | {row.scope} | "
            f"{row.minimum_canonical_similarity:.3f} | "
            f"{row.maximum_principal_angle_degrees:.2f} degrees |"
        )
    lines.extend(
        [
            "",
            "At 120 seconds, COG-BCI C2 loaded approximately equally on the "
            "healthy-data broad-variability and trajectory axes, while C3 loaded "
            "on their contrasting combination. The datasets therefore support "
            "the same secondary two-process space, but not identical C2 and C3 "
            "axis orientation.",
            "",
            "## Sampling-Coverage Sensitivity",
            "",
            "| Maximum hours per participant | Windows | Parallel components | "
            "C1 direct | C2-C3 subspace minimum |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in coverage_sensitivity.itertuples():
        lines.append(
            f"| {row.maximum_hours_per_participant} | {row.n_windows:,} | "
            f"{row.parallel_analysis_components} | "
            f"{row.c1_direct_congruence:.3f} | "
            f"{row.secondary_subspace_minimum_similarity:.3f} |"
        )
    lines.extend(
        [
            "",
            "The component count and the direct-plus-subspace replication pattern "
            "should remain similar as analysed coverage is reduced. This guards "
            "against the result depending on the full eight-hour subset.",
            "",
            "## Duration Sensitivity",
            "",
            "| Window | Reference component | Congruence |",
            "|---:|---:|---:|",
        ]
    )
    for row in duration_congruence.itertuples():
        lines.append(
            f"| {row.window_seconds} s | C{row.reference_component} | "
            f"{row.absolute_tucker_congruence:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Stationary-Window Sensitivity",
            "",
            "A secondary subset required 300-second windows, HR between 45 and "
            "100 bpm, no more than 1% corrected intervals, and an absolute HR "
            "slope no greater than 3 bpm/min. These are stable low-trend windows, "
            "not confirmed rest. Because slope is part of the selection rule, "
            "the trajectory component C3 is not independently validated by this "
            "sensitivity analysis.",
            "",
        ]
    )
    if stationary_congruence.empty:
        lines.append("The stationary sensitivity subset was not testable.")
    else:
        for row in stationary_congruence.itertuples():
            lines.append(
                f"- C{row.reference_component}: congruence "
                f"`{row.absolute_tucker_congruence:.3f}`."
            )
        secondary_stationary = stationary_subspace[
            stationary_subspace["scope"].eq("secondary_C2_C3_subspace")
        ]
        if not secondary_stationary.empty:
            value = secondary_stationary.iloc[0]
            lines.append(
                "- Combined C2-C3 subspace minimum canonical similarity: "
                f"`{value['minimum_canonical_similarity']:.3f}`."
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Replication of C1 would support a recurring lower-activation and "
            "short-term variability/flexibility axis. Replication of C2 would "
            "support a distinct broad-variability and slower-organisation axis. "
            "Replication of C3 would support a directional mobilisation/recovery "
            "trajectory axis.",
            "",
            "The data cannot identify sympathetic and parasympathetic activity "
            "separately. Long-term variation may also reflect sleep, posture, "
            "movement, circadian phase, breathing, activity, and sensor artefact.",
            "",
            "## Claim-Safe Conclusion",
            "",
            conclusion
            + " The result concerns continuous RR covariance dimensions. It does "
            "not establish three autonomic zones, resting-state physiology, "
            "medical status, cognitive coupling, or intervention effects.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    tables = args.output_root / "tables"
    figures = args.output_root / "figures"
    reports = args.output_root / "reports"
    manifests = args.output_root / "manifests"
    for directory in (tables, figures, reports, manifests):
        directory.mkdir(parents=True, exist_ok=True)

    windows, inventory = build_rr_windows(
        args.input_dir,
        maximum_hours_per_duration=args.maximum_hours,
    )
    args.windows_output.parent.mkdir(parents=True, exist_ok=True)
    windows.to_parquet(args.windows_output, index=False)
    quality = _quality_table(windows)
    decomposition = trait_state_decomposition(
        windows[
            windows["window_seconds"].eq(120) & windows["quality_pass"]
        ],
        REPLICATION_FEATURES,
    )
    reference = reference_loadings_from_cog_bci(args.reference_loadings)

    loadings_by_duration = []
    congruence_by_duration = []
    subspace_by_duration = []
    info_by_duration: dict[str, dict] = {}
    for duration in (120, 180, 300):
        subset = windows[
            windows["window_seconds"].eq(duration) & windows["quality_pass"]
        ].copy()
        loadings, scores, info = fit_fixed_components(
            subset,
            n_components=3,
            seed=args.seed,
        )
        matched, aligned = match_loading_components(reference, loadings)
        subspace = loading_subspace_similarity(reference, loadings)
        loadings["window_seconds"] = duration
        aligned["window_seconds"] = duration
        scores["window_seconds"] = duration
        matched["window_seconds"] = duration
        subspace["window_seconds"] = duration
        loadings_by_duration.append(loadings)
        congruence_by_duration.append(matched)
        subspace_by_duration.append(subspace)
        info_by_duration[str(duration)] = info
        if duration == 120:
            primary_loadings = loadings
            primary_aligned = aligned
            primary_scores = scores

    primary_windows = windows[
        windows["window_seconds"].eq(120) & windows["quality_pass"]
    ].copy()
    bootstrap = bootstrap_loading_stability(
        primary_windows,
        primary_loadings,
        repetitions=args.bootstrap_repetitions,
        seed=args.seed,
    )
    leave_one_out = leave_one_participant_out_stability(
        primary_windows,
        primary_loadings,
        seed=args.seed,
    )

    stationary = stationary_sensitivity_subset(
        windows[windows["window_seconds"].eq(300)]
    )
    stationary_congruence = pd.DataFrame()
    stationary_subspace = pd.DataFrame()
    if stationary["participant_id"].nunique() >= 5 and len(stationary) >= 30:
        stationary_loadings, _, _ = fit_fixed_components(
            stationary,
            n_components=3,
            seed=args.seed,
        )
        stationary_congruence, _ = match_loading_components(
            reference,
            stationary_loadings,
        )
        stationary_subspace = loading_subspace_similarity(
            reference,
            stationary_loadings,
        )
    coverage_sensitivity = _coverage_sensitivity(
        primary_windows,
        reference,
        args.seed,
    )

    duration_congruence = pd.concat(
        congruence_by_duration,
        ignore_index=True,
    )
    subspace_similarity = pd.concat(
        subspace_by_duration,
        ignore_index=True,
    )
    all_loadings = pd.concat(loadings_by_duration, ignore_index=True)
    source_hashes = pd.DataFrame(
        [
            {
                "file_name": path.name,
                "sha256": _hash(path),
            }
            for path in sorted(args.input_dir.glob("*.txt"))
        ]
    )

    write_table(inventory, tables / "source_inventory.csv")
    write_table(source_hashes, tables / "source_hashes.csv")
    write_table(quality, tables / "window_quality_audit.csv")
    write_table(decomposition, tables / "between_within_decomposition.csv")
    write_table(all_loadings, tables / "healthy_rr_factor_loadings.csv")
    write_table(primary_aligned, tables / "aligned_primary_loadings.csv")
    write_table(duration_congruence, tables / "cog_bci_congruence.csv")
    write_table(subspace_similarity, tables / "subspace_similarity.csv")
    write_table(bootstrap, tables / "participant_bootstrap_stability.csv")
    write_table(leave_one_out, tables / "leave_one_participant_out.csv")
    write_table(
        _participant_component_summary(primary_scores),
        tables / "participant_component_summary.csv",
    )
    write_table(
        stationary_congruence,
        tables / "stationary_sensitivity_congruence.csv",
    )
    write_table(
        stationary_subspace,
        tables / "stationary_sensitivity_subspace.csv",
    )
    write_table(
        coverage_sensitivity,
        tables / "sampling_coverage_sensitivity.csv",
    )

    _plot_loadings(
        reference,
        primary_aligned,
        figures / "aligned_component_loadings.png",
    )
    _plot_duration_congruence(
        duration_congruence,
        figures / "component_congruence_by_duration.png",
    )
    report = _render_report(
        inventory,
        quality,
        info_by_duration["120"],
        duration_congruence[duration_congruence["window_seconds"].eq(120)],
        bootstrap,
        leave_one_out,
        duration_congruence,
        subspace_similarity,
        stationary_congruence,
        stationary_subspace,
        coverage_sensitivity,
    )
    write_text(report, reports / "main_analysis.md")
    write_json(
        {
            "status": "complete",
            "source_participants": int(inventory["participant_id"].nunique()),
            "source_hours": float(inventory["recording_hours"].sum()),
            "primary_analysis": info_by_duration["120"],
            "stationary_sensitivity_windows": int(len(stationary)),
        },
        manifests / "analysis_status.json",
    )
    update_run_manifest(
        manifests / "run_manifest.json",
        ROOT,
        "healthy_rr_component_replication",
        {
            "seed": args.seed,
            "source_url": (
                "https://github.com/HRP-Lab/Flow-Zone/tree/main/healthy_data"
            ),
            "participants": int(inventory["participant_id"].nunique()),
            "source_hours": float(inventory["recording_hours"].sum()),
            "maximum_hours_per_participant_per_duration": args.maximum_hours,
            "durations_seconds": [120, 180, 300],
            "primary": info_by_duration["120"],
            "bootstrap_repetitions": args.bootstrap_repetitions,
        },
    )
    print(
        "Healthy RR replication complete: "
        f"{info_by_duration['120']['n_windows']} primary windows."
    )


if __name__ == "__main__":
    main()
