# Two-Minute SART Validation

> This is an internal abbreviation analysis. The first 96 trials are nested within the full 225-trial SART and are not an independent validation sample.

## 1. Purpose

This analysis tests whether the first 96 trials (2 minutes at 1250 ms per trial) preserve the paired study's full-session SART engagement-vigilance and inhibitory-stability information.

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

## 3. Two-Minute prefix

- Trials: 96.
- Go trials: 88.
- NoGo trials: 8.
- The source used one fixed semi-random sequence. Every session therefore has the same 88/8 composition.

A redesigned or rebalanced sequence is not validated by this analysis.

## 4. Raw metric agreement

| Measure | Pearson r | Spearman r | Lin CCC | Bias | MAE |
|---|---:|---:|---:|---:|---:|
| commission_rate | 0.844 | 0.840 | 0.823 | 0.055 | 0.121 |
| omission_rate | 0.853 | 0.799 | 0.810 | -0.008 | 0.014 |
| anticipatory_rate | 0.895 | 0.836 | 0.892 | -0.004 | 0.011 |
| go_mean_rt_ms | 0.920 | 0.902 | 0.899 | -16.328 | 23.143 |
| go_rt_cv | 0.808 | 0.809 | 0.790 | -0.023 | 0.047 |

## 5. Composite score agreement

| Dimension | Pearson r | Spearman r | Lin CCC | MAE | Heuristic result |
|---|---:|---:|---:|---:|---|
| Engagement-vigilance | 0.859 | 0.812 | 0.856 | 0.407 | supported |
| Inhibitory stability | 0.889 | 0.865 | 0.886 | 0.346 | supported |

The heuristic gates were not preregistered: engagement required Spearman r >= .80, CCC >= .75, and low-engagement balanced accuracy >= .75; inhibition required Spearman r >= .70 and CCC >= .65.

Agreement remains high after separating stable person differences from session deviations:

| Dimension | Level | Spearman correlation | N |
|---|---|---:|---:|
| engagement_vigilance | session | 0.812 | 744 |
| engagement_vigilance | between_person | 0.837 | 456 |
| engagement_vigilance | within_person | 0.777 | 491 |
| inhibitory_stability | session | 0.865 | 744 |
| inhibitory_stability | between_person | 0.884 | 456 |
| inhibitory_stability | within_person | 0.842 | 491 |

## 6. Low-engagement agreement

- Full-session low-engagement rate: 28.2%.
- Two-Minute low-engagement rate: 29.4%.
- Sensitivity: 0.748.
- Specificity: 0.884.
- Balanced accuracy: 0.816.
- Cohen's kappa: 0.623.

## 7. Control-profile association

- Full SART Cramer's V: 0.329.
- Two-Minute SART Cramer's V: 0.306.

| SART source | Neutral profile | Low-engagement rate |
|---|---|---:|
| full_225 | Paired-Control-GMM4-full-C1 | 35.1% |
| full_225 | Paired-Control-GMM4-full-C2 | 16.7% |
| full_225 | Paired-Control-GMM4-full-C3 | 72.3% |
| full_225 | Paired-Control-GMM4-full-C4 | 38.1% |
| abbreviated_96 | Paired-Control-GMM4-full-C1 | 38.1% |
| abbreviated_96 | Paired-Control-GMM4-full-C2 | 17.9% |
| abbreviated_96 | Paired-Control-GMM4-full-C3 | 68.1% |
| abbreviated_96 | Paired-Control-GMM4-full-C4 | 38.1% |

## 8. Between- and within-person associations

| SART source | Dimension | Level | Correlation with task-active efficacy | N |
|---|---|---|---:|---:|
| full_225 | sart_engagement_index | session | 0.382 | 744 |
| full_225 | sart_engagement_index | between_person | 0.473 | 456 |
| full_225 | sart_engagement_index | within_person | 0.102 | 491 |
| full_225 | sart_inhibitory_stability_index | session | 0.273 | 744 |
| full_225 | sart_inhibitory_stability_index | between_person | 0.286 | 456 |
| full_225 | sart_inhibitory_stability_index | within_person | 0.088 | 491 |
| abbreviated_96 | sart_engagement_index | session | 0.319 | 744 |
| abbreviated_96 | sart_engagement_index | between_person | 0.412 | 456 |
| abbreviated_96 | sart_engagement_index | within_person | 0.066 | 491 |
| abbreviated_96 | sart_inhibitory_stability_index | session | 0.293 | 744 |
| abbreviated_96 | sart_inhibitory_stability_index | between_person | 0.325 | 456 |
| abbreviated_96 | sart_inhibitory_stability_index | within_person | 0.095 | 491 |

## 9. Repeat-session ICC

