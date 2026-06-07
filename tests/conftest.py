from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.config import PilotConfig


@pytest.fixture
def pilot_config() -> PilotConfig:
    return replace(
        PilotConfig(),
        minimum_task_windows=8,
        minimum_task_datasets=2,
        minimum_pes_post_error_trials=2,
        minimum_pes_post_correct_trials=2,
        bootstrap_repetitions=2,
        confound_permutations=3,
        zone_alignment_bootstraps=10,
    )


def make_trials(
    datasets: int = 2,
    participants: int = 3,
    blocks: int = 2,
    trials_per_block: int = 130,
    task: str = "Stroop",
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for dataset in range(1, datasets + 1):
        for participant in range(participants):
            for block in range(1, blocks + 1):
                for trial in range(1, trials_per_block + 1):
                    congruency = (
                        "incongruent" if trial % 2 else "congruent"
                    )
                    correct = int(rng.random() > 0.10)
                    rt_ms = (
                        500
                        + 45 * (congruency == "incongruent")
                        + 10 * dataset
                        + rng.normal(0, 55)
                    )
                    rows.append(
                        {
                            "observation_id": len(rows) + 1,
                            "dataset_id": dataset,
                            "participant_id": f"{dataset}:{participant}",
                            "task_family": task,
                            "control_cost_type": (
                                "conflict" if task == "Flanker" else "interference"
                            ),
                            "block_raw": block,
                            "trial_raw": trial,
                            "congruency": congruency,
                            "correct": correct,
                            "rt_ms": rt_ms,
                            "within_id": np.nan,
                            "between_id": np.nan,
                        }
                    )
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_trials() -> pd.DataFrame:
    return make_trials()


@pytest.fixture
def make_trials_fixture():
    return make_trials


@pytest.fixture
def acdc_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE publication_table (
            publication_id INTEGER PRIMARY KEY,
            authors TEXT,
            conducted TEXT,
            added TEXT,
            country TEXT,
            contact TEXT,
            apa_reference TEXT,
            keywords TEXT,
            publication_code TEXT
        );
        CREATE TABLE study_table (
            study_id INTEGER PRIMARY KEY,
            publication_id INTEGER,
            n_groups INTEGER,
            n_tasks INTEGER,
            study_comment TEXT
        );
        CREATE TABLE task_table (
            task_id INTEGER PRIMARY KEY,
            task_name TEXT,
            task_description TEXT
        );
        CREATE TABLE dataset_table (
            dataset_id INTEGER PRIMARY KEY,
            study_id INTEGER,
            task_id INTEGER,
            data_excl TEXT,
            n_participants INTEGER,
            n_blocks INTEGER,
            n_trials INTEGER,
            neutral_trials INTEGER,
            fixation_cross TEXT,
            time_limit INTEGER,
            mean_dataset_rt INTEGER,
            mean_dataset_acc INTEGER,
            github TEXT,
            mean_age REAL,
            percentage_female REAL,
            n_members INTEGER,
            number_within_conditions INTEGER,
            group_description TEXT
        );
        CREATE TABLE within_table (
            within_id INTEGER PRIMARY KEY,
            dataset_id INTEGER,
            within_description TEXT,
            percentage_congruent REAL,
            percentage_neutral REAL,
            n_obs INTEGER,
            mean_obs_per_participant INTEGER,
            mean_condition_rt INTEGER,
            mean_condition_acc INTEGER
        );
        CREATE TABLE observation_table (
            observation_id INTEGER PRIMARY KEY,
            dataset_id INTEGER,
            subject INTEGER,
            block INTEGER,
            trial INTEGER,
            within_id INTEGER,
            congruency VARCHAR(20),
            accuracy INTEGER,
            rt REAL
        );
        """
    )
    connection.execute(
        "INSERT INTO publication_table VALUES "
        "(1, 'A', '2020', '2026', 'GB', '', 'Example', '', 'example_2020')"
    )
    connection.execute(
        "INSERT INTO study_table VALUES (1, 1, 1, 1, '')"
    )
    connection.execute(
        "INSERT INTO task_table VALUES (1, 'Color Stroop', 'conflict task')"
    )
    connection.execute(
        "INSERT INTO dataset_table VALUES "
        "(1, 1, 1, '', 1, 1, 4, 0, '', 2, 500, 95, "
        "'https://example.org', 30, 50, 1, 1, 'control')"
    )
    connection.execute(
        "INSERT INTO within_table VALUES "
        "(1, 1, 'baseline', 0.5, 0, 4, 4, 500, 95)"
    )
    observations = [
        (1, 1, 7, 1, 1, 1, "congruent", 1, 0.45),
        (2, 1, 7, 1, 2, 1, "incongruent", 1, 0.55),
        (3, 1, 7, 1, 3, 1, "congruent", 0, 0.50),
        (4, 1, 7, 1, 4, 1, "neutral", 1, 0.48),
    ]
    connection.executemany(
        "INSERT INTO observation_table VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        observations,
    )
    connection.commit()
    yield connection
    connection.close()
