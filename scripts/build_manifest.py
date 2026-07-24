#!/usr/bin/env python3
"""Orchestrator: run every fetch script + the seed passthrough, then build
manifest.json describing every published dataset (id, domain, file,
sha256, snapshot date, and whether it was live-fetched or a manual seed).

Run from the repo root: python3 scripts/build_manifest.py
"""
import json
import os
import sys
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import manifest as manifest_lib  # noqa: E402

PUBLISHED_DIR = "data/published"


def run_fetcher(module_name, label):
    print(f"--- {label} ---", file=sys.stderr)
    try:
        module = __import__(module_name)
        result = module.main()
        print(f"OK: {label}", file=sys.stderr)
        return result, None
    except Exception as e:
        print(f"FAILED: {label}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, str(e)


def main():
    os.makedirs(PUBLISHED_DIR, exist_ok=True)

    entries = []
    failures = []

    for module_name, label in [
        ("fetch_qhp", "Health (CMS QHP Landscape)"),
        ("fetch_medicare", "Medicare Advantage (CMS Landscape)"),
        ("fetch_zip_counties", "ZIP-county crosswalk (Census)"),
        ("fetch_tx_filings", "Texas rate filings (data.texas.gov)"),
    ]:
        result, error = run_fetcher(module_name, label)
        if error:
            failures.append({"dataset": module_name, "error": error})
            continue
        entries.append(result)

    print("--- Manual seeds (NAIC/MoneyGeek/USDA-RMA/Oregon-DCBS/NAPHIA/Squaremouth/NFIP-aggregate) ---", file=sys.stderr)
    import seed_passthrough
    entries.extend(seed_passthrough.main())

    dataset_entries = []
    for e in entries:
        dataset_entries.append(manifest_lib.dataset_entry(
            dataset_id=e["dataset_id"],
            domain_id=e["domain_id"],
            kind=e["kind"],
            file_name=e["file_name"],
            published_dir=PUBLISHED_DIR,
            snapshot_date=e["snapshot_date"],
            source_kind=e["source_kind"],
            source_name=e["source_name"],
            source_url=e["source_url"],
        ))

    manifest = {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": sorted(dataset_entries, key=lambda d: d["id"]),
    }
    if failures:
        manifest["failures"] = failures

    manifest_lib.write_json(f"{PUBLISHED_DIR}/manifest.json", manifest)
    print(f"\nWrote manifest.json with {len(dataset_entries)} datasets, {len(failures)} failures", file=sys.stderr)

    if failures:
        # A partial manifest still gets published (the app should keep
        # serving whatever last succeeded per-dataset), but a non-zero
        # exit makes the failure visible in the Actions run.
        sys.exit(1)


if __name__ == "__main__":
    main()
