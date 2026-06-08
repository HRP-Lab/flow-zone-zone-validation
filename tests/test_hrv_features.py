from __future__ import annotations

import numpy as np

from flowzone_validation.hrv_features import (
    PeakDetection,
    correct_rr_intervals,
    hrv_features_from_peaks,
    interval_window_bounds,
    peak_concordance_for_window,
    sample_entropy,
)


def test_rr_correction_flags_physiological_and_isolated_intervals() -> None:
    rr = np.array([800, 805, 250, 810, 1300, 815, 820], dtype=float)
    corrected = correct_rr_intervals(rr)

    assert corrected.physiological_invalid_mask[2]
    assert corrected.isolated_outlier_mask[4]
    assert 750 < corrected.rr_ms[2] < 900
    assert 750 < corrected.rr_ms[4] < 900
    assert corrected.corrected_fraction == 2 / 7


def test_peak_concordance_is_window_specific() -> None:
    detection = PeakDetection(
        primary=np.array([100, 500, 900, 1300]),
        sensitivity=np.array([105, 495, 905, 1500]),
        matched=3,
        concordance=0.75,
        unmatched_rate=0.25,
    )

    concordance, unmatched = peak_concordance_for_window(
        detection,
        start_sample=0,
        stop_sample=1000,
        sampling_rate=500,
    )

    assert concordance == 1.0
    assert unmatched == 0.0


def test_interval_windows_do_not_cross_block_end() -> None:
    bounds = interval_window_bounds(250.0, 120)

    assert bounds == [(0, 0.0, 120.0), (1, 120.0, 240.0)]
    assert all(stop <= 250 for _, _, stop in bounds)
    assert interval_window_bounds(250.0, "full") == [(0, 0.0, 250.0)]


def test_hrv_feature_edge_cases_and_quality_gate() -> None:
    sampling_rate = 500
    peak_samples = np.arange(0, 130 * sampling_rate, 500)
    result = hrv_features_from_peaks(
        peak_samples,
        sampling_rate,
        0,
        120 * sampling_rate,
        detector_concordance=1.0,
        detector_unmatched_rate=0.0,
    )

    assert result["ecg_quality_pass"]
    assert result["mean_hr_bpm"] == 60.0
    assert np.isnan(result["log_rmssd"])
    assert np.isnan(sample_entropy(np.ones(30)))
