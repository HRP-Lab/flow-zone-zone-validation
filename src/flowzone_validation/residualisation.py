"""Residualisation for trial RTs and pooled window features."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def _zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    standard_deviation = numeric.std(ddof=0)
    if not np.isfinite(standard_deviation) or standard_deviation == 0:
        return pd.Series(
            np.where(numeric.notna(), 0.0, np.nan),
            index=values.index,
            dtype=float,
        )
    return (numeric - numeric.mean()) / standard_deviation


def _design_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    categoricals = [
        column
        for column in (
            "congruency",
            "block_raw",
            "within_id",
            "between_id",
        )
        if column in frame
    ]
    categorical_frame = frame[categoricals].astype("string").fillna("__missing__")
    design = pd.get_dummies(
        categorical_frame,
        drop_first=True,
        dtype=float,
    )
    trial = pd.to_numeric(frame["trial_raw"], errors="coerce")
    trial = trial.fillna(trial.median())
    scale = trial.std(ddof=0)
    design["trial_trend"] = (
        (trial - trial.mean()) / scale if np.isfinite(scale) and scale > 0 else 0.0
    )
    return design


def _fit_fixed_effect_residuals(
    response: pd.Series,
    design: pd.DataFrame,
    participants: pd.Series,
    fit_mask: pd.Series,
    apply_mask: pd.Series,
) -> tuple[pd.Series, pd.Series, str]:
    fit_mask = fit_mask & response.notna() & design.notna().all(axis=1)
    apply_mask = apply_mask & response.notna() & design.notna().all(axis=1)
    residuals = pd.Series(np.nan, index=response.index, dtype=float)
    expected = pd.Series(np.nan, index=response.index, dtype=float)
    if int(fit_mask.sum()) <= design.shape[1] + 1:
        return residuals, expected, "insufficient_rows_for_design"

    fit_design_frame = design.loc[fit_mask].copy()
    fit_response_series = response.loc[fit_mask].copy()
    fit_participants = participants.loc[fit_mask].astype("string")
    response_group_mean = fit_response_series.groupby(
        fit_participants,
        dropna=False,
    ).transform("mean")
    if fit_design_frame.shape[1]:
        design_group_mean = fit_design_frame.groupby(
            fit_participants,
            dropna=False,
        ).transform("mean")
        demeaned_design = (
            fit_design_frame - design_group_mean
        ).to_numpy(dtype=float)
        demeaned_response = (
            fit_response_series - response_group_mean
        ).to_numpy(dtype=float)
        coefficients, *_ = np.linalg.lstsq(
            demeaned_design,
            demeaned_response,
            rcond=None,
        )
        fit_covariate_prediction = (
            fit_design_frame.to_numpy(dtype=float) @ coefficients
        )
    else:
        coefficients = np.empty(0, dtype=float)
        fit_covariate_prediction = np.zeros(len(fit_design_frame), dtype=float)

    fixed_effect_residual = (
        fit_response_series.to_numpy(dtype=float) - fit_covariate_prediction
    )
    participant_intercepts = pd.Series(
        fixed_effect_residual,
        index=fit_response_series.index,
    ).groupby(fit_participants, dropna=False).mean()
    global_intercept = float(np.mean(fixed_effect_residual))

    apply_design = design.loc[apply_mask]
    if apply_design.shape[1]:
        covariate_prediction = (
            apply_design.to_numpy(dtype=float) @ coefficients
        )
    else:
        covariate_prediction = np.zeros(len(apply_design), dtype=float)
    apply_participants = participants.loc[apply_mask].astype("string")
    intercepts = (
        apply_participants.map(participant_intercepts)
        .fillna(global_intercept)
        .to_numpy(dtype=float)
    )
    predictions = covariate_prediction + intercepts
    expected.loc[apply_mask] = predictions
    residuals.loc[apply_mask] = response.loc[apply_mask] - predictions
    return residuals, expected, "ok"


def residualise_trial_rt(frame: pd.DataFrame) -> pd.DataFrame:
    """Fit expected raw/log RT models independently within each dataset."""
    required = {
        "dataset_id",
        "participant_id",
        "trial_raw",
        "rt_ms",
        "valid_rt",
        "valid_correct_rt",
        "correct",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing residualisation columns: {sorted(missing)}")

    pieces: list[pd.DataFrame] = []
    for _, dataset in frame.groupby("dataset_id", dropna=False, sort=True):
        dataset = dataset.copy()
        design = _design_matrix(dataset)
        participants = dataset["participant_id"]
        raw_response = pd.to_numeric(dataset["rt_ms"], errors="coerce")
        log_response = np.log(raw_response.where(raw_response.gt(0)))
        fit_mask = dataset["valid_correct_rt"].fillna(False)
        apply_mask = dataset["valid_rt"].fillna(False)

        raw_residual, expected_raw, raw_status = _fit_fixed_effect_residuals(
            raw_response,
            design,
            participants,
            fit_mask,
            apply_mask,
        )
        log_residual, expected_log, log_status = _fit_fixed_effect_residuals(
            log_response,
            design,
            participants,
            fit_mask,
            apply_mask,
        )
        dataset["expected_rt_ms"] = expected_raw
        dataset["raw_rt_residual_ms"] = raw_residual
        dataset["expected_log_rt"] = expected_log
        dataset["log_rt_residual"] = log_residual
        dataset["residualisation_status"] = (
            raw_status if raw_status != "ok" else log_status
        )
        pieces.append(dataset)

    output = pd.concat(pieces, ignore_index=True)
    rt_seconds = output["rt_ms"] / 1000.0
    output["efficiency_t"] = np.where(
        output["valid_rt"],
        output["correct"].fillna(0) / rt_seconds,
        np.nan,
    )
    group_columns = ["dataset_id", "participant_id", "task_family", "block_raw"]
    grouped = output.groupby(group_columns, dropna=False, sort=False)
    output["efficiency_z"] = grouped["efficiency_t"].transform(_zscore)
    output["log_rt_residual_z"] = grouped["log_rt_residual"].transform(_zscore)
    output["correct_z"] = grouped["correct"].transform(_zscore)
    output["u_t"] = (
        output["efficiency_z"]
        - output["log_rt_residual_z"]
        + output["correct_z"]
    )
    return output


def robust_scale_within_sources(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    source_columns: Sequence[str] = ("dataset_id", "task_family"),
) -> pd.DataFrame:
    """Median/IQR adjust features within source groups for pooled sensitivity."""
    output = frame.copy()
    missing = (set(feature_columns) | set(source_columns)) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing pooled-adjustment columns: {sorted(missing)}")

    grouped = output.groupby(list(source_columns), dropna=False, sort=False)
    for feature in feature_columns:
        numeric = pd.to_numeric(output[feature], errors="coerce")
        medians = grouped[feature].transform("median")
        q25 = grouped[feature].transform(lambda values: values.quantile(0.25))
        q75 = grouped[feature].transform(lambda values: values.quantile(0.75))
        iqr = q75 - q25
        adjusted = (numeric - medians) / iqr.where(iqr.gt(0))
        output[f"{feature}__source_adjusted"] = adjusted.where(
            iqr.gt(0),
            numeric - medians,
        )
    return output
