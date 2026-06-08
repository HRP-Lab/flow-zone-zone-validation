# Data Provenance

## Source

Barzykowski, K., Wereszczyński, M., Hajdas, S., and Radel, R. (2022).
*Cognitive inhibition behavioral tasks in online and laboratory settings:
Data from Stroop, SART and Eriksen Flanker tasks*. Data in Brief, 43, 108398.
https://doi.org/10.1016/j.dib.2022.108398

- Article: https://pmc.ncbi.nlm.nih.gov/articles/PMC9249604/
- OSF record:
  https://osf.io/2gxhy/?view_only=31aa5d5964a943df8d3e7d911d2d7141

The source article reports 485 recruited online participants, with 19 excluded
for incomplete recording, leaving 466. The published dataset includes online
sessions and two possible laboratory retests.

## Files And Integrity

| File | Role | Expected SHA-256 |
|---|---|---|
| `STROOP_FLANKERS_SART_web_and_lab.xls` | Explicit participant/session linkage and published task summaries | `884ba8bbae097e81f826fa247c2a0bb785302eb88173fbf88dfb5d3c76b8cd5b` |
| `Raw_Stroop.xlsx` | Trial-level shortened Stroop analysis | `7b5dc8ebaae9f498b9d7b83116dbafe4582f0a2ca9301959193df6cc3862464e` |
| `Raw_Flanker.xlsx` | Trial-level shortened Flanker analysis | `80701562c8d9fcd1df9e418e2c1a237a126fedf7eaa0812132cc1bd2c324d82e` |
| `Raw_Sart.xlsx` | Available source trial data; published summaries are used in the main analysis | `b4f04ab9b583a92f31ee45e83a27fe9c63011147560118b1b9b06ded244998fe` |

Place these files in:

```text
data/raw/stroop_sart_flanker/
```

Raw data and participant-level processed files are excluded from Git.

## Task Structure

- Stroop: 140 main trials, split equally between congruent and incongruent
  trials; 14 practice trials; response-contingent stimulus duration; 400 ms
  inter-trial interval and 400 ms error feedback.
- Flanker: the source article describes 140 main trials, split equally between
  congruent and incongruent trials, plus 10 practice trials. The raw workbook
  contains 11 practice-coded rows, four prefatory instruction rows, and 141
  target-coded rows per session. Prefatory rows are explicitly excluded. The
  remaining one-row difference from the article is retained and documented
  rather than silently altered.
- SART: 225 main trials, including 200 Go and 25 NoGo trials, plus 18 practice
  trials. Stimulus onset asynchrony was 1250 ms.

## Analysis Sample

The published summary workbook yielded:

- 466 unique participants.
- 768 complete paired task sessions.
- 466 online sessions.
- 210 first laboratory sessions.
- 92 second laboratory sessions.
- 210 participants and 512 sessions in the repeated-session subset.

The raw-prefix analysis matched 742 sessions from 458 participants across both
Stroop and Flanker. Session matching uses participant identity and session
date/time information from the explicit published linkage table.

## Secondary-Analysis Boundary

The original study was not designed to validate the present mixture taxonomy
or a seven-minute classifier. The current work is an exploratory secondary
analysis. Selection into laboratory retests was partly based on inhibitory
control performance in the source study, so repeat-session estimates should not
be treated as population-representative without qualification.
