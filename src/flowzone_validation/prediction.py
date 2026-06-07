"""Participant-grouped next-window prediction comparisons."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler


def grouped_ridge_metrics(
    frame: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
    target: str,
    group_column: str = "participant_id",
    folds: int = 5,
    alpha: float = 1.0,
) -> dict[str, Any]:
    """Return out-of-fold ridge metrics with participant-isolated folds."""
    required = {
        target,
        group_column,
        *numeric_features,
        *categorical_features,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing prediction columns: {sorted(missing)}")

    usable = frame.dropna(subset=[target, group_column]).reset_index(drop=True)
    groups = usable[group_column].astype("string")
    n_groups = int(groups.nunique())
    n_splits = min(folds, n_groups)
    if n_splits < 2 or len(usable) < max(20, n_splits * 4):
        return {
            "status": "not_testable",
            "reason": "insufficient rows or participant groups",
            "n_windows": int(len(usable)),
            "n_subjects": n_groups,
            "folds": n_splits,
        }

    transformers: list[tuple[str, object, list[str]]] = []
    if numeric_features:
        transformers.append(
            (
                "numeric",
                make_pipeline(
                    SimpleImputer(strategy="median", add_indicator=True),
                    RobustScaler(),
                ),
                numeric_features,
            )
        )
    if categorical_features:
        transformers.append(
            (
                "categorical",
                make_pipeline(
                    SimpleImputer(strategy="most_frequent"),
                    OneHotEncoder(handle_unknown="ignore"),
                ),
                categorical_features,
            )
        )
    if not transformers:
        raise ValueError("At least one prediction feature is required")

    x = usable[numeric_features + categorical_features].copy()
    for feature in numeric_features:
        x[feature] = pd.to_numeric(x[feature], errors="coerce").astype(float)
    y = pd.to_numeric(usable[target], errors="coerce").to_numpy(dtype=float)
    splitter = GroupKFold(n_splits=n_splits)
    predictions = np.full(len(usable), np.nan, dtype=float)
    maximum_group_overlap = 0
    for train_index, test_index in splitter.split(x, y, groups):
        overlap = set(groups.iloc[train_index]) & set(groups.iloc[test_index])
        maximum_group_overlap = max(maximum_group_overlap, len(overlap))
        model = make_pipeline(
            ColumnTransformer(transformers, remainder="drop"),
            Ridge(alpha=alpha),
        )
        model.fit(x.iloc[train_index], y[train_index])
        predictions[test_index] = model.predict(x.iloc[test_index])

    valid = np.isfinite(predictions) & np.isfinite(y)
    if valid.sum() < 2:
        return {
            "status": "not_testable",
            "reason": "cross-validation produced insufficient predictions",
            "n_windows": int(len(usable)),
            "n_subjects": n_groups,
            "folds": n_splits,
        }
    return {
        "status": "ok",
        "r2": float(r2_score(y[valid], predictions[valid])),
        "mae": float(mean_absolute_error(y[valid], predictions[valid])),
        "rmse": float(
            np.sqrt(mean_squared_error(y[valid], predictions[valid]))
        ),
        "folds": n_splits,
        "n_windows": int(valid.sum()),
        "n_subjects": n_groups,
        "maximum_participant_group_overlap": maximum_group_overlap,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
    }


def compare_prediction_models(
    frame: pd.DataFrame,
    model_features: dict[str, list[str]],
    targets: list[str],
    source_categoricals: list[str],
    cluster_column: str,
    folds: int = 5,
    alpha: float = 1.0,
) -> pd.DataFrame:
    """Compare fixed feature blocks using identical grouped fold rules."""
    rows: list[dict[str, Any]] = []
    for target in targets:
        for model_name, candidates in model_features.items():
            numeric = [
                feature
                for feature in candidates
                if feature in frame and frame[feature].notna().any()
            ]
            categoricals = list(source_categoricals)
            if model_name == "Model E":
                categoricals.append(cluster_column)
            metrics = grouped_ridge_metrics(
                frame,
                numeric,
                categoricals,
                target,
                folds=folds,
                alpha=alpha,
            )
            rows.append(
                {
                    "target": target,
                    "model": model_name,
                    "status": metrics["status"],
                    "r2": metrics.get("r2"),
                    "mae": metrics.get("mae"),
                    "rmse": metrics.get("rmse"),
                    "folds": metrics.get("folds"),
                    "n_windows": metrics.get("n_windows"),
                    "n_subjects": metrics.get("n_subjects"),
                    "maximum_participant_group_overlap": metrics.get(
                        "maximum_participant_group_overlap"
                    ),
                    "numeric_features": "|".join(numeric),
                    "categorical_features": "|".join(categoricals),
                    "reason": metrics.get("reason"),
                }
            )
    output = pd.DataFrame(rows)
    if output.empty:
        return output
    pivot = output.pivot(index="target", columns="model", values="r2")
    output["delta_r2_vs_model_a"] = [
        (
            row.r2 - pivot.loc[row.target, "Model A"]
            if row.status == "ok"
            and "Model A" in pivot
            and pd.notna(pivot.loc[row.target, "Model A"])
            else np.nan
        )
        for row in output.itertuples(index=False)
    ]
    output["delta_r2_vs_model_b"] = [
        (
            row.r2 - pivot.loc[row.target, "Model B"]
            if row.status == "ok"
            and "Model B" in pivot
            and pd.notna(pivot.loc[row.target, "Model B"])
            else np.nan
        )
        for row in output.itertuples(index=False)
    ]
    return output
