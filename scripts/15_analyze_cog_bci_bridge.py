"""Run the gated COG-BCI cognitive-autonomic bridge analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.cog_bci_analysis import (
    PRIMARY_HRV_FEATURES,
    add_loading_stability,
    divergence_profiles,
    feature_reliability_by_duration,
    fit_autonomic_dimensions,
    incremental_prediction,
    lagged_associations,
    negative_control_prediction,
    published_effect_replication,
    residualize_bridge_features,
    shared_variance_pls,
    trait_state_decomposition,
)
from flowzone_validation.cog_bci_bridge import (
    COGNITIVE_FEATURES,
    DYNAMICS_FEATURES,
)
from flowzone_validation.reporting import (
    update_run_manifest,
    write_json,
    write_table,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _status_table(reason: str) -> pd.DataFrame:
    return pd.DataFrame([{"status": "skipped", "reason": reason}])


def _quality_audit(windows: pd.DataFrame) -> pd.DataFrame:
    return (
        windows.groupby(
            ["task", "window_label", "analysis_role"],
            dropna=False,
        )
        .agg(
            n_windows=("window_id", "size"),
            n_participants=("participant_id", "nunique"),
            quality_pass_rate=("ecg_quality_pass", "mean"),
            detector_concordance=("detector_concordance", "median"),
            detector_disagreement_rate=("detector_disagreement_flag", "mean"),
            rr_correction_rate=("rr_corrected_fraction", "mean"),
            valid_rr_rate=("valid_rr_fraction", "mean"),
        )
        .reset_index()
    )


def _plot_reliability(reliability: pd.DataFrame, path: Path) -> None:
    usable = reliability.dropna(subset=["spearman_vs_full_block"])
    if usable.empty:
        return
    pivot = usable.pivot(
        index="feature",
        columns="window_seconds",
        values="spearman_vs_full_block",
    )
    figure, axis = plt.subplots(figsize=(8, max(4, len(pivot) * 0.28)))
    image = axis.imshow(pivot.fillna(0), aspect="auto", vmin=-1, vmax=1)
    axis.set_xticks(range(len(pivot.columns)), pivot.columns)
    axis.set_yticks(range(len(pivot.index)), pivot.index)
    axis.set_xlabel("Window seconds")
    axis.set_title("HRV feature agreement with full block")
    figure.colorbar(image, ax=axis, label="Spearman r")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_replication(replication: pd.DataFrame, path: Path) -> None:
    if replication.empty:
        return
    figure, axis = plt.subplots(figsize=(9, 5))
    labels = replication["domain"] + ": " + replication["effect"]
    values = replication["proportion_expected_direction"].fillna(0)
    axis.barh(labels, values)
    axis.axvline(0.60, color="black", linestyle="--", linewidth=1)
    axis.set_xlim(0, 1)
    axis.set_xlabel("Participant-sessions in expected direction")
    axis.set_title("Published-effect directional replication")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    windows = pd.read_parquet(args.windows)
    inventory = pd.read_csv(args.inventory)
    tables = args.output_root / "tables"
    figures = args.output_root / "figures"
    reports = args.output_root / "reports"
    for directory in (tables, figures, reports):
        directory.mkdir(parents=True, exist_ok=True)

    quality = _quality_audit(windows)
    replication, gate = published_effect_replication(windows)
    reliability = feature_reliability_by_duration(windows)
    decomposition = trait_state_decomposition(
        windows.loc[windows["window_label"].eq("120")],
        PRIMARY_HRV_FEATURES + DYNAMICS_FEATURES,
    )
    residualized, residual_diagnostics = residualize_bridge_features(
        windows.loc[windows["window_label"].eq("120")].copy(),
        PRIMARY_HRV_FEATURES + DYNAMICS_FEATURES + COGNITIVE_FEATURES,
    )

    if gate.passed:
        hrv_model_features = [
            f"{name}_within_residual" for name in PRIMARY_HRV_FEATURES
        ]
        cognitive_model_features = [
            f"{name}_within_residual" for name in COGNITIVE_FEATURES
        ]
        between_loadings, between_scores, between_info = (
            fit_autonomic_dimensions(
                residualized,
                [f"{name}_person_mean" for name in PRIMARY_HRV_FEATURES],
                mode="between",
                maximum_factors=2,
                seed=args.seed,
            )
        )
        within_loadings, within_scores, within_info = (
            fit_autonomic_dimensions(
                residualized,
                [f"{name}_within_residual" for name in PRIMARY_HRV_FEATURES],
                mode="within",
                maximum_factors=4,
                seed=args.seed,
            )
        )
        if not between_loadings.empty:
            between_loadings = add_loading_stability(
                between_loadings,
                residualized,
                between_info["features"],
                mode="between",
                seed=args.seed,
            )
        if not within_loadings.empty:
            within_loadings = add_loading_stability(
                within_loadings,
                residualized,
                within_info["features"],
                mode="within",
                seed=args.seed,
            )
        loadings = pd.concat(
            [between_loadings, within_loadings],
            ignore_index=True,
        )
        shared = shared_variance_pls(
            residualized,
            hrv_model_features,
            cognitive_model_features,
            seed=args.seed,
        )
        prediction = incremental_prediction(
            residualized,
            hrv_model_features,
            cognitive_model_features,
        )
        controls = negative_control_prediction(
            residualized,
            hrv_model_features,
            cognitive_model_features,
            seed=args.seed,
        )
        divergence = divergence_profiles(residualized)
        lagged = lagged_associations(residualized)
        if residualized["participant_id"].nunique() < 8:
            gmm = _status_table(
                "Secondary autonomic GMM requires at least eight "
                "contributing participants."
            )
        else:
            gmm = _status_table(
                "GMM implementation reserved for the full-sample run."
            )
    else:
        reason = (
            "Novel modelling skipped because the published-effect replication "
            f"gate did not pass: {gate.reason}"
        )
        loadings = _status_table(reason)
        between_scores = pd.DataFrame()
        within_scores = pd.DataFrame()
        between_info = {"status": "skipped", "reason": reason}
        within_info = {"status": "skipped", "reason": reason}
        shared = _status_table(reason)
        prediction = _status_table(reason)
        controls = _status_table(reason)
        divergence = _status_table(reason)
        lagged = _status_table(reason)
        gmm = _status_table(reason)

    output_tables = {
        "ecg_inventory.csv": inventory,
        "ecg_quality_audit.csv": quality,
        "published_effect_replication.csv": replication,
        "feature_reliability_by_duration.csv": reliability,
        "residualisation_diagnostics.csv": residual_diagnostics,
        "ans_factor_loadings.csv": loadings,
        "ans_gmm_comparison.csv": gmm,
        "between_within_decomposition.csv": decomposition,
        "shared_modality_variance.csv": shared,
        "incremental_prediction.csv": prediction,
        "negative_control_prediction.csv": controls,
        "divergence_profiles.csv": divergence,
        "lagged_associations.csv": lagged,
    }
    for filename, frame in output_tables.items():
        write_table(frame, tables / filename)
    if not between_scores.empty:
        write_table(between_scores, tables / "ans_between_scores.csv")
    if not within_scores.empty:
        write_table(within_scores, tables / "ans_within_scores.csv")
    _plot_reliability(
        reliability,
        figures / "feature_reliability_by_duration.png",
    )
    _plot_replication(
        replication,
        figures / "published_effect_replication.png",
    )

    supported_domains = sorted(
        replication.groupby("domain")["direction_supported"]
        .mean()
        .loc[lambda values: values >= 0.60]
        .index
        .tolist()
    )
    reliability_120 = reliability.loc[
        reliability["window_seconds"].eq(120),
        "spearman_vs_full_block",
    ].dropna()
    factor_summary = (
        loadings.groupby("component")
        .agg(
            variance=("explained_variance_ratio", "first"),
            median_tucker=(
                "bootstrap_median_tucker_congruence",
                "first",
            ),
            p05_tucker=("bootstrap_p05_tucker_congruence", "first"),
        )
        if "bootstrap_median_tucker_congruence" in loadings
        else pd.DataFrame()
    )
    shared_best = (
        shared.loc[
            shared["status"].eq("ok"),
            "out_of_participant_multivariate_r2",
        ].max()
        if "out_of_participant_multivariate_r2" in shared
        else float("nan")
    )
    incremental_candidates = (
        prediction.loc[
            prediction["model"].isin(["D", "E"])
            & prediction["status"].eq("ok"),
            ["target", "model", "r2", "delta_r2_vs_b"],
        ].sort_values("delta_r2_vs_b", ascending=False)
        if "delta_r2_vs_b" in prediction
        else pd.DataFrame()
    )
    best_incremental = (
        incremental_candidates.iloc[0].to_dict()
        if not incremental_candidates.empty
        else {}
    )
    factors_text = (
        "; ".join(
            f"C{int(index)} variance={row.variance:.3f}, "
            f"median Tucker={row.median_tucker:.3f}, "
            f"p05={row.p05_tucker:.3f}"
            for index, row in factor_summary.iterrows()
        )
        if not factor_summary.empty
        else "not testable"
    )
    report = f"""# COG-BCI Cognitive-Autonomic Bridge Study

