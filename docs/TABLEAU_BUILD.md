# RoadLens India — Tableau construction specification

## Status and prerequisites

No existing .twb/.twbx was found. No Tableau Desktop, Server connection, or Tableau
control tool is available in this environment. This is a construction specification,
not a generated or tested Tableau workbook. Verified MoRTH extracts are now bundled
under `data/input/`; see `docs/DATA_VERIFICATION.md` for limitations.
All Tableau construction, publishing, and interaction acceptance checks below remain
manual. Use a current supported Tableau Desktop release (or Tableau Public only for
public, non-sensitive official extracts). Do not substitute screenshots for sheets.

1. Review the supplied official MoRTH extracts per `data/README.md`, and run
   `python tools/prepare_tableau.py` from the repository root.
2. Check `data/tableau/validation.json`, reconcile source tables, and archive provenance.
3. Create `RoadLens-India.twbx`. Save sources, workbook, version, and verification date.
   Build Desktop first; do not claim browser/device behavior until tested after publishing.

## Data model: four compatible sources, never a flattened fact join

Create four independent Tableau data sources named **Totals**, **Vehicles**, **Causes**,
and **Roads**. Use generated CSVs. Do not join the four fact files to one another or
union them into additive totals: the same deaths can appear in several source tables.

For each data source, inside one logical table use a physical left join:

- left: scaffold.csv, with a data-source filter `table` equal to state_totals,
  vehicle_categories, causes, or road_types respectively;
- right: the matching fact CSV;
- join on integer year, string state, string category (all three);
- use the **left/scaffold** year, state, category fields as dimensions everywhere;
- use only the right/fact accidents and fatalities as measures.

Name dimensions `Year`, `State`, `Category`, and measures `Accidents`, `Fatalities`.
Keep `source_id` for auditing. Year is a discrete whole number, not a continuous date.
Do not filter out null fact rows: they drive missing-data messages.
The scaffold is not an administrative-boundary history. Unmatched states mean
“Not reported / not applicable”, never zero or proof of statehood.

In Edit Relationships (filter relationships across data sources), explicitly map Year
and State from Totals to each other source. Test each mapping; identical names alone
are insufficient. For Year and State quick filters choose **Apply to Worksheets → All
Using Related Data Sources**. Include every KPI and availability sheet in scope. Keep
category filters local to their own source. Do not propagate cause/category/road filters
to other sources, and do not apply a vehicle category to national totals.
If a category source has zero rows, do not build fictitious categories: display a text
sheet “Vehicle/cause/road-type statistics unavailable in the supplied extracts”.

Choose State → Geographic Role → State/Province; Edit Locations → Country/Region →
India. Resolve all locations manually and inspect Delhi, union territories, Ladakh,
and historical Jammu and Kashmir. Never assign a centroid to an unmatched state just
to hide a map warning. Use an authenticated, licensed boundary source if Tableau's
built-in geography cannot resolve historical boundaries; disclose unresolved locations.
Maintain the state ranking as an accessible alternative to map selection.

## Shared parameters and calculated fields

Create workbook parameters:

| Name | Type / allowed values | Default |
| --- | --- | --- |
| Metric | String list: Accidents, Fatalities, Severity | Fatalities |
| Top N | Integer list: 5, 10, 15 | 10 |
| High Severity Threshold | Float, >= 0 | 50 |

The threshold is a transparent **demonstration rule**, deaths per 100 reported
accidents, not a scientific or government designation of risk. Document any change.
Severity is not population risk or crash probability. It can exceed 100.

Create these fields in each source, preserving the same names. These formulas assume
the renames above. Nulls from the left join are intentional.

```tableau
// Paired Accidents — row level, consistent denominator for severity
IF NOT ISNULL([Accidents]) AND NOT ISNULL([Fatalities])
THEN [Accidents] END

// Paired Fatalities
IF NOT ISNULL([Accidents]) AND NOT ISNULL([Fatalities])
THEN [Fatalities] END

// Severity — aggregate, never AVG of state severity
IF SUM([Paired Accidents]) > 0 THEN
  100.0 * SUM([Paired Fatalities]) / SUM([Paired Accidents])
END

// Selected Measure — aggregate
CASE [Metric]
WHEN 'Accidents' THEN SUM([Accidents])
WHEN 'Fatalities' THEN SUM([Fatalities])
WHEN 'Severity' THEN [Severity]
END

// Metric Available — row level
CASE [Metric]
WHEN 'Accidents' THEN NOT ISNULL([Accidents])
WHEN 'Fatalities' THEN NOT ISNULL([Fatalities])
WHEN 'Severity' THEN NOT ISNULL([Accidents]) AND NOT ISNULL([Fatalities])
END

// Reporting Status — aggregate, valid per state or total
IF COUNTD(IF [Metric Available] THEN [State] END) = 0 THEN
  'Unavailable: not reported / not applicable'
ELSEIF SUM(IIF([Metric Available], 0, 1)) > 0 THEN
  'Partial coverage: reported observations only'
ELSE 'Available in supplied extract' END

// Severity Status — aggregate
IF COUNT([Paired Accidents]) = 0 THEN 'Unavailable: paired counts not reported'
ELSEIF SUM([Paired Accidents]) = 0 THEN 'Unavailable: zero accident denominator'
ELSEIF COUNT([Paired Accidents]) < COUNT([State]) THEN
  'Partial coverage: paired observations only'
ELSE 'Available in supplied extract' END

// Year Label — aggregate
IF MIN([Year]) = MAX([Year]) THEN STR(MIN([Year]))
ELSE STR(MIN([Year])) + '–' + STR(MAX([Year])) END

// State Label — aggregate
IF COUNTD([State]) = 1 THEN MIN([State])
ELSE STR(COUNTD([State])) + ' selected states / UTs' END

// Dynamic Title — aggregate
[Year Label] + ' | ' + [State Label] + ' | ' + [Metric]

// Rank — aggregate table calculation
RANK_UNIQUE([Selected Measure], 'desc')

// In Top N — table calculation
[Rank] <= [Top N]
```

