"""Output helpers shared by analysis scripts."""

from __future__ import annotations

import json
import importlib.metadata
from pathlib import Path
import platform
import subprocess
from typing import Any

import numpy as np
import pandas as pd


def write_table(frame: pd.DataFrame, path: Path | str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".parquet":
        frame.to_parquet(destination, index=False)
    elif destination.suffix.lower() == ".csv":
        frame.to_csv(destination, index=False)
    else:
        raise ValueError(f"Unsupported table format: {destination.suffix}")


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if pd.isna(value):
        return None
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def write_json(payload: Any, path: Path | str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, default=_json_default, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_text(text: str, path: Path | str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text.rstrip() + "\n", encoding="utf-8")


def _git_commit(root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def update_run_manifest(
    path: Path | str,
    root: Path,
    stage: str,
    parameters: dict[str, Any],
) -> None:
    destination = Path(path)
    if destination.exists():
        payload = json.loads(destination.read_text(encoding="utf-8"))
    else:
        payload = {}
    packages = {}
    for package in (
        "numpy",
        "pandas",
        "pyarrow",
        "scikit-learn",
        "scipy",
        "statsmodels",
        "hdbscan",
    ):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    payload["git_commit"] = _git_commit(root)
    payload["python"] = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "packages": packages,
    }
    payload.setdefault("stages", {})[stage] = parameters
    write_json(payload, destination)


def plot_model_diagnostics(
    assignments: pd.DataFrame,
    metrics: dict[str, Any],
    output_dir: Path | str,
) -> list[str]:
    """Write compact PCA and GMM-comparison diagnostics."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    prefix = metrics["analysis_name"].lower().replace(" ", "_")
    outputs: list[str] = []

    comparison = pd.DataFrame(metrics["gmm_comparison"])
    if not comparison.empty:
        figure, axis = plt.subplots(figsize=(7, 4))
        for covariance, group in comparison.groupby("covariance"):
            axis.plot(group["k"], group["bic"], marker="o", label=f"{covariance} BIC")
        axis.set_xlabel("GMM components (k)")
        axis.set_ylabel("BIC")
        axis.set_title(f"{metrics['analysis_name']} GMM comparison")
        axis.legend()
        figure.tight_layout()
        path = destination / f"{prefix}_gmm_bic.png"
        figure.savefig(path, dpi=160)
        plt.close(figure)
        outputs.append(str(path))

    if "pc1" in assignments and "pc2" in assignments:
        figure, axis = plt.subplots(figsize=(6, 5))
        labels = assignments["gmm_component"].to_numpy()
        scatter = axis.scatter(
            assignments["pc1"],
            assignments["pc2"],
            c=labels,
            cmap="tab10",
            s=14,
            alpha=0.75,
        )
        axis.set_xlabel("PC1")
        axis.set_ylabel("PC2")
        axis.set_title(f"{metrics['analysis_name']} neutral GMM components")
        figure.colorbar(scatter, ax=axis, label="Component")
        figure.tight_layout()
        path = destination / f"{prefix}_pca_gmm.png"
        figure.savefig(path, dpi=160)
        plt.close(figure)
        outputs.append(str(path))
    return outputs
