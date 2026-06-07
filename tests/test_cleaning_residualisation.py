import numpy as np

from flowzone_validation.cleaning import flag_trials
from flowzone_validation.residualisation import residualise_trial_rt


def test_rt_flags_preserve_rows(synthetic_trials, pilot_config):
    frame = synthetic_trials.iloc[:20].copy()
    frame.loc[0, "rt_ms"] = 100
    frame.loc[1, "rt_ms"] = 3501
    frame.loc[2, "rt_ms"] = np.nan
    flagged = flag_trials(frame, pilot_config)
    assert len(flagged) == len(frame)
    assert flagged.loc[0, "rt_below_min"]
    assert flagged.loc[1, "rt_above_max"]
    assert flagged.loc[2, "rt_missing"]
    assert flagged.loc[2, "lapse_proxy"]
    assert flagged["rt_excluded"].sum() >= 3


def test_residualisation_builds_log_raw_and_update_series(
    synthetic_trials,
    pilot_config,
):
    flagged = flag_trials(synthetic_trials, pilot_config)
    result = residualise_trial_rt(flagged)
    assert result["log_rt_residual"].notna().mean() > 0.9
    assert result["raw_rt_residual_ms"].notna().mean() > 0.9
    assert result["u_t"].notna().mean() > 0.9
    assert set(result["residualisation_status"]) == {"ok"}


def test_slow_rt_is_not_automatically_a_lapse(synthetic_trials, pilot_config):
    frame = synthetic_trials.iloc[:30].copy()
    frame.loc[0, "rt_ms"] = 1200
    flagged = flag_trials(frame, pilot_config)
    assert not bool(flagged.loc[0, "lapse_proxy"])


def test_negative_practice_block_is_retained_but_ineligible(
    synthetic_trials,
    pilot_config,
):
    frame = synthetic_trials.iloc[:30].copy()
    frame["block_raw"] = -999
    flagged = flag_trials(frame, pilot_config)
    assert flagged["practice_block"].all()
    assert not flagged["analysis_eligible_trial"].any()
