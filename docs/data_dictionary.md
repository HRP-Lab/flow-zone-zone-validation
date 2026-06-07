# Derived Data Dictionary

## Trial Extract

The CSV representation is gzip-compressed as `acdc_trial_extract.csv.gz` to
avoid duplicating more than 1 GB of uncompressed data beside the Parquet file.

| Field | Meaning |
|---|---|
| `participant_id` | Dataset-scoped subject identifier, `<dataset_id>:<subject>` |
| `task_family` | `Stroop`, `Flanker`, or `Simon` |
| `control_cost_type` | `interference` for Stroop/Simon; `conflict` for Flanker |
| `block_source_raw` | Original ACDC block value preserved as text |
| `block_raw` | Integer block value; blank source values remain missing |
| `congruency_raw` | Original ACDC text value or legacy numeric code |
| `congruency` | `congruent`, `incongruent`, `neutral`, or `unknown` |
| `accuracy_raw` | Original ACDC accuracy value |
| `correct` | Normalized `1`, `0`, or missing |
| `rt_seconds_raw` | Original ACDC response time |
| `rt_ms` | Response time converted from seconds to milliseconds |
| `mapping_issue` | Explicit unknown-code warning |

## Cleaned Trials

| Field | Meaning |
|---|---|
| `rt_excluded` | Any RT cleaning rule failed |
| `practice_block` | Negative ACDC block identifier; retained but not windowed |
| `lapse_proxy` | Missing RT or documented timeout/non-response |
| `slow_tail_sensitivity` | RT exceeds participant-dataset 90th percentile |
| `log_rt_residual` | Residual from expected log-RT model |
| `raw_rt_residual_ms` | Audit residual from expected raw-RT model |
| `efficiency_t` | Correctness divided by RT in seconds |
| `u_t` | Standardized signed cognitive update series |

## Window Features

| Field | Meaning |
|---|---|
| `throughput_proxy` | Accuracy divided by median correct RT in seconds |
| `cog_alpha1` | DFA short-scale exponent of `u_t` |
| `cog_lag1`, `cog_lag2` | Lagged correlations of `u_t` |
| `cog_roughness` | RMS successive change divided by total SD |
| `cog_sign_change` | Fraction of non-zero differences reversing direction |
| `cog_sd1_sd2` | Poincare short/long variability ratio |
| `cog_perm_entropy3` | Normalized ordinal-pattern entropy |
| `cog_diff_entropy` | Normalized histogram entropy of successive changes |
| `control_cost_rt_ms` | Incongruent minus congruent correct RT |
| `control_cost_acc` | Congruent minus incongruent accuracy |

## Zhang-Tang Follow-Up Windows

| Field | Meaning |
|---|---|
| `mi_congruency_correct` | Bias-corrected MI in bits between congruency and correctness |
| `mi_congruency_response` | Structurally unavailable because response identity is absent |
| `mi_prev_error_next_correct` | Bias-corrected MI between previous error and current correctness |
| `mi_condition_efficiency_bin_sens` | Median condition-efficiency MI across registered bin counts |
| `delta_*` | Current minus immediately previous full window within the same boundary |
| `combined_update_magnitude` | RMS robust-standardized window update magnitude |
| `upper_tail_rate_abs_rt_resid_z` | Fraction of absolute log-RT residual z-scores at least 2 |
| `upper_tail_rate_abs_delta_u_z` | Fraction of absolute within-window delta-u z-scores at least 2 |
| `large_update_window` | Dataset-task upper-decile update indicator |
| `next_*` | Immediately subsequent full-window outcome within the same boundary |
| `post_error_slowing_ms` | Post-error minus post-correct RT when supported |
| `post_error_adjustment_abs_ms` | Magnitude of supported post-error adjustment |
| `pes_supported` | Whether both comparison sets meet minimum counts |
| `rt_cv` | Correct RT coefficient of variation |
| `nonresponse_rate` | Mean `lapse_proxy` |
| `slow_tail_rate` | Mean slow-tail sensitivity flag |
| `fast_error_rate` | Error responses below 250 ms |
| `rt_volatility` | Mean absolute successive log-RT residual change |
| `error_burstiness` | Consecutive-error pairs relative to independence |
| `rt_drift`, `error_drift` | Linear within-window trends |
