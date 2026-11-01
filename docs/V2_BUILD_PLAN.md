# RoadLens India V2 — proposed build plan

Prepared 1 November 2026. This records the approved proposal and reference research. The web implementation now follows it; current evidence and deliberate scope adjustments are in WEB_VALIDATION.md, V2_DATA.md and METHODOLOGY.md. Native Tableau and public deployment remain separate, outstanding work.

## Product direction

Expand RoadLens into an **India Road Safety Observatory**. All reported crashes are
the default; two-wheelers become one selectable road-user/vehicle category.

The user selected **web dashboard as primary, with Tableau exports and a supporting
workbook**. Preserve validated extraction and missing-value rules. Complete the web
workflow independently of the currently unverified Tableau draft. A Tableau deliverable
can be called functional only after native opening, calculation and action checks pass.

The product should answer: what happened, where it is concentrated, who is affected,
which reported circumstances recur, when incidents occur, and what investigation or
intervention should be prioritized. Each dashboard must support a real question and
a reproducible export, rather than provide decorative charts.

## Similar projects reviewed

Official product descriptions/data documentation were reviewed. No claim is made that
every interaction in these external applications was manually exercised.

| Reference | Verified pattern | Application to RoadLens |
| --- | --- | --- |
| UK DfT Collision Analysis Tool, casualty dashboard and MAVRIC | Custom casualty/collision/vehicle extracts, location/road casualty mapping, trends by area and road-user group | Task-oriented exploration, separate crash/person/vehicle definitions, filter-matched downloads and source revisions |
| European Road Safety Observatory / Road Safety Atlas | Themed indicators, country profiles, interactive maps, deaths and population rates, topic reports | State profiles, clear indicator definitions, compatible denominators and source-linked explanations |
| EU collision matrices | Road-user collision matrices, including urban/rural views | A victim-road-user × impacting-vehicle matrix only from jointly reported tables; metric coverage must be explicit |
| NYC Vision Zero View, described in NYC DOT's official data catalog | Crash types, dates and locations alongside safety initiatives | Connect evidence to an investigation/action register; add geographic interventions only when suitable local data is available |
| NHTSA FARS | Explicitly scoped fatal-injury census, downloadable data and query access | Define dataset scope clearly; a fatalities dataset cannot be presented as a census of all crashes |

Sources:

- UK tools: https://www.gov.uk/government/publications/road-safety-statistics-data-tools
- UK methodology/data: https://www.gov.uk/government/collections/road-safety-statistics
- ERSO: https://road-safety.transport.ec.europa.eu/european-road-safety-observatory/data-and-analysis_en
- EU matrices: https://road-safety.transport.ec.europa.eu/european-road-safety-observatory/data-and-analysis/collision-matrix_en
- NYC DOT Vision Zero: https://www.nyc.gov/html/dot/html/about/datafeeds.shtml#vision
- FARS: https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars
- MoRTH catalog inspected: https://morth.nic.in/backend/api/reports?per_page=100
- Archived MoRTH 2023 PDF/provenance: data/sources and docs/DATA_VERIFICATION.md

## Data scope and availability

First audit and reconcile the 2024 report listed in the official catalog, alongside the
existing 2022/2023 reports. Add the newest compatible published period; do not promise
years/categories until extraction and validation pass. Support at least the existing
verified coverage throughout development.

