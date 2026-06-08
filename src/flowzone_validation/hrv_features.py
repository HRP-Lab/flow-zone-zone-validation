"""Short-window ECG quality control and RR/HRV feature extraction."""

from __future__ import annotations

from dataclasses import dataclass
from math import factorial

import neurokit2 as nk
import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, sosfiltfilt

from .cognitive_features import (
    dfa_alpha,
    lag_correlation,
    permutation_entropy_3,
    roughness,
    sign_change_rate,
)


@dataclass(frozen=True)
class PeakDetection:
    primary: np.ndarray
    sensitivity: np.ndarray
    matched: int
    concordance: float
    unmatched_rate: float


@dataclass(frozen=True)
class RRCorrection:
    rr_ms: np.ndarray
    corrected_mask: np.ndarray
    physiological_invalid_mask: np.ndarray
    isolated_outlier_mask: np.ndarray

    @property
    def corrected_fraction(self) -> float:
        if len(self.rr_ms) == 0:
            return float("nan")
        return float(np.mean(self.corrected_mask))


def filter_ecg(
    signal: np.ndarray,
    sampling_rate: float,
    low_hz: float = 0.5,
    high_hz: float = 40.0,
    notch_hz: float | None = 50.0,
) -> np.ndarray:
    """Band-pass and optionally notch-filter a continuous ECG signal."""
    values = np.asarray(signal, dtype=float)
    if values.ndim != 1:
        raise ValueError("ECG signal must be one-dimensional")
    if len(values) < int(sampling_rate * 5):
        raise ValueError("ECG signal is too short for stable filtering")
    sos = butter(
        4,
        [low_hz, high_hz],
        btype="bandpass",
        fs=sampling_rate,
        output="sos",
    )
    filtered = sosfiltfilt(sos, values)
    if notch_hz is not None and notch_hz < sampling_rate / 2:
        numerator, denominator = iirnotch(
            notch_hz,
            Q=30,
            fs=sampling_rate,
        )
        filtered = filtfilt(numerator, denominator, filtered)
    return filtered


def _match_peaks(
    primary: np.ndarray,
    sensitivity: np.ndarray,
    tolerance_samples: int,
) -> int:
    left = np.asarray(primary, dtype=int)
    right = np.asarray(sensitivity, dtype=int)
    i = 0
    j = 0
    matches = 0
    while i < len(left) and j < len(right):
        difference = int(left[i] - right[j])
        if abs(difference) <= tolerance_samples:
            matches += 1
            i += 1
            j += 1
        elif difference < 0:
            i += 1
        else:
            j += 1
    return matches


def detect_r_peaks(
    filtered_ecg: np.ndarray,
    sampling_rate: float,
    tolerance_ms: float = 80.0,
) -> PeakDetection:
    """Run NeuroKit and Pan-Tompkins detectors and quantify agreement."""
    primary_info = nk.ecg_peaks(
        filtered_ecg,
        sampling_rate=sampling_rate,
        method="neurokit",
        correct_artifacts=False,
    )[1]
    sensitivity_info = nk.ecg_peaks(
        filtered_ecg,
        sampling_rate=sampling_rate,
        method="pantompkins1985",
        correct_artifacts=False,
    )[1]
    primary = np.asarray(primary_info["ECG_R_Peaks"], dtype=int)
    sensitivity = np.asarray(
        sensitivity_info["ECG_R_Peaks"],
        dtype=int,
    )
    denominator = max(len(primary), len(sensitivity))
    matched = _match_peaks(
        primary,
        sensitivity,
        tolerance_samples=max(1, round(tolerance_ms * sampling_rate / 1000)),
    )
    concordance = matched / denominator if denominator else float("nan")
    return PeakDetection(
        primary=primary,
        sensitivity=sensitivity,
        matched=matched,
        concordance=float(concordance),
        unmatched_rate=(
            float(1 - concordance)
            if np.isfinite(concordance)
            else float("nan")
        ),
    )


def peak_concordance_for_window(
    detection: PeakDetection,
    start_sample: int,
    stop_sample: int,
    sampling_rate: float,
    tolerance_ms: float = 80.0,
) -> tuple[float, float]:
    primary = detection.primary[
        (detection.primary >= start_sample)
        & (detection.primary < stop_sample)
    ]
    sensitivity = detection.sensitivity[
        (detection.sensitivity >= start_sample)
        & (detection.sensitivity < stop_sample)
    ]
    denominator = max(len(primary), len(sensitivity))
    if denominator == 0:
        return float("nan"), float("nan")
    matched = _match_peaks(
        primary,
        sensitivity,
        max(1, round(tolerance_ms * sampling_rate / 1000)),
    )
    concordance = matched / denominator
    return float(concordance), float(1 - concordance)