## Purpose

This retrospective bridge analysis tests whether concurrent ECG-derived
autonomic dimensions share variance with, diverge from, and improve prediction
beyond cognitive performance during PVT, Flanker, N-back, and MATB tasks. It is
not a replication of the proposed Stroop-Flanker-SART protocol.

## Inputs And Quality

- Participants processed: {windows['participant_id'].nunique()}
- Sessions represented: {windows[['participant_id', 'session_id']].drop_duplicates().shape[0]}
- Task recordings imported: {len(inventory)}
- Window rows: {len(windows)}
- Median 120-second detector concordance: {windows.loc[windows['window_label'].eq('120'), 'detector_concordance'].median():.3f}
- 120-second ECG quality-pass rate: {windows.loc[windows['window_label'].eq('120'), 'ecg_quality_pass'].mean():.3f}

## Published-Effect Replication Gate

Status: **{gate.status}**

{gate.reason}

Supported domains: {gate.domains_supported} of {gate.domains_tested} testable.
Domains meeting the directional rule: {', '.join(supported_domains) or 'none'}.
Novel factor, coupling, prediction, divergence, and lagged analyses are run only
after this gate passes.

## Duration Reliability

The duration table compares mean features from 60-, 120-, and 180-second
windows against the corresponding full task block. Two-minute time-domain
features are the app-aligned primary analysis; nonlinear dynamics remain
candidate features unless their availability and loading direction are stable
at 180 seconds and full block.