| Family | Current application | Candidate MoRTH tables for expansion |
| --- | --- | --- |
| All crashes, people killed | Available, 2020–2023 | Annexures 2–3 and newest compatible report |
| People injured and fatal crashes | Not extracted | Annexures 4–5, 7–8; distinguish injury severity from crash severity |
| Crash outcome categories | Not extracted | Annexure 7: fatal, grievous-injury, minor-injury, non-injury crashes |
| Collision type | Not extracted | Annexure 20: source-reported collision categories, preserving original definitions |
| Impacting vehicle/object | Not extracted | Annexure 26; verify denominator/attribution before exposing derived severity |
| Victim road-user category | Fatalities available, 2022–2023 | Annexure 29; includes pedestrians/bicycles, not just motor vehicles |
| Road-user/opponent relationship | Not extracted | Annexures 29(a)–29(e), fatalities only; report only supported victim groups |
| Reported violations | Available, 2022–2023 | Annexure 35; attribution is not a causal effect |
| Road class and urban/rural | Road class available, 2020–2023 | Annexures 9–19 and 39–40 |
| Road features/junction/control/weather | Not extracted | Annexures 21–25, independently scoped datasets |
| Month and time band | Not extracted | Annexures 41–42; time bands are aggregate bins, not live incident timestamps |
| Age/sex, helmet/seatbelt context | Not extracted | Annexures 30–33, 37–38; only measures actually reported |

Important distinctions:

- A fatal crash is an event; fatalities count people. They are not interchangeable.
- Injury outcomes and collision mechanism are different classification dimensions.
- Impacting vehicle is different from the victim's road-user category.
- Blank/unknown/unreported and explicit zero remain distinct. Preserve unknown categories.
- Severity = fatalities per 100 compatible crashes, not probability of death; it may
  exceed 100 when several people die in one crash.
- Population/vehicle-normalized rates require a documented denominator aligned to
  the reporting geography and period. Registered vehicles are not traffic exposure.
- All-years counts must say cumulative, rather than appear to be an annual total.
- Validate category additivity from source definitions before summing. Preserve source
  disagreements rather than forcing a reconciliation. See V2_BASELINE_QA.md for the
  18-person pedestrian discrepancy between 2023 Annexures 29 and 29(a).

## Data model and filter behavior

Use a shared state/geography registry, year/period dimension and explicit metadata
catalog, with separate facts for each reporting grain. Example grains:

- state × year (national/state measures)
- state × year × collision type
- state × year × impacting-vehicle category
- state × year × victim category × opponent category, where reported jointly
- state × year × month
- state × year × reported three-hour time band
- state × year × weather, road feature, road class or reported violation, separately

Store source ID, report revision/checksum, printed table/page, reporting unit,
availability status, applicable measures and dimensional scope. Preserve old geography
boundaries and definition changes; do not merge historical states casually.

Global controls: reporting year/range, states, metric and comparison mode. Support
single/multi-year selection with explicit cumulative/annual labels. A previous-period
comparison uses a compatible cohort and shows unavailable when either period is
missing. Annotate the pandemic years when interpreting trends.

Category controls apply only to the appropriate fact. The UI must explain unsupported
combinations: separate weather/time/vehicle marginals do not establish rainy-night
truck crashes. A road-user choice must not silently filter unrelated national totals.
Every panel needs a visible scope/period indicator and a view-data table. Use one
validated query specification for charts, KPIs, tables and exports.

## Dashboard suite

| Dashboard | Main questions and visuals |
| --- | --- |
| 1. National overview | All-crash, death, injury and fatal-crash KPIs; state choropleth; annual trends; comparable period change; Top-N state ranking |
| 2. Crash types and outcomes | Collision-type ranking, outcome composition, category share trends, count versus severity scatter; distinct outcome/mechanism controls |
| 3. Vehicles and road users | All supported vehicle/user groups, victim versus impacting-vehicle views, fatality rankings and a joint victim/opponent heatmap where supported |
| 4. Causes and conditions | Reported speeding/alcohol/wrong-side/mobile categories; weather, junctions and road features in clearly scoped subviews |
| 5. When and where | Monthly trends, state × time-band heatmap, urban/rural comparison and NH/SH/other road comparison; unknown time retained |
| 6. State comparison and priorities | Two-to-five-state comparisons, burden/severity quadrants, transparent set membership and intervention-follow-up shortlist |
| 7. Evidence and data quality | Coverage heatmap, missing/unknown shares, revision history, definitions, source links and filter-matched CSV/PDF evidence briefs |

