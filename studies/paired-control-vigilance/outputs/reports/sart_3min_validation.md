# Three-Minute SART Validation

> This is an internal abbreviation analysis. The first 144 trials are nested within the full 225-trial SART and are not an independent validation sample.

## 1. Purpose

This analysis tests whether the first 144 trials (three minutes at 1250 ms per trial) preserve the paired study's full-session SART engagement-vigilance and inhibitory-stability information.

## 2. Raw linkage and integrity

- Raw SART main sessions: 788.
- Paired study sessions: 768.
- Exact participant-bounded fingerprint matches: 744.
- Matched participants: 456.
- Rejected ambiguous/mismatched assignments: 20.
- Paired sessions without a candidate raw bout: 4.

Matching was restricted within participant and required agreement on full-session commissions, omissions, anticipatory responses, Go RT, and Go RT CV. Rejected rows were not forced.

The accepted raw full-session measures reproduce the published summary:

| Measure | N | Pearson r | Lin CCC | MAE |
|---|---:|---:|---:|---:|
| commission_percent | 744 | 1.000 | 1.000 | 0.000 |
| omission_percent | 744 | 1.000 | 1.000 | 0.000 |
| anticipatory_count | 744 | 1.000 | 1.000 | 0.000 |
| go_mean_rt_ms | 744 | 1.000 | 1.000 | 0.000 |
| go_rt_cv | 744 | 1.000 | 1.000 | 0.000 |

## 3. Three-minute prefix

- Trials: 144.
- Go trials: 131.
- NoGo trials: 13.
- The source used one fixed semi-random sequence. Every session therefore has the same 131/13 composition.

A redesigned 128/16 sequence is not validated by this analysis.

## 4. Raw metric agreement

| Measure | Pearson r | Spearman r | Lin CCC | Bias | MAE |
|---|---:|---:|---:|---:|---:|
| commission_rate | 0.932 | 0.930 | 0.929 | 0.017 | 0.073 |
| omission_rate | 0.953 | 0.909 | 0.942 | -0.004 | 0.008 |
| anticipatory_rate | 0.969 | 0.935 | 0.969 | -0.001 | 0.006 |
| go_mean_rt_ms | 0.970 | 0.964 | 0.963 | -8.976 | 13.763 |
| go_rt_cv | 0.914 | 0.918 | 0.910 | -0.010 | 0.028 |

## 5. Composite score agreement

| Dimension | Pearson r | Spearman r | Lin CCC | MAE | Heuristic result |
|---|---:|---:|---:|---:|---|
| Engagement-vigilance | 0.940 | 0.912 | 0.940 | 0.259 | supported |
| Inhibitory stability | 0.961 | 0.952 | 0.961 | 0.192 | supported |

The heuristic gates were not preregistered: engagement required Spearman r >= .80, CCC >= .75, and low-engagement balanced accuracy >= .75; inhibition required Spearman r >= .70 and CCC >= .65.

Agreement remains high after separating stable person differences from session deviations:

| Dimension | Level | Spearman correlation | N |
|---|---|---:|---:|
| engagement_vigilance | session | 0.912 | 744 |
| engagement_vigilance | between_person | 0.930 | 456 |
| engagement_vigilance | within_person | 0.898 | 491 |
| inhibitory_stability | session | 0.952 | 744 |
| inhibitory_stability | between_person | 0.960 | 456 |
| inhibitory_stability | within_person | 0.930 | 491 |

## 6. Low-engagement agreement

- Full-session low-engagement rate: 28.2%.
- Three-minute low-engagement rate: 28.8%.
- Sensitivity: 0.838.
- Specificity: 0.929.
- Balanced accuracy: 0.883.
- Cohen's kappa: 0.763.

## 7. Control-profile association

- Full SART Cramer's V: 0.329.
- Three-minute SART Cramer's V: 0.334.

| SART source | Neutral profile | Low-engagement rate |
|---|---|---:|
| full_225 | Paired-Control-GMM4-full-C1 | 35.1% |
| full_225 | Paired-Control-GMM4-full-C2 | 16.7% |
| full_225 | Paired-Control-GMM4-full-C3 | 72.3% |
| full_225 | Paired-Control-GMM4-full-C4 | 38.1% |
| abbreviated_144 | Paired-Control-GMM4-full-C1 | 34.0% |
| abbreviated_144 | Paired-Control-GMM4-full-C2 | 16.9% |
| abbreviated_144 | Paired-Control-GMM4-full-C3 | 72.3% |
| abbreviated_144 | Paired-Control-GMM4-full-C4 | 42.5% |

## 8. Between- and within-person associations

