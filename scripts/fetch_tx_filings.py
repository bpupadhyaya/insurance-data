#!/usr/bin/env python3
"""Texas real rate filings: real, live fetch from data.texas.gov's Socrata
API for "Home and auto insurance rate filings" (dataset iubg-btfs) --
genuinely open, no login/WAF, real SERFF IDs and filed percent-change
amounts. Produces tx_filings.json in the shape ContentDatabase.swift/.kt
already parse.

Selection rule (documented since this dataset has no natural "top N"):
among Closed (fully processed, not Pending) filings received in the
trailing 365 days, take the 15 largest rate changes by absolute value,
per line (auto/home). This is a rolling window recomputed on every run,
not a fixed historical snapshot.
"""
import json
import sys
from datetime import date, timedelta

import requests

BASE_URL = "https://data.texas.gov/resource/iubg-btfs.json"
LINES = {"auto": "Personal Automobile", "home": "Homeowners"}
TOP_N = 15
WINDOW_DAYS = 365


KEEP_UPPER = {"LLC", "LP", "LLP", "INC", "PC", "LTD", "CO"}


def title_case_company(name):
    # Feed returns ALL CAPS company names; title-case for display, keeping
    # a small set of legal-entity abbreviations uppercase.
    return " ".join(w if w in KEEP_UPPER else w.capitalize() for w in name.split())


def fetch_line(insurance_type, since_date):
    params = {
        "status": "Closed",
        "state_type_of_insurance": insurance_type,
        "$where": f"received_date >= '{since_date.isoformat()}'",
        "$select": "company_name,percent_change,serff_id,received_date",
        "$limit": 50000,
    }
    r = requests.get(BASE_URL, params=params, timeout=60)
    r.raise_for_status()
    rows = r.json()
    parsed = []
    for row in rows:
        pct_raw = row.get("percent_change")
        if not pct_raw:
            continue
        try:
            pct = float(pct_raw.strip().rstrip("%"))
        except ValueError:
            continue
        parsed.append({
            "company": title_case_company(row["company_name"]),
            "pct": pct,
            "serff": row["serff_id"],
            "date": row["received_date"][:10],
        })
    parsed.sort(key=lambda f: abs(f["pct"]), reverse=True)
    return parsed[:TOP_N]


def total_filing_count():
    r = requests.get(BASE_URL, params={"$select": "count(*)"}, timeout=30)
    r.raise_for_status()
    return int(r.json()[0]["count"])


def main():
    since_date = date.today() - timedelta(days=WINDOW_DAYS)
    snapshot_date = date.today().isoformat()

    output = {
        "meta": {
            "sourceName": "Texas Department of Insurance -- Home and Auto Insurance Rate Filings (open data)",
            "sourceURL": "https://data.texas.gov/dataset/Home-and-auto-rate-filings/iubg-btfs",
            "state": "Texas",
            "snapshotDate": snapshot_date,
            "totalFilingsInFeed": total_filing_count(),
        },
        "auto": fetch_line(LINES["auto"], since_date),
        "home": fetch_line(LINES["home"], since_date),
    }
    print(f"auto: {len(output['auto'])} filings, home: {len(output['home'])} filings", file=sys.stderr)

    with open("data/published/tx_filings.json", "w") as f:
        json.dump(output, f, separators=(",", ":"))

    return {
        "dataset_id": "tx_filings",
        "domain_id": "auto",
        "kind": "rate_filings",
        "file_name": "tx_filings.json",
        "snapshot_date": snapshot_date,
        "source_kind": "auto",
        "source_name": output["meta"]["sourceName"],
        "source_url": output["meta"]["sourceURL"],
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
