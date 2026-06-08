"""COG-BCI Zenodo access, archive handling, and behavioural event parsing."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Iterator
from zipfile import ZipFile

import mne
import numpy as np
import pandas as pd
import requests
from scipy.io import loadmat


ZENODO_RECORD_ID = 7413650
ZENODO_API_URL = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"

TASK_FILES = {
    "PVT": ("PVT", "PVT.mat"),
    "Flanker": ("Flanker", "Flanker.mat"),
    "NBack0": ("zeroBACK", "0-Back.mat"),
    "NBack1": ("oneBACK", "1-Back.mat"),
    "NBack2": ("twoBACK", "2-Back.mat"),
    "MATBEasy": ("MATBeasy", "MATB_Easy.mat"),
    "MATBMedium": ("MATBmed", "MATB_Med.mat"),
    "MATBDifficult": ("MATBdiff", "MATB_Diff.mat"),
}

TASK_ORDER_CODES = {
    1: "MATBEasy",
    2: "MATBMedium",
    3: "MATBDifficult",
    4: "NBack0",
    5: "NBack1",
    6: "NBack2",
    7: "PVT",
    8: "Flanker",
}


@dataclass(frozen=True)
class ZenodoFile:
    key: str
    size: int
    checksum: str
    url: str


@dataclass(frozen=True)
class ExtractedTask:
    set_path: Path
    behavior_path: Path
    participant_id: str
    session_id: str
    task: str


def fetch_zenodo_manifest(timeout_seconds: int = 60) -> list[ZenodoFile]:
    response = requests.get(ZENODO_API_URL, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    return [
        ZenodoFile(
            key=str(item["key"]),
            size=int(item["size"]),
            checksum=str(item["checksum"]),
            url=str(item["links"]["self"]),
        )
        for item in payload["files"]
    ]


def participant_filename(participant_number: int) -> str:
    if participant_number < 1 or participant_number > 29:
        raise ValueError("COG-BCI participant number must be from 1 to 29")
    return f"sub-{participant_number:02d}.zip"


def find_participant_directory(
    extracted_root: Path | str,
    participant_id: str,
) -> Path:
    """Resolve zero-padded and non-padded archive directory names safely."""
    root = Path(extracted_root)
    exact = root / participant_id
    if (exact / "ses-S1").is_dir():
        return exact
    participant_number = int(participant_id.split("-")[-1])
    candidates = []
    for session_directory in root.rglob("ses-S1"):
        directory = session_directory.parent
        if not directory.is_dir():
            continue
        suffix = directory.name.lower().removeprefix("sub-")
        if suffix.isdigit() and int(suffix) == participant_number:
            candidates.append(directory)
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Could not uniquely resolve {participant_id} under {root}; "
            f"candidates={sorted(path.name for path in candidates)}"
        )
    return candidates[0]


def file_digest(path: Path | str, algorithm: str = "md5") -> str:
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_zenodo_file(path: Path | str, metadata: ZenodoFile) -> bool:
    algorithm, expected = metadata.checksum.split(":", maxsplit=1)
    source = Path(path)
    return (
        source.exists()
        and source.stat().st_size == metadata.size
        and file_digest(source, algorithm).lower() == expected.lower()
    )


def download_zenodo_file(
    metadata: ZenodoFile,
    destination: Path | str,
    chunk_size: int = 8 * 1024 * 1024,
    maximum_attempts: int = 8,
) -> Path:
    """Download one file with resumable retries and verify its checksum."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    if verify_zenodo_file(path, metadata):
        return path
    partial = path.with_suffix(path.suffix + ".partial")
    if partial.exists() and partial.stat().st_size > metadata.size:
        partial.unlink()
    last_error: Exception | None = None
    for _ in range(maximum_attempts):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with requests.get(
                metadata.url,
                stream=True,
                headers=headers,
                timeout=(60, 300),
            ) as response:
                response.raise_for_status()
                resume_accepted = offset > 0 and response.status_code == 206
                mode = "ab" if resume_accepted else "wb"
                with partial.open(mode) as handle:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            handle.write(chunk)
        except requests.RequestException as error:
            last_error = error
            continue
        if partial.stat().st_size == metadata.size:
            break
        if partial.stat().st_size > metadata.size:
            partial.unlink()
    if not partial.exists() or partial.stat().st_size != metadata.size:
        raise ConnectionError(
            f"Download did not complete after {maximum_attempts} attempts "
            f"for {metadata.key}"
        ) from last_error
    partial.replace(path)
    if not verify_zenodo_file(path, metadata):
        path.unlink(missing_ok=True)
        raise ValueError(f"Checksum verification failed for {metadata.key}")
    return path


def archive_inventory(archive_path: Path | str) -> pd.DataFrame:
    with ZipFile(archive_path) as archive:
        return pd.DataFrame(
            [
                {
                    "archive_member": item.filename,
                    "uncompressed_bytes": item.file_size,
                    "compressed_bytes": item.compress_size,
                }
                for item in archive.infolist()
                if not item.is_dir()
            ]
        )


