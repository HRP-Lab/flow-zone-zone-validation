"""Gated replication and cognitive-autonomic bridge analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from scipy.optimize import linear_sum_assignment
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
import statsmodels.formula.api as smf

from .cog_bci_bridge import (
    COGNITIVE_FEATURES,
    DYNAMICS_FEATURES,
    TIME_DOMAIN_FEATURES,
)
from .prediction import grouped_ridge_metrics


PRIMARY_HRV_FEATURES = [
    "mean_hr_bpm",
    "mean_nn_ms",
    "log_rmssd",
    "sdnn_ms",
    "cvnn",
    "pnn20",
    "pnn50",
    "sd1_sd2",
    "hr_slope_bpm_per_min",
    "nn_slope_ms_per_min",
]


@dataclass(frozen=True)
class ReplicationGate:
    passed: bool
    status: str
    reason: str
    domains_supported: int
    domains_tested: int


def _group_slopes(
    frame: pd.DataFrame,
    outcome: str,
    predictor: str,
    group_columns: list[str],
) -> np.ndarray:
    if outcome not in frame or predictor not in frame:
        return np.asarray([], dtype=float)
    slopes: list[float] = []
    for _, group in frame.groupby(group_columns, dropna=False):
        x = pd.to_numeric(group[predictor], errors="coerce")
        y = pd.to_numeric(group[outcome], errors="coerce")
        valid = x.notna() & y.notna()
        if valid.sum() >= 3 and x[valid].nunique() >= 2:
            slopes.append(float(np.polyfit(x[valid], y[valid], 1)[0]))
    return np.asarray(slopes, dtype=float)


def _direction_row(
    domain: str,
    effect: str,
    values: np.ndarray,
    expected_sign: int,
) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    median = float(np.median(finite)) if len(finite) else np.nan
    proportion = (
        float(np.mean(np.sign(finite) == expected_sign))
        if len(finite)
        else np.nan
    )
    return {
        "domain": domain,
        "effect": effect,
        "expected_direction": "positive" if expected_sign > 0 else "negative",
        "median_participant_session_effect": median,
        "n_participant_sessions": int(len(finite)),
        "proportion_expected_direction": proportion,
        "direction_supported": bool(
            len(finite) >= 5
            and np.sign(median) == expected_sign
            and proportion >= 0.60
        ),
    }


def published_effect_replication(
    windows: pd.DataFrame,
) -> tuple[pd.DataFrame, ReplicationGate]:
    """Test the published directional PVT, N-back, and MATB effects."""
    participants = int(windows.get("participant_id", pd.Series()).nunique())
    rows: list[dict[str, Any]] = []

    pvt = windows.loc[
        windows["analysis_role"].eq("replication")
        & windows["task"].eq("PVT")
    ]
    for outcome, sign in (
        ("pvt_median_rt_ms", 1),
        ("mean_hr_bpm", 1),
        ("log_rmssd", -1),
        ("sdnn_ms", -1),
    ):
        rows.append(
            _direction_row(
                "PVT time-on-task",
                outcome,
                _group_slopes(
                    pvt,
                    outcome,
                    "time_on_task_fraction",
                    ["participant_id", "session_id"],
                ),
                sign,
            )
        )

    benchmark = windows.loc[windows["window_label"].eq("full")].copy()
    nback = benchmark.loc[benchmark["task_family"].eq("NBack")].copy()
    nback["difficulty"] = pd.to_numeric(
        nback["task"].str.extract(r"(\d)$")[0],
        errors="coerce",
    )
    for outcome, sign in (
        ("nback_accuracy", -1),
        ("nback_throughput", -1),
        ("mean_hr_bpm", 1),
        ("log_rmssd", -1),
        ("sdnn_ms", -1),
    ):
        rows.append(
            _direction_row(
                "N-back difficulty",
                outcome,
                _group_slopes(
                    nback,
                    outcome,
                    "difficulty",
                    ["participant_id", "session_id"],
                ),
                sign,
            )
        )

    matb = benchmark.loc[benchmark["task_family"].eq("MATB")].copy()
    difficulty_map = {
        "MATBEasy": 0,
        "MATBMedium": 1,
        "MATBDifficult": 2,
    }
    matb["difficulty"] = matb["task"].map(difficulty_map)
    for outcome, sign in (
        ("matb_tracking_error", 1),
        ("matb_monitoring_rt", 1),
        ("mean_hr_bpm", 1),
        ("log_rmssd", -1),
        ("sdnn_ms", -1),
    ):
        rows.append(
            _direction_row(
                "MATB difficulty",
                outcome,
                _group_slopes(
                    matb,
                    outcome,
                    "difficulty",
                    ["participant_id", "session_id"],
                ),
                sign,
            )
        )

    result = pd.DataFrame(rows)
    domain_summary = (
        result.groupby("domain")["direction_supported"]
        .mean()
        .rename("supported_fraction")
    )
    tested = int((result.groupby("domain")["n_participant_sessions"].max() >= 5).sum())
    supported = int((domain_summary >= 0.60).sum())
    if participants < 5:
        gate = ReplicationGate(
            passed=False,
            status="not_testable",
            reason=(
                "Published-effect gate requires at least five participants; "
                f"found {participants}."
            ),
            domains_supported=supported,
            domains_tested=tested,
        )
    else:
        passed = supported >= 2 and tested == 3
        gate = ReplicationGate(
            passed=passed,
            status="passed" if passed else "failed",
            reason=(
                "At least two of three published-effect domains supported."
                if passed
                else "Fewer than two of three domains met directional support."
            ),
            domains_supported=supported,
            domains_tested=tested,
        )
    result["participants_available"] = participants
    result["replication_gate_status"] = gate.status
    return result, gate


def feature_reliability_by_duration(
    windows: pd.DataFrame,
    features: list[str] | None = None,
) -> pd.DataFrame:
    """Compare short-window block means with full-block values."""
    candidates = features or (TIME_DOMAIN_FEATURES + DYNAMICS_FEATURES)
    full = windows.loc[windows["window_label"].eq("full")].set_index(
        "block_id"
    )
    rows: list[dict[str, Any]] = []
    for label in ("60", "120", "180"):
        abbreviated = (
            windows.loc[windows["window_label"].eq(label)]
            .groupby("block_id", as_index=True)
            .mean(numeric_only=True)
        )
        common = full.index.intersection(abbreviated.index)
        for feature in candidates:
            if feature not in full or feature not in abbreviated:
                continue
            x = pd.to_numeric(full.loc[common, feature], errors="coerce")
            y = pd.to_numeric(
                abbreviated.loc[common, feature],
                errors="coerce",
            )
            valid = x.notna() & y.notna()
            correlation = (
                float(spearmanr(x[valid], y[valid]).statistic)
                if valid.sum() >= 5 and x[valid].nunique() > 1
                else np.nan
            )
            rows.append(
                {
                    "window_seconds": int(label),
                    "feature": feature,
                    "n_blocks": int(valid.sum()),
                    "availability_rate": float(valid.mean()) if len(valid) else 0,
                    "spearman_vs_full_block": correlation,
                }
            )
    return pd.DataFrame(rows)


def residualize_bridge_features(
    windows: pd.DataFrame,
    features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Preserve participant means and person-centred mixed-model residuals."""
    output = windows.copy()
    diagnostics: list[dict[str, Any]] = []
    for feature in features:
        if feature not in output:
            continue
        usable = output.dropna(
            subset=[
                feature,
                "participant_id",
                "task_family",
                "condition",
                "session_number",
                "task_order",
                "time_on_task_fraction",
            ]
        ).copy()
        mean_column = f"{feature}_person_mean"
        residual_column = f"{feature}_within_residual"
        output[mean_column] = output.groupby("participant_id")[feature].transform(
            "mean"
        )
        output[residual_column] = np.nan
        if len(usable) < 30 or usable["participant_id"].nunique() < 3:
            diagnostics.append(
                {
                    "feature": feature,
                    "status": "not_testable",
                    "reason": "insufficient rows or participants",
                }
            )
            continue
        formula = (
            f"{feature} ~ C(task_family) + C(condition) + "
            "C(session_number) + task_order + time_on_task_fraction"
        )
        try:
            if usable["participant_id"].nunique() < 8:
                raise RuntimeError(
                    "MixedLM reserved for at least eight participants"
                )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = smf.mixedlm(
                    formula,
                    usable,
                    groups=usable["participant_id"],
                ).fit(reml=True, method="lbfgs", disp=False)
            if not model.converged:
                raise RuntimeError("MixedLM did not converge")
            covariance = np.asarray(model.cov_re, dtype=float)
            if (
                not np.isfinite(covariance).all()
                or np.min(np.linalg.eigvalsh(covariance)) <= 1e-8
            ):
                raise RuntimeError("MixedLM random effect is singular")
            residuals = model.resid
            status = "mixedlm"
        except Exception:
            model = smf.ols(
                formula + " + C(participant_id)",
                usable,
            ).fit()
            residuals = model.resid
            status = "participant_fixed_effect_fallback"
        centred = residuals - residuals.groupby(
            usable["participant_id"]
        ).transform("mean")
        output.loc[usable.index, residual_column] = centred
        diagnostics.append(
            {
                "feature": feature,
                "status": status,
                "n_windows": int(len(usable)),
                "n_participants": int(usable["participant_id"].nunique()),
            }
        )
    return output, pd.DataFrame(diagnostics)


