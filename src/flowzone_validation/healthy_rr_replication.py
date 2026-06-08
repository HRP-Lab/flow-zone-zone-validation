"""Replication utilities for long-term beat-to-beat RR recordings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .hrv_features import correct_rr_intervals


REPLICATION_FEATURES = [
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
class RRFile:
    participant_id: str
    path: Path
    rr_ms: np.ndarray
    nonnumeric_rows: int
    blank_rows: int


def read_rr_file(path: Path | str) -> RRFile:
    """Read one RR interval per line while auditing malformed rows."""
    source = Path(path)
    values: list[float] = []
    nonnumeric = 0
    blank = 0
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.strip()
        if not value:
            blank += 1
            continue
        try:
            values.append(float(value))
        except ValueError:
            nonnumeric += 1
    if not values:
        raise ValueError(f"No numeric RR intervals found in {source}")
    return RRFile(
        participant_id=source.stem,
        path=source,
        rr_ms=np.asarray(values, dtype=float),
        nonnumeric_rows=nonnumeric,
        blank_rows=blank,
    )


def deterministic_window_indices(
    available_windows: int,
    maximum_windows: int | None,
) -> np.ndarray:
    """Select windows evenly across a recording without random sampling."""
    if available_windows <= 0:
        return np.asarray([], dtype=int)
    if maximum_windows is None or available_windows <= maximum_windows:
        return np.arange(available_windows, dtype=int)
    selected = np.linspace(
        0,
        available_windows - 1,
        num=maximum_windows,
        dtype=int,
    )
    return np.unique(selected)


def rr_window_slices(
    rr_ms: np.ndarray,
    window_seconds: int,
    maximum_windows: int | None = None,
) -> list[tuple[int, int, int, float, float]]:
    """Return RR index slices wholly contained in non-overlapping windows."""
    values = np.asarray(rr_ms, dtype=float)
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    finite_for_clock = np.where(np.isfinite(values) & (values > 0), values, 0.0)
    interval_ends = np.cumsum(finite_for_clock)
    total_seconds = float(interval_ends[-1] / 1000.0)
    available = int(total_seconds // window_seconds)
    selected = deterministic_window_indices(available, maximum_windows)
    rows: list[tuple[int, int, int, float, float]] = []
    for window_index in selected:
        start_ms = float(window_index * window_seconds * 1000)
        stop_ms = float((window_index + 1) * window_seconds * 1000)
        start_index = int(np.searchsorted(interval_ends, start_ms, side="right"))
        stop_index = int(np.searchsorted(interval_ends, stop_ms, side="right"))
        rows.append(
            (
                int(window_index),
                start_index,
                stop_index,
                start_ms / 1000.0,
                stop_ms / 1000.0,
            )
        )
    return rows


def _slope(values: np.ndarray, time_seconds: np.ndarray) -> float:
    valid = np.isfinite(values) & np.isfinite(time_seconds)
    if valid.sum() < 3 or np.std(time_seconds[valid]) == 0:
        return float("nan")
    return float(np.polyfit(time_seconds[valid], values[valid], 1)[0])


def time_domain_features_from_rr(
    rr_ms: np.ndarray,
    *,
    minimum_beats: int = 30,
    maximum_corrected_fraction: float = 0.05,
) -> dict[str, Any]:
    """Calculate the COG-BCI replication feature set from one RR window."""
    raw = np.asarray(rr_ms, dtype=float)
    correction = correct_rr_intervals(raw)
    corrected = correction.rr_ms
    valid = np.isfinite(corrected)
    rr = corrected[valid]
    valid_fraction = float(valid.mean()) if len(valid) else 0.0
    reasons: list[str] = []
    if len(rr) < minimum_beats:
        reasons.append("insufficient beats")
    if correction.corrected_fraction > maximum_corrected_fraction:
        reasons.append("more than 5% RR intervals corrected")
    if valid_fraction < 0.95:
        reasons.append("less than 95% valid RR intervals")
    output: dict[str, Any] = {
        "n_intervals": int(len(raw)),
        "valid_rr_fraction": valid_fraction,
        "rr_corrected_fraction": correction.corrected_fraction,
        "rr_physiological_invalid_fraction": float(
            np.mean(correction.physiological_invalid_mask)
        ),
        "rr_isolated_outlier_fraction": float(
            np.mean(correction.isolated_outlier_mask)
        ),
        "quality_pass": not reasons,
        "quality_reason": "|".join(reasons) if reasons else "ok",
    }
    if len(rr) < 2:
        output.update({feature: np.nan for feature in REPLICATION_FEATURES})
        return output

    differences = np.diff(rr)
    mean_nn = float(np.mean(rr))
    rmssd = float(np.sqrt(np.mean(differences**2)))
    sdnn = float(np.std(rr, ddof=1))
    sd1 = rmssd / np.sqrt(2)
    sd2_squared = 2 * sdnn**2 - 0.5 * rmssd**2
    sd2 = float(np.sqrt(sd2_squared)) if sd2_squared > 0 else np.nan
    interval_times = np.cumsum(rr) / 1000.0
    instantaneous_hr = 60000.0 / rr
    output.update(
        {
            "mean_hr_bpm": float(60000.0 / mean_nn),
            "mean_nn_ms": mean_nn,
            "log_rmssd": float(np.log(rmssd)) if rmssd > 0 else np.nan,
            "sdnn_ms": sdnn,
            "cvnn": float(sdnn / mean_nn) if mean_nn > 0 else np.nan,
            "pnn20": float(np.mean(np.abs(differences) > 20)),
            "pnn50": float(np.mean(np.abs(differences) > 50)),
            "sd1_sd2": float(sd1 / sd2) if np.isfinite(sd2) else np.nan,
            "hr_slope_bpm_per_min": (
                _slope(instantaneous_hr, interval_times) * 60
            ),
            "nn_slope_ms_per_min": _slope(rr, interval_times) * 60,
        }
    )
    return output


def build_rr_windows(
    input_dir: Path | str,
    durations_seconds: Iterable[int] = (120, 180, 300),
    maximum_hours_per_duration: float = 8.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build participant-balanced HRV windows and a source inventory."""
    root = Path(input_dir)
    files = sorted(root.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt RR files found in {root}")
    window_rows: list[dict[str, Any]] = []
    inventory_rows: list[dict[str, Any]] = []
    for path in files:
        rr_file = read_rr_file(path)
        rr = rr_file.rr_ms
        inventory_rows.append(
            {
                "participant_id": rr_file.participant_id,
                "file_name": path.name,
                "n_numeric_intervals": int(len(rr)),
                "n_nonnumeric_rows": rr_file.nonnumeric_rows,
                "n_blank_rows": rr_file.blank_rows,
                "recording_hours": float(np.nansum(rr) / 3_600_000),
                "median_rr_ms": float(np.nanmedian(rr)),
                "mean_hr_bpm": float(60000 / np.nanmean(rr)),
                "physiological_invalid_rate": float(
                    np.mean(~np.isfinite(rr) | (rr < 300) | (rr > 2000))
                ),
                "minimum_rr_ms": float(np.nanmin(rr)),
                "maximum_rr_ms": float(np.nanmax(rr)),
            }
        )
        for duration in durations_seconds:
            maximum_windows = max(
                1,
                int(maximum_hours_per_duration * 3600 // int(duration)),
            )
            for (
                window_index,
                start_index,
                stop_index,
                start_seconds,
                stop_seconds,
            ) in rr_window_slices(rr, int(duration), maximum_windows):
                features = time_domain_features_from_rr(
                    rr[start_index:stop_index]
                )
                window_rows.append(
                    {
                        "participant_id": rr_file.participant_id,
                        "window_seconds": int(duration),
                        "window_index": int(window_index),
                        "start_seconds": start_seconds,
                        "stop_seconds": stop_seconds,
                        "source_start_interval": start_index,
                        "source_stop_interval": stop_index,
                        **features,
                    }
                )
    return pd.DataFrame(window_rows), pd.DataFrame(inventory_rows)


def person_center_features(
    windows: pd.DataFrame,
    features: list[str] = REPLICATION_FEATURES,
) -> pd.DataFrame:
    """Add person-centred feature columns without removing time structure."""
    output = windows.copy()
    for feature in features:
        output[f"{feature}_within"] = output[feature] - output.groupby(
            "participant_id"
        )[feature].transform("mean")
    return output


def parallel_factor_count(
    matrix: np.ndarray,
    maximum: int,
    seed: int = 42,
    repetitions: int = 100,
) -> int:
    """Select an exploratory component count using parallel analysis."""
    observed = PCA().fit(matrix).explained_variance_
    rng = np.random.default_rng(seed)
    random_eigenvalues = []
    for _ in range(repetitions):
        random = np.column_stack(
            [
                rng.permutation(matrix[:, column])
                for column in range(matrix.shape[1])
            ]
        )
        random_eigenvalues.append(PCA().fit(random).explained_variance_)
    threshold = np.quantile(np.asarray(random_eigenvalues), 0.95, axis=0)
    count = int(np.sum(observed[:maximum] > threshold[:maximum]))
    return max(1, min(maximum, count))


def fit_fixed_components(
    windows: pd.DataFrame,
    *,
    n_components: int = 3,
    features: list[str] = REPLICATION_FEATURES,
    seed: int = 42,
    calculate_parallel: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Fit a fixed component solution to person-centred healthy RR windows."""
    centred = person_center_features(windows, features)
    columns = [f"{feature}_within" for feature in features]
    usable = centred.dropna(subset=columns).copy()
    if usable["participant_id"].nunique() < 5:
        raise ValueError("At least five participants are required")
    scaled = StandardScaler().fit_transform(usable[columns])
    empirical_count = (
        parallel_factor_count(
            scaled,
            maximum=min(5, len(features)),
            seed=seed,
        )
        if calculate_parallel
        else None
    )
    pca = PCA(n_components=n_components, random_state=seed)
    scores = pca.fit_transform(scaled)
    loadings = pd.DataFrame(
        pca.components_.T,
        index=features,
        columns=[f"C{index + 1}" for index in range(n_components)],
    )
    loading_table = (
        loadings.rename_axis("feature")
        .reset_index()
        .melt(id_vars="feature", var_name="component", value_name="loading")
    )
    loading_table["component"] = (
        loading_table["component"].str.removeprefix("C").astype(int)
    )
    loading_table["explained_variance_ratio"] = loading_table[
        "component"
    ].map(
        {
            index + 1: float(value)
            for index, value in enumerate(pca.explained_variance_ratio_)
        }
    )
    score_table = usable[
        [
            "participant_id",
            "window_seconds",
            "window_index",
            "start_seconds",
        ]
    ].copy()
    for index in range(n_components):
        score_table[f"healthy_rr_component_{index + 1}"] = scores[:, index]
    return (
        loading_table,
        score_table,
        {
            "status": "ok",
            "n_windows": int(len(usable)),
            "n_participants": int(usable["participant_id"].nunique()),
            "fixed_components": n_components,
            "parallel_analysis_components": empirical_count,
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        },
    )


def loading_matrix(
    loadings: pd.DataFrame,
    features: list[str] = REPLICATION_FEATURES,
) -> np.ndarray:
    return (
        loadings.pivot(index="feature", columns="component", values="loading")
        .loc[features]
        .to_numpy()
    )


def match_loading_components(
    reference_loadings: pd.DataFrame,
    candidate_loadings: pd.DataFrame,
    features: list[str] = REPLICATION_FEATURES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match candidate components to a reference by absolute Tucker congruence."""
    reference = loading_matrix(reference_loadings, features)
    candidate = loading_matrix(candidate_loadings, features)
    similarity = reference.T @ candidate
    denominator = np.outer(
        np.linalg.norm(reference, axis=0),
        np.linalg.norm(candidate, axis=0),
    )
    similarity = similarity / denominator
    left, right = linear_sum_assignment(-np.abs(similarity))
    rows = []
    aligned = candidate.copy()
    for reference_index, candidate_index in zip(left, right, strict=True):
        signed = float(similarity[reference_index, candidate_index])
        sign = 1.0 if signed >= 0 else -1.0
        aligned[:, reference_index] = candidate[:, candidate_index] * sign
        rows.append(
            {
                "reference_component": int(reference_index + 1),
                "candidate_component": int(candidate_index + 1),
                "signed_tucker_congruence": signed,
                "absolute_tucker_congruence": abs(signed),
                "orientation_multiplier": sign,
            }
        )
    aligned_table = pd.DataFrame(
        aligned,
        index=features,
        columns=[index + 1 for index in range(aligned.shape[1])],
    )
    aligned_table = (
        aligned_table.rename_axis("feature")
        .reset_index()
        .melt(id_vars="feature", var_name="component", value_name="loading")
    )
    return pd.DataFrame(rows).sort_values("reference_component"), aligned_table


def loading_subspace_similarity(
    reference_loadings: pd.DataFrame,
    candidate_loadings: pd.DataFrame,
    features: list[str] = REPLICATION_FEATURES,
) -> pd.DataFrame:
    """Compare full and secondary loading subspaces using principal angles."""
    reference = loading_matrix(reference_loadings, features)
    candidate = loading_matrix(candidate_loadings, features)
    rows = []
    for scope, component_indices in (
        ("all_three_components", [0, 1, 2]),
        ("secondary_C2_C3_subspace", [1, 2]),
    ):
        reference_basis = np.linalg.qr(reference[:, component_indices])[0]
        candidate_basis = np.linalg.qr(candidate[:, component_indices])[0]
        canonical = np.linalg.svd(
            reference_basis.T @ candidate_basis,
            compute_uv=False,
        )
        angles = np.degrees(np.arccos(np.clip(canonical, -1, 1)))
        rows.append(
            {
                "scope": scope,
                "dimensions": len(component_indices),
                "minimum_canonical_similarity": float(np.min(canonical)),
                "mean_canonical_similarity": float(np.mean(canonical)),
                "maximum_principal_angle_degrees": float(np.max(angles)),
                "canonical_similarities": "|".join(
                    f"{value:.6f}" for value in canonical
                ),
            }
        )
    return pd.DataFrame(rows)


def reference_loadings_from_cog_bci(path: Path | str) -> pd.DataFrame:
    """Normalize the COG-BCI loading table to base feature names."""
    source = pd.read_csv(path)
    source = source[source["mode"].eq("within")].copy()
    source["feature"] = (
        source["feature"]
        .str.removesuffix("_within_residual")
        .str.removesuffix("_within")
    )
    return source[["feature", "component", "loading"]]


def bootstrap_loading_stability(
    windows: pd.DataFrame,
    baseline_loadings: pd.DataFrame,
    *,
    repetitions: int = 200,
    seed: int = 42,
) -> pd.DataFrame:
    """Bootstrap whole participants and compare with the baseline solution."""
    participants = windows["participant_id"].dropna().unique()
    rng = np.random.default_rng(seed)
    values: dict[int, list[float]] = {1: [], 2: [], 3: []}
    for repetition in range(repetitions):
        sampled = rng.choice(participants, size=len(participants), replace=True)
        pieces = []
        for copy_index, participant in enumerate(sampled):
            piece = windows[windows["participant_id"].eq(participant)].copy()
            piece["participant_id"] = (
                f"{participant}:bootstrap:{repetition}:{copy_index}"
            )
            pieces.append(piece)
        bootstrap = pd.concat(pieces, ignore_index=True)
        try:
            candidate, _, _ = fit_fixed_components(
                bootstrap,
                n_components=3,
                seed=seed,
                calculate_parallel=False,
            )
        except ValueError:
            continue
        matched, _ = match_loading_components(
            baseline_loadings,
            candidate,
        )
        for row in matched.itertuples():
            values[int(row.reference_component)].append(
                float(row.absolute_tucker_congruence)
            )
    return pd.DataFrame(
        [
            {
                "component": component,
                "bootstrap_median_tucker_congruence": float(
                    np.median(component_values)
                ),
                "bootstrap_p05_tucker_congruence": float(
                    np.quantile(component_values, 0.05)
                ),
                "bootstrap_repetitions_completed": len(component_values),
            }
            for component, component_values in values.items()
            if component_values
        ]
    )


def leave_one_participant_out_stability(
    windows: pd.DataFrame,
    baseline_loadings: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    rows = []
    for participant in sorted(windows["participant_id"].unique()):
        candidate, _, _ = fit_fixed_components(
            windows[~windows["participant_id"].eq(participant)],
            n_components=3,
            seed=seed,
            calculate_parallel=False,
        )
        matched, _ = match_loading_components(
            baseline_loadings,
            candidate,
        )
        for row in matched.itertuples():
            rows.append(
                {
                    "excluded_participant": participant,
                    "component": int(row.reference_component),
                    "absolute_tucker_congruence": float(
                        row.absolute_tucker_congruence
                    ),
                }
            )
    return pd.DataFrame(rows)


def stationary_sensitivity_subset(windows: pd.DataFrame) -> pd.DataFrame:
    """Return a transparent low-trend sensitivity subset, not confirmed rest."""
    return windows[
        windows["quality_pass"]
        & windows["mean_hr_bpm"].between(45, 100)
        & windows["rr_corrected_fraction"].le(0.01)
        & windows["hr_slope_bpm_per_min"].abs().le(3.0)
    ].copy()