def _rolling_local_median(values: np.ndarray, index: int) -> float:
    start = max(0, index - 3)
    stop = min(len(values), index + 4)
    neighbours = np.delete(values[start:stop], index - start)
    neighbours = neighbours[np.isfinite(neighbours)]
    return float(np.median(neighbours)) if len(neighbours) else float("nan")


def correct_rr_intervals(
    rr_ms: np.ndarray,
    minimum_ms: float = 300.0,
    maximum_ms: float = 2000.0,
    relative_threshold: float = 0.20,
) -> RRCorrection:
    """Correct isolated implausible intervals using a local-median rule."""
    original = np.asarray(rr_ms, dtype=float)
    corrected = original.copy()
    physiological = (
        ~np.isfinite(original)
        | (original < minimum_ms)
        | (original > maximum_ms)
    )
    physiological_clean = original.copy()
    physiological_clean[physiological] = np.nan
    isolated = np.zeros(len(original), dtype=bool)
    for index, value in enumerate(original):
        local_median = _rolling_local_median(
            physiological_clean,
            index,
        )
        if not np.isfinite(local_median) or local_median <= 0:
            continue
        if np.isfinite(value) and abs(value - local_median) > (
            relative_threshold * local_median
        ):
            isolated[index] = True
    replace = physiological | isolated
    for index in np.flatnonzero(replace):
        replacement = _rolling_local_median(
            physiological_clean,
            int(index),
        )
        corrected[index] = replacement
    return RRCorrection(
        rr_ms=corrected,
        corrected_mask=replace,
        physiological_invalid_mask=physiological,
        isolated_outlier_mask=isolated,
    )


def sample_entropy(
    values: np.ndarray,
    embedding_dimension: int = 2,
    tolerance_fraction: float = 0.2,
) -> float:
    """Return sample entropy for a short RR sequence."""
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if len(series) < 20 or np.std(series, ddof=1) == 0:
        return float("nan")
    tolerance = tolerance_fraction * np.std(series, ddof=1)

    def count_matches(dimension: int) -> int:
        vectors = np.asarray(
            [
                series[index : index + dimension]
                for index in range(len(series) - dimension + 1)
            ]
        )
        count = 0
        for index in range(len(vectors) - 1):
            distances = np.max(
                np.abs(vectors[index + 1 :] - vectors[index]),
                axis=1,
            )
            count += int(np.sum(distances <= tolerance))
        return count

    matches_m = count_matches(embedding_dimension)
    matches_next = count_matches(embedding_dimension + 1)
    if matches_m == 0 or matches_next == 0:
        return float("nan")
    return float(-np.log(matches_next / matches_m))


def difference_entropy(values: np.ndarray, bins: int = 12) -> float:
    differences = np.diff(np.asarray(values, dtype=float))
    differences = differences[np.isfinite(differences)]
    if len(differences) < 10 or np.std(differences) == 0:
        return float("nan")
    counts, _ = np.histogram(differences, bins=bins)
    probabilities = counts[counts > 0] / counts.sum()
    return float(
        -np.sum(probabilities * np.log(probabilities))
        / np.log(min(bins, factorial(3) * 2))
    )


def _linear_slope(values: np.ndarray, time_seconds: np.ndarray) -> float:
    valid = np.isfinite(values) & np.isfinite(time_seconds)
    if valid.sum() < 3 or np.std(time_seconds[valid]) == 0:
        return float("nan")
    return float(np.polyfit(time_seconds[valid], values[valid], 1)[0])