| SART source | Dimension | ICC(1) | Interpretation |
|---|---|---:|---|
| full_225 | sart_inhibitory_stability_index | 0.491 | mixed |
| full_225 | sart_engagement_index | 0.391 | mixed |
| abbreviated_96 | sart_inhibitory_stability_index | 0.367 | mixed |
| abbreviated_96 | sart_engagement_index | 0.248 | mostly_within_person |

Projected reliability of a personal baseline formed by averaging comparable repeated sessions:

| Dimension | Sessions | Projected reliability |
|---|---:|---:|
| sart_inhibitory_stability_index | 1 | 0.367 |
| sart_inhibitory_stability_index | 3 | 0.635 |
| sart_inhibitory_stability_index | 5 | 0.744 |
| sart_inhibitory_stability_index | 7 | 0.802 |
| sart_inhibitory_stability_index | 10 | 0.853 |
| sart_engagement_index | 1 | 0.248 |
| sart_engagement_index | 3 | 0.497 |
| sart_engagement_index | 5 | 0.622 |
| sart_engagement_index | 7 | 0.698 |
| sart_engagement_index | 10 | 0.767 |

These Spearman-Brown projections are planning estimates, not observed week-long reliability. They assume comparable sessions, independent measurement error, and a stable person baseline.

## 10. Participant-grouped prediction

Continuous task-active efficacy:

| SART source | Model | CV R2 | MAE | RMSE |
|---|---|---:|---:|---:|
| full_225 | intercept_only | -0.002 | 0.372 | 0.499 |
| full_225 | engagement_only | 0.128 | 0.346 | 0.465 |
| full_225 | inhibitory_only | 0.047 | 0.360 | 0.486 |
| full_225 | two_sart_dimensions | 0.115 | 0.349 | 0.469 |
| abbreviated_96 | intercept_only | -0.002 | 0.372 | 0.499 |
| abbreviated_96 | engagement_only | 0.090 | 0.353 | 0.475 |
| abbreviated_96 | inhibitory_only | 0.048 | 0.362 | 0.486 |
| abbreviated_96 | two_sart_dimensions | 0.086 | 0.354 | 0.476 |

Four-profile prediction:

| SART source | Model | Balanced accuracy | Chance |
|---|---|---:|---:|
| full_225 | engagement_only | 0.411 | 0.250 |
| full_225 | inhibitory_only | 0.330 | 0.250 |
| full_225 | two_sart_dimensions | 0.408 | 0.250 |
| abbreviated_96 | engagement_only | 0.369 | 0.250 |
| abbreviated_96 | inhibitory_only | 0.353 | 0.250 |
| abbreviated_96 | two_sart_dimensions | 0.371 | 0.250 |

## 11. Duration sensitivity

| Trials | Minutes | Go | NoGo | Dimension | Spearman r | Lin CCC | Low-engagement balanced accuracy |
|---:|---:|---:|---:|---|---:|---:|---:|
| 90 | 1.88 | 84 | 6 | engagement_vigilance | 0.818 | 0.844 | 0.808 |
| 90 | 1.88 | 84 | 6 | inhibitory_stability | 0.836 | 0.874 |  |
| 96 | 2.00 | 88 | 8 | engagement_vigilance | 0.812 | 0.856 | 0.816 |
| 96 | 2.00 | 88 | 8 | inhibitory_stability | 0.865 | 0.886 |  |
| 120 | 2.50 | 109 | 11 | engagement_vigilance | 0.882 | 0.922 | 0.871 |
| 120 | 2.50 | 109 | 11 | inhibitory_stability | 0.923 | 0.930 |  |
| 144 | 3.00 | 131 | 13 | engagement_vigilance | 0.912 | 0.940 | 0.883 |
| 144 | 3.00 | 131 | 13 | inhibitory_stability | 0.952 | 0.961 |  |
| 180 | 3.75 | 161 | 19 | engagement_vigilance | 0.962 | 0.975 | 0.933 |
| 180 | 3.75 | 161 | 19 | inhibitory_stability | 0.982 | 0.986 |  |

## 12. Interpretation

The two-minute prefix has internal support for the dimensions that pass the stated agreement gates. Commission-based inhibitory stability is expected to be less precise because the prefix contains only 8 NoGo trials.

Even a positive result is internal abbreviation evidence: the prefix is part of the full task, uses the same fixed sequence, and shares method variance with the reference. A prospective study must compare the abbreviated task with an independently administered full SART and an external outcome.

## 13. Claim-safe conclusion

This analysis estimates how much of the full paired-study SART signal is retained in its first 2 minutes. It can support selection of an abbreviated research protocol, but it does not validate under-activation, physiological arousal, work-readiness routing, or a production classifier.
