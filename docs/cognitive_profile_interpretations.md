# Cognitive Interpretation of the Stroop Profiles

> This is the ACDC Stroop interpretation and integrated protocol-development
> note. The publication-facing analysis of the independent paired Stroop,
> Flanker, and SART dataset is maintained separately in
> `studies/paired-control-vigilance/`.

## Purpose

This document provides a provisional cognitive-science interpretation of the
three neutral profiles identified in the focused ACDC Stroop analysis.

These interpretations are descriptive hypotheses. They do not establish
discrete cognitive or brain states, and the neutral cluster identifiers should
remain the primary labels in analysis outputs.

## Evidence Summary

The constrained Stroop analysis compared two-, three-, and four-component
Gaussian mixture models using 929 primary windows from 80 dataset-scoped
participants across four datasets.

The strongest valid solution contained three components:

- It had the lowest BIC among solutions passing the component-size rules.
- It showed moderate separation and good participant-bootstrap stability.
- All three components included observations from all four Stroop datasets.
- It outperformed the continuous Factor Analysis baseline on
  participant-grouped held-out density.
- The four-component solution failed the registered component-size criterion
  and reproduced acceptable component sizes in only 55% of held-out splits.

The evidence therefore supports three overlapping behavioural profiles more
strongly than four zones. It does not prove that the profiles are categorical
rather than useful approximations to a continuous distribution.

## Three Provisional Profiles

| Neutral profile | Provisional interpretation | Main observed characteristics |
|---|---|---|
| `Stroop-GMM3-full-C2` | Efficient regulated control | Highest accuracy and throughput, low RT variability, and almost no error burstiness |
| `Stroop-GMM3-full-C1` | Inefficient overloaded control | Slowest responses, lowest accuracy and throughput, elevated variability, and relatively large updates |
| `Stroop-GMM3-full-C3` | Fast brittle control | Fast responses, moderate accuracy, high error burstiness, and elevated serial persistence |

### Efficient Regulated Control

This profile combines high performance with stable response regulation:

- Accuracy: approximately `0.968`
- Throughput proxy: approximately `1.430`
- Median RT: approximately `717 ms`
- RT coefficient of variation: approximately `0.200`
- Error burstiness: approximately `0.047`

A plausible interpretation is effective conflict-control regulation. Responses
are relatively fast and accurate without marked volatility or clustered
failure.

This profile is broadly **In-Zone-like**, but it should not be renamed as a
validated In Zone. Mutual-information and post-error estimates are unavailable
for many of these windows, and its Stroop interference cost is not especially
low.

### Inefficient Overloaded Control

This profile shows slow, variable, and comparatively ineffective performance:

- Accuracy: approximately `0.794`
- Throughput proxy: approximately `1.045`
- Median RT: approximately `838 ms`
- RT coefficient of variation: approximately `0.289`
- Error burstiness: approximately `1.422`

The pattern may represent overloaded or inefficient control. Participants
appear to remain engaged with task-relevant information, but control is slow,
variable, and less successful.

This is not a clean **Flat-like** profile. Non-response is uncommon, update
magnitude is not suppressed, and task-relevant mutual information is present
where measurable. The profile may therefore reflect cognitive overload,
fatigue, uncertainty, or inefficient compensatory effort rather than simple
disengagement.

### Fast Brittle Control

This profile combines relatively fast responding with clustered failures:

- Accuracy: approximately `0.916`
- Throughput proxy: approximately `1.384`
- Median RT: approximately `681 ms`
- RT coefficient of variation: approximately `0.253`
- Error burstiness: approximately `5.063`
- Lag-1 persistence: approximately `0.184`

A plausible interpretation is a brittle response policy: performance can be
fast and effective for periods, but errors occur in pronounced bursts and
behaviour shows increased serial persistence.

This profile combines features of two proposed zones:

- **Spun-Out-like:** volatility and clustered errors.
- **Locked-In-like:** persistence and possible exaggerated post-error
  adjustment.

It does not cleanly satisfy either prototype. Post-error slowing is available
for only a minority of its windows, so rigidity cannot be established from
that feature.

## Two-Dimensional Interpretation

The three profiles can be understood using two broad cognitive dimensions:

1. **Control efficacy:** successful and efficient versus ineffective and
   error-prone control.
2. **Response policy:** cautious/slow versus fast/persistent responding.

This yields the following working model:

```text
Effective + balanced       -> efficient regulated control
Ineffective + slow/noisy   -> inefficient overloaded control
Ineffective + fast/brittle -> fast brittle control
```

This dimensional account may be more defensible than treating each component
as a completely separate natural state.

## Between-Person and Within-Person Variation

The repeated-window analysis indicates a **mixed trait-state structure**.
Profiles are neither completely fixed characteristics of a person nor purely
momentary states.

Across the 80 participants:

- The median participant spent 75% of their windows in their modal profile.
- Within-participant profile agreement was `0.718`, compared with `0.564`
  under a dataset-preserving permutation.
- Adjacent windows retained the same profile `76.6%` of the time, compared
  with a marginal chance expectation of `51.4%`.
- Nevertheless, `88.8%` of participants showed more than one profile.

This means that stable individual differences matter, but most people can also
move between profiles.

### Characteristics That Differ Strongly Between Individuals

After adjustment within each source dataset, the following features showed
high between-person consistency:

