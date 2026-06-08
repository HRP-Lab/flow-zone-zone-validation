# Methods

## Design

Eleven long-term healthy beat-to-beat interval files were used as an
independent replication dataset. Each text file contains one RR interval in
milliseconds per line. The recordings span approximately 12-23 hours per
participant.

No metadata identify sleep, posture, physical activity, respiration, or
confirmed resting periods. All conclusions therefore concern long-term RR
covariance rather than resting autonomic physiology.

## Sampling

Non-overlapping 120-, 180-, and 300-second windows were defined using cumulative
RR time. To balance participants and reduce computation, a maximum of eight
hours per participant was selected at each duration using evenly spaced,
deterministic window indices.

The 120-second analysis is primary because it matches the proposed app window.
The longer durations test loading-pattern sensitivity.

## Cleaning

Intervals outside 300-2000 ms or differing by more than 20% from a local
seven-interval median were replaced by that local median. Windows failed
quality control when more than 5% of intervals required correction, fewer than
95% were valid, or fewer than 30 intervals remained.

Malformed lines were counted and excluded rather than silently converted.

## Features

The replication uses the same ten time-domain variables as the COG-BCI
within-person PCA:

```text
mean HR
mean NN
log RMSSD
SDNN
CVNN
pNN20
pNN50
SD1/SD2
HR slope
NN slope
```

Features were centred within participant and standardized across windows.

## Component Analysis

A fixed three-component PCA provides the direct COG-BCI replication test.
Parallel analysis independently estimates an exploratory component count.
Candidate components are matched to COG-BCI components using the Hungarian
algorithm on absolute Tucker loading congruence, with signs aligned after
matching.

Descriptive replication requires Tucker congruence of at least `.85`.
Participant-level bootstrap stability uses 200 resamples. Leave-one-participant-
out analysis tests whether any participant determines the result.

Because PCA axes can rotate within a shared covariance plane, the complete
three-dimensional loading subspace and the combined C2-C3 secondary subspace
are also compared using canonical similarities and principal angles. This
distinguishes failure to reproduce a process from a different rotation of the
same multidimensional process space.

## Stationary Sensitivity

A secondary 300-second subset requires:

```text
45-100 bpm
no more than 1% corrected intervals
absolute HR slope no greater than 3 bpm/min
```

These are stable low-trend windows, not confirmed rest. Since the selection
uses HR slope, it cannot independently validate the mobilisation/recovery
trajectory component.