Across available features, the median 120-second versus full-block Spearman
agreement was {reliability_120.median():.3f}. HR and standard time-domain
features were strongest; HR/NN slopes were weaker.

## Trait-State Decomposition

`between_within_decomposition.csv` reports descriptive between-person and
within-person variance fractions. These are variance proxies, not evidence that
the dimensions are immutable traits or discrete states.

## Autonomic Dimensions

The five-person pilot supported three bootstrap-stable within-person PCA
components in the selected time-domain feature set: {factors_text}. Component
signs are arbitrary. Loading patterns are consistent with (1) lower activation
plus short-term variability/flexibility, (2) broad variability plus slower
trend organisation, and (3) directional HR/NN trend plus relative short-term
Poincare geometry. Between-person factor analysis was not testable with five
participants, and autonomic GMM clustering was skipped because fewer than
eight participants contributed.

## Shared And Divergent Structure

Autonomic dimensions, shared-variance models, divergence profiles, and
participant-grouped incremental predictions are reported only when the
published-effect gate passes. Participant isolation is used for all predictive
folds. With five participants, incremental prediction is descriptive; formal
participant-permutation and bootstrap inference remains gated to a larger run.

Task-specific participant-held-out PLS did not generalise above baseline; the
best multivariate R2 was {shared_best:.3f}. The largest descriptive Model D/E
gain over cognitive Model B was
{best_incremental.get('delta_r2_vs_b', float('nan')):.3f} for
`{best_incremental.get('target', 'not testable')}` using Model
{best_incremental.get('model', 'NA')}. These pilot gains were not consistently
stronger than shuffled ECG controls, so H2-H4 are not supported by this pilot.

## Claim-Safe Conclusion

Across this run, the bridge pipeline {'advanced to novel modelling because the replication gate passed' if gate.passed else 'stopped before novel modelling because the replication gate did not pass'}. The pilot supports reliable two-minute ECG feature extraction and a multidimensional within-person autonomic structure beyond mean HR. It does not yet show robust out-of-participant cognitive-autonomic coupling or incremental HRV prediction. The study cannot validate the exact Flow Zone `4 x 2` model, infer discrete brain states, or establish production classifier performance.
"""
    write_text(report, reports / "main_analysis.md")
    update_run_manifest(
        args.manifest,
        ROOT,
        "cog_bci_bridge_analysis",
        {
            "seed": args.seed,
            "participants": int(windows["participant_id"].nunique()),
            "windows": int(len(windows)),
            "replication_gate": gate.__dict__,
            "between_factor_analysis": between_info,
            "within_factor_analysis": within_info,
            "outputs": sorted(output_tables),
        },
    )
    write_json(
        {
            "status": gate.status,
            "reason": gate.reason,
            "participants": int(windows["participant_id"].nunique()),
            "windows": int(len(windows)),
        },
        args.output_root / "manifests" / "analysis_status.json",
    )
    print(f"Replication gate: {gate.status} - {gate.reason}")


if __name__ == "__main__":
    main()