| Feature | ICC(1) | Interpretation |
|---|---:|---|
| RT coefficient of variation | `0.868` | Strongly person-like |
| RT volatility | `0.840` | Strongly person-like |
| Median RT | `0.823` | Strongly person-like |
| Throughput proxy | `0.725` | Substantially person-like |
| Accuracy | `0.564` | Moderately to strongly person-like |

These results suggest that baseline processing speed, speed consistency,
response variability, and general performance efficiency differ substantially
between people.

Plausible contributors include:

- General processing speed.
- Fluid intelligence and reasoning efficiency.
- Working-memory capacity.
- Executive-control capacity.
- Stable speed-accuracy preferences.
- Trait attentional stability.
- Age, education, language, motor speed, and task familiarity.
- Neurodevelopmental or clinical differences.

The present ACDC analysis did not directly measure fluid intelligence,
working-memory capacity, sleep, chronotype, or clinical status. It therefore
cannot determine which of these factors caused the observed individual
differences. Associations with fluid intelligence or executive control would
need to be tested using independent measures collected from the same
participants.

### Characteristics That Vary More Within an Individual

The following features had low ICCs and therefore varied predominantly between
windows within the same person:

| Feature group | Approximate ICC range | Interpretation |
|---|---:|---|
| Stroop interference costs | `0.231-0.250` | Mostly within-person or mixed |
| Lag persistence and roughness | `0.100-0.103` | Mostly within-person |
| Difference and permutation entropy | `0.018-0.077` | Mostly within-person |
| Error burstiness | `0.021` | Mostly within-person |
| Temporal drift | `0.009` | Mostly within-person |
| Sign-change rate | `0.008` | Mostly within-person |

These dynamic features are plausible candidates for sensitivity to temporary
conditions such as:

- Time of day and circadian phase.
- Sleep duration, sleep quality, and sleep debt.
- Acute fatigue or sustained mental effort.
- Stress, anxiety, mood, or motivational changes.
- Caffeine, medication, alcohol, or other substances.
- Hunger, illness, pain, or physical exertion.
- Interruptions, noise, device differences, and testing environment.
- Practice, learning, boredom, and task disengagement.
- Recent success, conflict, and error history within the task.

ACDC generally does not provide controlled measurements of these conditions.
The low ICC values show within-person fluctuation, but they do not identify its
cause. A dedicated repeated-measures study would need to record sleep, time of
day, chronotype, stress, caffeine, medication, context, and subjective state
alongside each Stroop session.

### Profile-Specific Stability

The three profiles also differed in short-term persistence:

- **Efficient regulated control** was the most persistent profile, remaining
  the same across `85.6%` of its adjacent-window transitions.
- **Inefficient overloaded control** persisted across approximately `69.0%` of
  adjacent transitions.
- **Fast brittle control** persisted across only approximately `23.9%` of
  adjacent transitions and most often moved to efficient regulated control in
  the next window.

This suggests that efficient regulation may reflect a combination of stable
capacity and current state. The brittle profile appears more transient, while
the overloaded profile lies between them. These transitions are observational
and do not prove recovery, fatigue, or causal movement between psychological
states.

### Implications for an App

An app should separate two kinds of output:

1. **Personal baseline:** estimated only after several sessions and intended
   to capture stable differences in speed, consistency, and typical
   performance.
2. **Current-session deviation:** the extent to which the current session
   differs from that person's baseline in conflict cost, entropy, persistence,
   burstiness, and drift.

A single session should not interpret a naturally slow but consistent person
as overloaded merely because their RT is slower than the population average.
Repeated personal calibration would allow the app to distinguish:

```text
between-person difference:
"This person is usually slower but stable."

within-person change:
"This session is slower, more variable, or more error-bursty than usual."
```

The second comparison is more relevant to possible effects of sleep, fatigue,
stress, time of day, or environmental conditions.

## Proposed Three-Minute Longitudinal Protocol

The current data support the **plausibility** of a short longitudinal
assessment, but not yet a validated diagnostic protocol.

The trial-count recovery analysis provides the following empirical starting
point:

| Trials | Balanced accuracy | Confident coverage | Accuracy when confident |
|---:|---:|---:|---:|
| 40 | `0.651` | `68.6%` | `81.8%` |
| 50 | `0.685` | `79.0%` | `84.1%` |
| 60 | `0.751` | `84.9%` | `86.7%` |
| 80 | `0.837` | `94.8%` | `90.6%` |

These values measure recovery of the exploratory 80-trial ACDC profile, not
accuracy against an independently validated psychological state.

Sixty trials were the first shortened condition to exceed the provisional
`0.70` balanced-accuracy threshold. Eighty trials performed materially better,
especially for the fast brittle profile:

| Trials | Overloaded recall | Regulated recall | Brittle recall |
|---:|---:|---:|---:|
| 60 | `0.734` | `0.876` | `0.643` |
| 80 | `0.745` | `0.936` | `0.830` |

The initial protocol should therefore target **80 trials**, with **60 trials
as the minimum for a lower-confidence result**.

### Test Structure

Recommended research prototype:

1. Complete 12-20 practice trials that are not scored.
2. Run a fixed three-minute assessment.
3. Target 80 scored trials with a response-contingent pace.
4. Balance congruent and incongruent trials and response alternatives.
5. Use the same stimulus proportions, timing, response mapping, display rules,
   and feedback policy across every session.
6. Record millisecond stimulus onset, response, timeout, browser/device, and
   interruptions.
7. Preserve all trials with explicit quality flags.

A practical interpretation rule would be:

| Completed evidence | Output |
|---|---|
| At least 80 trials and acceptable quality | Standard profile probabilities |
| 60-79 trials and acceptable quality | Lower-confidence profile probabilities |
| Fewer than 60 trials | Insufficient evidence; do not classify |

Eighty trials in three minutes requires an average complete trial cycle of no
more than `2.25 seconds`; 60 trials permits `3.0 seconds` per cycle. A
response-contingent design with a fixed maximum response window should
therefore be piloted on representative phones and computers before fixing the
trial target.

Provisional quality gates should include:

- At least 60 analyzable trials.
- At least 20 observations from each conflict condition.
- No more than 20% missing, timed-out, or technically invalid responses.
- Successful practice and comprehension checks.
- No detected loss of browser focus or major interruption.
- Stable frame and input timing on the device.

The assessment should not force a result when the maximum profile probability
is low. The current analysis used `0.60` as an exploratory confidence
threshold. That threshold requires calibration in app-specific data.

### Combined Stroop-PVT Protocol

The paired SART follow-up supports adding a separate vigilance probe rather
than asking Stroop to identify under-activation by itself. The recommended
research app protocol is:

| Component | Initial duration | Purpose |
|---|---:|---|
| Context check | `20-30 seconds` | Sleep, fatigue, stress, caffeine, time of day, and interruptions |
| Stroop | `3 minutes` | Regulated, overloaded, and brittle task-active control probabilities |
| Brief PVT | `3 minutes` | Vigilance lapses, response-speed stability, and low-readiness evidence |
| Total | Approximately `7 minutes` | Combined control and readiness profile |

The three-minute PVT-B is the most practical initial deployment candidate. It
has shown sensitivity to total and partial sleep deprivation, although it is
less sensitive than the standard ten-minute PVT and has not always shown close
convergent agreement with it.

The validation study should therefore include:

```text
deployable protocol:
3-minute Stroop + 3-minute PVT-B

validation protocol:
3-minute Stroop + 5-minute PVT

benchmark subsample:
standard 10-minute PVT
```

The five-minute PVT provides a useful sensitivity and reliability margin while
the deployable three-minute version is calibrated. The benchmark subsample
should determine which readiness effects are lost when reducing the PVT to
three minutes.

The PVT should use randomized interstimulus intervals. The validated PVT-B
design used intervals of approximately `1-4 seconds`, but its lapse threshold
should not be copied blindly. Browser, touchscreen, keyboard, operating-system,
display, and input latency can shift reaction-time distributions. Thresholds
must be calibrated for the app implementation and device class.

Primary PVT features should include:

```text
mean reciprocal RT or response speed
slowest 10% response speed
lapse rate
false-start rate
RT coefficient of variation
within-test RT drift
```

Lapse count alone is unstable when few stimuli occur. The classifier should
therefore combine response speed, slow-tail behaviour, lapses, false starts,
and personal-baseline deviation.

### Combined Classifier Output

The classifier should not force four mutually exclusive states. It should
return two related outputs:

```text
task-active control:
regulated / overloaded / brittle probabilities

readiness and vigilance:
preserved <-> low or unstable vigilance
```

This permits combinations such as:

```text
regulated + preserved vigilance
overloaded + preserved vigilance
overloaded + low vigilance
brittle + low vigilance
```

This architecture reflects the paired analysis: SART engagement was moderately
related to task-active efficacy between people but only weakly related to
within-person session changes. Readiness is therefore relevant to control but
is not simply a fourth Stroop profile.

The app should report under-activation only as a provisional interpretation
when low or unstable PVT vigilance converges with personal-baseline deviation,
context, and preferably physiological or subjective evidence. A brief PVT
cannot by itself determine whether poor vigilance reflects sleep loss, low
arousal, low motivation, illness, medication, distraction, or device timing.

### Empirical Seven-Minute Feasibility Check

The raw paired Stroop and Flanker trials were used to test:

```text
3-minute vigilance probe
+ 2-minute Stroop
+ 2-minute Flanker
= approximately 7 minutes
```

The shortened control-task features were evaluated against the exploratory
four-component full-session partition using participant-isolated five-fold
validation:

- Matched sessions: `742`.
- Dataset-scoped participants: `458`.
- Modelled two-minute Stroop yield: median `101` trials.
- Conservative two-minute Flanker yield: `44` trials.
- Four-profile balanced accuracy: `0.744`.
- Macro F1: `0.718`.
- Coverage at prediction probability of at least `0.60`: `77.4%`.
- Accuracy among those higher-confidence predictions: `84.5%`.

Profile-specific recall was:

| Neutral full-session profile | Recall |
|---|---:|
| Slow compensatory/cautious candidate | `0.747` |
| Regulated candidate | `0.796` |
| Globally overloaded candidate | `0.673` |
| Fast brittle candidate | `0.759` |

Combined Stroop and Flanker prefixes were materially more informative than
either task alone. Eighty Stroop plus 44 Flanker trials achieved balanced
accuracy `0.743`; 100 Stroop plus 44 Flanker trials achieved `0.772`.

The main limitation is differential evidence within a fixed-duration Stroop:

| Candidate profile | Median two-minute trials | Sessions below 80 trials |
|---|---:|---:|
| Slow compensatory/cautious | `86` | `32.5%` |
| Regulated | `106` | `1.0%` |
| Globally overloaded | `81` | `49.0%` |
| Fast brittle | `104` | `0.9%` |

Slower profiles produce fewer observations in the same two-minute period. The
classifier must therefore include trial count as an evidence and quality
variable. Fewer than 60 valid Stroop trials should normally trigger
abstention, and 60-79 trials should produce a lower-confidence output.

