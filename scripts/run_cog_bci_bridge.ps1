param(
    [int[]]$Participants = @(1, 2, 3, 4, 5),
    [string]$CacheDir = "$env:LOCALAPPDATA\flowzone-cog-bci-cache",
    [switch]$CleanupArchives,
    [int]$Seed = 42
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$StudyRoot = Join-Path $RepoRoot "studies\cog-bci-hrv-bridge"
$OutputRoot = Join-Path $StudyRoot "outputs"
$ReferenceDir = Join-Path $RepoRoot "data\raw\cog_bci\reference"
$Windows = Join-Path $RepoRoot "data\processed\cog_bci_bridge_windows.parquet"
$CheckpointDir = Join-Path $RepoRoot "data\interim\cog_bci_bridge_checkpoints"
$Inventory = Join-Path $OutputRoot "tables\ecg_inventory.csv"
$Errors = Join-Path $OutputRoot "tables\import_errors.csv"
$Questionnaires = Join-Path $OutputRoot "tables\questionnaire_inventory.csv"
$DownloadManifest = Join-Path $OutputRoot "manifests\zenodo_download_manifest.json"
$BuildManifest = Join-Path $OutputRoot "manifests\window_build_manifest.json"
$RunManifest = Join-Path $OutputRoot "manifests\run_manifest.json"

if (-not (Test-Path $Python)) {
    throw "Python environment not found at $Python. Run .\scripts\setup_python.ps1."
}
New-Item -ItemType Directory -Force `
    (Join-Path $OutputRoot "tables"), `
    (Join-Path $OutputRoot "figures"), `
    (Join-Path $OutputRoot "reports"), `
    (Join-Path $OutputRoot "manifests"), `
    $CacheDir, `
    $ReferenceDir, `
    $CheckpointDir | Out-Null

foreach ($Participant in $Participants) {
    & $Python (Join-Path $PSScriptRoot "13_download_cog_bci.py") `
        --participants $Participant `
        --cache-dir $CacheDir `
        --reference-dir $ReferenceDir `
        --manifest $DownloadManifest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $ParticipantId = "sub-{0:D2}" -f $Participant
    $Archive = Join-Path $CacheDir "$ParticipantId.zip"
    $ExtractRoot = Join-Path $CacheDir "extracted-$ParticipantId"
    $ResolvedCache = [IO.Path]::GetFullPath($CacheDir)
    $ResolvedExtract = [IO.Path]::GetFullPath($ExtractRoot)
    if (-not $ResolvedExtract.StartsWith($ResolvedCache)) {
        throw "Unsafe extraction path outside cache: $ResolvedExtract"
    }
    if (Test-Path $ExtractRoot) {
        Remove-Item -LiteralPath $ExtractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force $ExtractRoot | Out-Null
    & tar.exe -xf $Archive -C $ExtractRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python (Join-Path $PSScriptRoot "14_build_cog_bci_windows.py") `
        --participants $Participant `
        --cache-dir $CacheDir `
        --reference-dir $ReferenceDir `
        --checkpoint-dir $CheckpointDir `
        --extracted-root $ExtractRoot `
        --windows $Windows `
        --inventory $Inventory `
        --errors $Errors `
        --questionnaires $Questionnaires `
        --manifest $BuildManifest `
        --append-existing
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $ParticipantRecordings = @(
        Import-Csv $Inventory |
        Where-Object { $_.participant_id -eq $ParticipantId }
    ).Count
    $ParticipantErrors = 0
    if ((Test-Path $Errors) -and (Get-Item $Errors).Length -gt 0) {
        $ParticipantErrors = @(
            Import-Csv $Errors |
            Where-Object { $_.participant_id -eq $ParticipantId }
        ).Count
    }
    if ($ParticipantRecordings -ne 24 -or $ParticipantErrors -ne 0) {
        throw (
            "$ParticipantId failed completeness gate: " +
            "$ParticipantRecordings recordings, $ParticipantErrors errors. " +
            "Raw archive and extraction retained for diagnosis."
        )
    }

    Remove-Item -LiteralPath $ExtractRoot -Recurse -Force
    if ($CleanupArchives) {
        Remove-Item -LiteralPath $Archive -Force
    }
}

& $Python (Join-Path $PSScriptRoot "15_analyze_cog_bci_bridge.py") `
    --windows $Windows `
    --inventory $Inventory `
    --output-root $OutputRoot `
    --manifest $RunManifest `
    --seed $Seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "COG-BCI bridge outputs written to $OutputRoot"
