# Paired Vigilance and Task-Active Control Follow-Up

> This analysis tests whether SART engagement/vigilance is a useful dimension beyond Stroop/Flanker task-active control. It does not diagnose under-arousal, disengagement, sleepiness, or a brain state.

## 1. Purpose

This secondary analysis uses participant-linked Stroop, Flanker, and SART sessions to identify neutral task-active control profiles and test whether vigilance-sensitive SART dimensions add information that conflict tasks do not measure directly.

## 2. Data and integrity

- Source: Barzykowski et al. (2022), paired online and laboratory Stroop, Flanker, and SART data.
- Published summary workbook SHA-256: `884ba8bbae097e81f826fa247c2a0bb785302eb88173fbf88dfb5d3c76b8cd5b`.
- Participants: 466.
- Paired sessions: 768.
- Online sessions: 466.
- First laboratory sessions: 210.
- Second laboratory sessions: 92.
- Participants with at least two sessions: 210.

The published participant-level session table was used because it provides explicit cross-task and repeat-session linkage. Raw trial workbooks remain available for a later time-on-task analysis.

## 3. Constructed dimensions

The SART engagement-vigilance index is oriented so higher values mean fewer Go omissions and lower Go RT variability. The inhibitory-stability index is oriented so higher values mean fewer NoGo commissions and fewer anticipatory responses.

| Score | Indicator | Direction | Weight | Diagnostic PC1 variance |
|---|---|---:|---:|---:|
| sart_engagement_index | sart_omission_rate | -1 | 0.500 | 87.1% |
| sart_engagement_index | sart_go_rt_cv | -1 | 0.500 | 87.1% |
| sart_inhibitory_stability_index | sart_commission_rate | -1 | 0.500 | 90.8% |
| sart_inhibitory_stability_index | sart_anticipatory_rate | -1 | 0.500 | 90.8% |

These are behavioural dimensions. A low engagement-vigilance score is a candidate lapse/instability signal, not proof of low arousal.

## 4. Neutral task-active profiles

Mixtures used three context-adjusted dimensions: control accuracy, response speed, and conflict resilience. Component count was selected by BIC subject to minimum component sizes; component counts from one through five were compared and four profiles were not forced.

| Model | Valid | BIC | Posterior entropy | Bootstrap ARI | Sizes |
|---|---|---:|---:|---:|---|
| Paired-Control-GMM1-diag | yes | 5914.3 | 0.000 | 1.000 | 768 |
| Paired-Control-GMM1-full | yes | 5658.1 | 0.000 | 1.000 | 768 |
| Paired-Control-GMM2-diag | yes | 5320.6 | 0.292 | 0.905 | 180;588 |
| Paired-Control-GMM2-full | yes | 5164.3 | 0.288 | 0.900 | 154;614 |
| Paired-Control-GMM3-diag | yes | 5263.1 | 0.370 | 0.307 | 95;218;455 |
| Paired-Control-GMM3-full | yes | 5152.7 | 0.393 | 0.298 | 78;187;503 |
| Paired-Control-GMM4-diag | yes | 5197.1 | 0.364 | 0.441 | 96;152;252;268 |
| Paired-Control-GMM4-full | yes | 5130.7 | 0.334 | 0.724 | 51;117;202;398 |
| Paired-Control-GMM5-diag | yes | 5163.4 | 0.308 | 0.497 | 56;101;138;229;244 |
| Paired-Control-GMM5-full | yes | 5155.3 | 0.333 | 0.458 | 52;111;176;207;222 |

- Selected neutral model: `Paired-Control-GMM4-full` (BIC 5130.7; bootstrap ARI 0.724).
- Best valid three-component comparison: `Paired-Control-GMM3-full` (BIC 5152.7).

| Neutral profile | Sessions | Efficacy | Accuracy index | Speed index | Conflict resilience | SART engagement | SART inhibition | Descriptive note |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Paired-Control-GMM4-full-C1 | 202 | -0.410 | -0.051 | -0.880 | -0.300 | -0.621 | -0.363 | slow_compensatory_candidate |
| Paired-Control-GMM4-full-C2 | 398 | 0.104 | 0.066 | 0.201 | 0.045 | -0.090 | -0.173 | regulated_control_candidate |
| Paired-Control-GMM4-full-C3 | 51 | -1.400 | -2.338 | -1.040 | -0.821 | -1.522 | -0.972 | overloaded_control_candidate |
| Paired-Control-GMM4-full-C4 | 117 | -0.493 | -1.270 | 0.144 | -0.354 | -0.657 | -0.624 | fast_brittle_candidate |

## 5. Is engagement a separate dimension?

Correlations are shown at the session level, between participant means, and within participants after person-mean centring. The within-person estimate uses only participants with repeated sessions.

