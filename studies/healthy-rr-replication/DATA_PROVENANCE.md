# Data Provenance

## Source

The source location supplied for this analysis is:

https://github.com/HRP-Lab/Flow-Zone/tree/main/healthy_data

The local source copy used for analysis was at commit:

```text
6e6a6a43ce44e0bbbfd992c67124f6613b0a7de9
```

The local checkout reports
`https://github.com/Trident-Cloud-Lab/Flow-Zone.git` as its Git remote, whereas
the supplied browser URL uses the `HRP-Lab` organization. This may reflect a
repository move or redirect and should be resolved before publication.

It contains 11 text files named by participant identifier. Each numeric line is
treated as one RR interval in milliseconds. File-level SHA-256 hashes are
written to `outputs/tables/source_hashes.csv`.

## Known Limitations

The source repository does not currently document:

- original study or database;
- sensor and RR extraction method;
- whether intervals are raw RR or corrected NN;
- participant characteristics;
- recording dates and time zones;
- posture, sleep, activity, or respiration;
- licence or consent terms for redistribution.

The raw files are not copied into this repository. Publication or external
distribution requires resolving these provenance and licensing gaps.
