# Interpretation

## Target Patterns

The replication tests three continuous covariance patterns:

| Reference component | Provisional physiological reading |
|---|---|
| C1 | Lower cardiac activation plus greater short-term variability/flexibility |
| C2 | Broader variability plus slower temporal organisation |
| C3 | Directional mobilisation/recovery trajectory plus relative Poincare geometry |

These labels describe loading patterns. They are not direct measurements of
sympathetic or parasympathetic activity and are not autonomic zones.

## What Replication Would Mean

High loading congruence would show that the same combinations of RR features
vary together in two independent datasets:

```text
COG-BCI concurrent cognitive-task ECG
long-term healthy RR recordings
```

This would strengthen the case for using reserve/flexibility, variability
organisation, and mobilisation trajectory as separable app outputs.

The two secondary PCA axes may rotate while spanning the same covariance
plane. In that case, the defensible conclusion is that broad variability
organisation and mobilisation trajectory recur as a two-process subspace, not
that C2 and C3 have identical numerical definitions in both datasets.

## Observed Result

The primary reserve/flexibility axis replicated directly. In both datasets it
combined lower HR and longer NN intervals with higher RMSSD and pNN20/pNN50.

The healthy long-term data then separated:

```text
broad variability organisation
from
directional mobilisation/recovery trajectory
```

more cleanly than COG-BCI. COG-BCI C2 and C3 were approximately rotated
mixtures of these two axes. Their shared two-dimensional subspace nevertheless
showed strong similarity.

This supports three useful continuous outputs:

1. regulatory reserve/flexibility;
2. broad variability organisation;
3. mobilisation or recovery trajectory.

It does not yet support three categorical autonomic zones. A state model would
require prospective labelled data, repeated person-specific baselines, and
external outcomes.

It would not show that the dimensions have identical causes in the datasets.
Long-term recordings can reflect sleep, posture, movement, circadian phase,
breathing, physical activity, illness, and measurement conditions.

## Claim Boundary

The study cannot establish confirmed resting states, discrete autonomic
classes, cognitive-autonomic coupling, diagnoses, or effective interventions.
Any later state classifier must be validated prospectively with activity,
posture, respiration, context, and external outcomes.
