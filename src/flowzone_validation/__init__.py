"""Reusable analysis components for Flow Zone validation."""

from .cleaning import flag_trials
from .cognitive_features import summarize_windows
from .residualisation import residualise_trial_rt
from .windowing import assign_trial_windows

__all__ = [
    "assign_trial_windows",
    "flag_trials",
    "residualise_trial_rt",
    "summarize_windows",
]
