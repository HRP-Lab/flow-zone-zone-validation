# Paired-Study Joint and Repeat-Session Results

> Profile names below are descriptive interpretations of neutral mixture components. They are not validated cognitive states.

## Control and engagement association

- Sessions: 768.
- Participants: 466.
- Low-engagement threshold: SART engagement index <= `-0.50`.
- Chi-square: `79.787`, df `3`, p `3.41e-17`.
- Cramer's V: `0.322`.

| Neutral profile | Interpretation | Sessions | Low engagement | Rate | Observed/expected |
|---|---|---:|---:|---:|---:|
| Paired-Control-GMM4-full-C1 | slow_compensatory_candidate | 202 | 72 | 35.6% | 1.25 |
| Paired-Control-GMM4-full-C2 | regulated_control_candidate | 398 | 66 | 16.6% | 0.58 |
| Paired-Control-GMM4-full-C3 | overloaded_control_candidate | 51 | 35 | 68.6% | 2.41 |
| Paired-Control-GMM4-full-C4 | fast_brittle_candidate | 117 | 46 | 39.3% | 1.38 |

Participant-clustered bootstrap intervals:

| Interpretation | Low-engagement rate, 95% CI | One-vs-rest OR, 95% CI |
|---|---:|---:|
| slow_compensatory_candidate | 35.6% [28.4%, 43.1%] | 1.58 [1.08, 2.30] |
| regulated_control_candidate | 16.6% [12.8%, 20.6%] | 0.28 [0.20, 0.40] |
| overloaded_control_candidate | 68.6% [55.8%, 80.5%] | 6.27 [3.53, 11.96] |
| fast_brittle_candidate | 39.3% [30.7%, 48.8%] | 1.80 [1.19, 2.71] |

The dimensions are associated but not deterministic. Every control profile contains both preserved- and low-engagement sessions.

## Repeat-session profile structure

- Repeated-session participants: 210.
- Repeated sessions: 512.
- Participants showing multiple profiles: 48.1%.
- Overall adjacent-session persistence: 60.9%.

| Interpretation | Sessions | Participants | Adjacent persistence | Always profile among ever-profile participants |
|---|---:|---:|---:|---:|
| slow_compensatory_candidate | 140 | 91 | 55.3% | 29.7% |
| regulated_control_candidate | 268 | 150 | 71.3% | 46.7% |
| overloaded_control_candidate | 24 | 20 | 27.3% | 5.0% |
| fast_brittle_candidate | 80 | 56 | 44.9% | 19.6% |

### Binary profile ICC

| Profile indicator | ICC(1) | Interpretation |
|---|---:|---|
| is_C1 | 0.385 | mixed |
| is_C2 | 0.371 | mixed |
| is_C4 | 0.328 | mixed |
| is_C3 | 0.187 | mostly_within_person |

The control profiles therefore show mixed trait-state structure. The regulated and slow-compensatory components are more persistent, whereas the globally overloaded component is comparatively transient in the repeated-session subset.
