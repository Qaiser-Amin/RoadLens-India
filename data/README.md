# Verified data contract

The input CSV files now contain extracts from official MoRTH 2022 and 2023 reports.
See `docs/DATA_VERIFICATION.md` for exact coverage, reconciliation evidence and footnotes.
Do not use test fixtures as data. PDFs are retained in `data/sources/` locally and are
excluded from Git because of size; `tools/fetch_morth.py` reproduces their downloads
with pinned SHA-256 verification. Extracts can populate the Tableau workbook, which
still requires manual construction and interaction testing.
The program checks structure and provenance declarations; it cannot certify authenticity.

Run from the repository root:

```sh
python tools/prepare_tableau.py
```

Each file uses the same columns, at a different grain:

| File | Unique grain | category |
| --- | --- | --- |
| state_totals.csv | year, state | All |
| vehicle_categories.csv | year, state, vehicle category | Road-user category (includes pedestrians); Two-wheelers, etc. |
| causes.csv | year, state, reported cause | Source category; preserve cause attribution definition |
| road_types.csv | year, state, road type | Source category |

Use canonical state names from `tools/prepare_tableau.py`. Preserve reporting boundaries:
do not merge Jammu and Kashmir/Ladakh or historical union territories across years.
Exclude India totals from state records. Blank means not reported; zero means explicitly
reported zero. Never infer accidents from fatalities. Do not duplicate national-only data
into states; such tables need a separate national source with no state filter. Do not
infer two-wheeler accident counts from counts of vehicles involved. “Two-wheelers” must
mean the same thing across years; record definition changes and compare only compatible
periods. Accident cause is a reported attribution, not a causal estimate.

Add one sources.json object per input source/table containing:
`source_id`, `table`, `title`, `url` (official HTTPS source), `locator` (page/table or approved
query/version), `retrieved_on` (ISO date), `definition`, `coverage`, `sha256` (original
archived document/query-export hash), and `verified` (boolean). Set verified=true only
after the extraction has been checked against its source with documented evidence. Record footnotes, excluded
states, boundary changes, and category comparability in definition/coverage.
A non-secret provenance URL for an Oracle export can reference the approved query's
versioned repository page; never include a database password or connection string.

Before verification: reconcile reported state counts and table totals; visually spot-check
at least three states and every year; verify units, missing-value symbols, and categories.
Do not require category totals to equal state totals unless source definitions establish
mutually exclusive, exhaustive categories. Fatalities may exceed accidents.

Outputs remain separate. `scaffold.csv` contains possible state-year-category combinations
for explicit missing-data displays, including administrative units that may not apply to
historical years. Label unmatched rows “Not reported / not applicable”; never interpret
scaffold rows as evidence that a jurisdiction existed in that year. Empty category files
mean that component is unavailable, not zero.
