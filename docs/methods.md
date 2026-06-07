# Pilot Methods

## Scientific Boundary

ACDC is used as a public conflict-control analogue. It cannot reproduce the
adaptive exposure staircase, catch-trial design, or personalized history used
by Zone Coach. Consequently:

- `throughput_proxy` is not CCC bits/second.
- Stroop, Simon, and Flanker yield conflict/interference costs, not switch cost.
- Neutral clusters are not renamed as validated zones.
- A null, dimensional, or source-dominated result is retained.

## ACDC Contract

The versioned schema is in `config/acdc_schema.json`. The R scripts validate
all required tables and columns before executing the SQL in `sql/`. If the
contract fails, the pipeline writes `reports/acdc_schema_discrepancy.md` and
stops.

The verified `initial-release` uses the flattened release schema: group
metadata is stored in `dataset_table`, condition summaries are stored in
`within_table`, and observations reference `within_id`. The pipeline does not
invent `between_id` or `condition_id` fields that are absent from this release.

ACDC stores RT in seconds. The extraction preserves `rt_seconds_raw` and
creates `rt_ms`. The verified release stores congruency as text; legacy
numeric codes are also normalized explicitly:

| ACDC value | Normalized label |
|---|---|
| `congruent` or `1` | congruent |
| `incongruent` or `2` | incongruent |
| `neutral` or `3` | neutral |

The unit of `dataset_table.time_limit` is not documented by the schema, so the
pipeline preserves it as `time_limit_raw` without conversion.

## Cleaning

Rows are preserved and flagged. RT is excluded from RT-dependent features when
it is missing, below 150 ms, above 3000 ms, or farther than three participant-
dataset MADs from the participant-dataset median.

ACDC uses negative block identifiers for practice in several source mappings.
Those rows remain in the cleaned trial file with `practice_block = TRUE` but
are excluded before analytical windows are formed.

`lapse_proxy` is limited to missing RT or explicitly documented timeout/non-
response fields. Slow responses are represented separately by a within-
participant-dataset upper-tail sensitivity flag.

## Expected RT And Update Series

Within each dataset, ordinary least squares models expected raw RT and log RT
from participant, congruency, block, trial trend, within-condition, and
between-group indicators. Models are fitted to valid correct responses and
applied to valid responses.

Within participant, dataset, task, and block:

```text
efficiency_t = correct_t / RT_seconds_t
u_t = z(efficiency_t) - z(log_RT_residual_t) + z(correct_t)
```

Dynamics are calculated on `u_t`.

## Windows

- Primary: non-overlapping 80-trial windows.
- Sensitivity: non-overlapping 60- and 120-trial windows.
- Primary remainders of 40-79 trials: aggregate features only.
- Fewer than 40 remaining trials: excluded.

No window crosses dataset, participant, task, or block boundaries.

## Modelling

The audit selects only non-degenerate features with at most 20% missingness,
then reduces the set if needed to retain at least 80% complete windows.
Remaining missing values are imputed with the task median. Structurally absent
metrics are never imputed.

Task-specific models precede pooled models. Modelling features are median/IQR
adjusted within dataset and task after source predictability is measured on
the unadjusted features. Dataset/task predictability before and after
adjustment is measured with participant-grouped, class-balanced multinomial
logistic cross-validation and permutation tests.

GMMs compare `k=1..8`. Four components are a hypothesis, not a target. Cluster
names remain neutral and are compared post hoc with directional prototypes.
