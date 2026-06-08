"""Build ECG and cognitive windows from verified COG-BCI archives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowzone_validation.cog_bci_bridge import (
    process_participant_archive,
    process_participant_directory,
)
from flowzone_validation.cog_bci_io import (
    find_participant_directory,
    participant_filename,
    questionnaire_tables,
    task_order_table,
)
from flowzone_validation.reporting import write_json, write_table


RSME_TASK_NAMES = {
    "MATB_easy": "MATBEasy",
    "MATB_med": "MATBMedium",
    "MATB_diff": "MATBDifficult",
    "ZeroBack": "NBack0",
    "OneBack": "NBack1",
    "TwoBack": "NBack2",
    "PVT": "PVT",
    "Flanker": "Flanker",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--participants", nargs="+", type=int, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--extracted-root", type=Path)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--errors", type=Path, required=True)
    parser.add_argument("--questionnaires", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cleanup-archives", action="store_true")
    parser.add_argument("--append-existing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    orders = task_order_table(args.reference_dir / "notebook.mat")
    kss, rsme = questionnaire_tables(args.reference_dir)
    rsme["task"] = rsme["condition"].map(RSME_TASK_NAMES)

    all_windows: list[pd.DataFrame] = []
    inventories: list[pd.DataFrame] = []
    errors: list[pd.DataFrame] = []
    processed = []
    for participant_number in args.participants:
        participant_id = f"sub-{participant_number:02d}"
        archive = args.cache_dir / participant_filename(participant_number)
        if not archive.exists():
            raise FileNotFoundError(
                f"Missing verified archive {archive}; run script 13 first."
            )
        extracted_participant = None
        if args.extracted_root is not None:
            extracted_participant = find_participant_directory(
                args.extracted_root,
                participant_id,
            )
        if extracted_participant is not None:
            result = process_participant_directory(
                extracted_participant,
                participant_id,
                orders,
                checkpoint_dir=args.checkpoint_dir,
            )
        else:
            result = process_participant_archive(
                archive,
                participant_id,
                orders,
                temporary_root=args.cache_dir,
                checkpoint_dir=args.checkpoint_dir,
            )
        if not result.windows.empty:
            all_windows.append(result.windows)
        if not result.inventory.empty:
            inventories.append(result.inventory)
        if not result.errors.empty:
            errors.append(result.errors)
        processed.append(
            {
                "participant_id": participant_id,
                "windows": int(len(result.windows)),
                "recordings": int(len(result.inventory)),
                "errors": int(len(result.errors)),
            }
        )
        if args.cleanup_archives:
            archive.unlink(missing_ok=True)

    windows = (
        pd.concat(all_windows, ignore_index=True)
        if all_windows
        else pd.DataFrame()
    )
    if not windows.empty:
        windows = windows.merge(
            rsme[
                [
                    "participant_number",
                    "session_number",
                    "task",
                    "rsme",
                ]
            ],
            on=["participant_number", "session_number", "task"],
            how="left",
            validate="many_to_one",
        )
    inventory = (
        pd.concat(inventories, ignore_index=True)
        if inventories
        else pd.DataFrame()
    )
    error_table = (
        pd.concat(errors, ignore_index=True) if errors else pd.DataFrame()
    )
    if args.append_existing and args.windows.exists():
        prior = pd.read_parquet(args.windows)
        windows = (
            pd.concat([prior, windows], ignore_index=True)
            .drop_duplicates("window_id", keep="last")
        )
    if args.append_existing and args.inventory.exists():
        prior = pd.read_csv(args.inventory)
        inventory = (
            pd.concat([prior, inventory], ignore_index=True)
            .drop_duplicates(
                ["participant_id", "session_id", "task"],
                keep="last",
            )
        )
    if (
        args.append_existing
        and args.errors.exists()
        and args.errors.stat().st_size > 0
    ):
        prior = pd.read_csv(args.errors)
        error_table = pd.concat(
            [prior, error_table],
            ignore_index=True,
        ).drop_duplicates()
    if not error_table.empty and not inventory.empty:
        successful = set(
            inventory[
                ["participant_id", "session_id", "task"]
            ].itertuples(index=False, name=None)
        )
        error_keys = error_table[
            ["participant_id", "session_id", "task"]
        ].apply(tuple, axis=1)
        error_table = error_table.loc[
            ~error_keys.isin(successful)
        ].reset_index(drop=True)
    questionnaire = pd.concat(
        [
            kss.assign(questionnaire="KSS"),
            rsme.assign(questionnaire="RSME"),
        ],
        ignore_index=True,
        sort=False,
    )
    write_table(windows, args.windows)
    write_table(inventory, args.inventory)
    write_table(error_table, args.errors)
    write_table(questionnaire, args.questionnaires)
    prior_processed = []
    if args.manifest.exists():
        prior_processed = json.loads(
            args.manifest.read_text(encoding="utf-8")
        ).get("processed", [])
    combined_processed = {
        row["participant_id"]: row
        for row in [*prior_processed, *processed]
    }
    write_json(
        {
            "participants_requested": sorted(
                {
                    int(row["participant_id"].split("-")[-1])
                    for row in combined_processed.values()
                }
            ),
            "processed": list(combined_processed.values()),
            "cleanup_archives": args.cleanup_archives,
            "window_rows": int(len(windows)),
            "recording_rows": int(len(inventory)),
            "error_rows": int(len(error_table)),
        },
        args.manifest,
    )
    print(json.dumps(processed, indent=2))


if __name__ == "__main__":
    main()
