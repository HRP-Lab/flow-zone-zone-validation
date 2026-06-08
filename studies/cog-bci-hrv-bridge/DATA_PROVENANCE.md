# Data Provenance

## Source

- Dataset: COG-BCI database, version 4
- Zenodo record: <https://zenodo.org/records/7413650>
- DOI: `10.5281/zenodo.7413650`
- Data descriptor: <https://www.nature.com/articles/s41597-022-01898-y>
- Participants: 29
- Sessions: three weekly sessions
- Tasks: PVT, Flanker, 0/1/2-back, easy/medium/difficult MATB
- Signal: synchronized 500 Hz recordings with dedicated `ECG1`

Zenodo provides one archive per participant. The downloader records the current
file URL, byte size, and MD5 checksum in
`outputs/manifests/zenodo_download_manifest.json`.

## Local Data Policy

Participant archives, extracted task files, and processed participant-level
windows are excluded from Git. Aggregate quality tables, model summaries,
figures, methods, results, interpretation, and manifests are committed.

The default cache is outside the OneDrive repository:

```text
%LOCALAPPDATA%\flowzone-cog-bci-cache
```

The runner can delete verified archives after processing with
`-CleanupArchives`. Any deleted archive is reproducible from the pinned Zenodo
record and checksum manifest.

## Schema Validation

The first verified archive, `sub-01.zip`, had:

```text
MD5 23f1f74cced86b40a0a956c67bba74fb
size 1,096,627,416 bytes
```

The real recording schema confirmed `ECG1`, 500 Hz sampling, synchronized task
annotations, separate behavioural files, and separate EEGLAB pairs per task.
