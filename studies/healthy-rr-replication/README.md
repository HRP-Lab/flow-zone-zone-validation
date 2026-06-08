# Healthy Long-Term RR Component Replication

This standalone study tests whether the three within-person autonomic
components identified in the COG-BCI ECG pilot recur in independent long-term
healthy RR recordings.

The source files contain beat-to-beat intervals but no confirmed rest, posture,
activity, sleep, respiration, or clock-time labels. The study is therefore a
long-term RR component replication, not a resting-state or autonomic-zone
validation.

## Study Materials

- [Methods](METHODS.md)
- [Results](RESULTS.md)
- [Interpretation](INTERPRETATION.md)
- [Data provenance](DATA_PROVENANCE.md)
- [Configuration](config/study.json)
- [Generated report](outputs/reports/main_analysis.md)
- [Tables](outputs/tables/)
- [Figures](outputs/figures/)

## Reproduce

From the `flow-zone-zone-validation` repository:

```powershell
.\.venv\Scripts\python.exe scripts\16_healthy_rr_replication.py `
  --input-dir `
  "C:\Users\admin\OneDrive\Documents\GitHub\trident-g-platform\Flow-Zone-analysis\healthy_data" `
  --maximum-hours 8 `
  --bootstrap-repetitions 200
```

Raw RR files remain in their source repository and are not copied into this
repository. The generated window-level parquet is under the ignored
`data/processed/` directory. Only aggregate, publication-oriented outputs are
tracked.