| SART source | Dimension | Level | Correlation with task-active efficacy | N |
|---|---|---|---:|---:|
| full_225 | sart_engagement_index | session | 0.382 | 744 |
| full_225 | sart_engagement_index | between_person | 0.473 | 456 |
| full_225 | sart_engagement_index | within_person | 0.102 | 491 |
| full_225 | sart_inhibitory_stability_index | session | 0.273 | 744 |
| full_225 | sart_inhibitory_stability_index | between_person | 0.286 | 456 |
| full_225 | sart_inhibitory_stability_index | within_person | 0.088 | 491 |
| abbreviated_144 | sart_engagement_index | session | 0.347 | 744 |
| abbreviated_144 | sart_engagement_index | between_person | 0.444 | 456 |
| abbreviated_144 | sart_engagement_index | within_person | 0.029 | 491 |
| abbreviated_144 | sart_inhibitory_stability_index | session | 0.280 | 744 |
| abbreviated_144 | sart_inhibitory_stability_index | between_person | 0.312 | 456 |
| abbreviated_144 | sart_inhibitory_stability_index | within_person | 0.068 | 491 |

## 9. Repeat-session ICC

| SART source | Dimension | ICC(1) | Interpretation |
|---|---|---:|---|
| full_225 | sart_inhibitory_stability_index | 0.491 | mixed |
| full_225 | sart_engagement_index | 0.391 | mixed |
| abbreviated_144 | sart_inhibitory_stability_index | 0.434 | mixed |
| abbreviated_144 | sart_engagement_index | 0.347 | mixed |

## 10. Participant-grouped prediction

Continuous task-active efficacy:

| SART source | Model | CV R2 | MAE | RMSE |
|---|---|---:|---:|---:|
| full_225 | intercept_only | -0.002 | 0.372 | 0.499 |
| full_225 | engagement_only | 0.128 | 0.346 | 0.465 |
| full_225 | inhibitory_only | 0.047 | 0.360 | 0.486 |
| full_225 | two_sart_dimensions | 0.115 | 0.349 | 0.469 |
| abbreviated_144 | intercept_only | -0.002 | 0.372 | 0.499 |
| abbreviated_144 | engagement_only | 0.109 | 0.348 | 0.470 |
| abbreviated_144 | inhibitory_only | 0.043 | 0.361 | 0.487 |
| abbreviated_144 | two_sart_dimensions | 0.091 | 0.352 | 0.475 |

Four-profile prediction:

| SART source | Model | Balanced accuracy | Chance |
|---|---|---:|---:|
| full_225 | engagement_only | 0.411 | 0.250 |
| full_225 | inhibitory_only | 0.330 | 0.250 |
| full_225 | two_sart_dimensions | 0.408 | 0.250 |
| abbreviated_144 | engagement_only | 0.369 | 0.250 |
| abbreviated_144 | inhibitory_only | 0.350 | 0.250 |
| abbreviated_144 | two_sart_dimensions | 0.359 | 0.250 |

## 11. Duration sensitivity

| Trials | Minutes | Go | NoGo | Dimension | Spearman r | Lin CCC | Low-engagement balanced accuracy |
|---:|---:|---:|---:|---|---:|---:|---:|
| 90 | 1.88 | 84 | 6 | engagement_vigilance | 0.818 | 0.844 | 0.808 |
| 90 | 1.88 | 84 | 6 | inhibitory_stability | 0.836 | 0.874 |  |
| 120 | 2.50 | 109 | 11 | engagement_vigilance | 0.882 | 0.922 | 0.871 |
| 120 | 2.50 | 109 | 11 | inhibitory_stability | 0.923 | 0.930 |  |
| 144 | 3.00 | 131 | 13 | engagement_vigilance | 0.912 | 0.940 | 0.883 |
| 144 | 3.00 | 131 | 13 | inhibitory_stability | 0.952 | 0.961 |  |
| 180 | 3.75 | 161 | 19 | engagement_vigilance | 0.962 | 0.975 | 0.933 |
| 180 | 3.75 | 161 | 19 | inhibitory_stability | 0.982 | 0.986 |  |

## 12. Interpretation

The three-minute prefix has internal support for the dimensions that pass the stated agreement gates. Commission-based inhibitory stability is expected to be less precise because the prefix contains only 13 NoGo trials.

Even a positive result is internal abbreviation evidence: the prefix is part of the full task, uses the same fixed sequence, and shares method variance with the reference. A prospective study must compare the abbreviated task with an independently administered full SART and an external outcome.

## 13. Claim-safe conclusion

This analysis estimates how much of the full paired-study SART signal is retained in its first three minutes. It can support selection of an abbreviated research protocol, but it does not validate under-activation, physiological arousal, work-readiness routing, or a production classifier.
