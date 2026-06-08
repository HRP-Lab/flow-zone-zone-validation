"""Publication-oriented summaries for the paired control-vigilance study."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from .profile_recoverability import one_way_icc


@dataclass(frozen=True)
class JointAssociationResult:
    counts: pd.DataFrame
    rates: pd.DataFrame
    odds_ratios: pd.DataFrame
    statistics: dict[str, float | int]


@dataclass(frozen=True)
class ProfileRepeatabilityResult:
    transitions: pd.DataFrame
    profiles: pd.DataFrame
    binary_icc: pd.DataFrame
    statistics: dict[str, float | int]


def control_vigilance_association(
    frame: pd.DataFrame,
    *,
    threshold: float = -0.5,
    bootstrap_repetitions: int = 5000,
    seed: int = 42,
) -> JointAssociationResult:
    """Quantify profile-specific low-engagement enrichment."""
    required = {
        "participant_id",
        "control_profile",
        "sart_engagement_index",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing joint-analysis columns: {sorted(missing)}")
    usable = frame.dropna(subset=list(required)).copy()
    usable["low_engagement"] = usable["sart_engagement_index"].le(threshold)
    profiles = sorted(usable["control_profile"].astype(str).unique())
    contingency = pd.crosstab(
        usable["control_profile"],
        usable["low_engagement"],
    ).reindex(index=profiles, columns=[False, True], fill_value=0)
    chi2, p_value, degrees_freedom, expected = chi2_contingency(contingency)
    n = int(contingency.to_numpy().sum())
    denominator = n * min(
        contingency.shape[0] - 1,
        contingency.shape[1] - 1,
    )
    cramers_v = float(np.sqrt(chi2 / denominator))

    counts = contingency.reset_index().rename(
        columns={
            False: "preserved_engagement_sessions",
            True: "low_engagement_sessions",
        }
    )
    counts["total_sessions"] = (
        counts["preserved_engagement_sessions"]
        + counts["low_engagement_sessions"]
    )
    expected_frame = pd.DataFrame(
        expected,
        index=profiles,
        columns=[False, True],
    )
    rates = counts[
        [
            "control_profile",
            "preserved_engagement_sessions",
            "low_engagement_sessions",
            "total_sessions",
        ]
    ].copy()
    rates["low_engagement_rate"] = (
        rates["low_engagement_sessions"] / rates["total_sessions"]
    )
    rates["expected_low_engagement_sessions"] = [
        expected_frame.loc[profile, True] for profile in profiles
    ]
    rates["low_engagement_observed_expected_ratio"] = (
        rates["low_engagement_sessions"]
        / rates["expected_low_engagement_sessions"]
    )
    rates["median_engagement_index"] = [
        usable.loc[
            usable["control_profile"].eq(profile),
            "sart_engagement_index",
        ].median()
        for profile in profiles
    ]

    cell_names = [
        f"{profile}|{status}"
        for status in (False, True)
        for profile in profiles
    ]
    boot_frame = usable.copy()
    boot_frame["cell"] = (
        boot_frame["control_profile"].astype(str)
        + "|"
        + boot_frame["low_engagement"].astype(str)
    )
    participant_counts = pd.crosstab(
        boot_frame["participant_id"],
        boot_frame["cell"],
    ).reindex(columns=cell_names, fill_value=0)
    count_array = participant_counts.to_numpy()
    rng = np.random.default_rng(seed)
    rate_samples = {profile: [] for profile in profiles}
    odds_samples = {profile: [] for profile in profiles}
    for _ in range(bootstrap_repetitions):
        sampled = count_array[
            rng.integers(0, len(count_array), size=len(count_array))
        ].sum(axis=0)
        preserved = sampled[: len(profiles)]
        low = sampled[len(profiles) :]
        for index, profile in enumerate(profiles):
            low_profile = low[index]
            preserved_profile = preserved[index]
            low_other = low.sum() - low_profile
            preserved_other = preserved.sum() - preserved_profile
            rate_samples[profile].append(
                low_profile / (low_profile + preserved_profile)
            )
            odds_samples[profile].append(
                ((low_profile + 0.5) * (preserved_other + 0.5))
                / ((preserved_profile + 0.5) * (low_other + 0.5))
            )

    odds_rows = []
    for profile in profiles:
        rate_values = np.asarray(rate_samples[profile])
        odds_values = np.asarray(odds_samples[profile])
        odds_rows.append(
            {
                "control_profile": profile,
                "low_engagement_rate": float(
                    rates.loc[
                        rates["control_profile"].eq(profile),
                        "low_engagement_rate",
                    ].iloc[0]
                ),
                "low_engagement_rate_ci_lower": float(
                    np.quantile(rate_values, 0.025)
                ),
                "low_engagement_rate_ci_upper": float(
                    np.quantile(rate_values, 0.975)
                ),
                "one_vs_rest_odds_ratio": float(np.median(odds_values)),
                "odds_ratio_ci_lower": float(
                    np.quantile(odds_values, 0.025)
                ),
                "odds_ratio_ci_upper": float(
                    np.quantile(odds_values, 0.975)
                ),
            }
        )
    statistics: dict[str, float | int] = {
        "n_sessions": n,
        "n_participants": int(usable["participant_id"].nunique()),
        "engagement_threshold": threshold,
        "chi_square": float(chi2),
        "degrees_freedom": int(degrees_freedom),
        "p_value": float(p_value),
        "cramers_v": cramers_v,
        "bootstrap_repetitions": bootstrap_repetitions,
    }
    return JointAssociationResult(
        counts=counts,
        rates=rates,
        odds_ratios=pd.DataFrame(odds_rows),
        statistics=statistics,
    )


def profile_repeatability(
    frame: pd.DataFrame,
) -> ProfileRepeatabilityResult:
    """Describe repeated-session persistence and profile switching."""
    required = {
        "participant_id",
        "session_id",
        "session_date",
        "session_type",
        "control_profile",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"Missing profile-repeatability columns: {sorted(missing)}"
        )
    usable = frame.dropna(subset=list(required)).copy()
    repeated = usable[
        usable.groupby("participant_id")["session_id"]
        .transform("size")
        .ge(2)
    ].copy()
    repeated = repeated.sort_values(
        ["participant_id", "session_date", "session_type"],
        kind="stable",
    )
    profiles = sorted(repeated["control_profile"].astype(str).unique())
    transition_counts = pd.DataFrame(
        0,
        index=profiles,
        columns=profiles,
        dtype=int,
    )
    participant_rows = []
    for participant, group in repeated.groupby(
        "participant_id",
        sort=True,
    ):
        labels = group["control_profile"].astype(str).tolist()
        counts = pd.Series(labels).value_counts()
        participant_rows.append(
            {
                "participant_id": participant,
                "n_sessions": len(group),
                "n_profiles": len(counts),
                "modal_profile": counts.index[0],
                "modal_share": counts.iloc[0] / len(group),
            }
        )
        for source, destination in zip(labels[:-1], labels[1:], strict=True):
            transition_counts.loc[source, destination] += 1
    participant_summary = pd.DataFrame(participant_rows)

    transition_rows = []
    for source in profiles:
        total = int(transition_counts.loc[source].sum())
        for destination in profiles:
            count = int(transition_counts.loc[source, destination])
            transition_rows.append(
                {
                    "from_profile": source,
                    "to_profile": destination,
                    "count": count,
                    "row_probability": count / total if total else np.nan,
                }
            )
    transitions = pd.DataFrame(transition_rows)
    profile_rows = []
    for profile in profiles:
        profile_sessions = repeated["control_profile"].eq(profile)
        participants = repeated.loc[
            profile_sessions,
            "participant_id",
        ].unique()
        participant_groups = repeated[
            repeated["participant_id"].isin(participants)
        ].groupby("participant_id")["control_profile"]
        outgoing = transition_counts.loc[profile].sum()
        profile_rows.append(
            {
                "control_profile": profile,
                "n_sessions": int(profile_sessions.sum()),
                "n_participants": len(participants),
                "adjacent_persistence": (
                    transition_counts.loc[profile, profile] / outgoing
                    if outgoing
                    else np.nan
                ),
                "ever_profile_always_profile_rate": float(
                    participant_groups.apply(
                        lambda values: values.eq(profile).all()
                    ).mean()
                ),
            }
        )
        repeated[f"is_{profile.rsplit('-', 1)[-1]}"] = (
            repeated["control_profile"].eq(profile).astype(float)
        )
    binary_columns = [
        column for column in repeated.columns if column.startswith("is_C")
    ]
    binary_icc = one_way_icc(repeated, binary_columns)
    total_transitions = int(transition_counts.to_numpy().sum())
    statistics: dict[str, float | int] = {
        "n_repeated_sessions": len(repeated),
        "n_repeated_participants": int(
            repeated["participant_id"].nunique()
        ),
        "participants_with_multiple_profiles_rate": float(
            participant_summary["n_profiles"].gt(1).mean()
        ),
        "median_modal_share": float(
            participant_summary["modal_share"].median()
        ),
        "adjacent_transitions": total_transitions,
        "overall_adjacent_persistence": float(
            np.trace(transition_counts.to_numpy()) / total_transitions
        ),
    }
    return ProfileRepeatabilityResult(
        transitions=transitions,
        profiles=pd.DataFrame(profile_rows),
        binary_icc=binary_icc,
        statistics=statistics,
    )
