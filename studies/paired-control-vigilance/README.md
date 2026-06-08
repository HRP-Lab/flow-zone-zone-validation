# Paired Stroop-Flanker-SART Study

This directory is the self-contained publication package for the secondary
analysis of the Barzykowski et al. (2022) paired Stroop, Eriksen Flanker, and
SART dataset. It is separate from the repository's ACDC pilot.

The study asks:

1. Do Stroop and Flanker performance support more than one task-active control
   profile?
2. Does SART engagement/vigilance add information beyond those profiles?
3. Are the profiles entirely person-like, entirely session-like, or mixed?
4. Can shortened Stroop and Flanker prefixes recover the full-session
   exploratory partition well enough to justify prospective validation?

The proposed protocol can use SART, which has direct continuity with this
dataset, or a PVT-like probe, which may provide a cleaner brief measure of
behavioural alertness. The alternatives are specified in
[PROTOCOL_TASK_SPECS.md](PROTOCOL_TASK_SPECS.md).

The selected exploratory model contains four neutral components. Interpretive
names are reported only as candidates:

| Neutral ID | Descriptive candidate |
|---|---|
| `Paired-Control-GMM4-full-C1` | slow compensatory control |
| `Paired-Control-GMM4-full-C2` | regulated control |
| `Paired-Control-GMM4-full-C3` | globally overloaded control |
| `Paired-Control-GMM4-full-C4` | fast brittle control |

These are behavioural profiles, not diagnoses, validated zones, brain states,
or demonstrated intervention targets.

## Study Materials

- [Methods](METHODS.md)
- [Results](RESULTS.md)
- [Interpretation](INTERPRETATION.md)
- [Three-task protocol specifications](PROTOCOL_TASK_SPECS.md)
- [Data provenance](DATA_PROVENANCE.md)
- [Paper guide](PAPER_GUIDE.md)
- [Analysis configuration](config/study.json)
- [Generated reports](outputs/reports/)
- [Generated tables](outputs/tables/)
- [Generated figures](outputs/figures/)
- [Run manifests](outputs/manifests/)

## Reproduce The Analysis

From the repository root:

```powershell
.\scripts\setup_python.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\run_paired_study.ps1
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

The raw source workbooks must be present in
`data/raw/stroop_sart_flanker/`. They are excluded from Git. Download links,
expected filenames, and SHA-256 hashes are recorded in
[DATA_PROVENANCE.md](DATA_PROVENANCE.md).

The runner regenerates all study tables, figures, reports, and manifests under
`studies/paired-control-vigilance/outputs/`. The processed session feature file
remains under `data/processed/` because it contains participant-level source
data and is not committed.

## Main Findings

- The BIC-selected valid model was a four-component full-covariance GMM
  (`BIC = 5130.7`, bootstrap median `ARI = 0.724`).
- SART engagement and control profile were associated but not interchangeable:
  `chi-square(3) = 79.79`, `p = 3.41e-17`, Cramer's `V = 0.322`.
- Repeat-session results showed mixed trait-state structure: 48.1% of repeated
  participants occupied more than one profile and adjacent-session persistence
  was 60.9%.
- A two-minute Stroop plus conservative two-minute Flanker prefix recovered the
  full-session four-profile partition with participant-grouped balanced
  accuracy `0.744`.
- The first 144 SART trials retained strong agreement with the full task:
  engagement-vigilance Spearman `r = .912`, inhibitory stability `r = .952`,
  and low-engagement balanced accuracy `0.883`.
- The exact two-minute, 96-trial SART retained engagement-vigilance concordance
  `.856`, inhibition concordance `.886`, and low-engagement balanced accuracy
  `.816`. It supports a six-minute minimum protocol, with weaker one-session
  reliability than the three-minute preferred version.

The shortened-task result is internal recovery, not independent validation. A
new prospective sample is required before clinical, occupational, routing, or
production use.
