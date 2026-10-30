# RoadLens India — Tableau draft

**Status: prior revisions failed to load in the user’s Tableau. The current revision is NOT RETESTED in Tableau Desktop/Public.**
The file is genuine Tableau workbook XML, packaged with CSV connections. It contains
editable worksheets, calculations, parameters, sets, and action definitions. It does
not contain screenshots. Passing XML checks does not prove that Tableau can compile,
render, or execute every definition. Version-specific repairs may be required.

## Open the draft

1. Download **RoadLens-India-DRAFT.twbx** and open it in a current Tableau Desktop or
   Tableau Public desktop application on Windows/macOS.
2. If Tableau reports an error, copy the complete error text and provide your Tableau
   version. This is the first required compatibility check; do not publish on the
   assumption that a generated workbook has passed it.
3. If asked to locate a CSV, extract the TWBX as ZIP and point the corresponding
   source to `Data/Totals.csv`, `Data/Vehicles.csv`, `Data/Causes.csv`, or `Data/Roads.csv`.
   The unpacked TWB and Data folder can also be opened together.
4. Open the **1 National Overview** dashboard. At default Year=2023, State=All,
   Metric=Fatalities, Top N=10, the source counts should be 480,583 accidents and
   172,890 fatalities. Coverage is partial for fatalities because the report uses an
   unqualified dash for Lakshadweep; that cell is retained as unavailable.
5. Work through the checks below, save a new tested TWBX, and record the exact Tableau
   version and outcomes in `docs/ACCEPTANCE.md` before publishing.

The separate `RoadLens-India-DRAFT.zip` bundle includes the packaged/unpacked workbook,
data, this guide, the build manifest and provenance. Keep their relative paths intact
when opening the TWB instead of TWBX.

## What the draft defines

- Three 1200×800 dashboards: National Overview; Two-Wheeler Safety; Causes and Risk
  Factors. Device/browser readability is untested.
- 26 worksheets: national and two-wheeler count/severity KPI cards, coverage and
  availability messages, India state map, state rankings, trends, road-user category
  comparison, two-state trend comparison, violation/road-type comparisons, combined
  risk ranking, navigation marks and a reset mark.
- Seven shared parameters: Year, State, Metric, Top N, High Severity Threshold,
  Compare A and Compare B.
- Shared Year and State parameters drive boolean **context filters** on every
  analytic sheet. These are parameter-driven filters rather than independently
  related quick filters across four sources. Do not add unrelated quick filters
  without considering reset scope and compatible grain.
- Top-N state filters use the current measure and selected context; the High
  Accidents set always ranks accident counts. High Severity uses complete paired
  counts and the threshold parameter; their native combined set uses intersection.
  The Combined Risk Ranking sheet displays the union of the two sets; the intersection
  remains a separate risk class. It is not truncated to Top-N by the displayed measure.
- Four state-selection parameter actions (map and state rankings) change the shared
  State parameter. Clearing a selection is configured to assign All. Native
  cross-dashboard behavior and multi-mark selection handling require testing.
- Seven parameter actions on Reset assign the complete default parameter values.
  Reset clears these parameter-driven filters; if extra quick filters are introduced
  later, use Tableau Revert or extend the reset workflow accordingly.
- Three navigation actions target the three dashboards. If a Tableau version exposes
  the navigation action in a mark's context menu, use that menu or worksheet tabs
  while repairing/configuring native Navigation buttons.
- Map/statistic tooltips and titles reference current fields/parameters. Native
  formatting, special values, and dynamic substitution require visual verification.

**State is a single-state selector (or All).** Compare A/B provide two-state comparison
on the historical comparison sheet. The global State filter also applies there: use
State=All to compare different A/B states; a single selected state intersects those
choices. Year=All shows four reporting years; unavailable 2020–2021 two-wheeler values
remain gaps. The national trend intentionally shows one point for a single year.

## Data and calculation rules

Each data source remains separate, at year × state × category grain. Each packaged
CSV has the current 36 reporting state names × four reporting years × its own
categories. Existing observations and their source IDs are copied unchanged. Additional
unreported combinations have blank measures, blank source IDs, and explicit
`Record Status = Not reported / not applicable`. They are not synthetic observations.
The draft uses pre-expanded CSVs instead of a native join to a shared scaffold, so
there are no cross-fact joins, repeated totals, or multiplicative relationships.

Accidents and fatalities remain counts; severity is 100 × sum of paired fatalities /
sum of paired accidents and is unavailable for a zero/absent denominator. The risk
class is calculated at the displayed state's aggregate grain, including All-years
pooled counts. Incomplete paired states are unclassified, rather than low risk.

Road-user fatality categories include pedestrians. All vehicle/road-user accident
counts are blank because Annexure 29 supplies no compatible denominator; their
accident/severity KPIs and charts must show unavailable. Two-wheeler fatalities total
74,897 in 2022 and 77,539 in 2023. Do not fill the blanks from impacting-vehicle tables.
See `data/input/sources.json` and `docs/DATA_VERIFICATION.md` for source definitions,
including Kerala category attribution and the J&K footnote override.

