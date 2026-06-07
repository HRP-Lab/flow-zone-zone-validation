from dataclasses import replace

import numpy as np
import pandas as pd

from flowzone_validation.cleaning import flag_trials
from flowzone_validation.cognitive_features import (
    dfa_alpha,
    difference_entropy,
    permutation_entropy_3,
    summarize_windows,
)
from flowzone_validation.residualisation import residualise_trial_rt
from flowzone_validation.windowing import assign_trial_windows


def _pipeline(frame, config):
    flagged = flag_trials(frame, config)
    residualized = residualise_trial_rt(flagged)
    windowed = assign_trial_windows(
        residualized,
        config.primary_window_size,
        config.sensitivity_window_sizes,
        config.minimum_remainder_trials,
    )
    return windowed, summarize_windows(windowed, config)


def test_windows_never_cross_boundaries(synthetic_trials, pilot_config):
    windowed, _ = _pipeline(synthetic_trials, pilot_config)
    uniqueness = windowed.groupby("window_id")[
        ["dataset_id", "participant_id", "task_family", "block_raw"]
    ].nunique()
    assert not uniqueness.gt(1).any().any()


def test_primary_remainder_is_aggregate_only(
    synthetic_trials,
    pilot_config,
):
    windowed, features = _pipeline(synthetic_trials, pilot_config)
    remainders = features[features["window_kind"].eq("aggregate_remainder")]
    assert not remainders.empty
    assert set(remainders["n_trials"]) == {50}
    assert remainders["cog_alpha1"].isna().all()
    full_primary = features[
        features["window_size"].eq(80) & features["window_kind"].eq("full")
    ]
    assert set(full_primary["n_trials"]) == {80}
    assert full_primary["cog_alpha1"].notna().all()


def test_pes_requires_both_support_sets(synthetic_trials, pilot_config):
    supported_config = replace(
        pilot_config,
        minimum_pes_post_error_trials=2,
        minimum_pes_post_correct_trials=2,
    )
    _, features = _pipeline(synthetic_trials, supported_config)
    unsupported = features.loc[~features["pes_supported"]]
    assert unsupported["post_error_slowing_ms"].isna().all()
    assert unsupported["post_error_adjustment_abs_ms"].isna().all()


def test_dynamics_functions_handle_constant_and_variable_series():
    constant = pd.Series(np.ones(80))
    variable = pd.Series(np.sin(np.linspace(0, 12, 80)))
    assert np.isnan(dfa_alpha(constant))
    assert np.isfinite(dfa_alpha(variable))
    assert np.isfinite(permutation_entropy_3(variable))
    assert np.isfinite(difference_entropy(variable))