def trait_state_decomposition(
    windows: pd.DataFrame,
    features: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for feature in features:
        if feature not in windows:
            continue
        frame = windows[["participant_id", feature]].dropna()
        if len(frame) < 5:
            continue
        person_means = frame.groupby("participant_id")[feature].mean()
        grand_mean = float(frame[feature].mean())
        between = float(np.mean((person_means - grand_mean) ** 2))
        within = float(
            frame.assign(
                person_mean=frame["participant_id"].map(person_means)
            )
            .eval(f"({feature} - person_mean) ** 2")
            .mean()
        )
        total = between + within
        rows.append(
            {
                "feature": feature,
                "between_person_variance_proxy": between,
                "within_person_variance_proxy": within,
                "between_fraction": between / total if total > 0 else np.nan,
                "within_fraction": within / total if total > 0 else np.nan,
                "n_windows": int(len(frame)),
                "n_participants": int(frame["participant_id"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def _parallel_factor_count(
    matrix: np.ndarray,
    maximum: int,
    seed: int,
    repetitions: int = 100,
) -> int:
    observed = PCA().fit(matrix).explained_variance_
    rng = np.random.default_rng(seed)
    random_eigenvalues = []
    for _ in range(repetitions):
        random = np.column_stack(
            [rng.permutation(matrix[:, column]) for column in range(matrix.shape[1])]
        )
        random_eigenvalues.append(PCA().fit(random).explained_variance_)
    threshold = np.quantile(np.asarray(random_eigenvalues), 0.95, axis=0)
    count = int(np.sum(observed[:maximum] > threshold[:maximum]))
    return max(1, min(maximum, count))


def fit_autonomic_dimensions(
    windows: pd.DataFrame,
    features: list[str],
    mode: str,
    maximum_factors: int,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    available = [
        feature
        for feature in features
        if feature in windows and windows[feature].notna().mean() >= 0.80
    ]
    if len(available) < 3:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {"status": "not_testable", "reason": "fewer than three HRV features"},
        )
    if mode == "between":
        source = windows.groupby("participant_id")[available].mean()
        identifiers = source.index.astype(str)
    elif mode == "within":
        source = windows[["participant_id", *available]].dropna().copy()
        source[available] = source[available] - source.groupby(
            "participant_id"
        )[available].transform("mean")
        identifiers = source.index.astype(str)
        source = source[available]
    else:
        raise ValueError("mode must be between or within")
    if len(source) < max(8, len(available) + 1):
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {
                "status": "not_testable",
                "reason": "insufficient complete observations",
                "n_observations": int(len(source)),
            },
        )
    scaled = StandardScaler().fit_transform(source)
    count = _parallel_factor_count(
        scaled,
        maximum=min(maximum_factors, len(available)),
        seed=seed,
    )
    pca = PCA(n_components=count, random_state=seed)
    scores = pca.fit_transform(scaled)
    loading_rows = []
    for component in range(count):
        for feature, loading in zip(
            available,
            pca.components_[component],
            strict=True,
        ):
            loading_rows.append(
                {
                    "mode": mode,
                    "component": component + 1,
                    "feature": feature,
                    "loading": float(loading),
                    "explained_variance_ratio": float(
                        pca.explained_variance_ratio_[component]
                    ),
                }
            )
    score_frame = pd.DataFrame(
        scores,
        columns=[
            f"ans_{mode}_component_{index + 1}" for index in range(count)
        ],
    )
    score_frame.insert(0, "row_id", identifiers.to_numpy())
    return (
        pd.DataFrame(loading_rows),
        score_frame,
        {
            "status": "ok",
            "mode": mode,
            "n_factors": count,
            "n_observations": int(len(source)),
            "features": available,
        },
    )


def add_loading_stability(
    loadings: pd.DataFrame,
    windows: pd.DataFrame,
    features: list[str],
    mode: str,
    repetitions: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """Add participant-bootstrap Tucker congruence to PCA loadings."""
    if loadings.empty or windows["participant_id"].nunique() < 5:
        return loadings
    components = sorted(loadings["component"].unique())
    baseline = (
        loadings.pivot(
            index="feature",
            columns="component",
            values="loading",
        )
        .loc[features, components]
        .to_numpy()
    )
    participants = windows["participant_id"].dropna().unique()
    rng = np.random.default_rng(seed)
    congruence: dict[int, list[float]] = {
        component: [] for component in components
    }
    for _ in range(repetitions):
        sampled = rng.choice(participants, size=len(participants), replace=True)
        pieces = []
        for copy_index, participant in enumerate(sampled):
            piece = windows.loc[
                windows["participant_id"].eq(participant),
                ["participant_id", *features],
            ].copy()
            piece["participant_id"] = f"{participant}:boot{copy_index}"
            pieces.append(piece)
        bootstrap = pd.concat(pieces, ignore_index=True)
        if mode == "between":
            source = bootstrap.groupby("participant_id")[features].mean()
        else:
            source = bootstrap.dropna(subset=features).copy()
            source[features] = source[features] - source.groupby(
                "participant_id"
            )[features].transform("mean")
            source = source[features]
        if len(source) <= len(components):
            continue
        scaled = StandardScaler().fit_transform(source)
        candidate = PCA(
            n_components=len(components),
            random_state=seed,
        ).fit(scaled).components_.T
        similarity = np.abs(baseline.T @ candidate)
        baseline_norm = np.linalg.norm(baseline, axis=0)
        candidate_norm = np.linalg.norm(candidate, axis=0)
        similarity = similarity / np.outer(baseline_norm, candidate_norm)
        base_index, candidate_index = linear_sum_assignment(-similarity)
        for left, right in zip(base_index, candidate_index, strict=True):
            congruence[components[left]].append(
                float(similarity[left, right])
            )
    stability_rows = []
    for component in components:
        values = np.asarray(congruence[component], dtype=float)
        stability_rows.append(
            {
                "component": component,
                "bootstrap_median_tucker_congruence": (
                    float(np.median(values)) if len(values) else np.nan
                ),
                "bootstrap_p05_tucker_congruence": (
                    float(np.quantile(values, 0.05)) if len(values) else np.nan
                ),
                "bootstrap_repetitions_completed": int(len(values)),
                "stable_tucker_ge_0_85": bool(
                    len(values)
                    and np.median(values) >= 0.85
                    and np.quantile(values, 0.05) >= 0.85
                ),
            }
        )
    return loadings.merge(
        pd.DataFrame(stability_rows),
        on="component",
        how="left",
    )


def shared_variance_pls(
    windows: pd.DataFrame,
    hrv_features: list[str],
    cognitive_features: list[str],
    seed: int = 42,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for task_family, task_frame in windows.groupby("task_family"):
        hrv = [
            feature
            for feature in hrv_features
            if feature in task_frame
            and task_frame[feature].notna().mean() >= 0.80
        ]
        cognitive = [
            feature
            for feature in cognitive_features
            if feature in task_frame
            and task_frame[feature].notna().mean() >= 0.50
        ]
        usable = task_frame.dropna(
            subset=["participant_id", *hrv, *cognitive]
        ).copy()
        n_participants = usable["participant_id"].nunique()
        if len(hrv) < 2 or len(cognitive) < 2 or n_participants < 5:
            rows.append(
                {
                    "status": "not_testable",
                    "task_family": task_family,
                    "reason": (
                        "insufficient complete task-specific features "
                        "or participants"
                    ),
                    "n_windows": int(len(usable)),
                    "n_participants": int(n_participants),
                }
            )
            continue
        x = StandardScaler().fit_transform(usable[hrv])
        y = StandardScaler().fit_transform(usable[cognitive])
        groups = usable["participant_id"].astype(str).to_numpy()
        folds = min(5, n_participants)
        splitter = GroupKFold(n_splits=folds)
        predictions = np.full_like(y, np.nan)
        for train, test in splitter.split(x, y, groups):
            component_count = min(
                2,
                len(hrv),
                len(cognitive),
                len(train) - 1,
            )
            model = PLSRegression(
                n_components=component_count,
                scale=False,
            )
            model.fit(x[train], y[train])
            predictions[test] = model.predict(x[test])
        rows.append(
            {
                "status": "ok",
                "task_family": task_family,
                "analysis": "participant_grouped_task_specific_pls",
                "out_of_participant_multivariate_r2": float(
                    r2_score(
                        y,
                        predictions,
                        multioutput="variance_weighted",
                    )
                ),
                "n_windows": int(len(usable)),
                "n_participants": int(n_participants),
                "folds": folds,
                "hrv_features": "|".join(hrv),
                "cognitive_features": "|".join(cognitive),
                "seed": seed,
            }
        )
    return pd.DataFrame(rows)


def add_next_window_targets(windows: pd.DataFrame) -> pd.DataFrame:
    output = windows.copy()
    primary = output["window_label"].eq("120")
    sort_columns = ["participant_id", "session_id", "task", "window_index"]
    ordered = output.loc[primary].sort_values(sort_columns, kind="stable")
    targets = {
        "pvt_lapse_rate": "next_pvt_lapse_rate",
        "pvt_median_rt_ms": "next_pvt_median_rt_ms",
        "flanker_accuracy": "next_flanker_accuracy",
        "flanker_median_rt_ms": "next_flanker_median_rt_ms",
        "nback_accuracy": "next_nback_accuracy",
        "nback_throughput": "next_nback_throughput",
        "matb_efficacy_raw": "next_matb_efficacy_raw",
    }
    group_columns = ["participant_id", "session_id", "task", "block_id"]
    for source, target in targets.items():
        output[target] = np.nan
        if source in ordered:
            shifted = ordered.groupby(group_columns)[source].shift(-1)
            output.loc[ordered.index, target] = shifted
    return output


def incremental_prediction(
    windows: pd.DataFrame,
    hrv_features: list[str],
    cognitive_features: list[str],
    folds: int = 5,
) -> pd.DataFrame:
    frame = add_next_window_targets(windows)
    targets = [
        column for column in frame.columns if column.startswith("next_")
    ]
    if "rsme" in frame and frame["rsme"].notna().any():
        targets.append("rsme")
    cognitive_columns = [
        feature for feature in cognitive_features if feature in frame
    ]
    if cognitive_columns:
        frame["cognitive_residual_magnitude"] = np.sqrt(
            frame[cognitive_columns].pow(2).mean(axis=1)
        )
    else:
        frame["cognitive_residual_magnitude"] = np.nan
    hr_column = next(
        (
            feature
            for feature in hrv_features
            if feature.startswith("mean_hr_bpm")
        ),
        None,
    )
    rmssd_column = next(
        (
            feature
            for feature in hrv_features
            if feature.startswith("log_rmssd")
        ),
        None,
    )
    if hr_column and rmssd_column:
        frame["autonomic_activation_residual"] = (
            pd.to_numeric(frame[hr_column], errors="coerce")
            - pd.to_numeric(frame[rmssd_column], errors="coerce")
        )
    else:
        frame["autonomic_activation_residual"] = np.nan
    frame["mind_body_divergence_magnitude"] = (
        frame["cognitive_residual_magnitude"]
        - frame["autonomic_activation_residual"].abs()
    ).abs()
    frame["mind_body_coupling_product"] = (
        frame["cognitive_residual_magnitude"]
        * frame["autonomic_activation_residual"]
    )
    divergence_features = [
        "cognitive_residual_magnitude",
        "autonomic_activation_residual",
        "mind_body_divergence_magnitude",
        "mind_body_coupling_product",
    ]
    base_numeric = ["task_order", "time_on_task_fraction", "session_number"]
    base_categorical = ["task_family", "condition"]
    model_features = {
        "A": base_numeric,
        "B": base_numeric + cognitive_features,
        "C": base_numeric + hrv_features,
        "D": base_numeric + cognitive_features + hrv_features,
        "E": (
            base_numeric
            + cognitive_features
            + hrv_features
            + divergence_features
        ),
    }
    rows: list[dict[str, Any]] = []
    for target in targets:
        target_rows = frame[target].notna()
        for name, features in model_features.items():
            numeric = [
                feature
                for feature in features
                if feature in frame and feature != target
                and frame.loc[target_rows, feature].notna().mean() >= 0.20
            ]
            metrics = grouped_ridge_metrics(
                frame,
                numeric_features=numeric,
                categorical_features=base_categorical,
                target=target,
                group_column="participant_id",
                folds=folds,
            )
            rows.append(
                {
                    "target": target,
                    "model": name,
                    **metrics,
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    baseline = result.loc[result["model"].eq("B"), ["target", "r2"]].rename(
        columns={"r2": "model_b_r2"}
    )
    result = result.merge(baseline, on="target", how="left")
    result["delta_r2_vs_b"] = result["r2"] - result["model_b_r2"]
    result["formal_incremental_inference_status"] = np.where(
        result["n_subjects"].fillna(0).ge(8),
        "eligible_for_participant_permutation",
        "pilot_descriptive_only_fewer_than_8_participants",
    )
    return result


def negative_control_prediction(
    windows: pd.DataFrame,
    hrv_features: list[str],
    cognitive_features: list[str],
    seed: int = 42,
) -> pd.DataFrame:
    aligned = incremental_prediction(
        windows,
        hrv_features,
        cognitive_features,
    )
    rng = np.random.default_rng(seed)
    shuffled = windows.copy()
    for _, index in shuffled.groupby(
        ["participant_id", "session_id", "task"],
        dropna=False,
    ).groups.items():
        order = np.asarray(list(index), dtype=int)
        permuted = rng.permutation(order)
        shuffled.loc[order, hrv_features] = (
            shuffled.loc[permuted, hrv_features].to_numpy()
        )
    control = incremental_prediction(
        shuffled,
        hrv_features,
        cognitive_features,
    )
    keep = ["target", "model", "status", "r2", "n_windows", "n_subjects"]
    aligned = aligned[keep].assign(control="temporally_aligned")
    control = control[keep].assign(control="within_task_shuffled_ecg")
    return pd.concat([aligned, control], ignore_index=True)


def divergence_profiles(windows: pd.DataFrame) -> pd.DataFrame:
    required = [
        "participant_id",
        "session_id",
        "task_family",
        "mean_hr_bpm",
        "log_rmssd",
    ]
    if any(column not in windows for column in required):
        return pd.DataFrame()
    frame = windows.loc[windows["window_label"].eq("120")].copy()
    performance_candidates = [
        feature for feature in COGNITIVE_FEATURES if feature in frame
    ]
    if not performance_candidates:
        return pd.DataFrame()
    performance = frame[performance_candidates].copy()
    for column in performance:
        if any(
            token in column
            for token in ("error", "lapse", "rt_ms", "tracking", "monitoring")
        ):
            performance[column] = -pd.to_numeric(
                performance[column],
                errors="coerce",
            )
    frame["cognitive_efficacy"] = performance.rank(pct=True).mean(axis=1)
    frame["autonomic_load"] = (
        frame["mean_hr_bpm"].rank(pct=True)
        + (-frame["log_rmssd"]).rank(pct=True)
    ) / 2
    frame["divergence_profile"] = "concordant_midrange"
    frame.loc[
        frame["cognitive_efficacy"].ge(0.67)
        & frame["autonomic_load"].ge(0.67),
        "divergence_profile",
    ] = "effective_cognition_elevated_autonomic_load"
    frame.loc[
        frame["cognitive_efficacy"].le(0.33)
        & frame["autonomic_load"].le(0.33),
        "divergence_profile",
    ] = "poor_cognition_preserved_autonomic_regulation"
    frame.loc[
        frame["task_family"].eq("PVT")
        & frame.get("pvt_lapse_rate", pd.Series(index=frame.index)).ge(
            frame.get("pvt_lapse_rate", pd.Series(index=frame.index)).quantile(
                0.67
            )
        )
        & frame["mean_hr_bpm"].le(frame["mean_hr_bpm"].quantile(0.33)),
        "divergence_profile",
    ] = "low_vigilance_low_cardiac_activation"
    frame.loc[
        frame.get(
            "flanker_fast_error_rate",
            pd.Series(index=frame.index),
        ).ge(
            frame.get(
                "flanker_fast_error_rate",
                pd.Series(index=frame.index),
            ).quantile(0.67)
        )
        & frame["autonomic_load"].ge(0.67),
        "divergence_profile",
    ] = "fast_error_prone_elevated_activation"
    return frame[
        [
            "window_id",
            "participant_id",
            "session_id",
            "task",
            "cognitive_efficacy",
            "autonomic_load",
            "divergence_profile",
        ]
    ]


def lagged_associations(windows: pd.DataFrame) -> pd.DataFrame:
    frame = add_next_window_targets(windows)
    rows: list[dict[str, Any]] = []
    hrv = [feature for feature in PRIMARY_HRV_FEATURES if feature in frame]
    targets = [
        column for column in frame if column.startswith("next_")
    ]
    for feature in hrv:
        for target in targets:
            usable = frame[[feature, target]].dropna()
            if len(usable) < 20:
                continue
            rows.append(
                {
                    "predictor": feature,
                    "next_window_outcome": target,
                    "spearman_r": float(
                        spearmanr(usable[feature], usable[target]).statistic
                    ),
                    "n_windows": int(len(usable)),
                    "interpretation": "temporal_association_not_causality",
                }
            )
    return pd.DataFrame(rows)
