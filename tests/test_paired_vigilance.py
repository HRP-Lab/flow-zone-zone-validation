import numpy as np
import pandas as pd

from flowzone_validation.paired_vigilance import (
    CORE_SESSION_COLUMNS,
    SESSION_SPECS,
    build_session_features,
    decompose_associations,
    fit_control_mixtures,
    grouped_control_prediction,
    reshape_paired_summary,
)


def _session_frame(n_participants=60, sessions_per_participant=2, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for participant in range(n_participants):
        person = rng.normal()
        for session in range(sessions_per_participant):
            state = rng.normal(scale=0.7)
            accuracy = np.clip(0.94 + 0.02 * person + 0.01 * state, 0.7, 1)
            rt = 750 - 35 * person - 20 * state
            rows.append(
                {
                    "participant_id": f"P{participant}",
                    "source_subject_id": participant,
                    "session_type": "online" if session == 0 else "lab1",
                    "dataset_id": "D1" if session == 0 else "D2",
                    "session_id": f"P{participant}:{session}",
                    "session_date": pd.Timestamp("2020-01-01")
                    + pd.Timedelta(days=session),
                    "session_hour": 10 + session,
                    "gender": "x",
                    "age": 30,
                    "stroop_congruent_accuracy": accuracy,
                    "stroop_incongruent_accuracy": accuracy - 0.02,
                    "stroop_congruent_rt_ms": rt,
                    "stroop_incongruent_rt_ms": rt + 90,
                    "flanker_congruent_accuracy": min(1, accuracy + 0.02),
                    "flanker_incongruent_accuracy": accuracy,
                    "flanker_congruent_rt_ms": rt - 280,
                    "flanker_incongruent_rt_ms": rt - 235,
                    "sart_commission_percent": np.clip(
                        50 - 8 * person + rng.normal(scale=5),
                        0,
                        100,
                    ),
                    "sart_omission_percent": np.clip(
                        2 - person - state + rng.normal(scale=0.3),
                        0,
                        50,
                    ),
                    "sart_anticipatory_count": np.clip(
                        3 - person + rng.normal(scale=1),
                        0,
                        50,
                    ),
                    "sart_go_mean_rt_ms": 350 - 10 * person,
                    "sart_go_sd_rt_ms": 80,
                    "sart_go_rt_cv": np.clip(
                        0.25 - 0.03 * person - 0.02 * state,
                        0.08,
                        0.7,
                    ),
                    "sart_pre_success_nogo_rt_ms": 370,
                    "sart_pre_failed_nogo_rt_ms": 320,
                }
            )
    return pd.DataFrame(rows)


def test_reshape_summary_keeps_only_observed_sessions():
    columns = {
        "subjectid": [1],
        "Gender": ["x"],
        "Age": [30],
    }
    for session_type, specification in SESSION_SPECS.items():
        for output, source in specification.items():
            if output == "date":
                columns[source] = [
                    pd.Timestamp("2020-01-01")
                    if session_type == "online"
                    else "did not participate"
                ]
            elif output == "time":
                columns[source] = [
                    "10:30:00"
                    if session_type == "online"
                    else "did not participate"
                ]
            else:
                columns[source] = [1.0 if session_type == "online" else np.nan]
    reshaped = reshape_paired_summary(pd.DataFrame(columns))
    assert len(reshaped) == 1
    assert reshaped.iloc[0]["session_type"] == "online"
    assert reshaped.iloc[0]["session_hour"] == 10.5
    assert set(CORE_SESSION_COLUMNS).issubset(reshaped.columns)


def test_sart_engagement_orientation_and_boundaries():
    sessions = _session_frame()
    features, loadings = build_session_features(sessions)
    assert features["session_id"].is_unique
    assert (
        features["sart_engagement_index"].corr(
            features["sart_omission_rate"],
            method="spearman",
        )
        < -0.7
    )
    assert (
        features["sart_inhibitory_stability_index"].corr(
            features["sart_commission_rate"],
            method="spearman",
        )
        < -0.7
    )
    assert set(loadings["score"]) == {
        "sart_engagement_index",
        "sart_inhibitory_stability_index",
    }


def test_within_between_decomposition_and_grouped_prediction():
    features, _ = build_session_features(_session_frame())
    associations = decompose_associations(
        features,
        [("sart_engagement_index", "task_active_efficacy")],
    )
    assert set(associations["level"]) == {
        "session",
        "between_person",
        "within_person",
    }
    prediction = grouped_control_prediction(features)
    assert prediction["maximum_participant_overlap"].eq(0).all()
    assert prediction["n_participants"].eq(60).all()


def test_control_mixtures_are_deterministic():
    features, _ = build_session_features(_session_frame(n_participants=90))
    first = fit_control_mixtures(
        features,
        k_values=(1, 2, 3),
        covariances=("diag",),
        bootstrap_repetitions=3,
        seed=42,
    )
    second = fit_control_mixtures(
        features,
        k_values=(1, 2, 3),
        covariances=("diag",),
        bootstrap_repetitions=3,
        seed=42,
    )
    assert first.selected_model_id == second.selected_model_id
    assert first.assignments["control_profile"].equals(
        second.assignments["control_profile"]
    )
