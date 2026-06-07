from dataclasses import replace

import numpy as np
import pandas as pd

from flowzone_validation.audit import evaluate_audit
from flowzone_validation.cleaning import flag_trials
from flowzone_validation.confounds import grouped_confound_test
from flowzone_validation.cognitive_features import summarize_windows
from flowzone_validation.residualisation import residualise_trial_rt
from flowzone_validation.windowing import assign_trial_windows


def _features(trials, config):
    flagged = flag_trials(trials, config)
    residualized = residualise_trial_rt(flagged)
    windowed = assign_trial_windows(
        residualized,
        config.primary_window_size,
        config.sensitivity_window_sizes,
        config.minimum_remainder_trials,
    )
    return summarize_windows(windowed, config)


def test_audit_passes_relaxed_fixture_gate(synthetic_trials, pilot_config):
    windows = _features(synthetic_trials, pilot_config)
    audit = evaluate_audit(windows, pilot_config)
    gate = audit["task_gates"]["Stroop"]
    assert gate["eligible"]
    assert len(gate["selected_features"]) >= pilot_config.minimum_clustering_features


def test_audit_records_gate_failure(synthetic_trials, pilot_config):
    strict = replace(pilot_config, minimum_task_windows=10_000)
    windows = _features(synthetic_trials, strict)
    audit = evaluate_audit(windows, strict)
    gate = audit["task_gates"]["Stroop"]
    assert not gate["eligible"]
    assert any("windows <" in reason for reason in gate["gate_reasons"])


def test_confound_cv_has_no_participant_overlap():
    rng = np.random.default_rng(7)
    rows = []
    for dataset in range(3):
        for participant in range(8):
            for window in range(3):
                rows.append(
                    {
                        "participant_id": f"{dataset}:{participant}",
                        "dataset_id": dataset,
                        "feature_a": dataset * 4 + rng.normal(0, 0.1),
                        "feature_b": rng.normal(),
                    }
                )
    frame = pd.DataFrame(rows)
    result = grouped_confound_test(
        frame,
        ["feature_a", "feature_b"],
        "dataset_id",
        permutations=3,
        seed=42,
    )
    assert result["status"] == "ok"
    assert result["maximum_participant_group_overlap"] == 0
    assert result["balanced_accuracy"] > result["chance_balanced_accuracy"]
