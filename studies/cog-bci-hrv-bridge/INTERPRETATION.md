# Interpretation

## Scientific Role

This study asks whether cardiac autonomic regulation supplies partly shared and
partly independent information about vigilance, conflict control, and workload.
It does not assume that autonomic dimensions must map one-to-one onto cognitive
profiles.

The strongest positive result would be:

1. at least one stable autonomic dimension beyond mean HR;
2. partial, not complete, cognitive-autonomic covariance;
3. participant-isolated improvement in prediction or calibration;
4. aligned ECG outperforming shuffled and temporally displaced controls;
5. recurrent divergence across at least two tasks or sessions.

## Candidate Dimensions

Names are assigned only after loadings are inspected. Plausible descriptions
include cardiac activation, variability/flexibility, and temporal organisation.
They are not direct measures of the entire sympathetic and parasympathetic
systems. LF/HF is not interpreted as sympathovagal balance.

The pilot loading patterns provisionally suggest:

| Component | Descriptive reading |
|---|---|
| Within C1 | lower cardiac activation with greater short-term variability/flexibility |
| Within C2 | broad variability with slower trend organisation |
| Within C3 | directional HR/NN trend with relative short-term Poincare geometry |

PCA signs are arbitrary, and these names are not autonomic states. The high
bootstrap loading congruence is encouraging but is based on only five
participants and many repeated windows.

## Divergence

Predeclared descriptive candidates are:

| Pattern | Claim-safe interpretation |
|---|---|
| Effective cognition plus elevated autonomic load | compensatory strain candidate |
| Poor cognition plus preserved autonomic regulation | task-specific cognitive inefficiency |
| Low vigilance plus low cardiac activation | under-activation candidate |
| Fast/error-prone cognition plus elevated activation | coupled brittle activation |

A candidate must recur across two tasks or sessions and predict KSS, RSME, or
next-window performance beyond shared factors before it is treated as more than
a descriptive pattern.

## Transfer To The Proposed Protocol

Flanker transfers directly. PVT is a vigilance analogue rather than SART.
N-back and MATB provide workload stress tests. Stroop is absent. Positive bridge
evidence would justify a prospective simultaneous ECG study using the actual
six-/seven-minute Stroop-Flanker-SART battery; it would not validate that
battery retrospectively.

Two-minute windows are expected to be most defensible for HR, RMSSD, SDNN, and
related time-domain readiness features. Nonlinear dynamics may require
three-minute or full-block estimates. Weak two-minute entropy/DFA reliability
does not invalidate simpler two-minute autonomic features.

In this pilot, two-minute time-domain and several dynamics features agreed well
with full-block estimates. This supports measurement feasibility. It does not
establish incremental utility: held-out cognitive-autonomic PLS was negative
for every task family, and combined HRV models did not consistently outperform
cognitive-only or shuffled-ECG controls.

### Prospective Dual-Output Use

A prospective app can collect continuous RR during the six-/seven-minute
SART-Stroop-Flanker battery while retaining task boundaries. The stronger
measurement design adds a 90-120 second seated baseline and a 60-second
post-test recovery period. It can then report cognitive control/vigilance and
autonomic reserve/organisation/mobilisation as separate outputs.

The pilot does not justify mapping an autonomic component directly onto a
cognitive profile. It instead supports testing whether independent mind and
body recommendations improve next-work-block routing. For example, regulated
cognition with elevated autonomic load may warrant a lower-intensity block or
earlier recovery, whereas overloaded cognition with preserved autonomic
regulation may warrant cognitive scaffolding rather than a physiological
intervention.

