"""Configuration loading for the ACDC pilot."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class PilotConfig:
    random_seed: int = 42
    subset_datasets_per_task: int = 4
    subset_participants_per_dataset: int = 20
    primary_window_size: int = 80
    sensitivity_window_sizes: tuple[int, ...] = (60, 120)
    minimum_remainder_trials: int = 40
    rt_min_ms: float = 150.0
    rt_max_ms: float = 3000.0
    rt_mad_multiplier: float = 3.0
    minimum_condition_trials: int = 5
    minimum_pes_post_error_trials: int = 5
    minimum_pes_post_correct_trials: int = 5
    minimum_task_windows: int = 300
    minimum_task_datasets: int = 3
    maximum_feature_missing_fraction: float = 0.2
    minimum_complete_window_fraction: float = 0.8
    minimum_clustering_features: int = 5
    gmm_k_min: int = 1
    gmm_k_max: int = 8
    gmm_initializations: int = 20
    bootstrap_repetitions: int = 50
    confound_permutations: int = 100
    zone_alignment_bootstraps: int = 500


@dataclass(frozen=True)
class ZhangTangConfig:
    random_seed: int = 42
    primary_window_size: int = 80
    mi_permutations: int = 50
    minimum_mi_observations: int = 40
    minimum_mi_class_count: int = 3
    efficiency_bin_counts: tuple[int, ...] = (3, 4, 5)
    tail_z_threshold: float = 2.0
    minimum_tail_observations: int = 20
    large_update_quantile: float = 0.90
    minimum_update_components: int = 3
    minimum_cluster_windows: int = 30
    minimum_cluster_subjects: int = 10
    source_dominance_threshold: float = 0.80
    minimum_task_next_windows: int = 50
    prediction_folds: int = 5
    ridge_alpha: float = 1.0
    bootstrap_repetitions: int = 500


def load_config(path: Path | str) -> PilotConfig:
    """Load the versioned JSON configuration."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "sensitivity_window_sizes" in payload:
        payload["sensitivity_window_sizes"] = tuple(
            int(value) for value in payload["sensitivity_window_sizes"]
        )
    return PilotConfig(**payload)


def load_zhang_tang_config(path: Path | str) -> ZhangTangConfig:
    """Load the versioned Zhang-Tang follow-up configuration."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "efficiency_bin_counts" in payload:
        payload["efficiency_bin_counts"] = tuple(
            int(value) for value in payload["efficiency_bin_counts"]
        )
    return ZhangTangConfig(**payload)
