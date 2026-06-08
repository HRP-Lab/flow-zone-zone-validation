# Healthy Long-Term RR Component Replication

## Purpose

This analysis tests whether the three within-person autonomic covariance patterns found in the five-participant COG-BCI pilot recur in an independent set of long-term healthy RR recordings.

The recordings are not labelled for posture, sleep, activity, respiration, or confirmed rest. The primary analysis is therefore a long-term RR replication, not a resting-state validation.

## Data And Sampling

- Participants/files: 11.
- Source recording time: 219.9 hours.
- Primary windows: 120 seconds.
- Sensitivity windows: 180 and 300 seconds.
- Maximum analysed coverage: eight evenly sampled hours per participant at each duration.
- Primary analysis windows: 2,625.

## Quality Audit

| Window | Windows | Participants | Quality pass | Mean correction |
|---:|---:|---:|---:|---:|
| 120 s | 2,640 | 11 | 99.4% | 0.27% |
| 180 s | 1,760 | 11 | 99.7% | 0.27% |
| 300 s | 1,056 | 11 | 99.7% | 0.27% |

## Component Selection And Replication

The COG-BCI comparison fits a fixed three-component PCA to the same ten person-centred time-domain features. Parallel analysis is also reported as an exploratory check and selected 3 component(s).

| COG-BCI component | Direct congruence | Bootstrap median | Bootstrap p05 | Minimum leave-one-participant-out |
|---|---:|---:|---:|---:|
| C1 | 0.984 | 0.998 | 0.985 | 0.999 |
| C2 | 0.713 | 0.994 | 0.975 | 0.998 |
| C3 | 0.705 | 0.997 | 0.980 | 0.998 |

The primary reserve/flexibility component replicated directly, while the two secondary COG-BCI components replicated as a shared two-dimensional subspace rather than as identical individual axes.

A Tucker congruence of `.85` is used as a descriptive replication threshold. It is not a significance test and does not validate discrete autonomic states.

## Subspace Replication

PCA axes can rotate when two components explain a similar covariance plane. The C2-C3 subspace test asks whether broad variability organisation and mobilisation trajectory recur jointly even when their individual axes are mixed differently.

| Window | Scope | Minimum canonical similarity | Maximum principal angle |
|---:|---|---:|---:|
| 120 s | all_three_components | 0.990 | 8.02 degrees |
| 120 s | secondary_C2_C3_subspace | 0.981 | 11.18 degrees |
| 180 s | all_three_components | 0.990 | 8.02 degrees |
| 180 s | secondary_C2_C3_subspace | 0.968 | 14.54 degrees |
| 300 s | all_three_components | 0.990 | 8.16 degrees |
| 300 s | secondary_C2_C3_subspace | 0.980 | 11.47 degrees |

At 120 seconds, COG-BCI C2 loaded approximately equally on the healthy-data broad-variability and trajectory axes, while C3 loaded on their contrasting combination. The datasets therefore support the same secondary two-process space, but not identical C2 and C3 axis orientation.

## Sampling-Coverage Sensitivity

| Maximum hours per participant | Windows | Parallel components | C1 direct | C2-C3 subspace minimum |
|---:|---:|---:|---:|---:|
| 2 | 660 | 3 | 0.989 | 0.983 |
| 4 | 1,320 | 3 | 0.981 | 0.977 |
| 8 | 2,625 | 3 | 0.984 | 0.981 |

The component count and the direct-plus-subspace replication pattern should remain similar as analysed coverage is reduced. This guards against the result depending on the full eight-hour subset.

## Duration Sensitivity

| Window | Reference component | Congruence |
|---:|---:|---:|
| 120 s | C1 | 0.984 |
| 120 s | C2 | 0.713 |
| 120 s | C3 | 0.705 |
| 180 s | C1 | 0.971 |
| 180 s | C2 | 0.774 |
| 180 s | C3 | 0.762 |
| 300 s | C1 | 0.983 |
| 300 s | C2 | 0.788 |
| 300 s | C3 | 0.774 |

## Stationary-Window Sensitivity

A secondary subset required 300-second windows, HR between 45 and 100 bpm, no more than 1% corrected intervals, and an absolute HR slope no greater than 3 bpm/min. These are stable low-trend windows, not confirmed rest. Because slope is part of the selection rule, the trajectory component C3 is not independently validated by this sensitivity analysis.

- C1: congruence `0.982`.
- C2: congruence `0.827`.
- C3: congruence `0.813`.
- Combined C2-C3 subspace minimum canonical similarity: `0.981`.

## Interpretation

Replication of C1 would support a recurring lower-activation and short-term variability/flexibility axis. Replication of C2 would support a distinct broad-variability and slower-organisation axis. Replication of C3 would support a directional mobilisation/recovery trajectory axis.

The data cannot identify sympathetic and parasympathetic activity separately. Long-term variation may also reflect sleep, posture, movement, circadian phase, breathing, activity, and sensor artefact.

## Claim-Safe Conclusion

The primary reserve/flexibility component replicated directly, while the two secondary COG-BCI components replicated as a shared two-dimensional subspace rather than as identical individual axes. The result concerns continuous RR covariance dimensions. It does not establish three autonomic zones, resting-state physiology, medical status, cognitive coupling, or intervention effects.