This is an internal recovery analysis: the full-session reference profiles and
shortened features came from the same dataset. It supports a seven-minute
research prototype but does not establish independent classifier validity.
The authoritative paired-study result is in
`studies/paired-control-vigilance/outputs/reports/short_combined_task_recovery.md`.

### Core Short-Test Features

The first implementation should prioritize features that are interpretable
and reasonably estimable from 60-80 trials:

```text
accuracy
median RT
throughput
RT coefficient of variation
RT volatility
interference cost in RT and accuracy
fast-error rate
error burstiness
lag-1 persistence
```

Entropy, drift, post-error slowing, and mutual-information measures should be
treated as secondary evidence until their short-test reliability is
established. Post-error slowing may be unavailable when the session contains
too few errors.

### Personal Baseline Schedule

The current participants contributed a median of eight 80-trial windows, and
the analysis detected both stable individual differences and within-person
movement. This makes approximately eight observations a reasonable
feasibility target, but the ACDC windows were usually collected within tasks,
not as independent sessions across days.

A proposed calibration schedule is:

```text
familiarization:
1 unscored or separately modelled session

minimum baseline:
6 scored sessions across at least 4 days

preferred baseline:
8-10 scored sessions across 5-7 days

context coverage:
at least two times of day and a range of ordinary rested/fatigued conditions
```

When two sessions occur on the same day, they should be separated by several
hours. The app should record sleep, fatigue, stress, caffeine, medication,
time of day, task context, and subjective readiness.

Six to ten sessions are a study-design recommendation, not a threshold proven
by ACDC. The required number should be estimated prospectively from
generalizability and test-retest analyses in app users.

For the combined classifier, each baseline session should include both the
Stroop and the brief PVT. A reasonable initial schedule is:

```text
5-7 days
2 assessments on several days where feasible
at least 8-10 valid paired sessions
morning and later-day coverage
ordinary rested and fatigued conditions
```

The baseline should estimate a person's usual PVT response speed, slow-tail
rate, lapse tendency, false-start tendency, and time-of-day pattern alongside
their Stroop profile distribution. Early outputs should use population
estimates with shrinkage rather than treating a small number of sessions as a
stable personal norm.

### Baseline Model

The personal model should estimate:

1. The person's usual median and variability for speed, accuracy, throughput,
   and RT consistency.
2. Their usual probability distribution across the three profiles.
3. The normal within-person range of interference cost, persistence, entropy,
   burstiness, and drift.
4. Practice effects across the first sessions.
5. Context effects such as device and time of day.

With only a few sessions, the app should not fit a separate personal mixture
model. It should use a hierarchical approach:

```text
early sessions:
population model with uncertainty

after repeated sessions:
population model + shrinkage toward the personal baseline

current result:
profile probabilities + deviation from personal baseline
```

This prevents an unstable baseline from being estimated from three or four
observations.

### Suggested Session Output

The output should contain three layers:

```text
1. Current profile probabilities
   regulated / overloaded / brittle

2. Personal deviation
   faster, slower, more variable, or more error-bursty than usual

3. Confidence and quality
   standard / lower confidence / insufficient evidence
```

For example:

> Current profile: 62% overloaded, 27% regulated, 11% brittle. Your responses
> were slower and more variable than your personal baseline. Confidence is
> moderate because 66 usable trials were available.

This wording is preferable to a definitive state label.

### Profile-Informed Support Options

The assessment could eventually support two distinct forms of personalized
decision support:

1. **Baseline support:** repeated assessments identify a person's usual bias
   toward regulated, overloaded, or brittle performance.
2. **Immediate support:** the current deviation from that baseline helps
   select an optional action before the next work block.

The system should identify potentially useful supports rather than diagnose a
deficit or state that someone needs treatment. A baseline tendency away from
regulated control is not necessarily a disorder. It may reflect ordinary
differences in processing speed, strategy, task familiarity, fatigue, or
speed-accuracy preference.

Provisional routing hypotheses include:

| Current pattern and context | Experimental support option |
|---|---|
| Regulated and near personal baseline | Proceed without an intervention |
| Overloaded with high stress or arousal | Slow-paced breathing, quiet recovery, then reduce or clarify task scope |
| Overloaded with fatigue or low activation | Brief movement, hydration, daylight, rest, or reduced workload rather than additional down-regulation |
| Fast brittle | Accuracy-first prompt, deliberate pacing, checklist, smaller sub-blocks, and explicit review points |
| Mixed or uncertain | No profile-specific intervention; use self-report and task context |

The same profile may require different support depending on context. Slow,
variable performance caused by acute stress may respond differently from slow
performance caused by sleep loss or low alertness.

### Breathing as a Candidate Intervention

Slow-paced breathing is a plausible candidate primarily for reducing acute
arousal or stress. Systematic reviews report autonomic and psychological
effects from controlled slow breathing, including changes associated with
parasympathetic regulation and reductions in stress or anxiety.

The evidence does **not** currently show that a breathing exercise moves a
person from an overloaded or brittle Stroop profile into the regulated
profile. That transition must be tested directly.

For a research prototype:

- Use a simple, comfortable slow-paced breathing exercise.
- Avoid fast-only breathing, prolonged breath holding, or technically complex
  practices.
- Allow the participant to stop if uncomfortable or light-headed.
- Treat approximately five minutes as a more evidence-aligned starting
  duration than a very brief exercise under five minutes.
