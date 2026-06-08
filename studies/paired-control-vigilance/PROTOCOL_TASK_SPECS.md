# High-Level Task Specifications

## Purpose And Status

This document defines candidate three-task batteries suggested by the paired
Stroop-Flanker-SART study. The vigilance task can be SART or PVT-like:

```text
3-minute abbreviated SART or PVT-like vigilance probe
+ 2-minute colour-word Stroop
+ 2-minute Eriksen Flanker
= 7 minutes of scored testing
```

The Stroop and Flanker specifications are grounded in the source tasks and the
short-prefix recovery analysis. SART is the vigilance/inhibition task directly
supported by the paired study. A PVT-like task is an alternative informed by
brief Psychomotor Vigilance Test (PVT-B) research. The current dataset did not
administer a PVT, so the PVT-to-SART bridge must be tested prospectively.

This is a research protocol outline, not a production classifier, medical
device specification, diagnostic test, or validated intervention router.

## Battery-Level Specification

| Item | Candidate specification |
|---|---|
| Scored duration | Approximately 7 minutes |
| Context check | Optional 20-30 seconds before testing; sleep, fatigue, stress, caffeine, illness, medication change, interruptions |
| Operational order | Vigilance probe, Stroop, Flanker |
| Validation order | Vigilance probe first; counterbalance Stroop and Flanker order to quantify order effects |
| Output | Continuous vigilance scores, four neutral control-profile probabilities, personal-baseline deviations, uncertainty |
| Abstention | Required when timing integrity, trial evidence, completion, or model confidence is inadequate |
| Longitudinal baseline | Initially 5-10 valid sessions across several days and times |
| Intended use | Research on short-term readiness and task-active control before a work block |

The vigilance probe should normally be first because conflict tasks may
phasically increase engagement. A final deployed order should be fixed only
after the validation study quantifies order, practice, and carry-over effects.

Practice and instructions are not included in the stated scored minutes. The
first use should include onboarding practice. Repeat sessions should use a
short reminder and invoke practice only after a mapping error or long gap.

## Choosing SART Or PVT

| Option | Main advantage | Main limitation | Scored battery duration |
|---|---|---|---:|
| Full source-compatible SART | Direct continuity with the paired study and its engagement/inhibitory-stability findings | Longer than the proposed seven-minute battery | About 8 min 41 sec |
| Three-minute abbreviated SART | Preserves the study's Go/NoGo construct within seven minutes | Only about 16 NoGo trials; shortened reliability is not established here | 7 min |
| Three-minute PVT-B | Better-established three-minute alertness and sleep-loss probe with low executive demand | Not present in this dataset; does not directly measure response inhibition | 7 min |

For a study intended to replicate and extend the current findings, SART is the
preferred first choice. For an app specifically targeting behavioural
alertness, sleep-loss sensitivity, and under-activation, PVT-B may be the
cleaner eventual choice.

The strongest development study would administer both abbreviated SART and
PVT-B, preferably in counterbalanced blocks, and test:

```text
Does PVT-B add readiness information beyond SART?
Does abbreviated SART retain the full SART engagement and inhibition signals?
Which task better predicts an independent next-work-block outcome?
```

Do not split three minutes between SART and PVT. Each would then contain too
little evidence, especially for SART NoGo errors and PVT tail/lapse measures.

## Task 1A: Sustained Attention To Response Task

### Construct

Executive vigilance under repetitive responding, omission-proneness, response
timing stability, and inhibition of an infrequent prepotent response.

SART is not a pure arousal task. Its commission errors depend partly on
response strategy and speed-accuracy trade-offs, so commissions, omissions, Go
RT variability, and anticipatory responses should be interpreted together.

### Full Source-Compatible Design

| Element | Specification |
|---|---|
| Duration | 225 trials x 1250 ms = approximately 4 min 41 sec |
| Stimuli | Digits 1-9 in a fixed or reproducibly randomized balanced sequence |
| Go response | Press the single response key for every digit except `3` |
| NoGo response | Withhold response to digit `3` |
| Main trials | 225: 200 Go and 25 NoGo |
| Stimulus duration | 250 ms |
| Mask duration | 900 ms |
| Stimulus onset asynchrony | 1250 ms |
| Practice | 18 trials at onboarding |

This is the closest candidate to the task used in the paired study and is the
preferred version when replication fidelity matters more than a strict
seven-minute total.

### Three-Minute Abbreviated Design

| Element | Candidate specification |
|---|---|
| Duration | 180 seconds |
| Main trials | 144 total trials at 1250 ms SOA |
| Composition | 128 Go and 16 NoGo trials |
| Sequence | Sixteen balanced repetitions of digits 1-9, pseudorandomized with constraints |
| Stimulus and mask | Preserve the 250 ms stimulus and 900 ms mask |
| Practice | 18 trials at onboarding; brief reminder on repeat use |

