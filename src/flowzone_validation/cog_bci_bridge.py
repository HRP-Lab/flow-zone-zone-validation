"""Window construction and analysis helpers for the COG-BCI HRV bridge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import resample_poly

from .cog_bci_io import (
    TASK_FILES,
    annotation_events,
    behavioral_trials,
    extracted_task,
    load_eeglab_task,
    matb_window_features,
)
from .hrv_features import (
    detect_r_peaks,
    filter_ecg,
    hrv_features_from_peaks,
    interval_window_bounds,
    peak_concordance_for_window,
)


TIME_DOMAIN_FEATURES = [
    "mean_hr_bpm",
    "mean_nn_ms",
    "log_rmssd",
    "sdnn_ms",
    "cvnn",
    "pnn20",
    "pnn50",
    "sd1_ms",
    "sd2_ms",
    "sd1_sd2",
    "hr_slope_bpm_per_min",
    "nn_slope_ms_per_min",
]

DYNAMICS_FEATURES = [
    "hrv_dfa_alpha1",
    "hrv_lag1",
    "hrv_roughness",
    "hrv_sign_change",
    "hrv_perm_entropy3",
    "hrv_difference_entropy",
    "hrv_sample_entropy",
]

COGNITIVE_FEATURES = [
    "pvt_reciprocal_rt",
    "pvt_median_rt_ms",
    "pvt_rt_cv",
    "pvt_lapse_rate",
    "pvt_anticipation_rate",
    "pvt_rt_drift_ms_per_trial",
    "flanker_accuracy",
    "flanker_median_rt_ms",
    "flanker_rt_cv",
    "flanker_conflict_rt_cost_ms",
    "flanker_conflict_accuracy_cost",
    "flanker_fast_error_rate",
    "flanker_post_error_adjustment_ms",
    "nback_accuracy",
    "nback_hit_rate",
    "nback_false_alarm_rate",
    "nback_dprime_proxy",
    "nback_median_rt_ms",
    "nback_throughput",
    "matb_tracking_error",
    "matb_monitoring_rt",
    "matb_resource_error",
    "matb_efficacy_raw",
]


@dataclass(frozen=True)
class ParticipantBuildResult:
    windows: pd.DataFrame
    inventory: pd.DataFrame
    errors: pd.DataFrame


def _slope(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.notna()
    if valid.sum() < 3:
        return float("nan")
    x = np.arange(len(numeric), dtype=float)[valid]
    return float(np.polyfit(x, numeric[valid].to_numpy(dtype=float), 1)[0])


def _subset_trials(
    trials: pd.DataFrame,
    start_seconds: float,
    stop_seconds: float,
) -> pd.DataFrame:
    if trials.empty:
        return trials
    return trials.loc[
        trials["onset_seconds"].ge(start_seconds)
        & trials["onset_seconds"].lt(stop_seconds)
    ].copy()


def _pvt_features(trials: pd.DataFrame) -> dict[str, float | int]:
    rt = pd.to_numeric(trials.get("rt_seconds"), errors="coerce")
    valid = rt[(rt >= 0.1) & rt.notna()]
    return {
        "behavioral_trials": int(len(trials)),
        "pvt_reciprocal_rt": (
            float(np.mean(1.0 / valid)) if len(valid) else np.nan
        ),
        "pvt_median_rt_ms": (
            float(valid.median() * 1000) if len(valid) else np.nan
        ),
        "pvt_rt_cv": (
            float(valid.std(ddof=1) / valid.mean())
            if len(valid) > 1 and valid.mean() > 0
            else np.nan
        ),
        "pvt_lapse_rate": (
            float(pd.to_numeric(trials.get("lapse"), errors="coerce").mean())
            if len(trials)
            else np.nan
        ),
        "pvt_anticipation_rate": (
            float(
                pd.to_numeric(
                    trials.get("anticipation"),
                    errors="coerce",
                ).mean()
            )
            if len(trials)
            else np.nan
        ),
        "pvt_rt_drift_ms_per_trial": _slope(rt) * 1000,
    }


def _post_error_adjustment(trials: pd.DataFrame) -> float:
    ordered = trials.sort_values("trial_index", kind="stable")
    correct = pd.to_numeric(ordered["correct"], errors="coerce")
    rt = pd.to_numeric(ordered["rt_seconds"], errors="coerce") * 1000
    previous = correct.shift(1)
    post_error = rt[previous.eq(0) & correct.eq(1)]
    post_correct = rt[previous.eq(1) & correct.eq(1)]
    if post_error.notna().sum() < 2 or post_correct.notna().sum() < 5:
        return float("nan")
    return float(post_error.mean() - post_correct.mean())


def _flanker_features(trials: pd.DataFrame) -> dict[str, float | int]:
    correct = pd.to_numeric(trials.get("correct"), errors="coerce")
    rt = pd.to_numeric(trials.get("rt_seconds"), errors="coerce")
    valid = rt[correct.eq(1) & rt.between(0.15, 3.0)]
    congruency = trials.get("congruency", pd.Series(dtype="string")).astype(
        "string"
    )
    congruent = rt[correct.eq(1) & congruency.eq("congruent")]
    incongruent = rt[correct.eq(1) & congruency.eq("incongruent")]
    congruent_acc = correct[congruency.eq("congruent")]
    incongruent_acc = correct[congruency.eq("incongruent")]
    fast_threshold = (
        float(valid.quantile(0.20)) if len(valid) >= 10 else 0.30
    )
    return {
        "behavioral_trials": int(len(trials)),
        "flanker_accuracy": float(correct.mean()) if len(trials) else np.nan,
        "flanker_median_rt_ms": (
            float(valid.median() * 1000) if len(valid) else np.nan
        ),
        "flanker_rt_cv": (
            float(valid.std(ddof=1) / valid.mean())
            if len(valid) > 1 and valid.mean() > 0
            else np.nan
        ),
        "flanker_conflict_rt_cost_ms": (
            float((incongruent.mean() - congruent.mean()) * 1000)
            if congruent.notna().sum() >= 3
            and incongruent.notna().sum() >= 3
            else np.nan
        ),
        "flanker_conflict_accuracy_cost": (
            float(congruent_acc.mean() - incongruent_acc.mean())
            if congruent_acc.notna().sum() >= 3
            and incongruent_acc.notna().sum() >= 3
            else np.nan
        ),
        "flanker_fast_error_rate": (
            float((correct.eq(0) & rt.le(fast_threshold)).mean())
            if len(trials)
            else np.nan
        ),
        "flanker_post_error_adjustment_ms": _post_error_adjustment(trials),
    }


def _nback_features(trials: pd.DataFrame) -> dict[str, float | int]:
    correct = pd.to_numeric(trials.get("correct"), errors="coerce")
    rt = pd.to_numeric(trials.get("rt_seconds"), errors="coerce")
    trial_type = trials.get(
        "trial_type",
        pd.Series(index=trials.index, dtype="string"),
    ).astype("string")
    hit_trials = trial_type.eq("hit")
    non_hit = ~hit_trials
    hit_rate = correct[hit_trials].mean()
    false_alarm_rate = (1 - correct[non_hit]).mean()
    median_rt = rt[correct.eq(1) & rt.between(0.15, 3.0)].median()
    accuracy = correct.mean()
    return {
        "behavioral_trials": int(len(trials)),
        "nback_accuracy": float(accuracy) if pd.notna(accuracy) else np.nan,
        "nback_hit_rate": float(hit_rate) if pd.notna(hit_rate) else np.nan,
        "nback_false_alarm_rate": (
            float(false_alarm_rate)
            if pd.notna(false_alarm_rate)
            else np.nan
        ),
        "nback_dprime_proxy": (
            float(hit_rate - false_alarm_rate)
            if pd.notna(hit_rate) and pd.notna(false_alarm_rate)
            else np.nan
        ),
        "nback_median_rt_ms": (
            float(median_rt * 1000) if pd.notna(median_rt) else np.nan
        ),
        "nback_throughput": (
            float(accuracy / median_rt)
            if pd.notna(accuracy) and pd.notna(median_rt) and median_rt > 0
            else np.nan
        ),
    }


def behavioral_window_features(
    task: str,
    trials: pd.DataFrame,
    behavior_path: Path | str,
    start_seconds: float,
    stop_seconds: float,
    task_duration_seconds: float,
) -> dict[str, float | int]:
    if task.startswith("MATB"):
        return {
            "behavioral_trials": np.nan,
            **matb_window_features(
                behavior_path,
                start_fraction=start_seconds / task_duration_seconds,
                stop_fraction=stop_seconds / task_duration_seconds,
            ),
        }
    selected = _subset_trials(trials, start_seconds, stop_seconds)
    if task == "PVT":
        return _pvt_features(selected)
    if task == "Flanker":
        return _flanker_features(selected)
    if task.startswith("NBack"):
        return _nback_features(selected)
    return {"behavioral_trials": int(len(selected))}


def process_task(
    set_path: Path | str,
    behavior_path: Path | str,
    participant_id: str,
    session_id: str,
    task: str,
    task_order: int | None,
    window_durations: tuple[int | str, ...] = (10, 60, 120, 180, "full"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw = load_eeglab_task(set_path)
    sampling_rate = float(raw.info["sfreq"])
    signal = raw.get_data(picks=["ECG1"])[0]
    duration_seconds = float(raw.n_times / sampling_rate)
    events = annotation_events(raw)
    trials = behavioral_trials(task, behavior_path, events)

    extended_signal = filter_ecg(signal, sampling_rate)
    extended_detection = detect_r_peaks(extended_signal, sampling_rate)

    replication_signal = resample_poly(signal, up=1, down=2)
    replication_rate = sampling_rate / 2
    replication_filtered = filter_ecg(
        replication_signal,
        replication_rate,
        low_hz=1.0,
        high_hz=40.0,
        notch_hz=None,
    )
    replication_detection = detect_r_peaks(
        replication_filtered,
        replication_rate,
    )

    rows: list[dict[str, Any]] = []
    for duration in window_durations:
        role = "replication" if duration == 10 else (
            "benchmark" if duration == "full" else "extended"
        )
        for window_index, start_seconds, stop_seconds in interval_window_bounds(
            duration_seconds,
            duration,
        ):
            if role == "replication":
                rate = replication_rate
                detection = replication_detection
            else:
                rate = sampling_rate
                detection = extended_detection
            start_sample = round(start_seconds * rate)
            stop_sample = round(stop_seconds * rate)
            concordance, unmatched_rate = peak_concordance_for_window(
                detection,
                start_sample,
                stop_sample,
                rate,
            )
            hrv = hrv_features_from_peaks(
                detection.primary,
                rate,
                start_sample,
                stop_sample,
                concordance,
                unmatched_rate,
                minimum_beats=5 if role == "replication" else 30,
            )
            behavior = behavioral_window_features(
                task,
                trials,
                behavior_path,
                start_seconds,
                stop_seconds,
                duration_seconds,
            )
            rows.append(
                {
                    "participant_id": participant_id,
                    "participant_number": int(participant_id.split("-")[-1]),
                    "session_id": session_id,
                    "session_number": int(session_id.split("-S")[-1]),
                    "task": task,
                    "task_family": (
                        "NBack"
                        if task.startswith("NBack")
                        else "MATB"
                        if task.startswith("MATB")
                        else task
                    ),
                    "condition": task,
                    "block_id": f"{participant_id}:{session_id}:{task}",
                    "task_order": task_order,
                    "window_id": (
                        f"{participant_id}:{session_id}:{task}:"
                        f"{duration}:{window_index}"
                    ),
                    "window_seconds": (
                        duration_seconds if duration == "full" else int(duration)
                    ),
                    "window_label": str(duration),
                    "window_index": window_index,
                    "window_start_seconds": start_seconds,
                    "window_stop_seconds": stop_seconds,
                    "time_on_task_fraction": (
                        (start_seconds + stop_seconds)
                        / (2 * duration_seconds)
                    ),
                    "analysis_role": role,
                    **hrv,
                    **behavior,
                }
            )
    inventory = {
        "participant_id": participant_id,
        "session_id": session_id,
        "task": task,
        "sampling_rate_hz": sampling_rate,
        "ecg_channel": "ECG1",
        "duration_seconds": duration_seconds,
        "n_annotations": int(len(events)),
        "n_behavioral_trials": int(len(trials)),
        "primary_r_peaks": int(len(extended_detection.primary)),
        "sensitivity_r_peaks": int(len(extended_detection.sensitivity)),
        "detector_concordance": extended_detection.concordance,
        "detector_unmatched_rate": extended_detection.unmatched_rate,
    }
    return pd.DataFrame(rows), inventory


def process_participant_archive(
    archive_path: Path | str,
    participant_id: str,
    task_orders: pd.DataFrame,
    tasks: tuple[str, ...] = tuple(
        [
            "PVT",
            "Flanker",
            "NBack0",
            "NBack1",
            "NBack2",
            "MATBEasy",
            "MATBMedium",
            "MATBDifficult",
        ]
    ),
    sessions: tuple[str, ...] = ("ses-S1", "ses-S2", "ses-S3"),
    temporary_root: Path | str | None = None,
    checkpoint_dir: Path | str | None = None,
) -> ParticipantBuildResult:
    windows: list[pd.DataFrame] = []
    inventory: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for session_id in sessions:
        session_number = int(session_id.split("-S")[-1])
        participant_number = int(participant_id.split("-")[-1])
        order_rows = task_orders.loc[
            task_orders["participant_number"].eq(participant_number)
            & task_orders["session_number"].eq(session_number)
        ]
        order_lookup = dict(
            zip(order_rows["task"], order_rows["task_order"], strict=False)
        )
        for task in tasks:
            checkpoint_stem = f"{participant_id}_{session_id}_{task}"
            checkpoint_windows = (
                Path(checkpoint_dir) / f"{checkpoint_stem}_windows.parquet"
                if checkpoint_dir
                else None
            )
            checkpoint_inventory = (
                Path(checkpoint_dir) / f"{checkpoint_stem}_inventory.csv"
                if checkpoint_dir
                else None
            )
            try:
                if (
                    checkpoint_windows is not None
                    and checkpoint_inventory is not None
                    and checkpoint_windows.exists()
                    and checkpoint_inventory.exists()
                ):
                    windows.append(pd.read_parquet(checkpoint_windows))
                    inventory.extend(
                        pd.read_csv(checkpoint_inventory).to_dict("records")
                    )
                    continue
                with extracted_task(
                    archive_path,
                    participant_id,
                    session_id,
                    task,
                    temporary_root=temporary_root,
                ) as extracted:
                    task_windows, task_inventory = process_task(
                        extracted.set_path,
                        extracted.behavior_path,
                        participant_id,
                        session_id,
                        task,
                        task_order=order_lookup.get(task),
                    )
                windows.append(task_windows)
                inventory.append(task_inventory)
                if (
                    checkpoint_windows is not None
                    and checkpoint_inventory is not None
                ):
                    checkpoint_windows.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )
                    task_windows.to_parquet(
                        checkpoint_windows,
                        index=False,
                    )
                    pd.DataFrame([task_inventory]).to_csv(
                        checkpoint_inventory,
                        index=False,
                    )
            except Exception as error:
                errors.append(
                    {
                        "participant_id": participant_id,
                        "session_id": session_id,
                        "task": task,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )
    return ParticipantBuildResult(
        windows=(
            pd.concat(windows, ignore_index=True)
            if windows
            else pd.DataFrame()
        ),
        inventory=pd.DataFrame(inventory),
        errors=pd.DataFrame(errors),
    )


def process_participant_directory(
    participant_root: Path | str,
    participant_id: str,
    task_orders: pd.DataFrame,
    tasks: tuple[str, ...] = tuple(TASK_FILES),
    sessions: tuple[str, ...] = ("ses-S1", "ses-S2", "ses-S3"),
    checkpoint_dir: Path | str | None = None,
) -> ParticipantBuildResult:
    """Process a participant directory extracted by the native runner."""
    root = Path(participant_root)
    windows: list[pd.DataFrame] = []
    inventory: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    participant_number = int(participant_id.split("-")[-1])
    for session_id in sessions:
        session_number = int(session_id.split("-S")[-1])
        order_rows = task_orders.loc[
            task_orders["participant_number"].eq(participant_number)
            & task_orders["session_number"].eq(session_number)
        ]
        order_lookup = dict(
            zip(order_rows["task"], order_rows["task_order"], strict=False)
        )
        for task in tasks:
            eeg_stem, behavior_name = TASK_FILES[task]
            set_path = root / session_id / "eeg" / f"{eeg_stem}.set"
            behavior_path = (
                root / session_id / "behavioral" / behavior_name
            )
            checkpoint_stem = f"{participant_id}_{session_id}_{task}"
            checkpoint_windows = (
                Path(checkpoint_dir) / f"{checkpoint_stem}_windows.parquet"
                if checkpoint_dir
                else None
            )
            checkpoint_inventory = (
                Path(checkpoint_dir) / f"{checkpoint_stem}_inventory.csv"
                if checkpoint_dir
                else None
            )
            try:
                if (
                    checkpoint_windows is not None
                    and checkpoint_inventory is not None
                    and checkpoint_windows.exists()
                    and checkpoint_inventory.exists()
                ):
                    windows.append(pd.read_parquet(checkpoint_windows))
                    inventory.extend(
                        pd.read_csv(checkpoint_inventory).to_dict("records")
                    )
                    continue
                if not set_path.exists() or not behavior_path.exists():
                    raise FileNotFoundError(
                        f"Missing extracted task files for {task}"
                    )
                task_windows, task_inventory = process_task(
                    set_path,
                    behavior_path,
                    participant_id,
                    session_id,
                    task,
                    task_order=order_lookup.get(task),
                )
                windows.append(task_windows)
                inventory.append(task_inventory)
                if (
                    checkpoint_windows is not None
                    and checkpoint_inventory is not None
                ):
                    checkpoint_windows.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )
                    task_windows.to_parquet(
                        checkpoint_windows,
                        index=False,
                    )
                    pd.DataFrame([task_inventory]).to_csv(
                        checkpoint_inventory,
                        index=False,
                    )
            except Exception as error:
                errors.append(
                    {
                        "participant_id": participant_id,
                        "session_id": session_id,
                        "task": task,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )
    return ParticipantBuildResult(
        windows=(
            pd.concat(windows, ignore_index=True)
            if windows
            else pd.DataFrame()
        ),
        inventory=pd.DataFrame(inventory),
        errors=pd.DataFrame(errors),
    )