def hrv_features_from_peaks(
    peak_samples: np.ndarray,
    sampling_rate: float,
    start_sample: int,
    stop_sample: int,
    detector_concordance: float,
    detector_unmatched_rate: float,
    minimum_beats: int = 30,
    maximum_corrected_fraction: float = 0.05,
) -> dict[str, float | int | bool | str]:
    """Calculate time-domain and candidate dynamics features for one window."""
    peaks = np.asarray(peak_samples, dtype=int)
    selected = peaks[
        (peaks >= int(start_sample)) & (peaks < int(stop_sample))
    ]
    duration_seconds = (stop_sample - start_sample) / sampling_rate
    if len(selected) < 2:
        return {
            "n_beats": int(len(selected)),
            "valid_duration_seconds": float(duration_seconds),
            "ecg_quality_pass": False,
            "ecg_quality_reason": "fewer than two detected beats",
            "detector_concordance": detector_concordance,
            "detector_unmatched_rate": detector_unmatched_rate,
        }
    rr_raw = np.diff(selected) / sampling_rate * 1000.0
    correction = correct_rr_intervals(rr_raw)
    rr = correction.rr_ms
    valid = np.isfinite(rr)
    valid_rr = rr[valid]
    valid_fraction = float(valid.sum() / len(rr)) if len(rr) else 0.0
    reasons: list[str] = []
    if len(selected) < minimum_beats:
        reasons.append("insufficient beats")
    if correction.corrected_fraction > maximum_corrected_fraction:
        reasons.append("more than 5% RR intervals corrected")
    if valid_fraction < 0.95:
        reasons.append("less than 95% valid RR intervals")
    quality_pass = not reasons
    output: dict[str, float | int | bool | str] = {
        "n_beats": int(len(selected)),
        "valid_duration_seconds": float(duration_seconds),
        "valid_rr_fraction": valid_fraction,
        "rr_corrected_fraction": correction.corrected_fraction,
        "rr_physiological_invalid_fraction": float(
            np.mean(correction.physiological_invalid_mask)
        ),
        "rr_isolated_outlier_fraction": float(
            np.mean(correction.isolated_outlier_mask)
        ),
        "detector_concordance": detector_concordance,
        "detector_unmatched_rate": detector_unmatched_rate,
        "detector_disagreement_flag": bool(detector_unmatched_rate > 0.01),
        "ecg_quality_pass": quality_pass,
        "ecg_quality_reason": "|".join(reasons) if reasons else "ok",
    }
    feature_names = (
        "mean_hr_bpm",
        "mean_nn_ms",
        "log_rmssd",
        "sdnn_ms",
        "cvnn",
        "pnn20",
        "pnn50",
        "sd1_ms",
        "sd2_ms",
        "sd1_sd2",
        "hr_slope_bpm_per_min",
        "nn_slope_ms_per_min",
        "hrv_dfa_alpha1",
        "hrv_lag1",
        "hrv_roughness",
        "hrv_sign_change",
        "hrv_perm_entropy3",
        "hrv_difference_entropy",
        "hrv_sample_entropy",
    )
    if len(valid_rr) < 2:
        output.update({name: float("nan") for name in feature_names})
        return output

    differences = np.diff(valid_rr)
    mean_nn = float(np.mean(valid_rr))
    mean_hr = float(60000.0 / mean_nn)
    rmssd = float(np.sqrt(np.mean(differences**2)))
    sdnn = float(np.std(valid_rr, ddof=1))
    sd1 = float(rmssd / np.sqrt(2))
    sd2_squared = 2 * sdnn**2 - 0.5 * rmssd**2
    sd2 = float(np.sqrt(sd2_squared)) if sd2_squared > 0 else float("nan")
    rr_times = (selected[1:] - start_sample) / sampling_rate
    instantaneous_hr = 60000.0 / valid_rr
    valid_times = rr_times[valid]
    output.update(
        {
            "mean_hr_bpm": mean_hr,
            "mean_nn_ms": mean_nn,
            "log_rmssd": float(np.log(rmssd)) if rmssd > 0 else float("nan"),
            "sdnn_ms": sdnn,
            "cvnn": float(sdnn / mean_nn) if mean_nn > 0 else float("nan"),
            "pnn20": float(np.mean(np.abs(differences) > 20)),
            "pnn50": float(np.mean(np.abs(differences) > 50)),
            "sd1_ms": sd1,
            "sd2_ms": sd2,
            "sd1_sd2": float(sd1 / sd2) if np.isfinite(sd2) else float("nan"),
            "hr_slope_bpm_per_min": (
                _linear_slope(instantaneous_hr, valid_times) * 60
            ),
            "nn_slope_ms_per_min": (
                _linear_slope(valid_rr, valid_times) * 60
            ),
            "hrv_dfa_alpha1": dfa_alpha(valid_rr),
            "hrv_lag1": lag_correlation(valid_rr, 1),
            "hrv_roughness": roughness(valid_rr),
            "hrv_sign_change": sign_change_rate(valid_rr),
            "hrv_perm_entropy3": permutation_entropy_3(valid_rr),
            "hrv_difference_entropy": difference_entropy(valid_rr),
            "hrv_sample_entropy": sample_entropy(valid_rr),
        }
    )
    return output


def interval_window_bounds(
    duration_seconds: float,
    window_seconds: int | str,
) -> list[tuple[int, float, float]]:
    """Return non-overlapping bounds that never extend past one task block."""
    if duration_seconds <= 0:
        return []
    if window_seconds == "full":
        return [(0, 0.0, float(duration_seconds))]
    length = int(window_seconds)
    if length <= 0:
        raise ValueError("Window duration must be positive")
    count = int(duration_seconds // length)
    return [
        (index, float(index * length), float((index + 1) * length))
        for index in range(count)
    ]
