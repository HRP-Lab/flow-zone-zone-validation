# Flow Zone Validation

Reproducible validation pipeline for deriving cognitive windows from ACDC
trial-level data and testing latent Flow Zone profiles.

This repository is separate from the
[Flow-Zone application](https://github.com/HRP-Lab/Flow-Zone) so that raw
research data, analysis dependencies, and validation outputs can be managed
independently.

## Pipeline

1. `scripts/00_download_acdc.R` downloads an ACDC archive or data file.
2. `scripts/01_inventory_acdc.R` creates a machine-readable file inventory.
3. `scripts/02_extract_trials_acdc.R` combines matching trial CSV files.
4. `scripts/03_build_cognitive_windows.py` assigns trials to windows and
   derives cognitive features.
5. `scripts/04_feature_audit.py` audits feature completeness and dispersion.
6. `scripts/05_pca_gmm_hdbscan.py` compares PCA-based GMM and HDBSCAN labels.

The R extraction script is intentionally schema-neutral. Update its
`required_columns` vector after confirming the ACDC release schema.

## Setup

Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

For R, install the packages declared in `DESCRIPTION`:

```r
install.packages(c("dplyr", "fs", "readr"))
```

## Run

Set the approved ACDC download URL rather than committing a data URL or
credentials:

```powershell
$env:ACDC_DOWNLOAD_URL = "https://example.org/acdc.zip"
Rscript scripts/00_download_acdc.R
Rscript scripts/01_inventory_acdc.R
Rscript scripts/02_extract_trials_acdc.R
python scripts/03_build_cognitive_windows.py
python scripts/04_feature_audit.py
python scripts/05_pca_gmm_hdbscan.py
```

Each script supports `--help` or positional path overrides. The defaults form
a pipeline from `data/raw/acdc` through `data/processed` and `reports`.

## Expected trial fields

The Python feature builder recognizes these fields when present:

- Required: `participant_id`, `timestamp`, `rt_ms`, `correct`
- Optional: `session_id`, `is_switch`, `perseverative_error`, `n_choices`

Missing optional fields produce missing derived features rather than fabricated
values.

## Data policy

Raw, interim, and processed participant data are ignored by Git. Keep only
directory placeholders and non-sensitive documentation under version control.
Before sharing any output, verify that it is de-identified and permitted by the
source dataset's license and ethics conditions.
