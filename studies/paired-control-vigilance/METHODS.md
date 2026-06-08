# Methods

## Design And Questions

This is an exploratory secondary analysis of a public repeated-measures dataset
containing Stroop, Eriksen Flanker, and Sustained Attention to Response Task
(SART) performance. The analysis separates:

- task-active control, estimated from Stroop and Flanker accuracy, speed, and
  congruency costs;
- engagement-vigilance, estimated from SART Go omissions and Go RT
  variability;
- inhibitory stability, estimated from SART NoGo commissions and anticipatory
  responses.

The principal analysis discovers neutral task-active control components without
using SART variables. SART variables are then used to test whether vigilance
adds a related but non-identical dimension. Repeat sessions estimate mixed
between-person and within-person structure. Trial prefixes assess internal
recoverability of the full-session partition.

## Sample

The published summary workbook contributed 768 complete paired sessions from
466 participants:

| Session | Sessions |
|---|---:|
| Online | 466 |
| First laboratory | 210 |
| Second laboratory | 92 |

The repeated-session subset contained 512 observations from 210 participants.
The trial-prefix analysis retained 742 sessions from 458 participants with
matched Stroop and Flanker raw records.

## Session Features

For each task:

```text
accuracy = mean(congruent accuracy, incongruent accuracy)
mean RT = mean(congruent correct RT, incongruent correct RT)
RT interference = incongruent correct RT - congruent correct RT
accuracy interference = congruent accuracy - incongruent accuracy
throughput = accuracy / mean RT in seconds
```

Each source measure was robustly standardized within session setting
(`online`, `lab1`, or `lab2`) using the median and interquartile range, with
standardized values clipped to `[-5, 5]`.

Three task-active indices were formed:

```text
control accuracy
  = mean(standardized Stroop accuracy, standardized Flanker accuracy)

control speed
  = negative mean(standardized Stroop RT, standardized Flanker RT)

conflict resilience
  = negative mean(standardized Stroop and Flanker RT and accuracy costs)

task-active efficacy
  = mean(control accuracy, control speed, conflict resilience)
```

Higher values consistently indicate stronger performance.

## SART Dimensions

Two transparent equal-weight scores were computed from robustly standardized
indicators:

```text
engagement-vigilance
  = mean(-omission rate, -Go RT coefficient of variation)

inhibitory stability
  = mean(-commission rate, -anticipatory response rate)
```

Each score was centered on its median and scaled by its interquartile range.
One-component PCA was used only as a diagnostic of common variance, not to set
the weights. The first component explained 87.1% of engagement-indicator
variance and 90.8% of inhibition-indicator variance.

`sart_engagement_index <= -0.5` was used as a preregistration-style descriptive
threshold for a low-engagement candidate session. It is not a clinical or
physiological arousal threshold.

## Task-Active Mixture Analysis

Gaussian mixture models were fitted to robust-scaled:

```text
control accuracy
control speed
conflict resilience
```

Models compared `k = 1..5` under diagonal and full covariance. Each model used
20 initializations and seed 42. Solutions were considered valid only when each
component contained at least 20 sessions and at least 5% of observations. Full
covariance was permitted only when the sample exceeded ten times the estimated
free-parameter count.

The valid solution with minimum BIC was selected. Participant-clustered
bootstrap resampling estimated adjusted Rand index stability over 50
replications. Cluster identifiers remained neutral. Descriptive labels were
assigned after examining centroids.

## Cross-Dimension Analyses

Spearman correlations between SART dimensions and task-active indices were
reported at:

1. the session level;
2. the between-person level using participant means;
3. the within-person level after person-mean centering among repeated
   participants.

One-way ICC(1) estimates described repeat-session consistency. Participant-
grouped five-fold models tested whether SART dimensions predicted continuous
task-active efficacy or four-component membership without participant leakage.

The association between control profile and low SART engagement used a
chi-square test and Cramer's V. One-versus-rest odds ratios and confidence
intervals were obtained using 5,000 participant-clustered bootstrap samples.

## Repeat-Session Profiles

Profile repeatability was summarized using:

- the proportion of repeated participants occupying more than one profile;
- adjacent-session persistence;
- profile-specific persistence;
- binary profile-membership ICC(1).

Session order was online, first laboratory, then second laboratory. These
statistics describe repeatability and transition, not the elapsed time required
for a cognitive state to change.

## Shortened-Task Recovery

Raw Stroop and Flanker rows were linked to the explicit session table. Prefix
features included trial count, accuracy, mean and median correct RT, RT
coefficient of variation, throughput, congruent and incongruent accuracy and
RT, and RT and accuracy congruency costs.

The modeled two-minute Stroop prefix accumulated:

```text
observed response latency
+ 400 ms inter-trial interval
+ 400 ms after an error
```

The source Flanker protocol allowed up to 2700 ms per trial. A conservative
two-minute prefix therefore used `floor(120000 / 2700) = 44` target-coded
trials. Practice and prefatory instruction rows were excluded.

Five-fold participant-grouped classification assessed recovery of the
full-session neutral partition. Preprocessing and classification were fitted
inside each training fold. Reported metrics were balanced accuracy, macro F1,
per-class recall, posterior confidence, confident coverage at probability
`>= 0.60`, and accuracy among confident predictions.

## Three-Minute SART Abbreviation

The raw SART workbook contained 788 complete main blocks of 225 trials. Raw
bouts were matched to paired-study sessions only within participant. One-to-one
assignment minimized a fingerprint distance based on full-session commission
percentage, omission percentage, anticipatory count, Go mean RT, and Go RT CV.
Assignments were accepted only when the normalized fingerprint cost was at most
`.01`. This retained 744 exact matches from 456 participants; 20 mismatched or
ambiguous assignments and four paired sessions without a candidate raw bout
were excluded.

The primary abbreviation was the first 144 trials:

```text
144 trials x 1250 ms = 180 seconds
131 Go trials
13 NoGo trials
```

For each prefix, commissions were divided by presented NoGo trials, omissions
and anticipatory responses by presented Go trials, and Go RT mean, SD, and CV
used valid Go responses. Engagement-vigilance and inhibitory-stability scores
were reconstructed using the same within-setting robust standardization,
orientation, equal weighting, median centering, and IQR scaling as the full
study.

Agreement with the full published scores was evaluated using Pearson and
Spearman correlations, Lin's concordance, bias, MAE, and RMSE. The existing
`-0.5` low-engagement threshold was compared using sensitivity, specificity,
balanced accuracy, and Cohen's kappa. Person-mean decomposition separated
between-person and within-person agreement.

The validation also repeated:

- control-profile versus low-engagement association;
- repeat-session ICC;
- participant-grouped prediction of task-active efficacy and neutral profile;
- duration sensitivity at 90, 120, 144, and 180 trials.

Interpretive agreement gates were post hoc and explicitly heuristic. The
analysis is internal because every abbreviated observation is nested within its
full-session reference and uses the same fixed sequence.

## Statistical Status

All mixture labels, thresholds, and short-protocol analyses are exploratory.
The shortened-task target is the full-session model from the same dataset, so
performance is internal partition recovery rather than external criterion
validity. No analysis demonstrates treatment response, workplace performance,
clinical diagnosis, physiological arousal, or a discrete brain state.

## Software

The analysis uses Python 3.12 with package versions frozen by the repository
environment. The exact seed, source hashes, parameters, Git commit, and package
versions are recorded in `outputs/manifests/`.