The three-minute version preserves the source timing and Go/NoGo ratio, but it
is a new shortened task. Sixteen NoGo observations may be adequate for a coarse
commission rate but are weak evidence for fine-grained inhibition dynamics or
post-NoGo measures.

### Sequence Constraints

- Balance each digit exactly across the block.
- Prevent immediate repeats of the NoGo digit.
- Avoid highly predictable NoGo spacing.
- Use a fixed set of versioned sequences or save the random seed.
- Keep the Go/NoGo ratio identical across sessions and participants.
- Do not change the NoGo target within a person's longitudinal series.

### Required Raw Events

```text
session_id
participant_id
task_version
sequence_version
trial_index
digit
go_nogo
stimulus_onset
mask_onset
response_time
rt_ms
commission_error
omission_error
anticipatory_response
post_nogo_trial_type
page_visibility_state
device_and_input_metadata
```

### Candidate Features

Primary:

```text
Go omission count and rate
NoGo commission count and rate
Go mean and median RT
Go RT coefficient of variation
anticipatory response count and rate
engagement index from reversed omissions and Go RT variability
inhibitory-stability index from reversed commissions and anticipations
```

Secondary, only with sufficient trials:

```text
pre-error speeding
post-NoGo slowing
time-on-task drift
error bursts
RT distribution tails
```

The paired study directly supports the two composite dimensions. It does not
establish that the same scores remain reliable in 144 trials.

### Provisional Quality Gates

- Full block completion without backgrounding or timing failure.
- All 16 abbreviated-task NoGo trials are presented.
- NoGo commission rate is reported with its denominator and uncertainty.
- Go RT variability has enough valid Go responses after exclusions.
- A comprehension failure or near-universal responding/nonresponding triggers
  abstention rather than an extreme cognitive interpretation.
- Full and abbreviated SART must use separate task-version identifiers and
  separate reference distributions.

## Task 1B: Brief PVT-Like Vigilance Probe

### Construct

Behavioural alertness, lapse-proneness, response-speed stability, and premature
responding under low executive demand.

This task is intended to complement, not duplicate, Stroop and Flanker. Relative
to SART it reduces response-inhibition demands and more directly targets simple
behavioural alertness. It should still not be labelled a direct measure of
physiological arousal, sleepiness, motivation, or disengagement.

### Candidate Design

| Element | Specification |
|---|---|
| Duration | 180 seconds, ending after the response to the final admitted stimulus |
| Stimulus | A clearly visible visual counter or target appearing in a persistent fixation box |
| Response | One fixed keyboard key or one large touch target |
| Schedule | Random 1-4 second response-to-stimulus interval, including 1 second of RT feedback, matching PVT-B timing |
| Instruction | Respond as quickly as possible when the stimulus appears; do not anticipate |
| Feedback | Display RT for 1 second; display a false-start warning for premature responses |
| False start | Response without a stimulus or RT below 100 ms |
| Timeout | 30 seconds without response, recorded as an overrun/lapse |
| Primary short-PVT lapse threshold | Report `RT >= 355 ms` as the PVT-B-compatible sensitivity metric |
| Secondary lapse threshold | Also report conventional `RT >= 500 ms` for comparability |

The `355 ms` threshold is protocol- and device-sensitive. It must not be used
as an absolute individual classification boundary until the implementation's
timing accuracy and longitudinal reference distributions have been validated.

### Required Raw Events

```text
session_id
participant_id
task_version
device_id_or_class
trial_index
scheduled_stimulus_time
actual_stimulus_time
response_time
rt_ms
response_before_stimulus
false_start
lapse_355
lapse_500
timeout
page_visibility_state
dropped_frame_or_timing_warning
```

### Candidate Features

Primary:

```text
valid stimulus count
mean reciprocal RT
median RT
lapse count and rate at 355 ms
lapse count and rate at 500 ms
false-start count and rate
lapses plus false starts
RT coefficient of variation
slowest 10% reciprocal RT
```

Secondary:

```text
fastest 10% RT
RT interquartile range
right-tail rate
time-on-task slope
performance score
```

The short-PVT literature identifies response speed and lapse/false-start
metrics as sensitive candidates. A three-minute PVT is less informative than a
ten-minute PVT and has shown mixed convergent validity, so several metrics
should be retained rather than relying on one cutoff.

### Provisional Quality Gates

- The full 180-second block is completed without app backgrounding.
- No timing-integrity or display-refresh failure is detected.
- At least 40 valid stimuli are presented; the final minimum must be set by the
  device pilot and observed stimulus-count distribution.
