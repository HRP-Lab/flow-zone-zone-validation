import pandas as pd

from flowzone_validation.paired_study import (
    control_vigilance_association,
    profile_repeatability,
)


def _study_frame():
    rows = []
    profiles = ["C1", "C2", "C3", "C4"]
    for participant in range(40):
        for session in range(2):
            profile = profiles[(participant + session) % 4]
            engagement = -1.0 if profile == "C3" else 0.2
            rows.append(
                {
                    "participant_id": f"P{participant}",
                    "session_id": f"P{participant}:{session}",
                    "session_date": pd.Timestamp("2020-01-01")
                    + pd.Timedelta(days=session),
                    "session_type": f"S{session}",
                    "control_profile": profile,
                    "sart_engagement_index": engagement,
                }
            )
    return pd.DataFrame(rows)


def test_joint_association_preserves_participant_bootstrap():
    result = control_vigilance_association(
        _study_frame(),
        bootstrap_repetitions=20,
        seed=42,
    )
    assert result.statistics["n_participants"] == 40
    assert result.statistics["cramers_v"] > 0
    assert result.counts["total_sessions"].sum() == 80
    assert result.odds_ratios["odds_ratio_ci_lower"].notna().all()


def test_profile_repeatability_counts_transitions_and_binary_icc():
    result = profile_repeatability(_study_frame())
    assert result.statistics["n_repeated_participants"] == 40
    assert result.statistics["adjacent_transitions"] == 40
    assert result.transitions["count"].sum() == 40
    assert set(result.profiles["control_profile"]) == {
        "C1",
        "C2",
        "C3",
        "C4",
    }