All autonomic interpretations should be person-referenced and quality-gated.
The full candidate measurement and routing specification is documented in
[`PROTOCOL_TASK_SPECS.md`](../paired-control-vigilance/PROTOCOL_TASK_SPECS.md#concurrent-rrhrv-extension).

## Claim Boundary

The study may support the statement that ECG-derived autonomic dynamics carry
shared and dissociable information about cognitive performance and readiness.
It cannot establish discrete brain states, clinical diagnoses, intervention
effects, or a production Flow Zone classifier.

---

# Depth Interpretation

The three components explain approximately **89.9% of within-person autonomic variation**. They describe how a person’s cardiac regulation changed across task windows after accounting for task and session effects.

PCA signs are arbitrary. The descriptions below assume the orientation shown in the results.

## C1: Regulatory Reserve/Flexibility

**Variance explained:** 46.9%

Strongest loadings:

```text
lower heart rate
longer NN intervals
higher RMSSD
higher pNN20 and pNN50
moderately higher SDNN
```

### Physiological interpretation

RMSSD, pNN20, pNN50 and Poincaré SD1 mainly reflect rapid beat-to-beat variation, which is strongly influenced by cardiac vagal modulation. Parasympathetic effects on the sinoatrial node operate more rapidly than sympathetic effects.

A high C1 score could therefore indicate:

```text
lower cardiac activation
+
greater vagally mediated beat-to-beat flexibility
+
greater capacity to adjust cardiac timing
```

A low score would indicate the converse:

```text
higher cardiac activation
+
reduced short-term variability
+
possible vagal withdrawal or reduced regulatory reserve
```

A suitable descriptive name is:

> **Regulatory reserve/flexibility**

This does not mean that high C1 is always “better.” During demanding activity, an appropriate temporary reduction in vagal HRV can represent useful mobilisation. The more informative question is whether C1 recovers afterward and how far it deviates from the individual’s baseline.

Heart rate and HRV are also mathematically and physiologically related, so C1 partly reflects a general low-HR/high-HRV axis rather than two entirely independent processes.

## C2: Broad Variability and Settling Organisation

**Variance explained:** 27.6%

Strongest loadings:

```text
higher SDNN and CVNN
falling heart rate
lengthening NN intervals
lower SD1/SD2 ratio
little change in RMSSD or pNN20/50
```

### Physiological interpretation

SDNN and CVNN represent broader variation across the complete measurement window. Unlike RMSSD, they include slower fluctuations and can be affected by:

- baroreflex and blood-pressure adjustments;
- slower respiratory effects;
- progressive settling or habituation;
- nonstationary heart-rate trends;
- posture and movement.

The lower SD1/SD2 ratio suggests that longer-timescale variation represented by SD2 is relatively more prominent than immediate beat-to-beat variation.

A high C2 score may therefore describe:

> **Broad, slowly organised variability during settling or recovery**

It may represent a cardiovascular system adjusting across the window rather than simply having greater resting vagal tone.

However, part of the high SDNN may be generated by the falling heart-rate trend itself. C2 should not automatically be called “coherent regulation” until respiration, posture and detrended HRV analyses confirm that interpretation.

The reverse pattern could indicate continuing mobilisation:

```text
rising heart rate
+
less broad variability
+
reduced evidence of settling
```

## C3: Mobilisation–Recovery Trajectory

**Variance explained:** 15.5%

Strongest loadings:

```text
strongly falling heart rate
strongly lengthening NN intervals
higher SD1/SD2 ratio
lower SDNN and CVNN
almost no RMSSD loading
```

### Physiological interpretation

C3 is dominated by **direction of change**, rather than absolute HRV level.

A high score represents:

```text
heart rate falling during the window
=
settling, habituation or recovery candidate
```

A low score represents:

```text
heart rate rising during the window
=
continued mobilisation or escalation candidate
```

The near-zero RMSSD loading means that C3 is not primarily a vagal-reserve dimension. It appears to describe the trajectory of cardiac activation.

The positive SD1/SD2 loading may arise because longer-timescale dispersion is declining relative to short-term variability. It should not be interpreted as direct “autonomic balance.”

A suitable name is:

> **Mobilisation–recovery trajectory**

## Combined Practical Reading

The three dimensions could be reported independently:

| Pattern | Possible interpretation |
|---|---|
| High C1 | Lower activation and greater short-term regulatory flexibility |
| Low C1 | Mobilisation with reduced short-term reserve |
| High C2 | Broad, slower adjustment while settling |
| Low C2 | Compressed variability or continuing activation |
| High C3 | HR decreasing: recovery/settling trajectory |
| Low C3 | HR increasing: mobilisation/escalation trajectory |

This permits useful combinations. For example:

```text
Low C1 + low C3
= activated, reduced reserve, still escalating

Low C1 + high C3
= activated but beginning to recover

High C1 + neutral trajectory
= flexible and relatively settled

High C2 + high C3
= broad adjustment during recovery
```

## Important Limits

The extremely high Tucker congruence means the loading patterns were stable when the five pilot participants were resampled. It does **not** establish population-wide replication because:

- only five participants contributed;
- 344 windows are repeated observations, not 344 independent people;
- respiration was not measured;
- posture, movement and other physiological influences remain possible;
- between-person components could not be estimated;
- no evidence yet supports discrete autonomic states;
- cognitive–autonomic coupling was not robustly demonstrated.

The safest conclusion is:

> The pilot reveals one reserve/flexibility dimension and two complementary temporal-organisation dimensions. These are plausible descriptions of cardiac regulation, but not validated sympathetic/parasympathetic states or medical classifications.

Relevant physiology sources: [HRV measurement and interpretation](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/), [HRV metrics and norms](https://pmc.ncbi.nlm.nih.gov/articles/PMC5624990/), [COG-BCI physiological validation](https://pmc.ncbi.nlm.nih.gov/articles/PMC9918545/), and [neurovisceral integration and cognition](https://pmc.ncbi.nlm.nih.gov/articles/PMC6637318/).