- False-start and timeout patterns are inspected rather than silently removed.
- Device and input method are recorded and supported by the calibration set.

## Task 2: Colour-Word Stroop

### Construct

Task-active response selection under interference, including accuracy, speed
policy, variability, and interference cost.

### Candidate Design

| Element | Specification |
|---|---|
| Duration | 120 seconds of scored trials |
| Stimuli | Four colour words displayed in one of four font colours |
| Response | Select font colour, ignoring word meaning |
| Conditions | 50% congruent and 50% incongruent |
| Balance | Equal target-colour and response-key frequency; balanced incongruent word-colour pairings |
| Stimulus duration | Response-contingent, as in the source study |
| Inter-trial interval | 400 ms |
| Error feedback | 400 ms after an incorrect response |
| Practice | 14 trials at onboarding, balanced 7 congruent/7 incongruent |
| Scored target | At least 80 trials |
| Minimum evidence | Normally abstain below 60 scored trials |

The scored timer should stop admitting new trials at 120 seconds and allow the
current trial to finish. Any engineering safety timeout should be recorded as a
nonresponse and treated as a protocol modification requiring validation.

Response mapping must remain fixed within and across a person's sessions.
Touch targets or keys should have stable spatial positions, adequate separation,
and equivalent visual salience.

### Trial Generation

- Generate balanced mini-blocks so early termination does not strongly distort
  congruency or colour proportions.
- Randomize within each mini-block.
- Avoid long runs of one condition or response.
- Record immediate condition and response repetitions so sequence effects can
  be audited.
- Do not adapt difficulty during the scored block.

### Required Raw Events

```text
session_id
participant_id
task_version
trial_index
mini_block
word_identity
font_colour
congruency
correct_response
observed_response
accuracy
stimulus_onset
response_time
rt_ms
timeout_or_nonresponse
feedback_onset
trial_end
device_and_input_metadata
```

### Candidate Features

```text
scored trial count
overall accuracy
congruent accuracy
incongruent accuracy
accuracy interference cost
mean and median correct RT
congruent correct RT
incongruent correct RT
RT interference cost
RT coefficient of variation
throughput
fast-error rate
slow-tail rate
post-error adjustment, only with sufficient supporting trials
```

The paired study's two-minute modeled Stroop yielded a median of 101 trials.
Yield differed by profile: slow and globally overloaded sessions produced less
evidence. Trial count is therefore both a quality variable and a potential
signal, and must never be hidden by fixed-count imputation.

### Provisional Quality Gates

- At least 60 scored trials for any profile output.
- Target at least 80 trials for normal-confidence output.
- Both congruency conditions have adequate representation.
- Accuracy is above a preregistered engagement/comprehension floor.
- Key mapping, fullscreen state, timing integrity, and interruptions pass.
- Confidence is reduced when trial yield is low, even if the classifier returns
  a label.

## Task 3: Eriksen Arrow Flanker

### Construct

Task-active selective attention and response competition using a simpler
stimulus-response mapping than Stroop.

### Candidate Design

| Element | Specification |
|---|---|
| Duration | Approximately 120 seconds |
| Stimuli | Central target arrow flanked by arrows on both sides |
| Response | Left or right according to the central target only |
| Conditions | 50% congruent and 50% incongruent |
| Balance | Equal left/right target responses within each condition |
| Target display | Up to 1750 ms, matching the source-task description |
| Maximum trial duration | 2700 ms |
| Practice | 10 trials at onboarding, balanced 5 congruent/5 incongruent |
| Conservative scored target | 44 target-coded trials |

The source timing supports 44 trials as a conservative two-minute quantity
because `floor(120000 / 2700) = 44`. A response-contingent implementation may
deliver more trials, but it is a changed task and requires prospective
validation rather than inheriting the current recovery estimate.

### Trial Generation

- Use four balanced cells: left-congruent, right-congruent,
  left-incongruent, and right-incongruent.
- Randomize balanced mini-blocks to protect condition balance if the block ends
  early.
- Avoid excessive response or congruency runs.
- Do not include instruction or prefatory rows in scored trial counts.
- Do not add adaptive feedback or changing stimulus durations during scoring.

### Required Raw Events

```text
session_id
participant_id
task_version
trial_index
mini_block
target_direction
flanker_direction
congruency
correct_response
observed_response
accuracy
stimulus_onset
response_time
rt_ms
timeout_or_nonresponse
trial_end
device_and_input_metadata
```

### Candidate Features

```text
scored trial count
overall accuracy
congruent accuracy
incongruent accuracy
accuracy conflict cost
mean and median correct RT
congruent correct RT
incongruent correct RT
RT conflict cost
RT coefficient of variation
throughput
fast-error rate
slow-tail rate
```

