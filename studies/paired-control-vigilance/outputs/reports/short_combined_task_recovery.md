# Two-Minute Stroop and Flanker Recovery

> This analysis tests recovery of the exploratory four-component full-session partition. The partition is not validated ground truth.

## Analysis set

- Matched paired sessions: 742.
- Dataset-scoped participants: 458.
- Five-fold validation isolated participants across train and test.
- Stroop elapsed time was modelled as RT + 400 ms interval + 400 ms error feedback.
- The conservative two-minute Flanker prefix used 44 trials, based on the source protocol's maximum 2700 ms trial duration.

## Recovery results

| Variant | Stroop trials | Flanker trials | Balanced accuracy | Macro F1 | Coverage p>=0.60 | Accuracy when confident |
|---|---:|---:|---:|---:|---:|---:|
| stroop_80+flanker_80 | 80 | 80 | 0.786 | 0.763 | 0.799 | 0.855 |
| stroop_100+flanker_44 | 100 | 44 | 0.772 | 0.738 | 0.794 | 0.842 |
| stroop_80+flanker_60 | 80 | 60 | 0.751 | 0.726 | 0.776 | 0.837 |
| stroop_2min+flanker_44 | 101 | 44 | 0.744 | 0.718 | 0.774 | 0.845 |
| stroop_80+flanker_44 | 80 | 44 | 0.743 | 0.713 | 0.778 | 0.828 |
| stroop_60+flanker_44 | 60 | 44 | 0.707 | 0.680 | 0.735 | 0.818 |
| stroop_100 | 100 |  | 0.634 | 0.600 | 0.554 | 0.765 |
| flanker_80 |  | 80 | 0.607 | 0.582 | 0.481 | 0.797 |
| flanker_60 |  | 60 | 0.596 | 0.567 | 0.440 | 0.754 |
| stroop_80 | 80 |  | 0.585 | 0.561 | 0.457 | 0.747 |
| stroop_2min | 101 |  | 0.582 | 0.564 | 0.484 | 0.789 |
| flanker_44 |  | 44 | 0.555 | 0.534 | 0.409 | 0.755 |

## Conservative seven-minute configuration

The operational candidate is approximately:

```text
3-minute vigilance probe
+ 2-minute Stroop
+ 2-minute Flanker
= approximately 7 minutes
```

Its four-profile balanced accuracy was `0.744` with macro F1 `0.718`. It returned predictions above `0.60` confidence for 77.4% of sessions; accuracy within those sessions was 84.5%.

| Full-session neutral profile | Recall |
|---|---:|
| Paired-Control-GMM4-full-C1 | 0.747 |
| Paired-Control-GMM4-full-C2 | 0.796 |
| Paired-Control-GMM4-full-C3 | 0.673 |
| Paired-Control-GMM4-full-C4 | 0.759 |

The globally overloaded component had the weakest recall. This component is also the smallest and produces fewer Stroop trials within a fixed two-minute period.

## Fixed-duration Stroop evidence bias

| Full-session profile | Median trials | P10-P90 | Below 60 | Below 80 |
|---|---:|---:|---:|---:|
| Paired-Control-GMM4-full-C1 | 86 | 68-103 | 5.2% | 32.5% |
| Paired-Control-GMM4-full-C2 | 106 | 92-119 | 0.0% | 1.0% |
| Paired-Control-GMM4-full-C3 | 81 | 54-111 | 18.4% | 49.0% |
| Paired-Control-GMM4-full-C4 | 104 | 87-119 | 0.0% | 0.9% |

A fixed-duration Stroop yields less evidence for slow and overloaded sessions. Trial count must therefore be an explicit model input and quality variable; fewer than 60 scored trials should normally trigger abstention.

## Interpretation

The seven-minute protocol is feasible for a research prototype. Combined prefixes materially outperform either task alone and cross the provisional 0.70 balanced-accuracy threshold. However, the result is an internal recovery analysis because full-session profiles and shortened features come from the same dataset.

A redesigned response-contingent Flanker could deliver more than 44 trials in two minutes, but changing stimulus duration or response termination changes the task and requires fresh validation. The present result should not be used to claim production classifier validity.

## Recommended next protocol

```text
20-30 second context check
3-minute PVT-like vigilance probe
2-minute Stroop, target >=80 and minimum 60 scored trials
2-minute Flanker, conservative target 44 scored trials
probabilistic four-profile control output
continuous vigilance output
abstain when evidence or confidence is insufficient
```
