"""Participant-grouped tests for dataset and task confounding."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler


def _cv_score(
    frame: pd.DataFrame,
    features: list[str],
    labels: pd.Series,
    groups: pd.Series,
    seed: int,
) -> tuple[float, int, int]:
    group_targets = pd.DataFrame({"group": groups, "label": labels}).drop_duplicates()
    per_class_groups = group_targets.groupby("label")["group"].nunique()
    n_splits = min(5, int(per_class_groups.min()))
    if n_splits < 2:
        return np.nan, n_splits, 0
    splitter = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=seed,
    )
    scores: list[float] = []
    maximum_group_overlap = 0
    x = frame[features]
    for train_index, test_index in splitter.split(x, labels, groups):
        overlap = set(groups.iloc[train_index]) & set(groups.iloc[test_index])
        maximum_group_overlap = max(maximum_group_overlap, len(overlap))
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            RobustScaler(),
            OneVsRestClassifier(
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=500,
                    random_state=seed,
                    solver="liblinear",
                ),
                n_jobs=1,
            ),
        )
        model.fit(x.iloc[train_index], labels.iloc[train_index])
        predictions = model.predict(x.iloc[test_index])
        scores.append(
            balanced_accuracy_score(labels.iloc[test_index], predictions)
        )
    return float(np.mean(scores)), n_splits, maximum_group_overlap


def grouped_confound_test(
    frame: pd.DataFrame,
    features: list[str],
    target_column: str,
    group_column: str = "participant_id",
    permutations: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    """Measure source predictability without participant leakage."""
    usable = frame.dropna(subset=[target_column, group_column]).reset_index(drop=True)
    labels = usable[target_column].astype("string")
    groups = usable[group_column].astype("string")
    class_count = int(labels.nunique())
    if class_count < 2:
        return {
            "status": "not_applicable",
            "reason": f"{target_column} has fewer than two classes",
        }
    observed, n_splits, maximum_group_overlap = _cv_score(
        usable,
        features,
        labels,
        groups,
        seed,
    )
    if not np.isfinite(observed):
        return {
            "status": "not_testable",
            "reason": "insufficient participant groups per class",
            "n_splits": n_splits,
        }

    rng = np.random.default_rng(seed)
    group_labels = (
        pd.DataFrame({"group": groups, "label": labels})
        .drop_duplicates("group")
        .set_index("group")["label"]
    )
    permutation_scores: list[float] = []
    for index in range(permutations):
        shuffled_values = rng.permutation(group_labels.to_numpy())
        shuffled_map = dict(zip(group_labels.index, shuffled_values, strict=True))
        shuffled_labels = groups.map(shuffled_map).astype("string")
        score, _, _ = _cv_score(
            usable,
            features,
            shuffled_labels,
            groups,
            seed + index + 1,
        )
        if np.isfinite(score):
            permutation_scores.append(score)
    chance = 1.0 / class_count
    normalized_improvement = (observed - chance) / (1.0 - chance)
    p_value = (
        (1 + sum(score >= observed for score in permutation_scores))
        / (1 + len(permutation_scores))
        if permutation_scores
        else np.nan
    )
    substantial = bool(
        normalized_improvement >= 0.25
        and np.isfinite(p_value)
        and p_value < 0.01
    )
    return {
        "status": "ok",
        "target": target_column,
        "classifier": "class-balanced multinomial logistic regression",
        "features": features,
        "classes": class_count,
        "participant_groups": int(groups.nunique()),
        "n_splits": n_splits,
        "maximum_participant_group_overlap": maximum_group_overlap,
        "balanced_accuracy": observed,
        "chance_balanced_accuracy": chance,
        "normalized_improvement_over_chance": normalized_improvement,
        "permutation_p_value": p_value,
        "permutations_completed": len(permutation_scores),
        "substantial_confounding": substantial,
    }