The paired analysis found that Stroop and Flanker together recovered the
full-session exploratory partition better than either task alone. Flanker
therefore functions as a cross-task check on whether a pattern generalizes
beyond colour-word interference.

### Provisional Quality Gates

- Complete 44 target-coded scored trials under source-compatible timing.
- Both congruency and response-direction cells are represented.
- Practice, instruction, and prefatory events are excluded.
- Accuracy passes a preregistered comprehension floor.
- Timing, input, fullscreen state, and interruption checks pass.

## Combined Scoring And Output

The first prospective model should keep the layers separate:

```text
SART or PVT-like task
  -> continuous vigilance/lapse-proneness score

Stroop + Flanker
  -> probabilities for neutral task-active control profiles

Longitudinal history
  -> deviation from the person's own reference distribution
```

The app should not collapse these immediately into a single state label.
Recommended output fields are:

```text
vigilance_task_type
vigilance_percentile_population
vigilance_deviation_personal
sart_inhibitory_stability, when SART is used
regulated_probability
slow_compensatory_probability
overloaded_probability
fast_brittle_probability
classification_confidence
data_quality_status
abstention_reason
```

The neutral machine-readable profile IDs should remain available even when the
interface uses descriptive candidate names.

## Timing And Device Requirements

All tasks depend on response timing. The implementation should:

- use a monotonic high-resolution clock;
- timestamp planned onset, actual onset, and response separately;
- detect page backgrounding, focus loss, dropped frames, and long event-loop
  stalls;
- lock orientation and prevent accidental scrolling on touch devices;
- store browser/app version, operating system, screen refresh rate, and input
  method;
- validate each supported hardware/software class against an external timing
  measurement or a calibrated reference implementation;
- avoid pooling keyboard, mouse, and touchscreen RTs without adjustment;
- version every change to timing, stimuli, feedback, or scoring.

For PVT research-grade inference, published work suggests that timing bias and
variability must be tightly controlled. SART RT features also require stable
timing, although its categorical commission and omission outcomes are less
sensitive to small constant latency offsets. Device effects should be modelled
or the output should be restricted to within-device longitudinal comparisons.

## Prospective Validation Minimum

Before use for routing or individual feedback:

1. Freeze the task implementations and analysis plan.
2. Collect repeated sessions across days and times, including sleep/context
   measures.
3. Test same-session and day-to-day reliability.
4. Test whether abbreviated SART reproduces the full SART dimensions and
   whether PVT-B reproduces or improves the study's distinct vigilance layer.
5. Validate shortened-task profiles against full independent Stroop and
   Flanker blocks in a held-out sample.
6. Evaluate device, order, language, colour vision, motor, age, and practice
   effects.
7. Set quality and abstention thresholds without using the final test sample.
8. Test prediction of an independent next-work-block outcome.
9. Test any proposed support through randomized intervention studies.

## References

- Barzykowski K, Wereszczyński M, Hajdas S, Radel R. *Cognitive
  inhibition behavioral tasks in online and laboratory settings: Data from
  Stroop, SART and Eriksen Flanker tasks*. Data in Brief. 2022;43:108398.
  https://doi.org/10.1016/j.dib.2022.108398
- Basner M, Mollicone D, Dinges DF. *Validity and sensitivity of a brief
  Psychomotor Vigilance Test (PVT-B) to total and partial sleep deprivation*.
  Acta Astronautica. 2011;69:949-959.
  https://doi.org/10.1016/j.actaastro.2011.07.015
- Grant DA et al. *3-minute smartphone-based and tablet-based psychomotor
  vigilance tests for the assessment of reduced alertness due to sleep
  deprivation*. Behavior Research Methods. 2017;49:1020-1029.
  https://doi.org/10.3758/s13428-016-0763-8
- Antler CA et al. *The 3-Minute Psychomotor Vigilance Test Demonstrates
  Inadequate Convergent Validity Relative to the 10-Minute Psychomotor
  Vigilance Test Across Sleep Loss and Recovery*. Frontiers in Neuroscience.
  2022;16:815697. https://doi.org/10.3389/fnins.2022.815697
- Basner M, Dinges DF. *Maximizing sensitivity of the Psychomotor Vigilance
  Test to sleep loss*. Sleep. 2011;34:581-591.
  https://doi.org/10.1093/sleep/34.5.581
- Seli P et al. *A methodological note on evaluating performance in a
  sustained-attention-to-response task*. Behavior Research Methods.
  2013;45:355-363. https://doi.org/10.3758/s13428-012-0266-1
- Wilson KM et al. *Go-stimuli proportion influences response strategy in a
  sustained attention to response task*. Experimental Brain Research.
  2016;234:2989-2998. https://doi.org/10.1007/s00221-016-4701-x
