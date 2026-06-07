from dataclasses import replace

import numpy as np
import pandas as pd

from flowzone_validation.cleaning import flag_trials
from flowzone_validation.cognitive_features import build_window_features
from flowzone_validation.prediction import grouped_ridge_metrics
from flowzone_validation.residualisation import residualise_trial_rt
from flowzone_validation.config import ZhangTangConfig
from flowzone_validation.zhang_tang import (
    bias_corrected_mutual_information,
    build_zhang_tang_windows,
    discrete_mutual_information_bits,
    upper_tail_rate,
)


def _followup_fixture(make_trials_fixture):
    trials = make_trials_fixture(
        datasets=2,
        participants=4,
        blocks=1,
        trials_per_block=260,
    )
    from flowzone_validation.config import PilotConfig

    pilot = replace(
        PilotConfig(),
        minimum_condition_trials=2,
        minimum_pes_post_error_trials=2,
        minimum_pes_post_correct_trials=2,
    )
    flagged = flag_trials(trials, pilot)
    residualized = residualise_trial_rt(flagged)
    windows = build_window_features(
        residualized[residualized["analysis_eligible_trial"]].copy(),
        pilot,
    )
    config = replace(
        ZhangTangConfig(),
        mi_permutations=3,
        minimum_mi_observations=20,
        minimum_mi_class_count=2,
        bootstrap_repetitions=10,
    )
    return residualized, windows, config


def test_discrete_mutual_information_detects_dependency():
    independent_left = pd.Series([0, 0, 1, 1] * 20)
    independent_right = pd.Series([0, 1, 0, 1] * 20)
    dependent_right = independent_left.copy()
    assert discrete_mutual_information_bits(
        independent_left,
        dependent_right,
    ) > 0.9
    assert discrete_mutual_information_bits(
        independent_left,
        independent_right,
    ) < 1e-9


def test_bias_corrected_mi_reports_sparse_classes():
    config = replace(
        ZhangTangConfig(),
        mi_permutations=2,
        minimum_mi_observations=10,
        minimum_mi_class_count=3,
    )
    value, reason = bias_corrected_mutual_information(
        pd.Series([0] * 19 + [1]),
        pd.Series([0, 1] * 10),
        config,
        seed=42,
    )
    assert np.isnan(value)
    assert reason == "sparse_left_class"


def test_upper_tail_rate_has_explicit_support_rule():
    value, reason = upper_tail_rate(
        pd.Series([0.0, 2.1, -2.2, 0.5]),
        threshold=2.0,
        minimum_observations=4,
    )
    assert value == 0.5
    assert reason is None
    value, reason = upper_tail_rate(
        pd.Series([0.0, 2.1]),
        threshold=2.0,
        minimum_observations=4,
    )
    assert np.isnan(value)
    assert reason == "insufficient_observations"


def test_followup_deltas_and_next_windows_respect_boundaries(
    make_trials_fixture,
):
    cleaned, windows, config = _followup_fixture(make_trials_fixture)
    enriched = build_zhang_tang_windows(
        cleaned,
        windows,
        config,
        progress_every=0,
    )
    assert len(enriched) == 2 * 4 * 3
    boundary = ["dataset_id", "participant_id", "task_family", "block_raw"]
    for _, group in enriched.groupby(boundary):
        ordered = group.sort_values("window_index")
        assert ordered["window_index"].tolist() == [0, 1, 2]
        assert not bool(ordered.iloc[0]["has_previous_window"])
        assert bool(ordered.iloc[0]["has_next_window"])
        assert bool(ordered.iloc[1]["has_previous_window"])
        assert bool(ordered.iloc[1]["has_next_window"])
        assert bool(ordered.iloc[2]["has_previous_window"])
        assert not bool(ordered.iloc[2]["has_next_window"])
        assert pd.isna(ordered.iloc[0]["delta_throughput"])
        assert pd.isna(ordered.iloc[2]["next_throughput"])
        assert ordered.iloc[0]["next_window_id"] == ordered.iloc[1]["window_id"]


def test_grouped_ridge_prediction_has_no_participant_leakage():
    rng = np.random.default_rng(42)
    rows = []
    for participant in range(12):
        for window in range(4):
            feature = participant + rng.normal(0, 0.2)
            rows.append(
                {
                    "participant_id": f"1:{participant}",
                    "dataset_id": 1,
                    "task_family": "Stroop",
                    "feature": feature,
                    "target": 0.5 * feature + rng.normal(0, 0.1),
                }
            )
    frame = pd.DataFrame(rows)
    result = grouped_ridge_metrics(
        frame,
        ["feature"],
        ["dataset_id", "task_family"],
        "target",
        folds=4,
    )
    assert result["status"] == "ok"
    assert result["maximum_participant_group_overlap"] == 0
