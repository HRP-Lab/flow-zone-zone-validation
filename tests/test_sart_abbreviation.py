import numpy as np
import pandas as pd

from flowzone_validation.sart_abbreviation import (
    agreement_table,
    binary_threshold_agreement,
    match_sart_sessions,
    prepare_sart_trials,
    score_sart_prefix,
    summarize_sart_trials,
)


def _raw_sart(sessions=24):
    rows = []
    sequence = ["Go"] * 8 + ["NoGo"]
    for participant in range(sessions):
        for trial in range(1, 226):
            trial_type = sequence[(trial - 1) % len(sequence)]
            is_nogo = trial_type == "NoGo"
            response_type = (
                "NoGo Failure"
                if is_nogo and participant % 3 == 0
                else "NoGo Success"
                if is_nogo
                else "Omission"
                if trial == participant + 1
                else "Go Success"
            )
            rows.append(
                {
                    "subjectid": participant,
                    "date": 10120,
                    "time": f"10:{participant:02d}:00",
                    "blockcode": "SART",
                    "expressions.trialcount": trial,
                    "values.trialtype": trial_type,
                    "values.responsetype": response_type,
                    "values.RT": (
                        np.nan
                        if response_type
                        in {"NoGo Success", "Omission"}
                        else 300 + participant + trial % 7
                    ),
                }
            )
    return pd.DataFrame(rows)


def _paired_summary(full):
    summary = full.rename(
        columns={
            "sart_commission_percent_raw": "sart_commission_percent",
            "sart_omission_percent_raw": "sart_omission_percent",
            "sart_anticipatory_count_raw": "sart_anticipatory_count",
            "sart_go_mean_rt_ms_raw": "sart_go_mean_rt_ms",
            "sart_go_rt_cv_raw": "sart_go_rt_cv",
        }
    ).copy()
    summary["session_id"] = [
        f"S{participant}" for participant in summary["source_subject_id"]
    ]
    summary["participant_id"] = [
        f"P{participant}" for participant in summary["source_subject_id"]
    ]
    summary["session_type"] = "online"
    summary["dataset_id"] = "online"
    summary["control_profile"] = "C1"
    summary["task_active_efficacy"] = 0.0
    summary["sart_engagement_index"] = 0.0
    summary["sart_inhibitory_stability_index"] = 0.0
    return summary


def test_sart_prefix_preserves_session_boundaries_and_counts():
    trials = prepare_sart_trials(_raw_sart())
    prefix = summarize_sart_trials(trials, prefix_trials=144)
    assert len(prefix) == 24
    assert prefix["sart_trial_count_raw"].eq(144).all()
    assert (
        prefix["sart_go_count_raw"] + prefix["sart_nogo_count_raw"]
    ).eq(144).all()
    assert prefix["raw_session_id"].is_unique


def test_fingerprint_matching_is_participant_bounded_and_exact():
    trials = prepare_sart_trials(_raw_sart())
    full = summarize_sart_trials(trials, prefix_trials=225)
    sessions = _paired_summary(full)
    accepted, candidates = match_sart_sessions(full, sessions)
    assert len(accepted) == 24
    assert candidates["accepted"].all()
    assert accepted["fingerprint_cost"].max() < 1e-10


def test_abbreviated_dimensions_and_agreement_are_finite():
    trials = prepare_sart_trials(_raw_sart())
    full = summarize_sart_trials(trials, prefix_trials=225)
    sessions = _paired_summary(full)
    accepted, _ = match_sart_sessions(full, sessions)
    metadata = accepted.merge(
        sessions[
            [
                "session_id",
                "participant_id",
                "session_type",
                "dataset_id",
                "control_profile",
                "task_active_efficacy",
                "sart_engagement_index",
                "sart_inhibitory_stability_index",
            ]
        ],
        on="session_id",
        validate="one_to_one",
    )
    prefix = summarize_sart_trials(trials, prefix_trials=144)
    scored = score_sart_prefix(prefix, metadata, label="sart_3min")
    assert scored["sart_3min_engagement_index"].notna().all()
    assert scored["sart_3min_inhibitory_stability_index"].notna().all()
    agreement = agreement_table(
        scored,
        [
            (
                "engagement",
                "sart_3min_engagement_index",
                "sart_engagement_index",
            )
        ],
    )
    assert agreement.loc[0, "n_sessions"] == 24


def test_binary_threshold_agreement_reports_confusion_counts():
    result = binary_threshold_agreement(
        pd.Series([-1.0, -0.7, 0.2, 0.5]),
        pd.Series([-0.8, 0.1, -0.6, 0.5]),
    )
    assert result["n_sessions"] == 4
    assert result["true_positive"] == 1
    assert result["false_positive"] == 1
    assert result["false_negative"] == 1
    assert result["true_negative"] == 1
