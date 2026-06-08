# Results

The source contained 11 participant files and approximately 219.9 hours of RR
intervals. The participant-balanced primary analysis used 2,625 quality-passing
120-second windows. Quality-pass rates were 99.4% at 120 seconds and at least
99.7% at 180 and 300 seconds.

Parallel analysis independently selected three components. The fixed
three-component solution explained:

| Component | Variance |
|---|---:|
| C1 | 43.9% |
| C2 | 25.1% |
| C3 | 19.4% |

The total was 88.4% of person-centred covariance.

The primary reserve/flexibility component directly replicated the COG-BCI C1
loading pattern with Tucker congruence `.984`. Direct component congruence was
lower for C2 (`.713`) and C3 (`.705`).

This reflected axis rotation rather than absence of the secondary processes.
For the combined C2-C3 subspace, the two canonical similarities were `.998`
and `.981`, with a maximum principal angle of `11.18` degrees. The complete
three-component subspace had minimum canonical similarity `.990`.

Participant bootstrap fifth-percentile congruence was `.985`, `.975`, and
`.980` for the three healthy-data axes. Minimum leave-one-participant-out
congruence exceeded `.997` for every axis. The direct C1 plus rotated C2-C3
pattern was also retained at 180 and 300 seconds.

The stationary 300-second sensitivity subset contained 838 windows. C1
congruence was `.982`, and the combined C2-C3 subspace minimum similarity was
`.981`. These windows are low-trend and technically stable, not confirmed rest.

## Output Files

The primary outputs are:

- `outputs/reports/main_analysis.md`
- `outputs/tables/source_inventory.csv`
- `outputs/tables/window_quality_audit.csv`
- `outputs/tables/healthy_rr_factor_loadings.csv`
- `outputs/tables/cog_bci_congruence.csv`
- `outputs/tables/subspace_similarity.csv`
- `outputs/tables/sampling_coverage_sensitivity.csv`
- `outputs/tables/participant_bootstrap_stability.csv`
- `outputs/tables/leave_one_participant_out.csv`
- `outputs/tables/between_within_decomposition.csv`
- `outputs/tables/participant_component_summary.csv`
- `outputs/figures/aligned_component_loadings.png`
- `outputs/figures/component_congruence_by_duration.png`

The claim-safe interpretation is in
[`INTERPRETATION.md`](INTERPRETATION.md), with complete numerical details in
[`outputs/reports/main_analysis.md`](outputs/reports/main_analysis.md).