@contextmanager
def extracted_task(
    archive_path: Path | str,
    participant_id: str,
    session_id: str,
    task: str,
    temporary_root: Path | str | None = None,
) -> Iterator[ExtractedTask]:
    """Extract exactly one EEGLAB pair and its behavioural file."""
    if task not in TASK_FILES:
        raise ValueError(f"Unknown COG-BCI task: {task}")
    eeg_stem, behavior_name = TASK_FILES[task]
    prefix = f"{participant_id}/{session_id}"
    members = {
        f"{prefix}/eeg/{eeg_stem}.set",
        f"{prefix}/eeg/{eeg_stem}.fdt",
        f"{prefix}/behavioral/{behavior_name}",
    }
    base = Path(temporary_root) if temporary_root else None
    with tempfile.TemporaryDirectory(
        prefix=f"{participant_id}-{session_id}-{task}-",
        dir=base,
    ) as temporary_directory:
        temporary = Path(temporary_directory)
        native_tar = shutil.which("tar")
        if native_tar:
            extraction = subprocess.run(
                [
                    native_tar,
                    "-xf",
                    str(Path(archive_path).resolve()),
                    "-C",
                    str(temporary),
                    *sorted(members),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if extraction.returncode != 0:
                raise FileNotFoundError(
                    "Native archive extraction failed: "
                    f"{extraction.stderr.strip()}"
                )
        else:
            with ZipFile(archive_path) as archive:
                available = set(archive.namelist())
                missing = members - available
                if missing:
                    raise FileNotFoundError(
                        "Archive is missing required task members: "
                        f"{sorted(missing)}"
                    )
                for member in members:
                    target = temporary / member
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        archive.open(member) as source,
                        target.open("wb") as output,
                    ):
                        shutil.copyfileobj(
                            source,
                            output,
                            length=8 * 1024 * 1024,
                        )
        extracted_members = {
            str(path.relative_to(temporary)).replace("\\", "/")
            for path in temporary.rglob("*")
            if path.is_file()
        }
        missing = members - extracted_members
        if missing:
            raise FileNotFoundError(
                f"Archive extraction omitted required members: {sorted(missing)}"
            )
        yield ExtractedTask(
            set_path=temporary / f"{prefix}/eeg/{eeg_stem}.set",
            behavior_path=temporary / f"{prefix}/behavioral/{behavior_name}",
            participant_id=participant_id,
            session_id=session_id,
            task=task,
        )


def load_eeglab_task(set_path: Path | str) -> mne.io.BaseRaw:
    raw = mne.io.read_raw_eeglab(
        Path(set_path),
        preload=False,
        verbose="ERROR",
    )
    if raw.info["sfreq"] != 500:
        raise ValueError(
            f"Expected 500 Hz COG-BCI data, found {raw.info['sfreq']} Hz"
        )
    if "ECG1" not in raw.ch_names:
        raise ValueError("Expected ECG1 channel is absent")
    return raw


def annotation_events(raw: mne.io.BaseRaw) -> pd.DataFrame:
    rows = []
    for onset, duration, description in zip(
        raw.annotations.onset,
        raw.annotations.duration,
        raw.annotations.description,
        strict=True,
    ):
        code = pd.to_numeric(description, errors="coerce")
        if pd.isna(code):
            continue
        rows.append(
            {
                "onset_seconds": float(onset),
                "duration_seconds": float(duration),
                "event_code": int(code),
            }
        )
    frame = pd.DataFrame(
        rows,
        columns=[
            "onset_seconds",
            "duration_seconds",
            "event_code",
        ],
    )
    return frame.sort_values(
        "onset_seconds",
        kind="stable",
    ).reset_index(drop=True)


def _events_to_trials(
    events: pd.DataFrame,
    stimulus_codes: dict[int, dict[str, object]],
    response_codes: dict[int, dict[str, object]],
    stop_codes: set[int] | None = None,
) -> pd.DataFrame:
    trials: list[dict[str, object]] = []
    event_rows = list(events.itertuples(index=False))
    for index, event in enumerate(event_rows):
        if event.event_code not in stimulus_codes:
            continue
        trial = {
            "trial_index": len(trials) + 1,
            "onset_seconds": float(event.onset_seconds),
            "rt_seconds": np.nan,
            "correct": np.nan,
            **stimulus_codes[event.event_code],
        }
        for next_event in event_rows[index + 1 :]:
            if next_event.event_code in stimulus_codes:
                break
            if stop_codes and next_event.event_code in stop_codes:
                break
            if next_event.event_code in response_codes:
                trial.update(response_codes[next_event.event_code])
                trial["rt_seconds"] = float(
                    next_event.onset_seconds - event.onset_seconds
                )
                break
        trials.append(trial)
    return pd.DataFrame(trials)


def pvt_trials(
    behavior_path: Path | str,
    events: pd.DataFrame,
) -> pd.DataFrame:
    payload = loadmat(
        behavior_path,
        squeeze_me=True,
        struct_as_record=False,
    )
    if "PVT" not in payload:
        raise ValueError("PVT behavioural file does not contain PVT")
    pvt = payload["PVT"]
    reaction_times = np.atleast_1d(pvt.reaction_times).astype(float)
    errors = np.atleast_1d(pvt.error_trial).astype(int)
    stimulus_onsets = events.loc[
        events["event_code"].eq(13),
        "onset_seconds",
    ].to_numpy(dtype=float)
    if len(stimulus_onsets) != len(reaction_times):
        raise ValueError(
            "PVT stimulus/event count differs from behavioural RT count"
        )
    return pd.DataFrame(
        {
            "trial_index": np.arange(1, len(reaction_times) + 1),
            "onset_seconds": stimulus_onsets,
            "rt_seconds": reaction_times,
            "correct": 1 - errors,
            "lapse": reaction_times >= 0.5,
            "anticipation": reaction_times < 0.1,
        }
    )


def flanker_trials(events: pd.DataFrame) -> pd.DataFrame:
    return _events_to_trials(
        events,
        stimulus_codes={
            241: {"congruency": "congruent"},
            242: {"congruency": "incongruent"},
        },
        response_codes={
            2511: {"correct": 1},
            2521: {"correct": 0},
            2512: {"correct": 1},
            2522: {"correct": 0},
        },
        stop_codes={25321, 25322},
    )


def nback_trials(events: pd.DataFrame, level: int) -> pd.DataFrame:
    prefix = 60 + level
    return _events_to_trials(
        events,
        stimulus_codes={
            int(f"{prefix}21"): {"trial_type": "normal"},
            int(f"{prefix}22"): {"trial_type": "hit"},
            int(f"{prefix}23"): {"trial_type": "conflict"},
        },
        response_codes={
            int(f"{prefix}31"): {"correct": 0},
            int(f"{prefix}32"): {"correct": 1},
            int(f"{prefix}33"): {"correct": 0},
        },
    )


def behavioral_trials(
    task: str,
    behavior_path: Path | str,
    events: pd.DataFrame,
) -> pd.DataFrame:
    if task == "PVT":
        return pvt_trials(behavior_path, events)
    if task == "Flanker":
        return flanker_trials(events)
    if task.startswith("NBack"):
        return nback_trials(events, int(task[-1]))
    return pd.DataFrame()


def _matb_output(behavior_path: Path | str):
    payload = loadmat(
        behavior_path,
        squeeze_me=True,
        struct_as_record=False,
    )
    if "output" in payload:
        return payload["output"]
    for key, value in payload.items():
        if not key.startswith("__") and hasattr(value, "output"):
            return value.output
    raise ValueError("MATB behavioural file has no output structure")


def matb_window_features(
    behavior_path: Path | str,
    start_fraction: float,
    stop_fraction: float,
) -> dict[str, float]:
    output = _matb_output(behavior_path)

    def segment(values: np.ndarray) -> np.ndarray:
        matrix = np.atleast_2d(values).astype(float)
        start = min(len(matrix), max(0, round(start_fraction * len(matrix))))
        stop = min(
            len(matrix),
            max(start + 1, round(stop_fraction * len(matrix))),
        )
        return matrix[start:stop]

    features: dict[str, float] = {}
    if hasattr(output, "TRACK"):
        track = segment(output.TRACK)
        features["matb_tracking_error"] = float(
            np.mean(np.sqrt(np.sum(track**2, axis=1)))
        )
    if hasattr(output, "SYSMON"):
        sysmon = segment(output.SYSMON)
        features["matb_monitoring_rt"] = float(np.mean(sysmon[:, -1]))
    if hasattr(output, "RESMAN"):
        resource = segment(output.RESMAN)
        features["matb_resource_error"] = float(
            np.mean(np.abs(resource[:, 0] - resource[:, 1]))
        )
    available = [value for value in features.values() if np.isfinite(value)]
    features["matb_efficacy_raw"] = (
        float(-np.mean(available)) if available else float("nan")
    )
    return features


def questionnaire_tables(reference_dir: Path | str) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = Path(reference_dir)
    kss = pd.read_csv(root / "KSS.txt")
    rsme = pd.read_csv(root / "RSME.txt")
    kss = kss.rename(
        columns={
            "sbj": "participant_number",
            "sess": "session_number",
            "score": "kss",
        }
    )
    rsme = rsme.rename(
        columns={
            "sbj": "participant_number",
            "Session": "session_number",
            "Score": "rsme",
        }
    )
    return kss, rsme


def task_order_table(notebook_path: Path | str) -> pd.DataFrame:
    notebook = loadmat(
        notebook_path,
        squeeze_me=True,
        struct_as_record=False,
    )["notebook"]
    rows: list[dict[str, object]] = []
    for participant_number in range(1, 30):
        participant = getattr(notebook, f"SBJ_{participant_number}")
        for session_number in range(1, 4):
            session = getattr(participant, f"SESS_{session_number}")
            order = np.atleast_1d(session.Order).astype(int)
            for position, task_code in enumerate(order, start=1):
                rows.append(
                    {
                        "participant_number": participant_number,
                        "session_number": session_number,
                        "task_order": position,
                        "task": TASK_ORDER_CODES[int(task_code)],
                        "session_interrupted": bool(session.interrupted),
                    }
                )
    return pd.DataFrame(rows)
