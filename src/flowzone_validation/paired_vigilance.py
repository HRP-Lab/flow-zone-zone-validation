"""Paired Stroop, Flanker, and SART engagement analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.decomposition import PCA
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    adjusted_rand_score,
    balanced_accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler


SESSION_SPECS: dict[str, dict[str, str]] = {
    "online": {
        "date": "Date of online session",
        "time": "Online session time",
        "flanker_congruent_accuracy": "ONLINE FLANKER CONGRUENT: % correct",
        "flanker_incongruent_accuracy": (
            "ONLINE FLANKER INCONGRUENT: % correct"
        ),
        "flanker_congruent_rt_ms": (
            "ONLINE FLANKER CONGRUENT: mean RT for correct"
        ),
        "flanker_incongruent_rt_ms": (
            "ONLINE FLANKER INCONGRUENT: mean RT for correct"
        ),
        "stroop_congruent_rt_ms": (
            "ONLINE STROOP CONGRUENT: mean RT for correct"
        ),
        "stroop_incongruent_rt_ms": (
            "ONLINE STROOP INCONGRUENT: mean RT for correct"
        ),
        "stroop_congruent_accuracy": "ONLINE STROOP CONGRUENT: % correct",
        "stroop_incongruent_accuracy": (
            "ONLINE STROOP INCONGRUENT: % correct"
        ),
        "sart_commission_percent": (
            "ONLINE SART:                 % COMMISSIONS"
        ),
        "sart_omission_percent": "ONLINE SART:           % OMISSIONS",
        "sart_anticipatory_count": "ONLINE SART: anticipatory count",
        "sart_go_mean_rt_ms": 'ONLINE SART "GO" TRIAL: mean RT',
        "sart_go_sd_rt_ms": "ONLINE SART SD RT GO",
        "sart_go_rt_cv": "ONLINE SART CV GO",
        "sart_pre_success_nogo_rt_ms": (
            " ONLINE SART GObeforesuccessNOGO mean RT"
        ),
        "sart_pre_failed_nogo_rt_ms": (
            "ONLINE SART_GObeforefailedNOGO mean RT"
        ),
    },
    "lab1": {
        "date": "Date of first lab session (low vs medium Vs high)",
        "time": "Hour of first lab session (low vs medium Vs high)",
        "flanker_congruent_accuracy": "L1 FLANKER CONGRUENT: % correct",
        "flanker_incongruent_accuracy": "L1 FLANKER INCONGRUENT: % correct",
        "flanker_congruent_rt_ms": (
            "L1 FLANKER CONGRUENT: mean RT for correct"
        ),
        "flanker_incongruent_rt_ms": (
            "L1 FLANKER INCONGRUENT: mean RT for correct"
        ),
        "stroop_congruent_rt_ms": (
            "L1 STROOP CONGRUENT: mean RT for correct"
        ),
        "stroop_incongruent_rt_ms": (
            "L1 STROOP INCONGRUENT: mean RT for correct"
        ),
        "stroop_congruent_accuracy": "L1 STROOP CONGRUENT: % correct",
        "stroop_incongruent_accuracy": "L1 STROOP INCONGRUENT: % correct",
        "sart_commission_percent": "L1 SART:                 % COMMISSIONS",
        "sart_omission_percent": "L1 SART:           % OMISSIONS",
        "sart_anticipatory_count": "L1 SART: anticipatory count",
        "sart_go_mean_rt_ms": 'L1 SART "GO" TRIAL: mean RT',
        "sart_go_sd_rt_ms": "L1 SART SD RT GO",
        "sart_go_rt_cv": "L1 SART CV GO",
        "sart_pre_success_nogo_rt_ms": (
            " L1 SART GObeforesuccessNOGO mean RT"
        ),
        "sart_pre_failed_nogo_rt_ms": (
            "L1 SART_GObeforefailedNOGO mean RT"
        ),
    },
    "lab2": {
        "date": "Date of second lab session (low vs high)",
        "time": "Hour of second lab session (low vs  high)",
        "flanker_congruent_accuracy": "L2 FLANKER CONGRUENT: % correct",
        "flanker_incongruent_accuracy": "L2 FLANKER INCONGRUENT: % correct",
        "flanker_congruent_rt_ms": (
            "L2 FLANKER CONGRUENT: mean RT for correct"
        ),
        "flanker_incongruent_rt_ms": (
            "L2 FLANKER INCONGRUENT: mean RT for correct"
        ),
        "stroop_congruent_rt_ms": (
            "L2 STROOP CONGRUENT: mean RT for correct"
        ),
        "stroop_incongruent_rt_ms": (
            "L2 STROOP INCONGRUENT: mean RT for correct"
        ),
        "stroop_congruent_accuracy": "L2 STROOP CONGRUENT: % correct",
        "stroop_incongruent_accuracy": "L2 STROOP INCONGRUENT: % correct",
        "sart_commission_percent": "L2 SART:                 % COMMISSIONS",
        "sart_omission_percent": "L2 SART:           % OMISSIONS",
        "sart_anticipatory_count": "L2 SART: anticipatory count",
        "sart_go_mean_rt_ms": 'L2 SART "GO" TRIAL: mean RT',
        "sart_go_sd_rt_ms": "L2 SART SD RT GO",
        "sart_go_rt_cv": "L2 SART CV GO",
        "sart_pre_success_nogo_rt_ms": (
            " L2 SART GObeforesuccessNOGO mean RT"
        ),
        "sart_pre_failed_nogo_rt_ms": (
            "L2 SART_GObeforefailedNOGO mean RT"
        ),
    },
}

CORE_SESSION_COLUMNS = (
    "stroop_congruent_accuracy",
    "stroop_incongruent_accuracy",
    "stroop_congruent_rt_ms",
    "stroop_incongruent_rt_ms",
    "flanker_congruent_accuracy",
    "flanker_incongruent_accuracy",
    "flanker_congruent_rt_ms",
    "flanker_incongruent_rt_ms",
    "sart_commission_percent",
    "sart_omission_percent",
    "sart_anticipatory_count",
    "sart_go_mean_rt_ms",
    "sart_go_rt_cv",
)


@dataclass(frozen=True)
class MixtureResult:
    comparison: pd.DataFrame
    assignments: pd.DataFrame
    selected_model_id: str


def _session_hour(value: object) -> float:
    if pd.isna(value) or str(value).strip().lower() == "did not participate":
        return np.nan
    parsed = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(parsed):
        return np.nan
    return float(parsed.hour + parsed.minute / 60 + parsed.second / 3600)


def reshape_paired_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Reshape the published participant summary into one row per session."""
    required = {"subjectid", *[value for spec in SESSION_SPECS.values() for value in spec.values()]}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"Missing paired-summary columns: {sorted(missing)}")

    rows: list[dict[str, Any]] = []
    for source in summary.itertuples(index=False, name=None):
        source_row = dict(zip(summary.columns, source, strict=True))
        participant = f"Barzykowski2022:{int(source_row['subjectid'])}"
        for session_type, specification in SESSION_SPECS.items():
            row: dict[str, Any] = {
                "participant_id": participant,
                "source_subject_id": int(source_row["subjectid"]),
                "session_type": session_type,
                "dataset_id": f"Barzykowski2022-{session_type}",
                "gender": source_row.get("Gender"),
                "age": pd.to_numeric(source_row.get("Age"), errors="coerce"),
            }
            for output_name, source_name in specification.items():
                if output_name == "date":
                    row["session_date"] = pd.to_datetime(
                        source_row[source_name],
                        errors="coerce",
                    )
                elif output_name == "time":
                    row["session_hour"] = _session_hour(source_row[source_name])
                else:
                    row[output_name] = pd.to_numeric(
                        source_row[source_name],
                        errors="coerce",
                    )
            if not any(pd.notna(row[column]) for column in CORE_SESSION_COLUMNS):
                continue
            row["session_id"] = f"{participant}:{session_type}"
            rows.append(row)
    sessions = pd.DataFrame(rows)
    if sessions.empty:
        raise ValueError("No paired task sessions were found")
    if sessions["session_id"].duplicated().any():
        raise ValueError("Duplicate participant-session rows detected")
    return sessions.sort_values(
        ["source_subject_id", "session_date", "session_type"],
        kind="stable",
    ).reset_index(drop=True)


