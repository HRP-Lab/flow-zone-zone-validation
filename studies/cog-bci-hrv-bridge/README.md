# COG-BCI Cognitive-Autonomic Bridge Study

This standalone study tests whether concurrent ECG-derived autonomic features
share variance with, diverge from, and add prediction beyond cognitive
performance during PVT, Flanker, N-back, and MATB tasks.

It is bridge evidence for a future simultaneous Stroop-Flanker-SART plus
RR/HRV protocol. COG-BCI does not contain Stroop or SART and therefore cannot
validate the exact proposed `4 x 2` classifier.

## Study Materials

- [Methods](METHODS.md)
- [Results](RESULTS.md)
- [Interpretation](INTERPRETATION.md)
- [Data provenance](DATA_PROVENANCE.md)
- [Analysis configuration](config/study.json)
- [Generated reports](outputs/reports/)
- [Generated tables](outputs/tables/)
- [Generated figures](outputs/figures/)
- [Run manifests](outputs/manifests/)

## Reproduce The Five-Participant Pilot

From the repository root:

```powershell
.\scripts\setup_python.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\run_cog_bci_bridge.ps1 `
  -Participants 1,2,3,4,5 `
  -CleanupArchives
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

The default archive cache is
`$env:LOCALAPPDATA\flowzone-cog-bci-cache`. Archives are verified against the
Zenodo MD5 manifest before processing. `-CleanupArchives` removes only those
disposable archives after their task windows and aggregate audits have been
written.

## Full Sample

```powershell
$all = 1..29
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\run_cog_bci_bridge.ps1 `
  -Participants $all `
  -CleanupArchives
```

Participants are processed one task pair at a time. The pipeline does not
unpack the 31.7 GB dataset as one directory. Completed task-condition windows
are checkpointed under `data/interim/cog_bci_bridge_checkpoints/`, allowing an
interrupted run to resume without repeating ECG processing.

## Gate

Novel factor, coupling, divergence, and prediction analyses run only after the
PVT time-on-task and N-back/MATB difficulty effects reproduce in the expected
direction. A failed or undersized gate produces complete audit outputs and a
documented stop rather than an invented result.
