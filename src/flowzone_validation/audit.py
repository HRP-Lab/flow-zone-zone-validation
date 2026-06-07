"""Quality gates and Markdown audit reporting."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd

from .cognitive_features import PRIMARY_CLUSTER_CANDIDATES
from .config import PilotConfig


def _select_features(
    frame: pd.DataFrame,
    config: PilotConfig,
) -> tuple[list[str], dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "structurally_unavailable": [],
        "too_missing": [],
        "degenerate": [],
        "dropped_for_complete_cases": [],
        "missing_fraction": {},
        "imputation_fraction": {},
    }
    selected: list[str] = []
    for feature in PRIMARY_CLUSTER_CANDIDATES:
        if feature not in frame or frame[feature].notna().sum() == 0:
            diagnostics["structurally_unavailable"].append(feature)
            continue
        missing_fraction = float(frame[feature].isna().mean())
        diagnostics["missing_fraction"][feature] = missing_fraction
        if missing_fraction > config.maximum_feature_missing_fraction:
            diagnostics["too_missing"].append(feature)
            continue
        if frame[feature].nunique(dropna=True) <= 1:
            diagnostics["degenerate"].append(feature)
            continue
        selected.append(feature)

    def complete_fraction(columns: list[str]) -> float:
        if not columns:
            return 0.0
        return float(frame[columns].notna().all(axis=1).mean())

    while (
        len(selected) > config.minimum_clustering_features
        and complete_fraction(selected) < config.minimum_complete_window_fraction
    ):
        drop = max(
            selected,
            key=lambda feature: diagnostics["missing_fraction"][feature],
        )
        selected.remove(drop)
        diagnostics["dropped_for_complete_cases"].append(drop)

    diagnostics["complete_window_fraction_before_imputation"] = complete_fraction(
        selected
    )
    diagnostics["imputation_fraction"] = {
        feature: float(frame[feature].isna().mean()) for feature in selected
    }
    return selected, diagnostics


def evaluate_audit(
    windows: pd.DataFrame,
    config: PilotConfig,
    trials: pd.DataFrame | None = None,
    inventory: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Evaluate task gates without running any models."""
    primary = windows[
        windows["window_size"].eq(config.primary_window_size)
        & windows["window_kind"].eq("full")
        & windows["dynamics_eligible"].eq(True)
    ].copy()
    tasks: dict[str, Any] = {}
    for task, task_frame in primary.groupby("task_family", sort=True):
        selected, diagnostics = _select_features(task_frame, config)
        gate_reasons: list[str] = []
        window_count = int(len(task_frame))
        dataset_count = int(task_frame["dataset_id"].nunique())
        if window_count < config.minimum_task_windows:
            gate_reasons.append(
                f"{window_count} windows < {config.minimum_task_windows}"
            )
        if dataset_count < config.minimum_task_datasets:
            gate_reasons.append(
                f"{dataset_count} datasets < {config.minimum_task_datasets}"
            )
        if len(selected) < config.minimum_clustering_features:
            gate_reasons.append(
                f"{len(selected)} eligible features < "
                f"{config.minimum_clustering_features}"
            )
        complete_fraction = diagnostics[
            "complete_window_fraction_before_imputation"
        ]
        if complete_fraction < config.minimum_complete_window_fraction:
            gate_reasons.append(
                f"complete-window fraction {complete_fraction:.3f} < "
                f"{config.minimum_complete_window_fraction:.3f}"
            )
        tasks[str(task)] = {
            "eligible": not gate_reasons,
            "gate_reasons": gate_reasons,
            "window_count": window_count,
            "participant_count": int(task_frame["participant_id"].nunique()),
            "dataset_count": dataset_count,
            "selected_features": selected,
            **diagnostics,
        }

    payload: dict[str, Any] = {
        "config": asdict(config),
        "window_rows": int(len(windows)),
        "primary_full_windows": int(len(primary)),
        "task_gates": tasks,
        "feature_missing_fraction": {
            column: float(windows[column].isna().mean())
            for column in PRIMARY_CLUSTER_CANDIDATES
            if column in windows
        },
    }
    if trials is not None:
        payload["trials"] = {
            "rows": int(len(trials)),
            "datasets": int(trials["dataset_id"].nunique()),
            "participants": int(trials["participant_id"].nunique()),
            "rt_excluded_fraction": float(trials["rt_excluded"].mean()),
            "nonresponse_fraction": float(trials["lapse_proxy"].mean()),
            "practice_trial_fraction": float(trials["practice_block"].mean()),
            "unknown_congruency_rows": int(
                trials["congruency"].astype("string").eq("unknown").sum()
            ),
            "residualisation_status": {
                str(key): int(value)
                for key, value in trials["residualisation_status"]
                .value_counts(dropna=False)
                .items()
            },
        }
    if inventory is not None:
        payload["inventory"] = {
            "rows": int(len(inventory)),
            "target_datasets": int(inventory["suitable_target_task"].sum())
            if "suitable_target_task" in inventory
            else None,
            "task_names": sorted(
                inventory["task_name_raw"].dropna().astype(str).unique().tolist()
            ),
        }
    return payload


