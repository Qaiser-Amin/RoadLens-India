# RoadLens India

A working, responsive road-safety analytics web app using official MoRTH extracts.
Three connected views: National Overview, Two-Wheeler Safety, and Causes & Risk
Factors. This web app complements the Tableau specification; a Tableau workbook
now has a generated draft in `tableau/RoadLens-India-DRAFT.twbx`; opening, calculation
compilation and interaction verification still require Tableau Desktop.

## Run on Windows or macOS

Install **Python 3.12 or newer** from [python.org](https://www.python.org/downloads/)
and [Git](https://git-scm.com/downloads). The web app uses only the Python standard
library: no pip packages, Node.js, npm installation, Oracle connection, or Tableau
installation is needed to run it. Verified CSVs and map assets are already included.

### Windows (PowerShell)

Open PowerShell in the folder where you want to keep the project:

```powershell
git clone https://github.com/Qaiser-Amin/RoadLens-India.git
cd RoadLens-India
py -3 --version
py -3 server.py --host 127.0.0.1 --port 8000
```

Check that the displayed Python version is 3.12 or newer. If `py` is unavailable but
Python is installed and on PATH, use `python` instead. Reopen PowerShell after
installing Python or Git so newly installed commands are available.

### macOS (Terminal)

Install Python from python.org rather than relying on an older system Python. Open
Terminal in the folder where you want to keep the project:

```sh
git clone https://github.com/Qaiser-Amin/RoadLens-India.git
cd RoadLens-India
python3 --version
python3 server.py --host 127.0.0.1 --port 8000
```

Check that the displayed Python version is 3.12 or newer. If macOS prompts for
Command Line Tools when running Git, complete that installation and retry Git.

### View and stop the app

With the terminal still running, open your browser and enter `http://localhost:8000`.
Keep that terminal open while using the app. Press **Ctrl+C** in the terminal to stop
it. If port 8000 is occupied, use `--port 8001` and browse to `http://localhost:8001`.

If you already cloned the project, run `git pull --ff-only` from its folder before
starting it. You can also use GitHub **Code → Download ZIP**, extract it, open a
terminal in the extracted folder, and run the appropriate server command above.
Do not open `web/index.html` directly: the dashboard requires the local data API.
If the dashboard does not load, check the terminal output and verify that `/api/data`
on the same local port returns JSON.

This is a local development server; running it does not publish a website. The
prepared cloud environment can still start it with `python server.py --port 8000`
from `/workspace/RoadLens-India`.

### Open the Tableau draft (Windows and macOS)

Install a current Tableau Desktop or Tableau Public desktop application, then open
`tableau/RoadLens-India-DRAFT.twbx`. It includes the CSV data; the Python server is not
needed for Tableau. If double-clicking does not select Tableau, use Tableau's
**File → Open** command. See [the draft opening guide](tableau/README.md) for data-path
repairs and acceptance checks.

**The Tableau workbook is an untested generated draft.** XML/data structural checks
passed here; compatibility, calculation compilation, rendering, interactions and
publishing must be verified inside Tableau. The working web app and its browser tests
are separate from that draft. Windows and macOS startup instructions are documented;
this cloud environment runs Linux and has not tested those operating systems directly.

## Explore

- Shared year, multi-state, measure and Top-N controls persist across navigation.
- Click a state on the map, or focus it and press Enter, to update the shared selection.
  Click the same single-selected state again to clear it.
- Select multiple states in State / Union Territory to compare two-wheeler trends.
- Choose All years to show 2020–2023 trends. A single selected year shows one point.
- Switch between accidents, fatalities, and weighted severity. Nulls never become zero.
- Causes & Risk Factors shows reported violations, road types, and the intersection
  of the Top-N accident set with the high-severity set. The table includes every state
  in either set, with overlapping states first. Adjust the severity threshold.
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

Generate the Tableau draft with `python tools/build_tableau.py`. Its nine structural/data
tests are included in the Python test command. They do not test the Tableau engine.