The road-user view retains two-wheelers as a first-class filter. The menu and defaults
will stop presenting the entire product as only a two-wheeler project.

Priority rules stay explainable: show high-count and high-severity membership, their
union for review and their intersection as a separate class. Expose the threshold and
minimum denominator rule; flag small counts. Do not label an arbitrary weighted score
an official risk rating. Sensitivity analysis should show how the shortlist changes.

An initial release need not show a new chart type for each dataset. Reuse a consistent
visual vocabulary: readable bars for categories, lines for time, heatmaps for a real
joint table, maps for geography, and scatterplots for burden-versus-severity analysis.

## Animations and accessibility

- Smooth, keyed bar/line updates and map color transitions around 200–400 ms.
- Keep final numerical values and filter state accurate while graphics transition.
- Optional year-play control with play/pause, clear current year and stable color scale.
- Preserve state identity and axes across comparisons; animate meaningful changes.
- Honor prefers-reduced-motion and provide equivalent tables, keyboard tooltips and
  accessible chart descriptions. Announce completed changes, not every animation frame.
- Preserve focus through selections/navigation, support keyboard controls and color
  vision differences. Use text/status patterns alongside high-risk colors.
- Avoid distracting 3-D effects, endless motion, deceptive axis changes and mixed-period
  transitions. Print/download output uses a stable completed state.

## Technical implementation

Recommended target: React + TypeScript for modular UI/state, ECharts for interactive
animated chart components, FastAPI for typed query/validation endpoints, and DuckDB
SQL over a versioned verified CSV snapshot (loaded into DuckDB; Parquet can be added if volume warrants it). The current data is small enough for a
single API service and static frontend deployment. Reuse and expand the verified Python
extractors rather than replacing their provenance rules.

Keep statistical logic in a shared audited query layer. The frontend renders the
returned values and coverage metadata instead of independently redefining metrics.
A dataset capability registry drives category controls, years and allowed measures.
Derive available years/categories from metadata; remove hardcoded 2020–2023 UI lists.
If the university requires Oracle, provide equivalent reporting views/query exports
against the same dimensional contract; do not invent a need for an Oracle server.

Version state in shareable URLs; include a reset default, visible active-filter chips,
compatible multi-state comparison, filtered exports and linked source evidence. A
production service needs HTTPS, health/readiness checks, validated query parameters,
cached immutable snapshots, controlled refresh/publish and clear failure states.

Given the earlier load failures, the supporting Tableau handoff should use verified
exports and a workbook saved/validated inside Tableau, or a native template supplied
from that installation. Generated XML and a third-party schema check will not be used
as evidence that the workbook is functional. This does not block the primary web build.

Keep cross-platform startup simple and documented. Test the built production artifact,
not just development pages. Do not expose credentials in browser bundles or CSV outputs.

## Build sequence and acceptance gates

| Phase | Work | Exit evidence |
| --- | --- | --- |
| 1. Stabilize and specify | Turn QA-01–QA-04 into regressions; fix input/focus/tooltip/mobile issues; finalize question-to-dataset map and required metrics | Existing tests pass; new regressions reproduce then pass; agreed data dictionary |
| 2. Expand verified data | Extract latest compatible annual measures, injuries/outcomes, collision types, vehicles, month/time and supported context; investigate source discrepancies | Checksums/provenance; row uniqueness/type/availability checks; official total reconciliation; reviewed exceptions |
| 3. Build the shared foundation | Modular frontend, typed query API, separate SQL facts and capability registry; source-driven years/categories and URL state | Same query yields identical chart/KPI/export data; unsupported combinations rejected or explained |
| 4. Deliver core exploration | National overview, crash types, vehicles/road users, comparisons, accessible view-data tables | Real question-driven user journeys and independent numeric fixtures pass |
| 5. Add decision support and motion | Conditions/time/place, joint matrices, transparent priority views, evidence briefs and reduced-motion-aware transitions | User journeys remain accurate under rapid filtering; stable axes; keyboard and animation checks pass |
| 6. Release QA and deployment | Cross-browser/device, accessibility, data/SQL/API tests, error recovery, performance, fresh-clone Windows/macOS startup, deployed smoke tests | No unresolved critical/high defects; required scenarios pass; measured performance and documented residual limitations |
| 7. Academic handoff | Reproducible notebook/SQL analysis, methodology, data dictionary, charts explanation, viva script, supporting Tableau exports/workbook | Rebuild from clean snapshot; web acceptance complete; Tableau claims limited to native checks actually performed |

