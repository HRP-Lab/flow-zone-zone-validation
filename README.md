# Flow Zone Validation: ACDC Pilot

Reproducible exploratory analysis of whether public Stroop, Flanker, and Simon
data contain latent behavioral profiles resembling **In Zone**, **Flat**,
**Locked In**, and **Spun Out**.

ACDC is a conflict-control analogue. This project does not claim to validate
MFT-M, adaptive CCC bits/second, diagnoses, or brain states.

## Requirements

- Windows PowerShell
- Git
- R 4.4 or newer
- Python 3.12 through the Windows Python launcher (`py -3.12`)

Do not use the system Python or Python 3.14 for this project.

## Setup

From the repository root:

```powershell
.\scripts\setup_python.ps1
& "C:\Program Files\R\R-4.6.0\bin\Rscript.exe" scripts/setup_r.R
```

The Python script creates `.venv`, installs the package and development
dependencies from exact tested pins, then runs the tests. The R script
creates/restores the `renv` environment and writes `renv.lock`.

## Run The Pipeline

Development uses the latest ACDC release:

```powershell
.\scripts\run_pipeline.ps1
```

By default, development runs use a deterministic subset containing four
datasets per task and 20 complete participants per dataset. This preserves
whole participant/block sequences and enough source diversity for the
registered gates while keeping iteration practical.

To reuse the existing download and extract:

```powershell
.\scripts\run_pipeline.ps1 -SkipDownload -SkipExtraction
```

For a frozen formal run, select a release tag:

```powershell
.\scripts\run_pipeline.ps1 -AcdcTag "initial-release" -FullData
```

The release tag, database SHA-256, package versions, Git commit, and parameters
are written to `reports/run_manifest.json`.

Individual stages:

```powershell
Rscript scripts/00_download_acdc.R
Rscript scripts/01_inventory_acdc.R
Rscript scripts/02_extract_trials_acdc.R
.\.venv\Scripts\python.exe scripts/02b_build_pilot_subset.py
.\.venv\Scripts\python.exe scripts/03_build_cognitive_windows.py `
  --input data/interim/acdc_pilot_trial_extract.parquet
.\.venv\Scripts\python.exe scripts/04_feature_audit.py
.\.venv\Scripts\python.exe scripts/05_pca_gmm_hdbscan.py
```

The modelling script reads the audit JSON and automatically skips tasks that
fail the registered gates. It never bypasses a failed gate.

## Pipeline

1. Download `acdc.db` with `acdcquery` and verify its release SHA-256.
2. Validate the SQLite schema against `config/acdc_schema.json`.
3. Inventory all datasets and identify Stroop, Flanker, and Simon families.
4. Extract trial rows with documented ACDC joins and original values.
5. Flag RT quality without deleting raw rows.
6. Fit expected raw/log-RT models and construct `u_t`.
7. Build block-bounded 80-trial primary windows and 60/120 sensitivity windows.
8. Produce an audit and task-level modelling decisions.
9. Run neutral PCA/GMM/HDBSCAN analyses only for eligible tasks.
10. Test source confounding before any pooled interpretation.

See [methods.md](docs/methods.md) and
[data_dictionary.md](docs/data_dictionary.md) for exact definitions.

## Outputs

```text
data/interim/acdc_task_inventory.csv
data/interim/acdc_trial_extract.csv.gz
data/interim/acdc_trial_extract.parquet
data/interim/acdc_pilot_trial_extract.parquet
data/processed/acdc_cleaned_trials.parquet
data/processed/cognitive_windows.parquet
data/processed/cluster_assignments.parquet
reports/run_manifest.json
reports/acdc_data_audit.md
reports/acdc_pilot_subset.md
reports/exploratory_clusters.md
reports/figures/
```

Raw, interim, processed, and generated report contents are excluded from Git.

## Quality Gates

A task enters modelling only when it has:

- At least 300 valid primary windows.
- At least three contributing datasets.
- No selected feature above 20% missingness.
- No constant or degenerate selected features.
- At least 80% complete support for the selected feature set before minimal
  task-median imputation.

Metrics structurally unavailable for a task are not imputed.

Pooled modelling is skipped when participant-grouped classifiers show
substantial residual dataset or task predictability.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

The suite covers the shared SQLite schema/SQL contract, RT cleaning,
residualisation, block boundaries, dynamics, conflict costs, PES sufficiency,
audit failures, participant leakage, deterministic GMM behavior, and neutral
zone alignment.

## Interpretation

`k=4` is tested but never forced. Clusters retain neutral identifiers such as
`Stroop-GMM4-C1`. A null, unstable, source-dominated, or continuous-manifold
result is a valid outcome and would favor dimensional descriptions of
throughput, persistence, and instability over four discrete zones.
