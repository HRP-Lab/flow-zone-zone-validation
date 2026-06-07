"""Residualise cognitive features against measured covariates."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def residualise_features(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    covariate_columns: Sequence[str],
    suffix: str = "_residual",
) -> pd.DataFrame:
    """Add OLS residuals while retaining rows with incomplete covariates."""
    missing = (set(feature_columns) | set(covariate_columns)) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    output = frame.copy()
    covariates = pd.get_dummies(
        frame[list(covariate_columns)],
        drop_first=True,
        dtype=float,
    )
    covariates.insert(0, "intercept", 1.0)

    for feature in feature_columns:
        response = pd.to_numeric(frame[feature], errors="coerce")
        valid = response.notna() & covariates.notna().all(axis=1)
        residuals = pd.Series(np.nan, index=frame.index, dtype=float)
        if valid.sum() > covariates.shape[1]:
            design = covariates.loc[valid].to_numpy(dtype=float)
            values = response.loc[valid].to_numpy(dtype=float)
            coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
            residuals.loc[valid] = values - design @ coefficients
        output[f"{feature}{suffix}"] = residuals
    return output
