# RoadLens India — Road Safety Observatory

An interactive analysis project covering **all reported road accidents**, with
seven connected web dashboards. Two-wheelers are one selectable road-user group.
React/TypeScript and ECharts provide animated charts; FastAPI and DuckDB calculate
all values from verified official MoRTH extracts. No runtime CDN or database account
is required. The primary interface is the web app; Tableau is a supporting handoff.

## Run on Windows

Install **Python 3.12** and [Git](https://git-scm.com/downloads), then open PowerShell:

```powershell
git clone https://github.com/Qaiser-Amin/RoadLens-India.git
cd RoadLens-India
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python server.py
```

If you already cloned it, stop the server with Ctrl+C, run `git pull --ff-only`, then
repeat the dependency installation and server command. No PowerShell activation or
execution-policy change is needed. If using another supported Python 3.12+ installation,
use its executable in place of `py -3.12`.

## Run on macOS or Linux

Install Python 3.12 and Git. On macOS, use Python from python.org or Homebrew rather
than an older system interpreter. In Terminal:

```sh
git clone https://github.com/Qaiser-Amin/RoadLens-India.git
cd RoadLens-India
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py
```

Open **http://localhost:8000** in your browser and keep the terminal running.
Press **Ctrl+C** to stop. Use `server.py --port 8001` if port 8000 is occupied.
Do not open an HTML file directly: the dashboard requires its API.

The production frontend is included in `web/dist`; **Node.js is needed only to
change/rebuild the frontend or run its legacy calculation tests**. Download ZIP from
GitHub also works: extract it, open a terminal there, and follow the commands starting
with virtual-environment creation. This serves the app locally; no public website has
been deployed. Windows/macOS commands are provided; see the QA record for actual
platforms tested.

## Explore the dashboards

| Dashboard | Explore |
| --- | --- |
| National overview | Accident, fatality, injury and fatal-crash KPIs, selectable India map, Top-N state ranking and trends |
| Accident types | Collision mechanisms and crash injury outcomes, separately scoped |
| Vehicles & road users | Victim groups, impacting vehicles, victim/opponent matrix and age/sex fatalities |
| Causes & conditions | Reported violations, weather, features, junctions, traffic controls and road environment |
| When & where | Monthly patterns, state/time-band heatmap, urban/rural and road-class comparisons |
| State priorities | Compare 2–5 states; inspect accident/severity set union and intersection; adjust thresholds and minimum denominator |
| Evidence & quality | Availability heatmap, definitions, source links/checksums and known source discrepancies |

Year, custom range, state, metric and Top-N controls are shared. Category selection
applies only to its compatible dataset. Select a map mark or focus it and press Enter;
select it again to clear. Charts have accessible view-data tables. Filters persist in
the URL, so a copied link reproduces a selection on the same running installation.
Reset restores the default 2023 all-state view. CSV exports contain the actual filtered
fact rows; PDF briefs preserve the selected scope and source caveats.

Charts transition in 300–350 ms. Optional year playback uses stable scales and stops
at the final prepared year; Pause and Motion off controls are available. System
reduced-motion preferences disable playback/animation.

## Data and interpretation

**6,732 rows, 17 datasets, 36 states/UTs; prepared annual coverage 2020–2024.**
2023 is the default because it has the broadest prepared detail. 2024 covers annual
totals, crash outcomes and victim road users; most other detail is prepared for 2023.
Selecting an unprepared period or incompatible measure shows **unavailable**, not zero.
An all-years selection is cumulative; unprepared years are identified explicitly.

Severity is deaths per 100 compatible accidents, using only matched reported pairs;
it is not a personal death probability or exposure-adjusted risk. Victim-user tables
have no accident denominator. Impacting-vehicle severity is disabled because the
source includes an unresolved anomaly. Junction/control tables cover a smaller
junction-related universe. Distinct facts are never joined to invent rainy-night
truck-crash statistics. The current map is illustrative, not authoritative historical
geography; see [map attribution](web/assets/GEOGRAPHY.md).

- [V2 data dictionary and source verification](docs/V2_DATA.md)
- [Methodology, findings and viva walkthrough](docs/METHODOLOGY.md)
- [QA results and limitations](docs/WEB_VALIDATION.md)
- [Research and build plan](docs/V2_BUILD_PLAN.md)
- [Original extract verification](docs/DATA_VERIFICATION.md)

## Develop and validate

Use Node.js **24 LTS** and Python 3.12. The npm lockfile and Python dependency pins
are included. `npm run dev` starts Vite; run the Python API on port 8000 in another
terminal. To rebuild the included production app:

```sh
npm ci
npm run build
npm test
```

Install the optional test dependencies in the same virtual environment. On Windows,
replace `.venv/bin/python` with `.venv\Scripts\python`:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m playwright install chromium
.venv/bin/python tools/check_web.py --browser chromium
.venv/bin/python analysis/reproduce.py
```

`check_web.py` starts and stops its own production server. Linux browser runners may
need `python -m playwright install --with-deps chromium`. Firefox/WebKit can be selected
with `--browser` after installing those engines. Native Safari/Edge testing and Tableau
acceptance remain separate. CI is configured for three OSes and three browser engines;
configuration alone is not proof that those remote jobs passed.

`analysis/RoadLens.ipynb` and `analysis/queries.sql` provide a reproducible analytical
walkthrough, including like-for-like comparisons and 27 priority-rule sensitivity cases.
The notebook requires a Jupyter installation/kernel using the project environment;
the equivalent script runs without Jupyter.

## Rebuild data from official reports

Prepared CSVs are committed, so downloads are unnecessary for normal use. Reproduction
requires Poppler `pdftotext` on PATH (`brew install poppler` on Mac; install Poppler for
Windows or use WSL). Downloads are verified against pinned SHA-256 hashes:

```sh
.venv/bin/python tools/fetch_morth.py
.venv/bin/python tools/extract_morth.py
.venv/bin/python tools/extract_v2.py
.venv/bin/python analysis/reproduce.py
```

Inspect reconciliation output and source exceptions before committing refreshed data.
Restart the API after refresh: each process serves an immutable startup snapshot.
PDFs are large and are excluded from Git. Runtime data is a small verified CSV snapshot
queried in memory by DuckDB; Parquet is unnecessary at this scale.

## Supporting Tableau deliverable

The web app's filtered CSVs and `data/analytics/facts.csv` can be opened in Tableau.
Filter `dataset` to exactly one family before aggregating; never sum the whole fact
file across datasets. See [the V2 Tableau handoff](docs/V2_TABLEAU.md).

The earlier `tableau/RoadLens-India-DRAFT.twbx` remains a generated **unverified draft**
using the original four data sources. It does not contain all V2 dashboards. It has
previously failed to load in Tableau; structural tests cannot verify native loading,
calculations, actions or publishing. Native Tableau acceptance is still outstanding:
[opening guide](tableau/README.md), [construction blueprint](docs/TABLEAU_BUILD.md),
[acceptance checklist](docs/ACCEPTANCE.md).