def _robust_z_within(
    frame: pd.DataFrame,
    columns: Iterable[str],
    group_column: str = "session_type",
) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        standardized = pd.Series(np.nan, index=frame.index, dtype=float)
        for _, indices in frame.groupby(group_column, sort=False).groups.items():
            group = values.loc[indices]
            median = float(group.median())
            iqr = float(group.quantile(0.75) - group.quantile(0.25))
            if not np.isfinite(iqr) or iqr <= 0:
                iqr = float(group.std(ddof=0))
            if not np.isfinite(iqr) or iqr <= 0:
                iqr = 1.0
            standardized.loc[indices] = (group - median) / iqr
        result[column] = standardized.clip(-5, 5)
    return result


def _component_score(
    frame: pd.DataFrame,
    indicators: list[tuple[str, int]],
    score_name: str,
) -> tuple[pd.Series, pd.DataFrame]:
    columns = [column for column, _ in indicators]
    standardized = _robust_z_within(frame, columns)
    oriented = standardized.copy()
    for column, direction in indicators:
        oriented[column] *= direction
    complete = oriented.notna().all(axis=1)
    if complete.sum() < 20:
        raise ValueError(f"Insufficient complete rows for {score_name}")
    pca = PCA(n_components=1, random_state=42).fit(oriented.loc[complete])
    complete_scores = oriented.loc[complete].mean(axis=1).to_numpy()
    score = pd.Series(np.nan, index=frame.index, dtype=float, name=score_name)
    score.loc[complete] = complete_scores
    scale = float(score.quantile(0.75) - score.quantile(0.25))
    if not np.isfinite(scale) or scale <= 0:
        scale = float(score.std(ddof=0))
    score = (score - score.median()) / (scale if scale > 0 else 1.0)
    loading_table = pd.DataFrame(
        {
            "score": score_name,
            "indicator": columns,
            "direction": [direction for _, direction in indicators],
            "equal_weight": 1 / len(indicators),
            "diagnostic_pc1_variance": pca.explained_variance_ratio_[0],
            "n_complete": int(complete.sum()),
        }
    )
    return score, loading_table