- Do not recommend down-regulating breathing when low alertness or fatigue is
  the more plausible problem.

The breathing intervention should be optional and presented as an experiment,
not a treatment.

### Other Candidate Supports

Different profile-context combinations may require different actions:

```text
high arousal / overloaded:
slow breathing, quiet pause, simplify the next task

low activation / overloaded:
movement, daylight, hydration, rest, reduce workload

fast brittle:
slow-down cue, accuracy emphasis, checklist, review checkpoint

uncertain:
no automated intervention
```

Brief mindfulness or breath-awareness practice may also be useful, but much of
the evidence for attentional-control improvement concerns repeated training
rather than a single immediate exercise. It should not be assumed to produce
an acute profile shift without testing.

### Learning an Individual Intervention Response

The long-term objective should not be a fixed mapping from profile to
intervention. The app should learn whether a particular action improves a
particular person's subsequent work under a particular context:

```text
P(improved work outcome
  | current profile,
    personal-baseline deviation,
    intervention,
    context,
    person)
```

For example, slow breathing may help one person when overloaded under stress,
but may be neutral or counterproductive when that person is already sleepy or
underactivated.

The intervention policy should therefore begin conservatively:

```text
population evidence
+ personal response history
+ current context
+ uncertainty
```

### Intervention Validation Design

A suitable prospective study is a personalized randomized crossover:

```text
three-minute Stroop
-> profile probabilities and baseline deviation
-> randomized intervention or control
-> approximately 40-minute work block
-> objective and subjective outcomes
```

Candidate randomized conditions could include:

- Five-minute slow-paced breathing.
- Five-minute quiet rest with neutral instructions.
- Brief movement or activation.
- Accuracy-first planning and checklist.
- No-intervention control.

Randomization should be stratified by current profile and context where
possible. Each participant should experience each appropriate intervention
multiple times.

Primary outcomes should concern the subsequent work block:

- Task completion.
- Objective quality and error rate.
- Sustained engagement and interruptions.
- Time on task.
- Subjective effort, stress, fatigue, and confidence.

A secondary Stroop assessment may measure short-term profile change, but it
should not be the primary intervention outcome. Immediate retesting is
vulnerable to practice effects, regression to the mean, and simple
familiarization.

The decisive test is whether profile-informed intervention selection improves
the next work block compared with generic intervention, self-selection, or no
intervention.

### Intervention Safety and Claim Boundary

- Supports should be optional, low risk, and easy to discontinue.
- Do not describe profile outputs as diagnoses.
- Do not infer that someone requires clinical treatment.
- Do not use the system to restrict access to work, education, or other
  consequential opportunities.
- Avoid fast breathing or breath-holding protocols.
- Provide appropriate cautions for people with respiratory, cardiovascular,
  panic-related, or other relevant health concerns.
- Escalate persistent impairment or distress to suitable professional support
  rather than relying on the app.

The correct initial claim is:

> A current behavioural profile and deviation from personal baseline may help
> select an optional support strategy to test before the next work block.

The incorrect claim is:

> The test diagnoses a cognitive state and identifies the intervention that
> will correct it.

### Proposed Feasibility Study

A practical next study could use:

```text
participants:
at least 60-100

baseline:
8-10 three-minute sessions over 5-7 days

validation:
additional sessions held out from baseline estimation

contexts:
morning/evening, rested/tired, and different ordinary work conditions
```

Primary analyses should test:

- Recovery of the 80-trial profile from 60-trial and fixed-duration tests.
- Agreement and sensitivity of three-minute, five-minute, and benchmark
  ten-minute PVT conditions.
- Incremental prediction from the PVT beyond Stroop, context, and self-report.
- Test-retest reliability of baseline features.
- Generalizability across days, devices, and time of day.
- Incremental value of personal baselines over population norms.
- Calibration of profile probabilities and abstention thresholds.
- Prediction of independently measured subsequent work-block outcomes.

The decisive comparison is:

```text
population features only
versus
population features + personal baseline
versus
population features + baseline + current context
```

### Current Conclusion

The data make the following protocol plausible:

```text
three-minute Stroop
+ target of 80 trials
+ minimum of 60 trials
+ three-minute deployable PVT
+ five-minute PVT during initial validation
+ 8-10 baseline sessions over approximately one week
+ two-axis probabilistic output
+ comparison with personal baseline
```

The data do not yet establish that three minutes is sufficient on every
device for either task, that eight sessions produce a stable baseline across
days, or that the result improves routing for a subsequent work block. Those
are the central questions for the prospective feasibility study.

### Intervention References

