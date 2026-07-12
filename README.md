# insurance-data

Refreshed data for the [Insurance Hub](http://equalinformation.com/insurance-site/) app's on-device "Refresh data" button (Settings tab). This repo holds no app code -- just the pipeline that fetches/parses public insurance data sources and publishes the result as static JSON files via GitHub Pages, and the manually-curated seed files for sources that can't be scripted yet.

Why this exists: the app can't parse a 58MB CMS spreadsheet or a WAF-blocked survey site on-device for every user. This pipeline does that fetching/parsing once, on a schedule, and publishes the already-clean result so the app's refresh button is just a plain HTTPS GET.

## Published output

`https://bpupadhyaya.github.io/insurance-data/manifest.json` lists every dataset: which domain it feeds, a sha256 (so the app can tell if it actually changed), snapshot date, source, and whether it's `"auto"` (this pipeline fetched it live this run) or `"manual"` (a curated seed -- see below).

Per-domain files (`qhp.json`, `zip_map.json`, `tx_filings.json`, etc.) are in the exact JSON shape the app's `ContentDatabase.swift`/`.kt` importers already parse -- publishing here doesn't require any app-side parsing changes, only where the file comes from.

## Datasets

| dataset | domain | source_kind | source |
|---|---|---|---|
| `qhp` | health | **auto** | CMS QHP Landscape PY2026 (DKAN API + xlsx) |
| `zip_map` | geography | **auto** | Census 2020 ZCTA-to-county relationship file |
| `tx_filings` | auto | **auto** | data.texas.gov Socrata API (real rate filings) |
| `nfip` | flood | manual | OpenFEMA `FimaNfipPolicies` -- real API, but 80M+ raw policy transactions with no server-side aggregation; reducing that to zone-level averages needs its own design, not a weekly CI job |
| `crop` | crop | manual | USDA RMA discovery-period bulletin (HTML, bulletin number changes yearly -- not a stable API) |
| `workerscomp` | workerscomp | manual | Oregon DCBS biennial PDF report |
| `autohome` | auto/home/renters | manual | NAIC PDF report + MoneyGeek (WAF-blocks scripted requests) |
| `life` | life | manual | MoneyGeek (WAF-blocked) |
| `pet` | pet | manual | NAPHIA member listing page (no API) |
| `motorcycle` | motorcycle | manual | MoneyGeek (WAF-blocked) |
| `umbrella` | umbrella | manual | Forbes Advisor / Chubb study (no API) |
| `travel` | travel | manual | Squaremouth marketplace listing page (no API) |

`manual` datasets are still real, cited, and dated -- just not automatically refreshable given their source format. Updating them means re-running the same manual research pass and replacing the file under `data/seeds/`.

### Why `tx_filings` is Texas-only (researched 2026-07-12)

The obvious next step for `tx_filings` is "do this for every state" -- checked whether California, Florida, Washington, Oklahoma, Colorado, New York, Illinois, and Pennsylvania publish rate filings the same way Texas does (a structured, scriptable open-data endpoint with company name, percent change, filing id, and date). None of them do. Every one of those eight states routes public access through one of two non-scriptable paths: NAIC's generic `filingaccess.serff.com/sfa/home/<STATE>` portal (a login/search UI, not an API), or a state-run search tool (e.g. Florida's IRFS, California's rate-filing-lists page) with no JSON/CSV endpoint behind it. Illinois publishes company/producer *registries* on its own CKAN-based data.illinois.gov portal, but not rate filings specifically.

Texas's `data.texas.gov/resource/iubg-btfs` Socrata dataset is a genuine exception -- TDI chose to also mirror SERFF filing data onto Texas's own open-data portal, which is not something most states' DOIs do. Adding more states here isn't a matter of writing more fetch scripts against a known pattern; it would require finding an actual equivalent open feed per state first, which as of this check doesn't exist for the states above. Worth re-checking periodically (a state could stand one up), but not assumed.

Provider directories, plain-language domain info, and Learn-tab articles are reference content maintained directly in the app's `ContentDatabase` (not part of this pipeline) -- they change far less often than priced data and aren't sourced from a periodically-updated report.

## Running locally

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/build_manifest.py
```

Output lands in `data/published/` (gitignored -- this is build output, not checked in; the GitHub Actions workflow publishes it to Pages on every run).

## Schedule

`.github/workflows/refresh-data.yml` runs **hourly** (and on-demand via `workflow_dispatch`), regenerates every dataset, and deploys to GitHub Pages.

Why hourly: this repo is public, so GitHub Actions minutes are free regardless of cadence — only private repos meter minutes. The real constraint isn't cost, it's that most of the underlying sources (CMS QHP Landscape, Census ZCTA, NAIC reports) don't publish sub-daily at all, so polling them more than hourly would just re-fetch identical data. Hourly is the useful ceiling: it means a genuinely new Texas SERFF filing, or a fix to this pipeline itself, lands in the published manifest within the hour instead of waiting up to a week. Each run takes well under a minute (build ~47s, deploy ~9s per the Phase 3 verification), so hourly costs nothing extra either in money or in real GitHub load.