Build estimates should follow the source audit: PDF layouts, category coverage and
access to granular records determine effort. Do not promise a full incident-level
system from annual state summaries.

## QA strategy

Baseline tests were actually run and exploratory findings recorded in V2_BASELINE_QA.md.
The planned release gates include:

1. Numerical truth: independent SQL/source examples, weighted denominators, category
   additivity only when justified, cohort-consistent comparisons and source revisions.
2. Data contracts: unique grain keys, numeric/null checks, source links/hashes,
   boundary histories, unknown categories and invalid-date/metric combinations.
3. Full filter matrix: all datasets × allowed periods × state/category/metric choices,
   global/local scope, multi-state comparisons, sorting/ties, Top-N, reset and exports.
4. Regression tests for previous risk-set omissions and all newly reproduced bugs.
5. Browser journeys on Chromium/Firefox/WebKit plus actual Windows Edge and macOS
   Safari checks when available. Mobile widths 320/390/768, laptop 1366/1440, zoom,
   keyboard navigation, focus, contrast and tooltip equivalence.
6. Animation cases: rapid repeated changes, interruption, reduced motion, paused year
   playback, export during transitions and accurate final labels.
7. Failure modes: empty/partial datasets, request failure, malformed API input, stale
   refresh, refresh reconciliation failure and clean recovery. Test the production build.
8. Performance targets: measure p95 filter-to-stable-chart response against an agreed
   reference machine/network; target under 500 ms for warm ordinary queries and under
   3 seconds initial usable view. Pin data volume and measurement conditions.
9. Deterministic acceptance evidence and a release checklist with results, not only a
   claim that the tests exist. Native Tableau verification is separate.

No finite QA pass proves universal absence of bugs. A defensible release has no known
critical/high defects, verified required journeys, reproducible evidence and explicit
limits. Do not describe the current project as bug-free because its existing suite passes.

## Real-world usefulness and limits

- State road-safety officials: compare burden, changes, road-user mix and coverage;
  prioritize follow-up audits and document evidence for allocating attention.
- Traffic police: review reported violation patterns and separately available time
  distributions to plan investigations or campaigns, checked against local incident data.
- Engineers: screen collision/road-feature categories for site investigations; annual
  state summaries alone do not identify a specific dangerous junction or segment.
- Public-health researchers: compare injury/fatality patterns and victim demographics,
  while acknowledging reporting differences and ecological/aggregate limitations.
- Fleet/education teams: support targeted training and public awareness with source-linked
  evidence. Category totals are not per-trip personal risk estimates.

A useful evidence brief should show the selected question, period, source facts,
coverage, comparison basis, caveats and a concrete follow-up investigation. Later, an
intervention register could record an owner, location, action date, evidence and review
outcome. Before/after changes alone must not be called causal intervention effects.

Precise hotspot ranking, safe-route advice, real-time warnings, emergency dispatch,
weekday × hour heatmaps, or arbitrary vehicle × weather × time filtering require
suitable incident-level/geocoded joint records and the corresponding data permissions.
Those are a later phase contingent on data access, not promises in the initial release.

Forecasting/ML is optional research only after enough consistent history and predictors
exist, with backtesting against simple baselines. Four annual points do not justify a
credible prediction feature. The master's-level contribution can instead be rigorous
source reconciliation, SQL modeling, transparent comparative analysis, sensitivity
analysis, reproducibility and a demonstrably useful interactive interface.