def build_session_features(
    sessions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create transparent control and SART dimensions from paired sessions."""
    frame = sessions.copy()
    frame["stroop_accuracy"] = frame[
        ["stroop_congruent_accuracy", "stroop_incongruent_accuracy"]
    ].mean(axis=1)
    frame["stroop_mean_rt_ms"] = frame[
        ["stroop_congruent_rt_ms", "stroop_incongruent_rt_ms"]
    ].mean(axis=1)
    frame["stroop_interference_rt_ms"] = (
        frame["stroop_incongruent_rt_ms"] - frame["stroop_congruent_rt_ms"]
    )
    frame["stroop_interference_accuracy"] = (
        frame["stroop_congruent_accuracy"]
        - frame["stroop_incongruent_accuracy"]
    )
    frame["stroop_throughput"] = frame["stroop_accuracy"] / (
        frame["stroop_mean_rt_ms"] / 1000
    )

    frame["flanker_accuracy"] = frame[
        ["flanker_congruent_accuracy", "flanker_incongruent_accuracy"]
    ].mean(axis=1)
    frame["flanker_mean_rt_ms"] = frame[
        ["flanker_congruent_rt_ms", "flanker_incongruent_rt_ms"]
    ].mean(axis=1)
    frame["flanker_interference_rt_ms"] = (
        frame["flanker_incongruent_rt_ms"] - frame["flanker_congruent_rt_ms"]
    )
    frame["flanker_interference_accuracy"] = (
        frame["flanker_congruent_accuracy"]
        - frame["flanker_incongruent_accuracy"]
    )
    frame["flanker_throughput"] = frame["flanker_accuracy"] / (
        frame["flanker_mean_rt_ms"] / 1000
    )

    frame["sart_commission_rate"] = frame["sart_commission_percent"] / 100
    frame["sart_omission_rate"] = frame["sart_omission_percent"] / 100
    frame["sart_anticipatory_rate"] = frame["sart_anticipatory_count"] / 200
    frame["sart_pre_failure_speeding_ms"] = (
        frame["sart_pre_success_nogo_rt_ms"]
        - frame["sart_pre_failed_nogo_rt_ms"]
    )
    frame["session_hour_sin"] = np.sin(2 * np.pi * frame["session_hour"] / 24)
    frame["session_hour_cos"] = np.cos(2 * np.pi * frame["session_hour"] / 24)

    control_columns = [
        "stroop_accuracy",
        "flanker_accuracy",
        "stroop_mean_rt_ms",
        "flanker_mean_rt_ms",
        "stroop_interference_rt_ms",
        "flanker_interference_rt_ms",
        "stroop_interference_accuracy",
        "flanker_interference_accuracy",
    ]
    control_z = _robust_z_within(frame, control_columns)
    frame["control_accuracy_index"] = control_z[
        ["stroop_accuracy", "flanker_accuracy"]
    ].mean(axis=1)
    frame["control_speed_index"] = -control_z[
        ["stroop_mean_rt_ms", "flanker_mean_rt_ms"]
    ].mean(axis=1)
    frame["conflict_resilience_index"] = -control_z[
        [
            "stroop_interference_rt_ms",
            "flanker_interference_rt_ms",
            "stroop_interference_accuracy",
            "flanker_interference_accuracy",
        ]
    ].mean(axis=1)
    frame["task_active_efficacy"] = frame[
        [
            "control_accuracy_index",
            "control_speed_index",
            "conflict_resilience_index",
        ]
    ].mean(axis=1)

    engagement, engagement_loadings = _component_score(
        frame,
        [
            ("sart_omission_rate", -1),
            ("sart_go_rt_cv", -1),
        ],
        "sart_engagement_index",
    )
    inhibition, inhibition_loadings = _component_score(
        frame,
        [
            ("sart_commission_rate", -1),
            ("sart_anticipatory_rate", -1),
        ],
        "sart_inhibitory_stability_index",
    )
    frame["sart_engagement_index"] = engagement
    frame["sart_inhibitory_stability_index"] = inhibition
    frame["low_engagement_candidate"] = engagement.le(-0.5)
    frame["high_engagement_candidate"] = engagement.ge(0.5)
    loadings = pd.concat(
        [engagement_loadings, inhibition_loadings],
        ignore_index=True,
    )
    return frame, loadings


def _posterior_entropy(probabilities: np.ndarray) -> float:
    if probabilities.shape[1] == 1:
        return 0.0
    clipped = np.clip(probabilities, 1e-12, 1)
    entropy = -np.sum(clipped * np.log(clipped), axis=1)
    return float(np.mean(entropy / np.log(probabilities.shape[1])))


def fit_control_mixtures(
    frame: pd.DataFrame,
    *,
    k_values: Iterable[int] = (1, 2, 3, 4, 5),
    covariances: Iterable[str] = ("diag", "full"),
    bootstrap_repetitions: int = 50,
    seed: int = 42,
) -> MixtureResult:
    """Compare neutral mixtures of task-active control dimensions."""
    features = [
        "control_accuracy_index",
        "control_speed_index",
        "conflict_resilience_index",
    ]
    usable = frame.dropna(subset=[*features, "participant_id"]).copy()
    values = RobustScaler().fit_transform(usable[features])
    participants = usable["participant_id"].astype(str).to_numpy()
    unique_participants = np.unique(participants)
    group_indices = {
        participant: np.flatnonzero(participants == participant)
        for participant in unique_participants
    }
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    fitted: dict[str, tuple[GaussianMixture, np.ndarray]] = {}
    for covariance in covariances:
        for k in k_values:
            model_id = f"Paired-Control-GMM{k}-{covariance}"
            covariance_parameters = (
                len(features)
                if covariance == "diag"
                else len(features) * (len(features) + 1) // 2
            )
            parameter_count = k * (len(features) + covariance_parameters) + k - 1
            if covariance == "full" and len(usable) <= 10 * parameter_count:
                rows.append(
                    {
                        "model_id": model_id,
                        "k": k,
                        "covariance": covariance,
                        "valid": False,
                        "invalid_reason": "insufficient_rows_for_full_covariance",
                    }
                )
                continue
            model = GaussianMixture(
                n_components=k,
                covariance_type=covariance,
                n_init=20,
                random_state=seed,
                reg_covar=1e-6,
            )
            labels = model.fit_predict(values)
            counts = np.bincount(labels, minlength=k)
            valid_sizes = bool(
                np.all(counts >= 20) and np.all(counts / len(labels) >= 0.05)
            )
            bootstrap_ari: list[float] = []
            for repetition in range(bootstrap_repetitions):
                sampled = rng.choice(
                    unique_participants,
                    size=len(unique_participants),
                    replace=True,
                )
                sampled_indices = np.concatenate(
                    [group_indices[participant] for participant in sampled]
                )
                bootstrap_model = GaussianMixture(
                    n_components=k,
                    covariance_type=covariance,
                    n_init=5,
                    random_state=seed + repetition + 1,
                    reg_covar=1e-6,
                )
                try:
                    bootstrap_model.fit(values[sampled_indices])
                    bootstrap_ari.append(
                        float(
                            adjusted_rand_score(
                                labels,
                                bootstrap_model.predict(values),
                            )
                        )
                    )
                except ValueError:
                    continue
            rows.append(
                {
                    "model_id": model_id,
                    "k": k,
                    "covariance": covariance,
                    "valid": valid_sizes,
                    "invalid_reason": "" if valid_sizes else "small_component",
                    "bic": model.bic(values),
                    "aic": model.aic(values),
                    "posterior_entropy": _posterior_entropy(
                        model.predict_proba(values)
                    ),
                    "component_sizes": ";".join(map(str, sorted(counts))),
                    "bootstrap_ari_median": (
                        float(np.median(bootstrap_ari))
                        if bootstrap_ari
                        else np.nan
                    ),
                }
            )
            fitted[model_id] = (model, labels)
    comparison = pd.DataFrame(rows)
    eligible = comparison[comparison["valid"].fillna(False)].copy()
    if eligible.empty:
        raise ValueError("No valid task-active control mixture")
    selected = eligible.sort_values(
        ["bic", "bootstrap_ari_median"],
        ascending=[True, False],
    ).iloc[0]
    selected_model_id = str(selected["model_id"])
    model, labels = fitted[selected_model_id]
    assignments = usable[
        ["session_id", "participant_id", "dataset_id", "session_type"]
    ].copy()
    assignments["control_profile"] = [
        f"{selected_model_id}-C{label + 1}" for label in labels
    ]
    assignments["control_profile_probability"] = model.predict_proba(values).max(
        axis=1
    )
    return MixtureResult(comparison, assignments, selected_model_id)


def summarize_control_profiles(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize neutral task-active profiles and add cautious pattern notes."""
    metrics = [
        "task_active_efficacy",
        "control_accuracy_index",
        "control_speed_index",
        "conflict_resilience_index",
        "stroop_accuracy",
        "stroop_mean_rt_ms",
        "stroop_interference_rt_ms",
        "stroop_throughput",
        "flanker_accuracy",
        "flanker_mean_rt_ms",
        "flanker_interference_rt_ms",
        "flanker_throughput",
        "sart_engagement_index",
        "sart_inhibitory_stability_index",
        "sart_omission_rate",
        "sart_go_rt_cv",
        "sart_commission_rate",
        "sart_anticipatory_rate",
    ]
    rows: list[dict[str, Any]] = []
    for profile, group in frame.groupby("control_profile", sort=True):
        row: dict[str, Any] = {
            "control_profile": profile,
            "n_sessions": len(group),
            "n_participants": group["participant_id"].nunique(),
            "online_fraction": group["session_type"].eq("online").mean(),
            "low_engagement_candidate_rate": group[
                "low_engagement_candidate"
            ].mean(),
        }
        for metric in metrics:
            row[f"mean_{metric}"] = group[metric].mean()
            row[f"median_{metric}"] = group[metric].median()
        rows.append(row)
    profiles = pd.DataFrame(rows)
    profiles["provisional_pattern_note"] = "mixed_or_unclear"
    if len(profiles) >= 2:
        regulated = profiles["mean_task_active_efficacy"].idxmax()
        profiles.loc[regulated, "provisional_pattern_note"] = (
            "regulated_control_candidate"
        )
        remaining = profiles.drop(index=regulated)
        overloaded_score = (
            remaining["mean_control_accuracy_index"]
            + remaining["mean_control_speed_index"]
        )
        overloaded = overloaded_score.idxmin()
        profiles.loc[overloaded, "provisional_pattern_note"] = (
            "overloaded_control_candidate"
        )
        if len(profiles) == 3:
            brittle = profiles.index.difference([regulated, overloaded])[0]
            profiles.loc[brittle, "provisional_pattern_note"] = (
                "fast_brittle_candidate"
            )
    return profiles


def _safe_correlation(
    left: pd.Series,
    right: pd.Series,
    method: str,
) -> tuple[float, int]:
    complete = pd.concat([left, right], axis=1).dropna()
    if len(complete) < 4:
        return np.nan, len(complete)
    if complete.iloc[:, 0].nunique() < 2 or complete.iloc[:, 1].nunique() < 2:
        return np.nan, len(complete)
    function = spearmanr if method == "spearman" else pearsonr
    return float(function(complete.iloc[:, 0], complete.iloc[:, 1]).statistic), len(
        complete
    )


def decompose_associations(
    frame: pd.DataFrame,
    pairs: Iterable[tuple[str, str]],
) -> pd.DataFrame:
    """Separate session-level, between-person, and within-person associations."""
    rows: list[dict[str, Any]] = []
    repeated = frame[
        frame.groupby("participant_id")["session_id"].transform("size").ge(2)
    ].copy()
    for predictor, outcome in pairs:
        session_r, session_n = _safe_correlation(
            frame[predictor],
            frame[outcome],
            "spearman",
        )
        participant_means = frame.groupby("participant_id")[
            [predictor, outcome]
        ].mean()
        between_r, between_n = _safe_correlation(
            participant_means[predictor],
            participant_means[outcome],
            "spearman",
        )
        predictor_centered = repeated[predictor] - repeated.groupby(
            "participant_id"
        )[predictor].transform("mean")
        outcome_centered = repeated[outcome] - repeated.groupby(
            "participant_id"
        )[outcome].transform("mean")
        within_r, within_n = _safe_correlation(
            predictor_centered,
            outcome_centered,
            "pearson",
        )
        rows.extend(
            [
                {
                    "predictor": predictor,
                    "outcome": outcome,
                    "level": "session",
                    "correlation": session_r,
                    "n": session_n,
                },
                {
                    "predictor": predictor,
                    "outcome": outcome,
                    "level": "between_person",
                    "correlation": between_r,
                    "n": between_n,
                },
                {
                    "predictor": predictor,
                    "outcome": outcome,
                    "level": "within_person",
                    "correlation": within_r,
                    "n": within_n,
                },
            ]
        )
    return pd.DataFrame(rows)


def grouped_control_prediction(
    frame: pd.DataFrame,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Predict independent task-active efficacy from SART features."""
    usable = frame.dropna(
        subset=["participant_id", "task_active_efficacy"]
    ).reset_index(drop=True)
    groups = usable["participant_id"].astype(str)
    feature_sets = {
        "intercept_only": [],
        "engagement_only": ["sart_engagement_index"],
        "inhibitory_only": ["sart_inhibitory_stability_index"],
        "two_sart_dimensions": [
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
        ],
        "expanded_sart": [
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
            "sart_go_mean_rt_ms",
            "sart_pre_failure_speeding_ms",
        ],
    }
    splitter = GroupKFold(n_splits=5)
    rows: list[dict[str, Any]] = []
    target = usable["task_active_efficacy"].to_numpy(dtype=float)
    for model_name, features in feature_sets.items():
        predictions = np.full(len(usable), np.nan)
        maximum_overlap = 0
        for train, test in splitter.split(usable, target, groups):
            maximum_overlap = max(
                maximum_overlap,
                len(set(groups.iloc[train]) & set(groups.iloc[test])),
            )
            if not features:
                model = DummyRegressor(strategy="mean")
                train_x = np.zeros((len(train), 1))
                test_x = np.zeros((len(test), 1))
            else:
                model = make_pipeline(
                    SimpleImputer(strategy="median", add_indicator=True),
                    RobustScaler(),
                    Ridge(alpha=1.0, random_state=seed),
                )
                train_x = usable.iloc[train][features]
                test_x = usable.iloc[test][features]
            model.fit(train_x, target[train])
            predictions[test] = model.predict(test_x)
        rows.append(
            {
                "model": model_name,
                "features": ";".join(features),
                "n_sessions": len(usable),
                "n_participants": groups.nunique(),
                "folds": 5,
                "maximum_participant_overlap": maximum_overlap,
                "r2": r2_score(target, predictions),
                "mae": mean_absolute_error(target, predictions),
                "rmse": mean_squared_error(
                    target,
                    predictions,
                )
                ** 0.5,
            }
        )
    return pd.DataFrame(rows)


def grouped_profile_prediction(
    frame: pd.DataFrame,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Test whether SART dimensions discriminate neutral control profiles."""
    usable = frame.dropna(
        subset=[
            "participant_id",
            "control_profile",
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
        ]
    ).reset_index(drop=True)
    labels = usable["control_profile"].astype(str).to_numpy()
    groups = usable["participant_id"].astype(str)
    feature_sets = {
        "engagement_only": ["sart_engagement_index"],
        "inhibitory_only": ["sart_inhibitory_stability_index"],
        "two_sart_dimensions": [
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
        ],
    }
    splitter = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=seed,
    )
    rows: list[dict[str, Any]] = []
    for model_name, features in feature_sets.items():
        predictions = np.full(len(usable), "", dtype=object)
        maximum_overlap = 0
        for train, test in splitter.split(usable, labels, groups):
            maximum_overlap = max(
                maximum_overlap,
                len(set(groups.iloc[train]) & set(groups.iloc[test])),
            )
            model = make_pipeline(
                RobustScaler(),
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=3000,
                    random_state=seed,
                ),
            )
            model.fit(usable.iloc[train][features], labels[train])
            predictions[test] = model.predict(usable.iloc[test][features])
        rows.append(
            {
                "model": model_name,
                "features": ";".join(features),
                "n_sessions": len(usable),
                "n_participants": groups.nunique(),
                "folds": 5,
                "maximum_participant_overlap": maximum_overlap,
                "balanced_accuracy": balanced_accuracy_score(
                    labels,
                    predictions,
                ),
                "chance_accuracy": 1 / len(np.unique(labels)),
            }
        )
    return pd.DataFrame(rows)


