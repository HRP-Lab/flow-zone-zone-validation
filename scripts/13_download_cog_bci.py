"""Download and verify selected COG-BCI participant archives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.cog_bci_io import (
    download_zenodo_file,
    fetch_zenodo_manifest,
    participant_filename,
    verify_zenodo_file,
)
from flowzone_validation.reporting import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--participants", nargs="+", type=int, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = fetch_zenodo_manifest()
    lookup = {item.key: item for item in manifest}
    reference_names = (
        "COG-BCI_info.pdf",
        "triggerlist.txt",
        "KSS.txt",
        "RSME.txt",
        "notebook.mat",
    )
    references = []
    for filename in reference_names:
        if filename not in lookup:
            raise FileNotFoundError(
                f"{filename} is absent from the Zenodo record"
            )
        metadata = lookup[filename]
        path = download_zenodo_file(
            metadata,
            args.reference_dir / filename,
        )
        references.append(
            {
                "filename": filename,
                "bytes": metadata.size,
                "checksum": metadata.checksum,
                "url": metadata.url,
                "local_path": str(path),
                "verified": verify_zenodo_file(path, metadata),
            }
        )
    records = []
    for participant in args.participants:
        filename = participant_filename(participant)
        if filename not in lookup:
            raise FileNotFoundError(f"{filename} is absent from Zenodo record")
        metadata = lookup[filename]
        path = download_zenodo_file(metadata, args.cache_dir / filename)
        records.append(
            {
                "participant_number": participant,
                "filename": filename,
                "bytes": metadata.size,
                "checksum": metadata.checksum,
                "url": metadata.url,
                "local_path": str(path),
                "verified": verify_zenodo_file(path, metadata),
            }
        )
    existing_records = []
    if args.manifest.exists():
        existing_records = json.loads(
            args.manifest.read_text(encoding="utf-8")
        ).get("participants", [])
    combined = {
        row["filename"]: row for row in [*existing_records, *records]
    }
    write_json(
        {
            "zenodo_record": 7413650,
            "reference_files": references,
            "participants": list(combined.values()),
        },
        args.manifest,
    )
    print(json.dumps({"references": references, "participants": records}, indent=2))


if __name__ == "__main__":
    main()