def render_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ACDC Data Audit",
        "",
        "> ACDC is treated as a conflict-control analogue. This report does not "
        "validate CCC bits/second, MFT-M, or brain states.",
        "",
        "## Overview",
        "",
        f"- Window rows: {payload['window_rows']:,}",
        f"- Primary full windows: {payload['primary_full_windows']:,}",
    ]
    trials = payload.get("trials")
    if trials:
        lines.extend(
            [
                f"- Trial rows: {trials['rows']:,}",
                f"- Datasets: {trials['datasets']:,}",
                f"- Dataset-scoped participants: {trials['participants']:,}",
                f"- RT exclusion fraction: {trials['rt_excluded_fraction']:.3f}",
                f"- Non-response fraction: {trials['nonresponse_fraction']:.3f}",
                f"- Practice-trial fraction retained but not windowed: "
                f"{trials['practice_trial_fraction']:.3f}",
                f"- Unknown congruency rows: {trials['unknown_congruency_rows']:,}",
            ]
        )
    lines.extend(["", "## Modelling Gates", ""])
    if not payload["task_gates"]:
        lines.append("No primary full windows were available. Modelling is blocked.")
    for task, gate in payload["task_gates"].items():
        status = "PASS" if gate["eligible"] else "FAIL"
        lines.extend(
            [
                f"### {task}: {status}",
                "",
                f"- Windows: {gate['window_count']:,}",
                f"- Participants: {gate['participant_count']:,}",
                f"- Datasets: {gate['dataset_count']:,}",
                "- Selected features: "
                + (
                    ", ".join(f"`{value}`" for value in gate["selected_features"])
                    if gate["selected_features"]
                    else "none"
                ),
                "- Complete-window fraction before imputation: "
                f"{gate['complete_window_fraction_before_imputation']:.3f}",
            ]
        )
        if gate["gate_reasons"]:
            lines.append(
                "- Gate failures: "
                + "; ".join(gate["gate_reasons"])
            )
        if gate["structurally_unavailable"]:
            lines.append(
                "- Structurally unavailable/not observed: "
                + ", ".join(gate["structurally_unavailable"])
            )
        if gate["too_missing"]:
            lines.append(
                "- Excluded for missingness: " + ", ".join(gate["too_missing"])
            )
        if gate["degenerate"]:
            lines.append(
                "- Excluded as degenerate: " + ", ".join(gate["degenerate"])
            )
        if gate["dropped_for_complete_cases"]:
            lines.append(
                "- Dropped to preserve complete-window support: "
                + ", ".join(gate["dropped_for_complete_cases"])
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation Boundary",
            "",
            "Passing a gate permits exploratory modelling only. Failure is a useful "
            "result and is recorded instead of being bypassed.",
            "",
        ]
    )
    return "\n".join(lines)


def median_impute_selected(
    frame: pd.DataFrame,
    selected_features: list[str],
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Minimally impute selected, conceptually available task features."""
    output = frame.copy()
    rates: dict[str, float] = {}
    for feature in selected_features:
        rates[feature] = float(output[feature].isna().mean())
        median = output[feature].median(skipna=True)
        if not np.isfinite(median):
            raise ValueError(f"Cannot impute structurally unavailable feature: {feature}")
        output[feature] = output[feature].fillna(median)
    return output, rates
