# Methods

## Design

COG-BCI version 4 contains 29 participants completing three weekly sessions of
PVT, Flanker, 0/1/2-back, and easy/medium/difficult MATB while 500 Hz EEG and a
dedicated `ECG1` channel were recorded. The present study is a retrospective
cognitive-autonomic bridge analysis.

## Data Integrity

Participant archives are downloaded from Zenodo record `7413650`, checked
against the record size and MD5 digest, and processed sequentially. The
importer requires:

- three session directories;
- a matching EEGLAB `.set/.fdt` pair for each task;
- `ECG1` at exactly 500 Hz;
- task annotations consistent with the published trigger map;
- the corresponding behavioural `.mat` file.

Schema discrepancies are written to `import_errors.csv`. A task is not silently
substituted or remapped.

## Windowing

Non-overlapping windows remain inside participant, session, task, condition,
and task-file block:

| Duration | Role |
|---|---|
| 10 seconds | Published HR/SDNN/RMSSD replication |
| 60 seconds | Feasibility stress test |
| 120 seconds | App-aligned primary analysis |
| 180 seconds | Dynamics reliability compromise |
| Full task | Reliability benchmark |

Tasks are never concatenated into an artificial battery.

## ECG Processing

The replication path downsamples ECG to 250 Hz, applies a 1–40 Hz bandpass,
and calculates HR, RMSSD, and SDNN in 10-second windows.

The extended path retains 500 Hz, applies a 0.5–40 Hz fourth-order Butterworth
bandpass and a 50 Hz notch, and detects R peaks with NeuroKit as primary and
Pan-Tompkins as sensitivity. Peaks match when separated by no more than 80 ms.
Windows with more than 1% unmatched peaks are flagged.

RR intervals outside 300–2000 ms or isolated by more than 20% from the local
median are replaced with that local median. This is a transparent
Kubios-inspired isolated-beat rule, not the proprietary Kubios algorithm.
Windows fail quality control when more than 5% of intervals require correction,
fewer than 95% remain valid, or too few beats are present.

Primary 120-second features are mean HR/NN, log RMSSD, SDNN, CVNN, pNN20,
pNN50, Poincare SD1/SD2 and their ratio, and HR/NN slopes. Candidate dynamics
are DFA alpha1, lag-1 persistence, roughness, sign-change rate, permutation
entropy, difference entropy, and sample entropy.

Dynamics are interpretable only when missingness is below 20%, detector
concordance is at least `.75`, and duration sensitivity supports stable loading
directions at 180 seconds and full block.

## Cognitive Features

- PVT: reciprocal RT, median RT, RT CV, lapses at 500 ms, anticipations below
  100 ms, and RT drift.
- Flanker: accuracy, RT, congruency costs, fast errors, variability, and
  supported post-error adjustment.
- N-back: accuracy, hit rate, false-alarm rate, a descriptive hit-minus-false
  alarm proxy, RT, throughput, and workload level.
- MATB: tracking error, monitoring RT, resource-management discrepancy, and a
  descriptive raw efficacy composite.

RSME is linked by participant, session, and exact task label. The KSS source
table is retained without inventing a task mapping for ambiguous repeated
`after_PVT` labels.

## Replication Gate

Before novel modelling, participant-session slopes test:

- PVT time-on-task: RT up, HR up, RMSSD/SDNN down;
- N-back difficulty: performance down, HR up, RMSSD/SDNN down;
- MATB difficulty: error/RT up, HR up, RMSSD/SDNN down.

A directional effect requires at least five participant-sessions, the median in
the expected direction, and at least 60% of participant-sessions in that
direction. At least two of three domains must support the published direction,
and all three must be testable.

## Statistical Analysis

Task, condition, session, order, and time-on-task effects are removed with
mixed-effects models containing participant random intercepts. A participant
fixed-effect model is the declared numerical fallback and is used for pilot
runs with fewer than eight participants. Participant means and person-centred
residuals are retained separately.

Between-person and within-person autonomic covariance are analysed separately.
Parallel analysis selects up to two between-person and four within-person
components. Participant bootstrap stability and Tucker congruence are required
for confirmatory interpretation in a full run.

Participant-grouped PLS is secondary to mixed models and incremental
prediction. Ridge models compare task-only, cognitive, HRV, and combined
feature blocks. All out-of-participant folds isolate dataset-scoped participant
IDs. Temporally aligned ECG is compared with within-participant/session/task
shuffling and simple HR/RMSSD baselines.

Adjacent-window models are temporal associations, not causal effects.
