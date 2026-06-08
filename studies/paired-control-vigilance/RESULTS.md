# Results

## Sample And Model Selection

The complete analysis included 768 paired sessions from 466 participants. The
BIC-selected valid task-active model was the four-component full-covariance GMM:

```text
model: Paired-Control-GMM4-full
BIC: 5130.7
AIC: 4949.6
posterior entropy: 0.334
participant-bootstrap median ARI: 0.724
component sizes: 51, 117, 202, 398
```

The best three-component model had BIC `5152.7` and bootstrap median ARI
`0.298`. Thus, the four-component model improved BIC by 22.0 and was markedly
more stable in this sample. This supports four distinguishable statistical
profiles here, not four validated natural kinds.

## Profile Centroids

| Neutral profile | Sessions | Stroop accuracy | Stroop RT, ms | Stroop cost, ms | Flanker accuracy | Flanker RT, ms | SART engagement | Descriptive candidate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| C1 | 202 | .968 | 984 | 159 | .989 | 501 | -.621 | slow compensatory |
| C2 | 398 | .972 | 718 | 82 | .991 | 416 | -.090 | regulated |
| C3 | 51 | .874 | 1041 | 153 | .895 | 520 | -1.522 | globally overloaded |
| C4 | 117 | .931 | 740 | 100 | .962 | 415 | -.657 | fast brittle |

C1 and C3 were both slow, but C1 retained high accuracy whereas C3 showed broad
accuracy failure. C4 was fast but less accurate than C2. This accuracy-speed
separation is the main reason the fourth component is not redundant with the
three-profile interpretation obtained in the earlier ACDC Stroop-focused work.

## Vigilance As An Additional Dimension

SART engagement and task-active efficacy were related:

| Level | Spearman correlation |
|---|---:|
| Session | .370 |
| Between person | .437 |
| Within person | .156 |

The weaker within-person association and incomplete cross-profile prediction
show that SART engagement is not simply a duplicate of task-active control.
Using both SART dimensions to predict four-component membership gave
participant-grouped balanced accuracy `.407`, compared with chance `.250`.

Control profile and low SART engagement were associated:

```text
chi-square(3) = 79.787
p = 3.41e-17
Cramer's V = .322
```

| Candidate profile | Low-engagement rate | One-vs-rest odds ratio, 95% CI |
|---|---:|---:|
| Slow compensatory | 35.6% | 1.58 [1.08, 2.30] |
| Regulated | 16.6% | 0.28 [0.20, 0.40] |
| Globally overloaded | 68.6% | 6.27 [3.53, 11.96] |
| Fast brittle | 39.3% | 1.80 [1.19, 2.71] |

The association is substantial but not deterministic: every task-active
profile contained both preserved- and low-engagement sessions.

## Mixed Trait-State Structure

| Feature | ICC(1) | Interpretation |
|---|---:|---|
| Control speed | .718 | mostly between person |
| SART inhibitory stability | .473 | mixed |
| Task-active efficacy | .396 | mixed |
| SART engagement | .361 | mixed |
| Control accuracy | .343 | mixed |
| Conflict resilience | .292 | mixed |

Among 210 repeated participants, 48.1% occupied more than one task-active
profile. Overall adjacent-session persistence was 60.9%.

| Candidate profile | Adjacent persistence | Binary membership ICC |
|---|---:|---:|
| Slow compensatory | 55.3% | .385 |
| Regulated | 71.3% | .371 |
| Globally overloaded | 27.3% | .187 |
| Fast brittle | 44.9% | .328 |

The profiles therefore mix stable individual differences with session-specific
variation. The globally overloaded candidate was the least persistent.

## Shortened Stroop And Flanker

The conservative two-minute Stroop plus two-minute Flanker configuration used
a median of 101 Stroop trials and 44 Flanker trials:

```text
matched sessions: 742
participants: 458
participant-grouped balanced accuracy: .744
macro F1: .718
coverage at probability >= .60: 77.4%
accuracy when confident: 84.5%
```

| Candidate profile | Recall |
|---|---:|
| Slow compensatory | .747 |
| Regulated | .796 |
| Globally overloaded | .673 |
| Fast brittle | .759 |

Combined task prefixes outperformed either task alone. For comparison, Stroop
100-trial balanced accuracy was `.634`, Flanker 80-trial accuracy was `.607`,
and an 80+80-trial combination reached `.786`.

Fixed-duration Stroop produced unequal evidence. Median two-minute yield was 86
trials for C1, 106 for C2, 81 for C3, and 104 for C4. Almost half of C3 sessions
produced fewer than 80 trials and 18.4% produced fewer than 60. Trial count and
abstention are therefore essential in any prospective protocol.

## Claim-Safe Result

This dataset supports a reproducible four-component statistical description of
paired conflict-task performance and a related but non-identical SART
engagement dimension. It also supports prospective testing of a seven-minute
protocol. It does not establish that the profiles are discrete cognitive
states, validate intervention routing, or provide independent evidence for a
deployable classifier.