| Predictor | Outcome | Level | Correlation | N |
|---|---|---|---:|---:|
| sart_engagement_index | task_active_efficacy | session | 0.370 | 768 |
| sart_engagement_index | task_active_efficacy | between_person | 0.437 | 466 |
| sart_engagement_index | task_active_efficacy | within_person | 0.156 | 512 |
| sart_engagement_index | control_accuracy_index | session | 0.227 | 768 |
| sart_engagement_index | control_accuracy_index | between_person | 0.288 | 466 |
| sart_engagement_index | control_accuracy_index | within_person | 0.112 | 512 |
| sart_engagement_index | control_speed_index | session | 0.265 | 768 |
| sart_engagement_index | control_speed_index | between_person | 0.274 | 466 |
| sart_engagement_index | control_speed_index | within_person | 0.182 | 512 |
| sart_engagement_index | conflict_resilience_index | session | 0.246 | 768 |
| sart_engagement_index | conflict_resilience_index | between_person | 0.298 | 466 |
| sart_engagement_index | conflict_resilience_index | within_person | 0.063 | 512 |
| sart_inhibitory_stability_index | task_active_efficacy | session | 0.268 | 768 |
| sart_inhibitory_stability_index | task_active_efficacy | between_person | 0.265 | 466 |
| sart_inhibitory_stability_index | task_active_efficacy | within_person | 0.128 | 512 |
| sart_inhibitory_stability_index | control_accuracy_index | session | 0.247 | 768 |
| sart_inhibitory_stability_index | control_accuracy_index | between_person | 0.273 | 466 |
| sart_inhibitory_stability_index | control_accuracy_index | within_person | 0.141 | 512 |
| sart_inhibitory_stability_index | control_speed_index | session | 0.090 | 768 |
| sart_inhibitory_stability_index | control_speed_index | between_person | 0.068 | 466 |
| sart_inhibitory_stability_index | control_speed_index | within_person | 0.051 | 512 |
| sart_inhibitory_stability_index | conflict_resilience_index | session | 0.196 | 768 |
| sart_inhibitory_stability_index | conflict_resilience_index | between_person | 0.192 | 466 |
| sart_inhibitory_stability_index | conflict_resilience_index | within_person | 0.059 | 512 |

Low-to-moderate correlations support treating SART engagement and task-active control as related but non-identical dimensions. A large correlation would instead suggest that the SART score mostly relabels general performance.

## 6. Trait-state structure

| Feature | ICC(1) | Interpretation | Repeated sessions | Participants |
|---|---:|---|---:|---:|
| control_speed_index | 0.718 | mostly_between_person | 512 | 210 |
| sart_inhibitory_stability_index | 0.473 | mixed | 512 | 210 |
| task_active_efficacy | 0.396 | mixed | 512 | 210 |
| sart_engagement_index | 0.361 | mixed | 512 | 210 |
| control_accuracy_index | 0.343 | mixed | 512 | 210 |
| conflict_resilience_index | 0.292 | mixed | 512 | 210 |

ICC describes repeat-session consistency, not causation. Stable differences may reflect capacity, strategy, motor speed, or other person-level factors; session deviations may reflect time, fatigue, practice, context, or measurement noise.

## 7. Incremental prediction

All folds isolate dataset-scoped participants.

| Model | Features | CV R2 | MAE | RMSE | Participant overlap |
|---|---|---:|---:|---:|---:|
| intercept_only | none | -0.007 | 0.374 | 0.500 | 0 |
| engagement_only | sart_engagement_index | 0.126 | 0.347 | 0.466 | 0 |
| inhibitory_only | sart_inhibitory_stability_index | 0.045 | 0.361 | 0.487 | 0 |
| two_sart_dimensions | sart_engagement_index;sart_inhibitory_stability_index | 0.117 | 0.349 | 0.468 | 0 |
| expanded_sart | sart_engagement_index;sart_inhibitory_stability_index;sart_go_mean_rt_ms;sart_pre_failure_speeding_ms | 0.109 | 0.350 | 0.471 | 0 |

| SART profile model | Balanced accuracy | Chance | Participant overlap |
|---|---:|---:|---:|
| engagement_only | 0.384 | 0.250 | 0 |
| inhibitory_only | 0.325 | 0.250 | 0 |
| two_sart_dimensions | 0.407 | 0.250 | 0 |

Prediction above chance indicates cross-task association. Weak prediction alongside reliable SART measurement is also meaningful: it favours a separate readiness/vigilance layer rather than a duplicate control classifier.

## 8. Does the overloaded candidate split by engagement?

The descriptive overloaded candidate was `Paired-Control-GMM4-full-C3`. Its low-engagement candidate rate was 68.6%.

| SART mixture | BIC | AIC | Sizes | Valid sizes |
|---|---:|---:|---|---|
| overloaded-SART-GMM1 | 242.4 | 232.8 | 51 | yes |
| overloaded-SART-GMM2 | 234.4 | 213.1 | 20;31 | yes |

The two-subgroup BIC improvement over one subgroup was 8.0. A positive value favours two descriptive SART subgroups, but does not prove categorical under-activation.

## 9. Interpretation

The defensible architecture is layered:

```text
SART engagement/vigilance
  -> lapse-proneness and response-timing stability

SART inhibitory stability
  -> NoGo suppression and premature response control

Stroop/Flanker task-active control
  -> accuracy, speed policy, and conflict resilience
```

A slow or inefficient conflict-task profile should therefore not be called under-activated without convergent SART, subjective, sleep, context, or physiological evidence. Conversely, low SART engagement can occur without the same conflict-control profile.

The SART is an executive-vigilance and response-inhibition task, not a pure Psychomotor Vigilance Test. A future app should use a short PVT-like probe if the primary target is arousal vigilance and sleep-loss sensitivity.

## 10. Claim-safe conclusion

This paired follow-up tests whether vigilance-sensitive SART behaviour adds a dimension beyond conflict-task performance. It can support a multi-layer readiness model if engagement and inhibitory stability show distinct repeat-session and cross-task patterns. It does not validate under-activation, clinical states, intervention routing, or production classification.
