# Results

Generated numerical results are written by
`scripts/15_analyze_cog_bci_bridge.py` to:

- `outputs/reports/main_analysis.md`
- `outputs/tables/ecg_quality_audit.csv`
- `outputs/tables/published_effect_replication.csv`
- `outputs/tables/feature_reliability_by_duration.csv`
- `outputs/tables/ans_factor_loadings.csv`
- `outputs/tables/between_within_decomposition.csv`
- `outputs/tables/shared_modality_variance.csv`
- `outputs/tables/incremental_prediction.csv`
- `outputs/tables/negative_control_prediction.csv`
- `outputs/tables/divergence_profiles.csv`
- `outputs/tables/lagged_associations.csv`

## Five-Participant Pilot

The pilot processed five participants, 15 sessions, 120 task recordings, and
6,079 windows with zero import errors. All 120-second windows passed ECG quality
control; median detector concordance was `1.000`.

The directional replication gate passed. N-back and MATB difficulty effects met
the predeclared domain rule. PVT slowing was reproduced, while the PVT cardiac
directions did not reach the 60% participant-session threshold.

The selected within-person HRV feature set yielded three bootstrap-stable PCA
components explaining `46.8%`, `27.5%`, and `15.5%` of covariance. Their
bootstrap fifth-percentile Tucker congruences were `.948`, `.950`, and `.979`.
Between-person factor analysis and autonomic GMM were not testable with five
participants.

Median agreement between 120-second feature averages and full-block features
was high. Mean HR, mean NN, log RMSSD, pNN20/pNN50, and several dynamics
features exceeded `.90`; HR and NN slopes were weaker (`.68` and `.65`).

Task-specific participant-held-out PLS produced negative multivariate R2 for
PVT, Flanker, N-back, and MATB. Combined cognitive plus HRV models did not
consistently improve over cognitive-only models or temporally shuffled ECG.
Isolated gains for next-window N-back throughput, MATB efficacy, and a
divergence-augmented Flanker RT model are descriptive only because the pilot has
five participants and lacks participant-permutation/bootstrap inference.

The pilot therefore supports feasibility and multidimensional autonomic
measurement, but not robust incremental cognitive prediction.
