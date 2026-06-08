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

## Studies

This repository now contains four distinct analyses:

| Study | Scope | Publication materials |
|---|---|---|
| ACDC pilot | Public Stroop, Flanker, and Simon discovery analysis | [ACDC methods](docs/methods.md) |
| Paired control-vigilance study | Barzykowski et al. paired Stroop, Flanker, and SART sessions | [Standalone study package](studies/paired-control-vigilance/README.md) |
| COG-BCI cognitive-autonomic bridge | Concurrent ECG and cognitive performance across PVT, Flanker, N-back, and MATB | [Standalone bridge study](studies/cog-bci-hrv-bridge/README.md) |
| Healthy long-term RR replication | Independent replication of the COG-BCI autonomic component structure in 11 long-term RR recordings | [Standalone replication study](studies/healthy-rr-replication/README.md) |

The paired study has its own provenance, methods, results, interpretation,
paper guide, reproducible runner, and tracked output artifacts. It should not
be described as an ACDC replication.

The COG-BCI bridge study tests short-window RR/HRV measurement, autonomic
dimensions, cognitive-autonomic coupling, and incremental prediction. It is
bridge evidence for prospective concurrent RR collection during the proposed
SART-Stroop-Flanker protocol, not validation of that exact battery.

The healthy RR study tests whether those within-person autonomic covariance
patterns recur in an independent dataset. The source recordings are not
labelled as rest, so this is a long-term RR replication rather than a
resting-state or autonomic-zone validation.

## Paired Study Data

The paired study uses the published Barzykowski et al. (2022) summary and raw
task workbooks. Download instructions and verified hashes are in
[DATA_PROVENANCE.md](studies/paired-control-vigilance/DATA_PROVENANCE.md).
The summary workbook can be downloaded directly with:

```powershell
New-Item -ItemType Directory -Force data/raw/stroop_sart_flanker
Invoke-WebRequest `
  "https://osf.io/9km5f/download?view_only=31aa5d5964a943df8d3e7d911d2d7141" `
  -OutFile `
  "data/raw/stroop_sart_flanker/STROOP_FLANKERS_SART_web_and_lab.xls"
```

The tested file SHA-256 is
`884ba8bbae097e81f826fa247c2a0bb785302eb88173fbf88dfb5d3c76b8cd5b`.
The analysis records the observed hash in the run manifest and report.

Run the complete standalone paired study with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\run_paired_study.ps1
```

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
.\.venv\Scripts\python.exe scripts/06_zhang_tang_followup.py
.\.venv\Scripts\python.exe scripts/07_stroop_zone_count_comparison.py
.\.venv\Scripts\python.exe scripts/08_short_test_individual_differences.py
```

The modelling script reads the audit JSON and automatically skips tasks that
fail the registered gates. It never bypasses a failed gate.

Paired study stages are intentionally separate from the ACDC runner:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\run_paired_study.ps1
```

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
[data_dictionary.md](docs/data_dictionary.md) for exact definitions. The
provisional cognitive interpretation of the focused Stroop profiles is in
[cognitive_profile_interpretations.md](docs/cognitive_profile_interpretations.md).

## Outputs

```text
data/interim/acdc_task_inventory.csv
data/interim/acdc_trial_extract.csv.gz
data/interim/acdc_trial_extract.parquet
data/interim/acdc_pilot_trial_extract.parquet
data/processed/acdc_cleaned_trials.parquet
data/processed/cognitive_windows.parquet
data/processed/cluster_assignments.parquet
data/processed/acdc_zhang_tang_windows.parquet
reports/run_manifest.json
reports/acdc_data_audit.md
reports/acdc_pilot_subset.md
reports/exploratory_clusters.md
reports/zhang_tang_followup.md
reports/stroop_zone_count_comparison.md
reports/stroop_short_test_individual_differences.md
reports/tables/zhang_tang_feature_audit.csv
reports/tables/zhang_tang_cluster_profiles.csv
reports/tables/large_update_usefulness.csv
reports/tables/next_window_prediction_comparison.csv
reports/tables/stroop_zone_count_models.csv
reports/tables/stroop_continuous_vs_mixture.csv
reports/tables/stroop_zone_count_profiles.csv
reports/tables/stroop_trial_count_recovery.csv
reports/tables/stroop_trial_count_class_recall.csv
reports/tables/stroop_participant_profile_occupancy.csv
reports/tables/stroop_profile_transitions.csv
reports/tables/stroop_feature_icc.csv
reports/figures/
studies/paired-control-vigilance/outputs/reports/
studies/paired-control-vigilance/outputs/tables/
studies/paired-control-vigilance/outputs/figures/
studies/paired-control-vigilance/outputs/manifests/
```

Raw, interim, processed, and top-level generated report contents are excluded
from Git. The paired study's compact publication tables, figures, and manifests
are tracked under its standalone directory.

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
