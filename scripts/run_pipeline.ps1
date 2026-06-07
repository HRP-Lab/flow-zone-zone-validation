param(
  [string]$AcdcTag = "",
  [switch]$SkipDownload,
  [switch]$SkipExtraction,
  [switch]$FullData,
  [switch]$SkipModels
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
  throw "Python environment is missing. Run .\scripts\setup_python.ps1 first."
}
$rscriptCommand = Get-Command Rscript -ErrorAction SilentlyContinue
if ($rscriptCommand) {
  $rscript = $rscriptCommand.Source
} else {
  $rscript = Get-ChildItem "C:\Program Files\R" -Recurse -Filter Rscript.exe |
    Where-Object { $_.FullName -match "\\bin\\Rscript.exe$" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1 -ExpandProperty FullName
}
if (-not $rscript) {
  throw "Rscript is not available. Install R 4.4+ and run Rscript scripts/setup_r.R."
}

if (-not $SkipDownload) {
  $downloadArgs = @("scripts/00_download_acdc.R")
  if ($AcdcTag) {
    $downloadArgs += @("--tag", $AcdcTag)
  }
  & $rscript @downloadArgs
}

if (-not $SkipExtraction) {
  & $rscript scripts/01_inventory_acdc.R
  & $rscript scripts/02_extract_trials_acdc.R
}

$trialInput = "data/interim/acdc_trial_extract.parquet"
if (-not $FullData) {
  & .\.venv\Scripts\python.exe scripts/02b_build_pilot_subset.py
  $trialInput = "data/interim/acdc_pilot_trial_extract.parquet"
}

& .\.venv\Scripts\python.exe scripts/03_build_cognitive_windows.py --input $trialInput
& .\.venv\Scripts\python.exe scripts/04_feature_audit.py

if (-not $SkipModels) {
  & .\.venv\Scripts\python.exe scripts/05_pca_gmm_hdbscan.py
}