Sort State ascending before applying RANK_UNIQUE to make tie handling reproducible;
verify actual Tableau ordering and annotate the tie rule. Configure **Compute Using →
Specific Dimensions → State only** for rank, partitioned by any displayed Year/Category.
Do not put In Top N on KPI sheets; it filters only the ranking after aggregate
calculations. Keep null measures out of ranking with `NOT ISNULL([Selected Measure])`
on ranking sheets only. State selection can reduce the eligible states below Top N.

On KPI Text put the numeric aggregate plus a separate status line. Set special-value
text for null to “Unavailable”. For a complete message (especially zero denominators),
use the status sheet beneath the number. Do not use ZN/IFNULL to turn missing into zero.
For accidents/fatalities KPI coverage labels, duplicate Reporting Status with the relevant
metric's availability condition rather than letting the Metric parameter change its
coverage label. Always title national aggregates **Reported state totals** until an
official full-coverage check establishes all-India comparability for that year.

A partial severity uses only rows with both counts and must say “paired observations
only”; do not combine a numerator and denominator from different reporting coverage.
Vehicle/cause/road categories with no accident denominator can show fatalities but
must show unavailable severity. Category comparisons use the source's definitions.

## Context filters, sets, and combined sets (Totals source)

- Add Year and State filters to context on **every Totals sheet that uses sets**.
  Default Year to the latest verified year; State to All. Use a single-select Year
  control for the main view. A trend requires multiple years: its title must say
  “selected year(s)”; a single-year selection intentionally produces one point.
  Users can switch Year to multiple values to explore historical trends. Do not
  silently ignore the Year filter on a sheet called globally filtered.
- Create State set **High Accidents**, Top tab → By field → Top `[Top N]` by
  SUM(Accidents). Exclude null accidents for this set's evaluation using an
  appropriate context availability filter on its risk sheet; do not suppress missing
  state messages from other sheets. Tableau top sets may include ties: verify and
  disclose tie behavior separately from the exact-N ranked chart.
- Create State set **High Severity**, Condition → By formula:

```tableau
SUM([Paired Accidents]) > 0
AND COUNT([Paired Accidents]) = COUNT([State])
AND 100.0 * SUM([Paired Fatalities]) / SUM([Paired Accidents])
    >= [High Severity Threshold]
```

- Create combined set **High Accidents AND High Severity**, All Members in Both Sets
  (intersection). This is the required combined set; keep its membership auditable.
- Create Risk Class:

```tableau
IF ISNULL([Accidents]) OR ISNULL([Fatalities]) THEN 'Unclassified: missing data'
ELSEIF [High Accidents AND High Severity] THEN 'High accidents + high severity'
ELSEIF [High Accidents] THEN 'High accidents'
ELSEIF [High Severity] THEN 'High severity'
ELSE 'Other reported states' END
```

Risk Class is evaluated at state-year rows. The default single-year view is its
supported classification view. For multi-year risk views use an aggregate classification
based on set membership plus aggregate completeness, or label/disable classification
until a single year is selected. Never average annual class labels or call missing
states low risk. Confirm set behavior in Tableau before using it in the viva.

## Three connected dashboards

Use a fixed 1200 × 800 primary desktop canvas, tiled containers, 16–24 px spacing,
Segoe UI/Tableau Book, dark navy text, white/light-gray surfaces, restrained teal
measure color, orange/red high-risk emphasis, gray unavailable values. Use readable
legends and units: counts with separators; severity with 1 decimal and “deaths / 100
accidents”. Avoid a percent suffix that implies a probability. Color must be backed by
text labels and rank, and remain distinguishable for color vision deficiency.

Create a shared header, three Navigation objects, common filter strip (Year, State,
Metric, Top N), and Reset control on each dashboard. Show visible source/coverage text.

### 1. National Road Safety Overview

- Three KPI sheets: reported accidents, reported fatalities, weighted severity.
- Filled India map by State; color Selected Measure, tooltip fields below.
- Horizontal State bars using Selected Measure, descending, In Top N=true.
- Year trend using Selected Measure; discrete year order ascending; missing marks
  remain gaps. No extrapolation or interpolation. Multiple selected years produce
  the historical comparison; one year produces a single point with explanatory label.
