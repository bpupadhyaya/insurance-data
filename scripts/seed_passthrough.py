#!/usr/bin/env python3
"""Manual-seed datasets: sources with no practical scriptable path today.

Each of these was investigated for a live-fetchable source this session
and hit a real, documented blocker:
  - NAIC market share/average-premium reports: locked inside PDFs, not a
    structured API (autohome).
  - MoneyGeek surveys: return WAF/bot-blocking to scripted requests (life,
    motorcycle).
  - Oregon DCBS workers' comp study: a biennial PDF report (workerscomp).
  - USDA RMA discovery-period bulletin: an HTML bulletin whose number
    changes every year, not a stable API -- scraping its prose would be
    as fragile as parsing a PDF (crop).
  - NAPHIA / Squaremouth: member/marketplace listing pages, no public API
    (pet, travel).
  - NFIP: OpenFEMA's FimaNfipPolicies API is real and live, but represents
    80M+ raw policy transactions with no server-side aggregation -- a
    weekly free CI job can't reduce that to zone-level averages without
    its own dedicated design (see dotfiles memory for the investigation).
    Kept as a seed until that's built out separately.

These datasets are still real, cited, and dated -- just not automatically
refreshable yet. This script copies the current seed file verbatim into
the published output, tagged source_kind: "manual" in the manifest, so the
app can show (and Settings can eventually surface) which numbers are
live-refreshed vs. awaiting a human to redo the same research pass.
"""
import json
import shutil
from datetime import date

SEEDS = [
    {
        "dataset_id": "nfip", "domain_id": "flood", "kind": "nfip_zones",
        "seed_file": "nfip.json", "published_file": "nfip.json",
        "source_name": "OpenFEMA FIMA NFIP Redacted Policies",
        "source_url": "https://www.fema.gov/openfema-data-page/fima-nfip-redacted-policies-v2",
    },
    {
        "dataset_id": "crop", "domain_id": "crop", "kind": "crop_commodities",
        "seed_file": "crop.json", "published_file": "crop.json",
    },
    {
        "dataset_id": "workerscomp", "domain_id": "workerscomp", "kind": "wc_rankings",
        "seed_file": "workerscomp.json", "published_file": "workerscomp.json",
    },
    {
        "dataset_id": "autohome", "domain_id": "auto", "kind": "state_line_averages",
        "seed_file": "autohome.json", "published_file": "autohome.json",
        "source_name_key": "autoSourceName", "source_url_key": "autoSourceURL",
    },
    {
        "dataset_id": "life", "domain_id": "life", "kind": "life_term_rates",
        "seed_file": "life.json", "published_file": "life.json",
    },
    {
        "dataset_id": "pet", "domain_id": "pet", "kind": "pet_rates",
        "seed_file": "pet.json", "published_file": "pet.json",
    },
    {
        "dataset_id": "motorcycle", "domain_id": "motorcycle", "kind": "motorcycle_state_rates",
        "seed_file": "motorcycle.json", "published_file": "motorcycle.json",
    },
    {
        "dataset_id": "umbrella", "domain_id": "umbrella", "kind": "umbrella_profiles",
        "seed_file": "umbrella.json", "published_file": "umbrella.json",
    },
    {
        "dataset_id": "travel", "domain_id": "travel", "kind": "travel_plans",
        "seed_file": "travel.json", "published_file": "travel.json",
    },
]


def meta_of(seed_path):
    with open(seed_path) as f:
        d = json.load(f)
    return d.get("meta") if isinstance(d, dict) else None


def main():
    results = []
    for seed in SEEDS:
        seed_path = f"data/seeds/{seed['seed_file']}"
        published_path = f"data/published/{seed['published_file']}"
        shutil.copyfile(seed_path, published_path)

        meta = meta_of(seed_path)
        if meta:
            name_key = seed.get("source_name_key", "sourceName")
            url_key = seed.get("source_url_key", "sourceURL")
            source_name = meta.get(name_key, "")
            source_url = meta.get(url_key, "")
            snapshot_date = meta.get("snapshotDate", date.today().isoformat())
        else:
            source_name = seed.get("source_name", "")
            source_url = seed.get("source_url", "")
            snapshot_date = seed.get("snapshot_date", date.today().isoformat())

        results.append({
            "dataset_id": seed["dataset_id"],
            "domain_id": seed["domain_id"],
            "kind": seed["kind"],
            "file_name": seed["published_file"],
            "snapshot_date": snapshot_date,
            "source_kind": "manual",
            "source_name": source_name,
            "source_url": source_url,
        })
    return results


if __name__ == "__main__":
    print(json.dumps(main()))