## Validation performed here

- 17 automated structural/data and loader-regression tests passed: archive integrity, workbook/data path
  portability, field and parameter references, shared context filters, dashboard and
  action references, native set definitions, exact observation preservation, missing two-wheeler denominators, and union-based risk-sheet membership.
- Both TWB and TWBX were read by Tableau's Python Document API as five data sources
  (four CSV sources plus Parameters) and 26 worksheets. This is document parsing,
  **not Tableau Desktop compatibility or calculation compilation**.
- The previous nine data-pipeline tests remain passing. The nine JavaScript tests and
  Chromium validation concern the separate web app; they do not test this workbook.

## Required Tableau checks — all NOT RUN

1. Open without schema/connection errors; save and reopen to confirm upgrade/migration.
2. Confirm four CSV sources, all calculated fields, semantic roles and null data types.
3. Resolve every state/UT location with Country=India, especially Ladakh, Delhi and
   the merged Dadra and Nagar Haveli and Daman and Diu. Confirm historical-boundary
   limitations. Online Tableau geocoding/background map access may be required.
4. Check parameter cards, dynamic title/tooltip tokens and readable KPI number
   formatting; use special-value text or availability sheets for null marks.
5. Year changes must affect all relevant sheets. State map/ranking selection must
   change the shared State parameter and persist when switching dashboards.
6. Metric switches must change chart values/units; Top 5/10/15 must change state
   rankings. Verify null exclusion and the desired treatment of rank ties.
7. Verify context-filter order, both native sets, their intersection and risk colors.
   Set membership should recompute with year/state context, Top N and threshold.
8. Check A/B comparison in Year=All, State=All. Selecting an unavailable reporting
   year should show informative unavailable messages, not zero values.
9. Verify all navigation and reset actions. Test reset after changing all seven
   parameters and selecting a map state. Tableau Revert is the recovery fallback.
10. Inspect the 1200×800 dashboard on a 1366×768 laptop and other required devices;
    adjust tiled/floating layout, font sizes, legends and device layouts as needed.
11. Publish the tested workbook with appropriate permissions and repeat acceptance
    checks in the published browser view. No publishing has been performed here.

Send the full Tableau error text and version if step 1 fails. Further corrections can
be made to the generator without changing any verified input data.

## Rebuild

From the repository root, using Python 3.12+:

```sh
python tools/build_tableau.py
python -m unittest discover -s tests -v
```

The generator and structural tests use the standard library and existing verified
inputs. Tableau's Document API was used as an additional validation tool; it is not a
runtime dependency. `build-manifest.json` records actual generation scope and source
hashes. The original manual construction blueprint remains in docs/TABLEAU_BUILD.md.

XML structure was informed by saved workbook examples in the public
`tableau/document-api-python` and `DataWithBaraa/tableau-ultimate-course` repositories.
No example workbook content, sample records, server connections or credentials are
included. This project does not claim an official supported Tableau workbook authoring
API or a Tableau XSD validation guarantee.

## Reported Windows load error D2E8DA72

Two prior revisions failed to load in the user's Tableau installation. The current
revision is a compatibility repair based on the complete error text, not a claim of
successful Desktop execution.

Retained repairs from the first error report:

- Required `source-build` metadata is present. This is a compatibility header from
  saved XML, not a claim that Tableau Desktop authored the generated file.
- Parameter actions use `min` rather than the invalid `none` aggregation. State
  selection is a single-state control; selecting multiple marks uses the minimum
  state name. Constant reset values are unchanged by the minimum aggregation.
- Action datasource declarations/dependencies precede navigation and parameter actions.
- Native sets are defined at datasource scope rather than inside worksheet dependencies.
- Clear-selection actions use the supported `clear-option` element.

Repairs based on the second, complete error report:

- Removed all 58 optional `simple-id` elements rejected from worksheets, dashboards
  and windows. Actions still identify sheets by name and dashboard zones by numeric ID.
- Restored six `sort class="computed"` elements. The user's reported view content model
  names `sort` and rejects `computed-sort`, regardless of the application's release.
- Removed optional `explain-data` and `explanation-types` metadata, which the reported
  workbook content model rejects. Dashboard calculations and source data are unchanged.

**The earlier community-hosted 2026.1 XSD check did not match the actual loader.** Its
PASS result for an earlier package is superseded in `schema-validation.json` and must
not be used as evidence that this workbook opens. The record binds the current package
hash and records known errors/repairs. Current validation consists of targeted loader
regressions, field/action/path references and preservation of verified observations.

Download the new TWBX or pull the latest commit. If another error appears, send its
complete text. A small `.twb` saved directly from the same Tableau installation would
also provide a reliable native-format reference; the precise version/build appears
under Help → About Tableau. Avoid reopening a copy from an earlier ZIP download.

The optional validator remains available for a schema that actually matches the
installed workbook format (requires `lxml` for validation only):

```sh
python tools/validate_tableau_schema.py --schema /path/to/matching-tableau-schema.xsd
```

Keep any imported XSD files beside that schema. The validator disables network
resolution. Even a matching XSD cannot compile formulas or test Tableau interactions.