- Availability sheet with selected states missing the active measure and coverage counts.

### 2. Two-Wheeler Safety Analysis

- Vehicles source only for two-wheeler KPIs, state fatalities ranking, and Year trend.
- Filter Category to the exact official two-wheeler label on these sheets; keep that
  filter off the vehicle-category comparison sheet, which shows all reported categories.
- A multi-select State control supplies state comparison; place State on Color/Detail
  on the trend and State on Rows for the comparison bars. Use compatible years only;
  display source definition changes in the subtitle/footnote.
- Fatalities and severity KPIs use Vehicles, never Totals as a proxy. For missing
  two-wheeler accidents, leave severity unavailable and retain the fatality view.
- Label the category comparison **Road-user fatalities by category**: this extract
  includes pedestrians and bicycles as well as vehicle users, not impacting vehicles.
  Category comparison sheet uses Selected Measure and flags categories lacking the
  selected measure. Never assume category rows are exhaustive or disjoint.
- Display “Two-wheeler statistics unavailable for selected year/state” when there are
  no paired source records; a national value must not replace a missing state value.

### 3. Causes and Risk Factors

- Causes source: sorted reported-cause bars, with speeding label exactly as documented.
- Roads source: road-type comparison bars; no blending with causes.
- Totals source: high-risk state table/map, High Accidents/High Severity membership,
  combined-set membership, severity and count columns, conditional Risk Class color.
- Separate titles/status blocks for each data source. Missing cause or road coverage
  must not remove a state from the independent high-risk totals view.
- Dynamic Top N ranking uses Selected Measure on its own source. Road and cause
  category ranking uses Category as the table-calculation address rather than State.
  Label “Top N states” versus “reported categories” accurately; do not apply a
  state Top N table calculation to cause bars without defining a separate sheet.
- Explain that reported causes and aggregate correlations do not establish causation.

## Actions, tooltip, navigation, and reset

1. On the Overview map, Dashboard → Actions → Add Action → Filter, run on Select,
   targets all relevant KPI, ranking, trend, and availability sheets across the three
   dashboards; selected fields State → State only. Clearing selection → Show All Values.
   Include source mapping for each related source. The shared State quick filter is
   authoritative; a map action intersects it. If cross-dashboard action scope is not
   supported by the chosen Tableau version, create separate State-only target actions
   for each dashboard. Do not mark this done until navigation preserves the selection.
2. Add equivalent State-only selection actions from the two-wheeler state bars and
   risk state table as useful. Do not make cause selection filter unrelated data.
3. Tooltip on state marks: State, Year Label, Category where applicable, reported
   accidents, reported fatalities, Severity, Reporting Status, source_id. Include
   explicit null text. Avoid unsourced population-normalized rates.
4. Three Navigation objects point to the three actual dashboards (not images/URLs).
   Publish with toolbar enabled for Revert and download policy appropriate to the data.
5. **Reset all**: configure a Navigation object to the workbook's default published
   dashboard/custom view only if verified to reset filter actions AND parameters.
   Standard navigation alone does NOT reset state. Reliable baseline: expose the
   Tableau toolbar **Revert** button and a visible instruction “Reset all: Revert”.
   Verify it restores Year, State, Metric, Top N, threshold, selections and navigation
   state to the saved baseline. In an embedded deployment use the supported Tableau
   Embedding API `viz.revertAllAsync()` from an accessible external Reset button;
   await completion and handle errors. Do not claim a dashboard parameter-action
   button clears arbitrary quick filters. Record tested reset behavior/version.
6. Dynamic titles insert Dynamic Title and Top N parameter where relevant. Put titles
   on a marks Text sheet if a field cannot be inserted directly into a dashboard title.

## Responsive layout and publishing

Create a Desktop device layout tested at 1366 × 768 and 1440 × 900 (including toolbar
and browser chrome); use Fit Width as appropriate and inspect tooltip clipping. Add
a laptop layout if the primary canvas needs vertical scrolling; never shrink labels
until illegible. Optional tablet/phone layouts can stack KPI → map → ranking → trend.
Test the actual published view, keyboard access to filters and navigation, and visible
focus/contrast. Tableau dashboards do not automatically become usable mobile layouts.

Publish only verified public extracts to Tableau Public. For private material, use an
approved Tableau Server/Cloud project with access controls. Package extracts in twbx,
set permissions, retain provenance, record workbook URL/version, and rerun the complete
acceptance matrix in `docs/ACCEPTANCE.md`. Publishing and URL creation remain manual.

## Viva walkthrough (5–7 minutes)

Explain grain and source verification; select a year, choose a state on the map, and
show corresponding KPI changes. Switch Metric and Top N. Navigate to two-wheelers and
compare two states. Explain why missing denominators show unavailable. In Causes,
show context-filter order, the two sets and their intersection; distinguish reported
counts, severity, and causal inference. Revert to baseline and show published access.
State boundaries, partial coverage, and Tableau/manual verification limits explicitly.
