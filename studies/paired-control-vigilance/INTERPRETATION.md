# Interpretation

## Working Taxonomy

The paired Stroop-Flanker data support four task-active control candidates more
cleanly than the earlier Stroop-only analysis:

| Candidate | Behavioural interpretation | Possible baseline support |
|---|---|---|
| Regulated control | Accurate, relatively fast, and resilient to conflict | Preserve challenge, normal pacing, avoid unnecessary intervention |
| Globally overloaded control | Slow, inaccurate, and conflict-vulnerable across both tasks | Simplify, scaffold, reduce information density, protect recovery, build bandwidth gradually |
| Fast brittle control | Fast response policy with elevated accuracy failure | Slow commitment, force disconfirmation, use checklists, add circuit breakers, train reset after errors |
| Slow compensatory control | Slow but highly accurate, suggesting deliberate caution or costly compensation rather than global failure | Reduce unnecessary checking, time-box review, practise graded speed with accuracy safeguards, and distinguish strategic caution from fatigue |

These supports are hypotheses for prospective intervention studies. The current
dataset contains no intervention outcomes and cannot show that any suggestion
causes movement toward regulated control.

## Why Four Profiles Appeared Here

Stroop alone can confound two forms of slowness:

```text
slow because control is failing
slow because accuracy is being protected through caution or compensation
```

Adding Flanker provides a second conflict task with a different response
mapping and lower overall latency. The paired data separate a slow,
high-accuracy profile from a slow, broadly inaccurate profile. That distinction
was less visible in the ACDC Stroop-only analysis and is the strongest
substantive justification for the fourth component.

## Information-Processing Interpretation

A cautious mapping onto an information-processing account is:

```text
regulated
  reliable information selection and transmission under conflict

globally overloaded
  demand exceeds effective stabilising capacity, producing slow and unreliable
  performance

fast brittle
  high-gain or low-threshold response policy that preserves speed but produces
  clustered or broad accuracy failure

slow compensatory
  reliable selection maintained through a conservative threshold or costly
  compensatory effort
```

The data measure behavioural outcomes, not channel capacity in bits per second.
MFT-M or another parametric information-rate task would be required to test a
capacity-limit interpretation directly.

## Vigilance And Arousal Layer

SART engagement-vigilance is related to the four control profiles but is not
fully determined by them. The practical architecture is therefore closer to a
`4 x continuous` model than a single categorical taxonomy:

```text
task-active control
  regulated / overloaded / brittle / slow compensatory

engagement-vigilance
  preserved <----------------------------> lapse-prone
```

For communication, a binary preserved/low-engagement flag can be used, but the
continuous score should be retained analytically. SART is not a pure arousal
measure. A short PVT-like probe, subjective sleepiness/context check, and
RR/HRV baseline would be needed to distinguish low arousal, sleep debt,
disengagement, stress, and task-specific instability.

All combinations are possible, but they are not equally common. Low engagement
was least frequent in regulated sessions and most frequent in globally
overloaded sessions. The dimensions should therefore be treated as associated,
not independent or redundant.

## Individual Differences And Within-Person Change

The evidence supports a mixed model:

- Control speed is strongly person-like in these repeated sessions.
- Accuracy, conflict resilience, task-active efficacy, SART engagement, and
  inhibitory stability all contain both between-person and within-person
  variance.
- Nearly half of repeated participants occupied more than one control profile.
- The overloaded profile was comparatively transient, while regulated
  membership was more persistent.

Stable differences could reflect processing speed, executive-control ability,
learned strategy, response caution, task familiarity, or other person-level
factors. Session deviations could reflect fatigue, practice, sleep, stress,
motivation, time of day, environment, caffeine, or measurement noise. Most of
these causes were not measured, so they should not be assigned from the
behavioural profile alone.

The spacing of the available sessions permits a statement that profile changes
occur across sessions or days. It does not estimate minute-scale transition
rates or prove that a profile will remain stable across a subsequent 40-minute
work block.

## Candidate Protocol

The current internal-recovery evidence justifies prospective validation of:

```text
20-30 second context check
3-minute abbreviated SART or PVT-like vigilance probe
2-minute Stroop
2-minute Flanker
probabilistic four-profile task-active output
continuous vigilance output
abstention for insufficient trials or low confidence
```

High-level implementation requirements for all three tasks are specified in
[PROTOCOL_TASK_SPECS.md](PROTOCOL_TASK_SPECS.md).

SART is the replication-first option because it was administered in the paired
study. PVT-B is an alternative when the primary target is low-control
behavioural alertness and sleep-loss sensitivity. A full source-compatible SART
would extend the scored battery to approximately 8 minutes 41 seconds; a
three-minute abbreviated SART preserves the seven-minute target but requires
new reliability validation.

For Stroop, target at least 80 scored trials and normally abstain below 60. The
source Flanker timing supports 44 trials as a conservative two-minute minimum.
A response-contingent app may obtain more, but changing the source timing is a
new protocol requiring validation.

The first several longitudinal sessions should establish a personal reference
distribution rather than produce strong routing advice. A defensible
development sequence is:

1. collect 5-10 baseline sessions across several days and times;
2. estimate person-centered deviations alongside population scores;
3. return probabilities and uncertainty rather than a hard label;
4. test same-day reliability and prediction of an independent work outcome;
5. randomize low-risk supports and test whether they improve later performance;
6. lock the model before external validation.

## Routing Boundary

The proposed use is decision support for the next work block, not diagnosis.
Until intervention trials exist, routing should remain optional, low risk, and
easy to reverse. Breathing, activation, workload simplification, or pacing
instructions cannot be selected solely from a cognitive label because similar
behaviour may arise from opposite physiological conditions.

An eventual decision rule should combine:

```text
control profile probability
+ vigilance score
+ departure from personal baseline
+ recent sleep/stress/context
+ optional RR/HRV
+ uncertainty and data-quality checks
```

## Claim Boundary

The strongest defensible conclusion is that this public dataset contains four
repeatable statistical profiles of task-active control and a partially separate
engagement-vigilance dimension. The profiles show mixed trait-state structure
and shortened paired conflict tasks recover them moderately well internally.
They are not validated zones, diagnoses, brain states, or proven treatment
selectors.
