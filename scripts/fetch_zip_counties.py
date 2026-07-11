#!/usr/bin/env python3
"""ZIP -> county crosswalk: real, live fetch from the Census Bureau's 2020
ZCTA-to-county relationship file. Produces zip_map.json in the exact
"ZIP": "ST-CountyName" shape the app already parses. A ZCTA can straddle
multiple counties; each ZIP is assigned to whichever county covers the
most land area of that ZCTA (matches how the bundled snapshot was built).
"""
import csv
import io
import json
import re
import sys
from datetime import date

import requests

RELATIONSHIP_FILE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
    "tab20_zcta520_county20_natl.txt"
)

STATE_ABBR_BY_FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "72": "PR",
}

# Strip the county-equivalent type suffix Census appends to NAMELSAD --
# the app's county names/IDs never include it (matches the bundled
# snapshot's "OH-Franklin", "PR-Aguadilla" style, not "OH-Franklin County").
SUFFIX_RE = re.compile(
    r"\s+(County|Parish|Borough|Census Area|Municipio|Municipality|"
    r"City and Borough|city)$"
)


def strip_suffix(name):
    return SUFFIX_RE.sub("", name)


def main():
    r = requests.get(RELATIONSHIP_FILE_URL, timeout=120)
    r.raise_for_status()
    text = r.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter="|")

    best_for_zip = {}  # zip -> (area_land_part, county_fips, county_name)
    for row in reader:
        zcta = row["GEOID_ZCTA5_20"]
        county_fips = row["GEOID_COUNTY_20"]
        if not zcta or not county_fips:
            continue
        state_fips = county_fips[:2]
        if state_fips not in STATE_ABBR_BY_FIPS:
            continue  # territory outside the app's 50-states+DC+PR scope
        area_part = int(row["AREALAND_PART"] or 0)
        current = best_for_zip.get(zcta)
        if current is None or area_part > current[0]:
            best_for_zip[zcta] = (area_part, county_fips, row["NAMELSAD_COUNTY_20"])

    zip_map = {}
    for zcta, (_, county_fips, namelsad) in best_for_zip.items():
        state_abbr = STATE_ABBR_BY_FIPS[county_fips[:2]]
        county_name = strip_suffix(namelsad)
        zip_map[zcta] = f"{state_abbr}-{county_name}"

    print(f"Built {len(zip_map)} ZIP -> county mappings", file=sys.stderr)

    snapshot_date = date.today().isoformat()
    with open("data/published/zip_map.json", "w") as f:
        json.dump(zip_map, f, separators=(",", ":"), sort_keys=True)

    return {
        "dataset_id": "zip_map",
        "domain_id": "geography",
        "kind": "zip_county_crosswalk",
        "file_name": "zip_map.json",
        "snapshot_date": snapshot_date,
        "source_kind": "auto",
        "source_name": "US Census Bureau 2020 ZCTA-to-County Relationship File",
        "source_url": RELATIONSHIP_FILE_URL,
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
