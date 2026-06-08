# Paper Guide

## Recommended Paper Type

Frame the manuscript as an exploratory secondary analysis with four linked
contributions:

1. multivariate task-active control profiles across paired Stroop and Flanker;
2. incremental SART engagement-vigilance and inhibitory-stability dimensions;
3. repeat-session structure and shortened-task recoverability.
4. internal validation of two-minute and three-minute SART prefixes.

Do not lead with an app, interventions, four zones, or brain-state language.
Those are implications for prospective research, not findings of this dataset.

## Candidate Title

> Task-active control profiles and vigilance form related but distinct
> dimensions: An exploratory repeated-session analysis of paired Stroop,
> Flanker, and SART data

## Abstract Structure

**Background:** Conflict-control and vigilance tasks may capture different
sources of cognitive performance variation.

**Method:** Report the public dataset, 466 participants, 768 paired sessions,
three robust task-active dimensions, neutral GMM comparison, SART dimensions,
participant-grouped inference, repeat-session analyses, raw-prefix recovery,
and the 96- and 144-trial SART abbreviation analyses.

**Results:** Report the four-component BIC/stability result, centroid contrasts,
control-vigilance association, mixed ICC/transition structure, and `.744`
balanced accuracy for the conservative shortened pair. Report two-minute SART
engagement and inhibition concordance (`.856` and `.886`) and low-engagement
balanced accuracy (`.816`), alongside the stronger three-minute values (`.940`,
`.961`, and `.883`).

**Conclusion:** Paired conflict tasks distinguish regulated, slow compensatory,
globally overloaded, and fast brittle candidate profiles, while SART engagement
adds partially separate information. Prospective external validation is
required.

## Manuscript Structure

### Introduction

- Explain why mean RT or accuracy alone collapses speed-accuracy policy and
  control failure.
- Motivate paired conflict tasks as a way to test cross-task generality.
- Separate task-active control from vigilance and response inhibition.
- State that profile count is empirical and exploratory.
- Prestate the mixed trait-state and shortened-protocol questions.

### Methods

Use [METHODS.md](METHODS.md) as the source. Include:

- source study, ethics, recruitment, and retest selection;
- data integrity hashes and inclusion flow;
- exact composite equations and orientation;
- session-setting robust standardization;
- GMM candidate set, validity rules, BIC selection, and grouped bootstrap;
- participant-grouped cross-validation;
- repeat-session ICC and transition definitions;
- raw-prefix timing assumptions and Flanker discrepancy;
- participant-bounded SART fingerprint linkage and 96-/144-trial
  abbreviations;
- analysis status and claim boundary.

### Results

Use [RESULTS.md](RESULTS.md) and the tracked CSV files. Recommended order:

1. sample and data completeness;
2. mixture comparison and centroid table;
3. SART construct checks;
4. control-vigilance association;
5. between/within and ICC results;
6. repeat-session transitions;
7. shortened-task recovery;
8. two- and three-minute SART agreement and duration sensitivity;
9. sensitivity and limitations.

### Discussion

- Emphasize the slow-compensatory versus globally overloaded distinction.
- Explain that vigilance is associated with, but not reducible to, control
  profile.
- Interpret ICC and transitions as mixed trait-state structure.
- Treat the six-minute minimum and seven-minute preferred protocols as
  prospective design hypotheses.
- Discuss source retest selection, no subjective/physiological measures,
  internal recovery target, small overloaded component, and exploratory model
  selection.

## Primary Tables

1. Sample and task measures.
2. GMM model comparison.
3. Raw profile centroids with neutral IDs.
4. SART association, ICC, and repeat-session results.
5. Shortened-task recovery and per-profile recall.
6. Two- and three-minute SART agreement and duration sensitivity.

## Primary Figures

1. Task-active efficacy versus SART engagement, coloured by neutral component.
2. Low-engagement rate by neutral component.
3. Shortened-task balanced accuracy by prefix configuration.

## Supplement

- Full mixture comparison and component sizes.
- Factor diagnostic table.
- All between/within correlations.
- Participant-grouped prediction tables.
- Transition matrix and binary membership ICC.
- Fixed-duration Stroop trial-yield bias.
- Source hashes, software versions, and run manifest.

## Required Sensitivity Analyses Before Submission

- Repeat model selection separately in online and laboratory sessions.
- Leave-one-session-setting-out centroid or assignment sensitivity.
- Compare GMM results with a continuous-factor account.
- Repeat shortened recovery with nested model/threshold selection.
- Quantify effects of source-study retest selection.
- Add confidence intervals for key centroid contrasts and short-test metrics.
- Freeze a final analysis specification before any confirmatory rerun.

## Publication Positioning

The strongest publication claim is methodological and descriptive:

> Joint Stroop-Flanker performance separates accuracy-preserving slowness from
> broad overload and fast brittle responding, while SART vigilance adds a
> partially distinct dimension with mixed trait-state structure.

Avoid:

- “four cognitive states were validated”;
- “the test diagnoses readiness”;
- “the classifier predicts work performance”;
- “the profiles prescribe interventions”;
- “SART measures physiological arousal.”

Potential journal fit should be assessed against current aims before
submission. Broadly plausible categories are cognitive methods, attention and
performance, open secondary analysis, and behavioural data-science journals.
