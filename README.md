# RoadLens India

A working, responsive road-safety analytics web app using official MoRTH extracts.
Three connected views: National Overview, Two-Wheeler Safety, and Causes & Risk
Factors. This web app complements the Tableau specification; a Tableau workbook
now has a generated draft in `tableau/RoadLens-India-DRAFT.twbx`; opening, calculation
compilation and interaction verification still require Tableau Desktop.

## Run

Python 3.12+; the application has no third-party runtime dependencies or CDN requests.

```sh
cd /workspace/RoadLens-India
python server.py --port 8000
```

Open port 8000 through your development environment, or use localhost port 8000 on
your own machine. The server uses the verified CSVs already included in `data/input`.
It serves the HTML/CSS/JavaScript app, the data API and source CSV downloads. It is a
local development server; use an approved production server/reverse proxy to deploy.

## Explore

- Shared year, multi-state, measure and Top-N controls persist across navigation.
- Click a state on the map, or focus it and press Enter, to update the shared selection.
  Click the same single-selected state again to clear it.
- Select multiple states in State / Union Territory to compare two-wheeler trends.
- Choose All years to show 2020–2023 trends. A single selected year shows one point.
- Switch between accidents, fatalities, and weighted severity. Nulls never become zero.
- Causes & Risk Factors shows reported violations, road types, and the intersection
  of the Top-N accident set with the high-severity set. Adjust the severity threshold.
- Reset restores the default dashboard, 2023, all states, fatalities, Top 10, and
  threshold 50. Export downloads the complete verified source CSV for the current
  dashboard (not only the filtered marks).
- Data Sources & Methodology explains definitions, coverage and source limitations.

State totals and road types cover 2020–2023; road-user fatalities and violations cover
2022–2023. There are 1,656 input records for 36 reporting states/UTs. Road-user tables
have no accident denominator, so two-wheeler accident and severity views explicitly
show unavailable. Severity uses only paired observations and reports partial coverage.
The illustrative map uses current third-party geometry, not official historical
boundaries. Attribution is in `web/assets/GEOGRAPHY.md`.

## Validate

```sh
npm test
python -m unittest discover -s tests -v
```

Node is needed only for JavaScript calculation tests. For browser smoke tests, install
Python Playwright and its Chromium browser, start the server, then run
`python tests/browser_smoke.py`. In the prepared cloud environment use
`PLAYWRIGHT_BROWSERS_PATH=/workspace/.roadlens-browsers python tests/browser_smoke.py`.
See [web validation](docs/WEB_VALIDATION.md) for actual test outcomes.

## Sources and Tableau

- [Data contract](data/README.md) and [source verification](docs/DATA_VERIFICATION.md)
- [Generated Tableau draft: opening and validation guide](tableau/README.md)
- [Tableau manual construction blueprint](docs/TABLEAU_BUILD.md)
- [Tableau acceptance checklist — still manual](docs/ACCEPTANCE.md)

Reproduce data preparation:

```sh
python tools/fetch_morth.py
python tools/extract_morth.py
python tools/prepare_tableau.py
```

Extraction requires Poppler `pdftotext`. The PDF downloader checks pinned SHA-256
hashes. The pipeline preserves separate reporting grains. No synthetic observations
or static screenshots are used in the application.

Generate the Tableau draft with `python tools/build_tableau.py`. Its eight structural/data
tests are included in the Python test command. They do not test the Tableau engine.
