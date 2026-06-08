param(
    [int]$MixtureBootstrapRepetitions = 50,
    [int]$AssociationBootstrapRepetitions = 5000,
    [int]$Seed = 42
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$StudyRoot = Join-Path $RepoRoot "studies\paired-control-vigilance"
$OutputRoot = Join-Path $StudyRoot "outputs"
$TableDir = Join-Path $OutputRoot "tables"
$FigureDir = Join-Path $OutputRoot "figures"
$ReportDir = Join-Path $OutputRoot "reports"
$ManifestDir = Join-Path $OutputRoot "manifests"
$FeatureFile = Join-Path $RepoRoot "data\processed\paired_vigilance_session_features.parquet"

if (-not (Test-Path $Python)) {
    throw "Python environment not found at $Python. Run .\scripts\setup_python.ps1 first."
}

New-Item -ItemType Directory -Force `
    $TableDir, $FigureDir, $ReportDir, $ManifestDir | Out-Null

& $Python (Join-Path $PSScriptRoot "09_paired_vigilance_analysis.py") `
    --features $FeatureFile `
    --report (Join-Path $ReportDir "main_analysis.md") `
    --output-dir $TableDir `
    --figure-dir $FigureDir `
    --metrics (Join-Path $ManifestDir "paired_vigilance_metrics.json") `
    --manifest (Join-Path $ManifestDir "study_run_manifest.json") `
    --bootstrap-repetitions $MixtureBootstrapRepetitions `
    --seed $Seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python (Join-Path $PSScriptRoot "11_paired_study_results.py") `
    --input $FeatureFile `
    --profile-table (Join-Path $TableDir "paired_control_cluster_profiles.csv") `
    --output-dir $TableDir `
    --report (Join-Path $ReportDir "joint_repeat_results.md") `
    --metrics (Join-Path $ManifestDir "joint_repeat_metrics.json") `
    --figure (Join-Path $FigureDir "control_vigilance_joint.png") `
    --bootstrap-repetitions $AssociationBootstrapRepetitions `
    --seed $Seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python (Join-Path $PSScriptRoot "10_short_combined_task_recovery.py") `
    --sessions $FeatureFile `
    --report (Join-Path $ReportDir "short_combined_task_recovery.md") `
    --table (Join-Path $TableDir "short_combined_task_recovery.csv") `
    --yield-table (Join-Path $TableDir "short_stroop_trial_yield_by_profile.csv") `
    --figure (Join-Path $FigureDir "short_combined_task_recovery.png") `
    --seed $Seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python (Join-Path $PSScriptRoot "12_validate_sart_3min.py") `
    --sessions $FeatureFile `
    --output-dir $TableDir `
    --figure-dir $FigureDir `
    --report (Join-Path $ReportDir "sart_3min_validation.md") `
    --metrics (Join-Path $ManifestDir "sart_3min_validation_metrics.json") `
    --manifest (Join-Path $ManifestDir "study_run_manifest.json") `
    --bootstrap-repetitions $AssociationBootstrapRepetitions `
    --seed $Seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Paired study outputs written to $OutputRoot"
