# COG-BCI Cognitive-Autonomic Bridge Study

## Purpose

This retrospective bridge analysis tests whether concurrent ECG-derived
autonomic dimensions share variance with, diverge from, and improve prediction
beyond cognitive performance during PVT, Flanker, N-back, and MATB tasks. It is
not a replication of the proposed Stroop-Flanker-SART protocol.

## Inputs And Quality

- Participants processed: 5
- Sessions represented: 15
- Task recordings imported: 120
- Window rows: 6079
- Median 120-second detector concordance: 1.000
- 120-second ECG quality-pass rate: 1.000

## Published-Effect Replication Gate

Status: **passed**

At least two of three published-effect domains supported.

Supported domains: 2 of 3 testable.
Domains meeting the directional rule: MATB difficulty, N-back difficulty.
Novel factor, coupling, prediction, divergence, and lagged analyses are run only
after this gate passes.

## Duration Reliability

The duration table compares mean features from 60-, 120-, and 180-second
windows against the corresponding full task block. Two-minute time-domain
features are the app-aligned primary analysis; nonlinear dynamics remain
candidate features unless their availability and loading direction are stable
at 180 seconds and full block.

Across available features, the median 120-second versus full-block Spearman
agreement was 0.970. HR and standard time-domain
features were strongest; HR/NN slopes were weaker.

## Trait-State Decomposition

`between_within_decomposition.csv` reports descriptive between-person and
within-person variance fractions. These are variance proxies, not evidence that
the dimensions are immutable traits or discrete states.

## Autonomic Dimensions

The five-person pilot supported three bootstrap-stable within-person PCA
components in the selected time-domain feature set: C1 variance=0.469, median Tucker=0.993, p05=0.948; C2 variance=0.276, median Tucker=0.992, p05=0.951; C3 variance=0.155, median Tucker=0.998, p05=0.978. Component
signs are arbitrary. Loading patterns are consistent with (1) lower activation
plus short-term variability/flexibility, (2) broad variability plus slower
trend organisation, and (3) directional HR/NN trend plus relative short-term
Poincare geometry. Between-person factor analysis was not testable with five
participants, and autonomic GMM clustering was skipped because fewer than
eight participants contributed.

## Shared And Divergent Structure

Autonomic dimensions, shared-variance models, divergence profiles, and
participant-grouped incremental predictions are reported only when the
published-effect gate passes. Participant isolation is used for all predictive
folds. With five participants, incremental prediction is descriptive; formal
participant-permutation and bootstrap inference remains gated to a larger run.

Task-specific participant-held-out PLS did not generalise above baseline; the
best multivariate R2 was -0.036. The largest descriptive Model D/E
gain over cognitive Model B was
0.383 for
`next_flanker_median_rt_ms` using Model
E. These pilot gains were not consistently
stronger than shuffled ECG controls, so H2-H4 are not supported by this pilot.

## Claim-Safe Conclusion

Across this run, the bridge pipeline advanced to novel modelling because the replication gate passed. The pilot supports reliable two-minute ECG feature extraction and a multidimensional within-person autonomic structure beyond mean HR. It does not yet show robust out-of-participant cognitive-autonomic coupling or incremental HRV prediction. The study cannot validate the exact Flow Zone `4 x 2` model, infer discrete brain states, or establish production classifier performance.