- Zaccaro, A. et al. (2018). [How breath-control can change your
  life](https://doi.org/10.3389/fnhum.2018.00353).
- Bentley, T. G. K. et al. (2023). [Breathing practices for stress and anxiety
  reduction](https://pubmed.ncbi.nlm.nih.gov/38137060/).
- Moore, A. et al. (2012). [Regular, brief mindfulness meditation practice
  improves electrophysiological markers of attentional
  control](https://doi.org/10.3389/fnhum.2012.00018).
- Basner, M., Mollicone, D., and Dinges, D. F. (2011). [Validity and
  sensitivity of a brief psychomotor vigilance test to total and partial sleep
  deprivation](https://doi.org/10.1016/j.actaastro.2011.07.015).
- Grant, D. A. et al. (2017). [Three-minute smartphone-based and tablet-based
  psychomotor vigilance tests for reduced alertness due to sleep
  deprivation](https://doi.org/10.3758/s13428-016-0763-8).
- Antler, C. A. et al. (2022). [The three-minute PVT demonstrates inadequate
  convergent validity relative to the ten-minute PVT across sleep loss and
  recovery](https://doi.org/10.3389/fnins.2022.815697).

## Profile-Informed Routing for a Work Block

The mixed trait-state result provides a plausible basis for testing whether a
short Stroop assessment can support routing recommendations for a subsequent
work block, such as a focused period of approximately 40 minutes.

The diagnostic should combine:

```text
current profile probabilities
+ deviation from the person's baseline
+ classification confidence
+ current context and intended task
```

This is preferable to routing from the hard profile label alone. The same
observed performance can have different implications for different people. A
naturally slower but consistent person should not be treated as overloaded
unless the current session is also slower, more variable, or more error-prone
than their established baseline.

### Provisional Routing Hypotheses

| Current pattern | Possible routing for the next work block |
|---|---|
| Efficient regulated control | Proceed with complex, focused, or high-priority work |
| Inefficient overloaded control | Reduce complexity, clarify priorities, narrow the task, or take a short recovery period first |
| Fast brittle control | Use a deliberate pace, explicit quality checks, shorter sub-blocks, or structured review points |
| Mixed or uncertain result | Use a neutral plan, gather more trials, or rely on self-report and task context |

These are hypotheses for experimental evaluation, not validated prescriptions.
The Stroop profiles may indicate differences in cognitive-control performance,
but the current ACDC data do not contain subsequent 40-minute work outcomes.
They therefore cannot show that a particular routing recommendation improves
productivity, quality, learning, or wellbeing.

### Example App Output

A claim-safe output could state:

> Your current performance is more variable and error-bursty than your usual
> baseline. For the next work block, a more structured task with an explicit
> review checkpoint may be worth considering.

The app should avoid statements such as:

> You are in a validated cognitive zone and should not perform complex work.

Recommendations should remain optional and should communicate classification
uncertainty.

### Required Prospective Validation

Profile-informed routing should be tested in a repeated, prospective study:

1. Establish each participant's baseline across several sessions.
2. Administer the short Stroop immediately before a work block.
3. Record sleep, fatigue, stress, time of day, caffeine, environment, task
   type, and subjective readiness.
4. Randomly assign participants to a profile-informed strategy or a suitable
   control strategy.
5. Measure the following work block using objective and subjective outcomes:
   completion, quality, errors, persistence, effort, distraction, and
   wellbeing.
6. Test whether routing improves outcomes beyond personal baseline, context,
   and self-report alone.
7. Evaluate whether effects generalize across people, task types, days, and
   devices.

The most informative comparison is not simply whether profiles predict work
performance. It is whether a profile-informed recommendation improves the
next work block compared with a generic recommendation or no recommendation.

### Decision-Support Boundary

Until prospective routing evidence exists, the assessment should be described
as experimental decision support:

```text
observed profile
= stable personal baseline
+ current cognitive condition
+ immediate task context
+ measurement uncertainty
```

The mixed model makes adaptive routing scientifically testable. It does not yet
establish that any specific recommendation will improve a 40-minute work
block.

## Paired Vigilance Follow-Up

An independent paired dataset from Barzykowski et al. (2022) provides a useful
test of whether engagement/vigilance is separable from task-active conflict
control. The dataset contains Stroop, Flanker, and SART results from the same
participants:

- `466` participants.
- `768` paired task sessions.
- `210` participants with at least two sessions.

Two transparent SART dimensions were constructed:

1. **Engagement-vigilance:** fewer Go omissions and lower Go RT variability.
2. **Inhibitory stability:** fewer NoGo commissions and fewer anticipatory
   responses.

These are behavioural indices. Low engagement-vigilance does not by itself
establish low arousal, sleepiness, low motivation, or disengagement.

### Engagement Is Related but Not Redundant

SART engagement-vigilance was moderately associated with Stroop/Flanker
task-active efficacy across participant means (`r = 0.437`), but only weakly
associated with session-to-session changes within a participant
(`r = 0.156`).

The corresponding associations for SART inhibitory stability were:

- Between participants: `r = 0.265`.
- Within participants: `r = 0.128`.

Participant-isolated prediction showed the same pattern:

- SART engagement alone predicted `12.6%` of held-out task-active efficacy
  variance.
- The two SART dimensions classified neutral task-active profiles with
  balanced accuracy `0.407`, compared with four-class chance of `0.250`.

This is enough overlap to show that vigilance matters for control performance,
but not enough to treat SART as a duplicate Stroop classifier. The safer
interpretation is:

```text
readiness/vigilance and task-active control are related layers
that share some variance but retain substantial independent information
```

### Mixed Trait-State Structure

Repeat-session ICC estimates were:

| Dimension | ICC(1) | Interpretation |
|---|---:|---|
| Control speed | `0.718` | Strongly person-like |
| SART inhibitory stability | `0.473` | Mixed person and session variation |
| Task-active efficacy | `0.396` | Mixed person and session variation |
| SART engagement-vigilance | `0.361` | Mixed person and session variation |
| Control accuracy | `0.343` | Mixed person and session variation |
| Conflict resilience | `0.292` | Mixed person and session variation |

This supports the existing longitudinal model. People differ in their typical
vigilance and control, while the same person also changes across sessions.
The data do not identify whether within-person change was caused by sleep,
time of day, stress, fatigue, practice, motivation, or testing context.

### Task-Active Profile Result

A neutral mixture analysis of context-adjusted Stroop and Flanker accuracy,
speed, and conflict resilience selected a four-component solution:

- Four-component full-covariance BIC: `5130.7`.
- Three-component full-covariance BIC: `5152.7`.
- Four-component participant-bootstrap ARI: `0.724`.
- Three-component participant-bootstrap ARI: `0.298`.

The four components descriptively resembled:

```text
relatively regulated control
slow/cautious mixed control
severely inefficient overloaded control
fast but inaccurate mixed/brittle control
```

This does not validate the original four zones. The paired analysis used
session aggregates, different tasks, and different features from the ACDC
window analysis. The extra component primarily separates slow/cautious
performance from more globally impaired performance; it is not independently
identified as Flat, Locked In, or under-activated.

### The Overloaded Profile Contains Engagement Subtypes

The most impaired task-active profile contained `51` sessions. Its SART
engagement distribution favoured two descriptive subgroups over one by
`8.0` BIC points:

| Descriptive subgroup | Sessions | Mean omission rate | Mean Go RT CV | Mean commission rate |
|---|---:|---:|---:|---:|
| Relatively engaged but overloaded | `20` | `1.55%` | `0.282` | `54.0%` |
| Low-engagement/lapse-prone overloaded | `31` | `13.26%` | `0.448` | `67.1%` |

This is the clearest evidence for the proposed distinction:

```text
poor conflict-task performance can occur with relatively preserved vigilance
or with marked vigilance instability
```

The second subgroup is compatible with under-engagement or poor readiness, but
the data cannot determine its cause. The two-subgroup result may also
approximate a continuous tail rather than two natural states.

### Revised Assessment Architecture

The evidence supports a layered assessment:

```text
Layer 1: readiness and vigilance
SART or a short PVT-like task + subjective/context measures

Layer 2: task-active control
Stroop or Flanker accuracy, speed policy, and conflict resilience

Layer 3: personal baseline
repeat-session estimates of typical performance and current deviation
```

For an app, a PVT-like task would be preferable when the main target is
arousal vigilance or sleep-loss sensitivity. SART includes executive
vigilance and response inhibition, so it does not provide a pure measure of
under-activation.

The full analysis is reported in
`reports/paired_vigilance_followup.md`.

## Relation to the Proposed Four Zones

The focused ACDC Stroop analysis does not currently support four distinct
zones.

| Proposed zone | Current support |
|---|---|
| In Zone | Partial support through the efficient regulated profile |
| Flat | No clean independent profile |
| Locked In | Some characteristics appear within the fast brittle profile |
| Spun Out | Strong instability characteristics appear within the fast brittle and overloaded profiles |

The key distinction recovered by Stroop is:

```text
stable effective control
versus
slow overloaded dysregulation
versus
fast brittle dysregulation
```

The results do not independently separate slow disengagement from
over-controlled slowing, or unstable variability from rigid persistence, well
enough to establish four profiles.

## Cognitive-Science Interpretation

The profiles may reflect different solutions to conflict-monitoring and
speed-accuracy regulation:

- **Efficient regulation** maintains task goals while balancing response speed
  and accuracy.
- **Overloaded regulation** may recruit effort without achieving efficient
  control, producing slow and noisy performance.
- **Brittle regulation** may favour a fast or persistent response policy that
  performs well until control fails in bursts.

Possible mechanisms include proactive versus reactive control, response
threshold differences, fatigue, attentional engagement, conflict sensitivity,
and individual differences in speed-accuracy policy. ACDC cannot determine
which mechanism is causal.

## Fan's Information-Theory Account

Fan's information-theory account of cognitive control is a useful framework
for interpreting these results. It treats cognitive control as the flexible
allocation of limited mental resources under uncertainty. In this account,
conflict tasks such as Stroop are special cases of uncertainty over competing
responses, actions, or policies.

This is a strong conceptual match for the three-profile taxonomy because the
profiles can be viewed as different behavioural patterns of response selection
under conflict:

| Stroop profile | Qualified information-processing interpretation |
|---|---|
| Efficient regulated control | Reliable and stable response selection under task uncertainty |
| Inefficient overloaded control | Slow, noisy, and unreliable control that is consistent with, but does not prove, demand exceeding effective capacity |
| Fast brittle control | Rapid response selection with unstable reliability and clustered failure |

The framework supports interpreting the profiles as patterns of control under
uncertainty rather than as fixed brain states.

### Efficient Regulated Control

The efficient regulated profile is consistent with reliable
information-through-control:

```text
task uncertainty is handled effectively
+ response selection remains stable
+ behavioural output remains reliable
```

Its high accuracy and throughput, low variability, and minimal error
burstiness indicate that the demands of the Stroop task remain within the
person's effective control regime.

This interpretation is stronger than describing the profile only as good
performance, but it remains behavioural. The data do not identify a neural
channel or directly measure information-transfer capacity.

### Inefficient Overloaded Control

The overloaded profile is compatible with limited-capacity control:

```text
slow responses
+ reduced accuracy and throughput
+ elevated variability
+ continued task engagement
```

This can be interpreted as control operating inefficiently under conflict,
possibly because task demand approaches or exceeds the person's currently
effective capacity. The evidence of continued task-relevant processing makes
simple disengagement an incomplete explanation.

However, the ACDC Stroop data do not manipulate information rate or estimate a
capacity threshold. The profile could also reflect fatigue, cautious response
thresholds, weak stimulus-response mapping, lower baseline ability, or other
forms of inefficient control. **Capacity exceeded** should therefore be
treated as a hypothesis for subsequent testing, not as an observed result.

### Fast Brittle Control

The fast brittle profile is consistent with a speed-prioritized response
policy whose reliability is unstable:

```text
rapid responding
+ reasonable average throughput
+ serial persistence
+ clustered errors
```

An information-processing interpretation is that the response policy performs
quickly under ordinary demand but becomes unreliable during local periods of
uncertainty or instability.

This profile should not yet be described as failed channel switching. The
current Stroop analysis did not manipulate channels or task switching, and
serial persistence does not establish a switching deficit. A safer term is
**brittle information-routing policy** or **rapid but unstable response
selection**.

### Three Different Meanings of Entropy

Three distinct quantities must not be conflated:

1. **Task or response uncertainty:** Fan's Shannon-information account of the
   uncertainty produced by competing response alternatives.
2. **Behavioural time-series entropy:** permutation and difference entropy
   computed from the residualized trial sequence in this project.
3. **Task-relevant mutual information:** measured statistical dependence
   between selected task variables and behavioural outcomes.

The second and third quantities may help characterize behaviour under
uncertainty, but neither is a direct estimate of Fan's cognitive-control
capacity or an information-transmission rate in bits per second.

### What MFT-M Could Add

The Majority Function Task-Masked (MFT-M) provides a more direct test of the
capacity interpretation. It varies:

- The entropy of the information that must be coordinated.
- Stimulus exposure time.
- The resulting required information rate.

Unlike the flanker task, all arrows in the majority set can contribute to the
correct decision. The task can therefore estimate how accuracy changes as
information-processing demand approaches a modelled upper limit.

Fan and colleagues reported an MFT-M estimate of cognitive-control capacity of
approximately `3-4 bits/second`. This is a task- and model-dependent estimate,
not a universal constant that can be assigned to the current Stroop windows.
The later MFT-M study also distinguished cognitive-control capacity from the
processing efficiency measured by conflict tasks and found that cognitive
control was associated with working memory and fluid intelligence.

The combined design would treat the tasks as complementary:

```text
Stroop
= behavioural response-regulation profile under interference

MFT-M
= capacity and information-rate tolerance under parametrically varied demand
```

### Testable Cross-Task Predictions

| Stroop profile | MFT-M prediction if the interpretation is correct |
|---|---|
| Efficient regulated control | Higher or more resilient capacity estimate, with stable performance as entropy and time pressure increase |
| Inefficient overloaded control | Lower capacity estimate or earlier, gradual performance decline as required information rate increases |
| Fast brittle control | Adequate performance at lower demand but a sharper or more variable collapse near high entropy or short exposure |

These predictions could help distinguish:

```text
overloaded control
= capacity or efficiency limitation

fast brittle control
= unstable response policy or reliability boundary
```

The predictions require a study in which the same participants complete both
tasks. They cannot be tested by joining unrelated ACDC and MFT-M samples.

### Role in a Future Classifier

MFT-M should initially be added as a continuous capacity or stress-test layer,
not used to force another category:

```text
Stroop output:
probabilities for regulated, overloaded, and brittle control

MFT-M output:
estimated capacity and performance decline under increasing information rate
```

A combined model could then ask both how the person is regulating responses
now and how much parametrically defined information demand they can reliably
coordinate. This may be more informative than either task alone.

The published MFT-M implementation involved hundreds of trials and
approximately 40 minutes. A short app version would require a separately
validated adaptive design; the published capacity estimate cannot simply be
reproduced by adding a few majority-function trials to a three-minute test.

### Overall Evaluation

Fan's theory provides a coherent interpretation of the three profiles:

```text
regulated = reliable control under uncertainty
overloaded = slow and unreliable control consistent with capacity pressure
brittle = rapid control operating near an unstable reliability boundary
```

The fit is theoretically useful but currently indirect. The ACDC results
support behavioural differences in regulation, efficiency, persistence, and
failure dynamics. They do not directly demonstrate channel capacity,
information-rate overload, neural information transmission, or channel
switching.

### References

- Fan, J. (2014). [An information theory account of cognitive
  control](https://doi.org/10.3389/fnhum.2014.00680).
- Wu, T. et al. (2016). [The capacity of cognitive control estimated from a
  perceptual decision making task](https://doi.org/10.1038/srep34025).
- Chen, X. et al. (2019). [Testing a cognitive control model of human
  intelligence](https://doi.org/10.1038/s41598-019-39685-2).

## Interpretation Guardrails

- Keep neutral cluster identifiers in all primary results.
- Treat the cognitive labels as provisional summaries, not diagnoses.
- Do not infer brain states from behavioural clusters.
- Do not interpret slow performance as disengagement without lapse or
  non-response evidence.
- Do not interpret post-error slowing as rigidity without adequate post-error
  trial support.
- Do not infer conflict adaptation because it was not directly estimated in
  the current pipeline.
- Recognize that one Stroop dataset produced substantially weaker
  leave-one-dataset-out replication.
- Replicate the profiles in independent data before developing a classifier or
  making confirmatory zone claims.

## Claim-Safe Conclusion

The ACDC Stroop results provide exploratory evidence for three overlapping
behavioural profiles: efficient regulated control, inefficient overloaded
control, and fast brittle control. These profiles offer a useful cognitive
interpretation of stable performance and two different forms of
dysregulation. They do not validate four discrete zones or establish discrete
brain states.
