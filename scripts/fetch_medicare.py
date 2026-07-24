#!/usr/bin/env python3
"""Medicare Advantage: real, live fetch from CMS's annual Landscape file.

Source: cms.gov's Medicare Advantage & Part D Landscape zip (the same
publisher and file family CMS uses for the Part C/D program overall --
distinct from the QHP Landscape file already used for the Health/ACA
marketplace domain). Filters to "MA" and "MA-PD" contract category types
(standard Medicare Advantage plans open to any MA-eligible beneficiary --
excludes Special Needs Plans, which require specific eligibility, and
standalone PDP/Cost plans, which aren't MA). Produces medicare.json keyed
by state-county, mirroring the county-keyed shape ContentDatabase.swift/.kt
already knows how to parse for Health, so the app-side pattern is familiar
even though this is a new domain.
"""
import csv
import io
import json
import re
import sys
import zipfile
from datetime import date

import requests

LANDSCAPE_PAGE = "https://www.cms.gov/medicare/coverage/prescription-drug-coverage"
INCLUDED_CATEGORIES = {"MA", "MA-PD"}


def fetch_zip_url():
    r = requests.get(
        LANDSCAPE_PAGE,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; insurance-data-pipeline/1.0)"},
    )
    r.raise_for_status()
    # CMS names this file "cyYYYY-landscape-YYYYMM.zip"; the exact month
    # code changes with each quarterly-ish revision, so find it rather
    # than hardcode it.
    matches = re.findall(r'href="(/files/zip/cy\d{4}-landscape-\d+\.zip)"', r.text, re.IGNORECASE)
    if not matches:
        raise RuntimeError("no landscape zip link found on the CMS page")
    return "https://www.cms.gov" + matches[0]


def parse_money(cell):
    if cell is None:
        return None
    s = str(cell).strip().lstrip("$").replace(",", "").strip()
    if not s or s.lower() == "not applicable":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_stars(cell):
    if cell is None:
        return None
    s = str(cell).strip()
    if not s or s.lower() == "not applicable":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def download_csv(zip_url):
    r = requests.get(zip_url, timeout=300)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError("no .csv file found inside the downloaded landscape zip")
        return zf.read(csv_names[0])


def build_counties(csv_bytes):
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    counties = {}
    for row in reader:
        category = row.get("Contract Category Type", "").strip()
        if category not in INCLUDED_CATEGORIES:
            continue
        if row.get("Sanctioned Plan", "").strip().lower() == "yes":
            continue  # under sanction -- not a real option a consumer can enroll in today

        state = row.get("State Territory Abbreviation", "").strip()
        county_name = row.get("County Name", "").strip()
        if not state or not county_name or county_name.lower() == "all counties":
            continue

        part_c_premium = parse_money(row.get("Part C Premium"))
        consolidated_premium = parse_money(row.get("Monthly Consolidated Premium (Part C + D)"))
        if part_c_premium is None:
            continue  # incomplete row -- skip rather than fabricate a missing premium

        key = f"{state}-{county_name}"
        county = counties.setdefault(key, {
            "state": state, "county": county_name,
            "totalPlans": 0, "totalIssuers": 0, "zeroPremiumPlans": 0,
            "_partCSum": 0.0, "plans": [], "_issuers": set(),
        })
        issuer = row.get("Organization Marketing Name", "").strip()
        county["plans"].append({
            "issuer": issuer,
            "name": row.get("Plan Name", "").strip(),
            "type": row.get("Plan Type", "").strip(),
            "partCPremium": part_c_premium,
            "consolidatedPremium": consolidated_premium,
            "starRating": parse_stars(row.get("Overall Star Rating")),
        })
        county["_issuers"].add(issuer)
        county["totalPlans"] += 1
        county["_partCSum"] += part_c_premium
        if part_c_premium == 0.0:
            county["zeroPremiumPlans"] += 1

    for county in counties.values():
        county["totalIssuers"] = len(county.pop("_issuers"))
        total = county["totalPlans"]
        county["avgPartCPremium"] = round(county.pop("_partCSum") / total, 2) if total else 0.0
        # Cap the plan list per county -- some large metro counties carry
        # 100+ plans, and the app only ever needs "cheapest few" + honest
        # counts, not every row, to stay a reasonable bundle size.
        county["plans"] = sorted(county["plans"], key=lambda p: p["partCPremium"])[:25]

    return counties


def main():
    zip_url = fetch_zip_url()
    print(f"Downloading {zip_url}", file=sys.stderr)
    csv_bytes = download_csv(zip_url)
    counties = build_counties(csv_bytes)
    total_plans = sum(c["totalPlans"] for c in counties.values())
    print(f"Parsed {len(counties)} counties, {total_plans} MA/MA-PD plans", file=sys.stderr)

    snapshot_date = date.today().isoformat()
    with open("data/published/medicare.json", "w") as f:
        json.dump(counties, f, separators=(",", ":"))

    return {
        "dataset_id": "medicare",
        "domain_id": "medicare",
        "kind": "medicare_advantage_plans",
        "file_name": "medicare.json",
        "snapshot_date": snapshot_date,
        "source_kind": "auto",
        "source_name": "CMS Medicare Advantage & Part D Landscape File, CY2026 -- MA and MA-PD contract categories, full national file",
        "source_url": "https://www.cms.gov/medicare/coverage/prescription-drug-coverage",
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