def overloaded_engagement_check(
    frame: pd.DataFrame,
    profiles: pd.DataFrame,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Check whether the overloaded candidate contains SART subgroups."""
    match = profiles[
        profiles["provisional_pattern_note"].eq("overloaded_control_candidate")
    ]
    if match.empty:
        return pd.DataFrame(
            [{"status": "unavailable", "reason": "no_overloaded_candidate"}]
        )
    profile = str(match.iloc[0]["control_profile"])
    subset = frame[frame["control_profile"].eq(profile)].dropna(
        subset=[
            "sart_engagement_index",
            "sart_inhibitory_stability_index",
        ]
    )
    values = RobustScaler().fit_transform(
        subset[
            ["sart_engagement_index", "sart_inhibitory_stability_index"]
        ]
    )
    rows: list[dict[str, Any]] = []
    for k in (1, 2):
        model = GaussianMixture(
            n_components=k,
            covariance_type="full",
            n_init=20,
            random_state=seed,
            reg_covar=1e-6,
        )
        labels = model.fit_predict(values)
        counts = np.bincount(labels, minlength=k)
        rows.append(
            {
                "status": "ok",
                "control_profile": profile,
                "model": f"overloaded-SART-GMM{k}",
                "k": k,
                "n_sessions": len(subset),
                "n_participants": subset["participant_id"].nunique(),
                "bic": model.bic(values),
                "aic": model.aic(values),
                "component_sizes": ";".join(map(str, sorted(counts))),
                "valid_components": bool(
                    np.all(counts >= 20)
                    and np.all(counts / len(labels) >= 0.10)
                ),
            }
        )
        if k == 2:
            labelled = subset.copy()
            labelled["sart_subgroup"] = labels
            subgroup_means = labelled.groupby("sart_subgroup")[
                [
                    "sart_engagement_index",
                    "sart_inhibitory_stability_index",
                    "sart_omission_rate",
                    "sart_go_rt_cv",
                    "sart_commission_rate",
                ]
            ].mean()
            rows[-1]["subgroup_means"] = subgroup_means.to_json()
    return pd.DataFrame(rows)
