# Tableau acceptance record

Tableau status: **NOT RUN — no Tableau runtime available.**
A generated TWB/TWBX draft is available in `tableau/`; its eight structural/data tests
passed, but workbook compatibility and all Tableau interactions remain NOT RUN.
Verified extracts are now available; extraction validation completed outside Tableau
(251 reconciliation checks and 9 pipeline tests passed; see DATA_VERIFICATION.md).
A Python test pass does not test Tableau. Record Desktop version, source hashes,
workbook revision, tester, date, and published URL before changing any status below.
Use independent source calculations as expected values; capture actual numbers and
screenshots only as test evidence, never as the delivered interface.

| Test | Procedure / expected evidence | Status |
| --- | --- | --- |
| Extract integrity | Pinned PDFs, count totals, provenance and selected visual spot checks; see DATA_VERIFICATION.md | PASS (extraction only) |
| Model grain | Compare sheet sums to CSVs; no multiplication from scaffold joins | NOT RUN |
| Year | Select two different years; reconcile each KPI and affected chart in all dashboards | NOT RUN |
| State | Select state quick filter; then map mark; reconcile all target sheets, including navigation | NOT RUN |
| Clear selection | Click map background; action clears, quick-filter selection remains authoritative | NOT RUN |
| KPI | Compare counts and paired severity with independent arithmetic; partial status visible | NOT RUN |
| Metric | Switch all three choices; map, ranks, titles, labels, units and null handling update | NOT RUN |
| Top N | 5, 10, 15 eligible states; ranking changes, deterministic ties, KPI totals unaffected | NOT RUN |
| Context / sets | Year changes top-accident set; inspect high-severity set and intersection manually | NOT RUN |
| High risk | Missing counts unclassified; threshold boundary classified correctly | NOT RUN |
| Two-wheelers | Category remains two-wheelers on KPI/trend; comparison retains other categories | NOT RUN |
| Grain isolation | Cause/road/category selections never alter incompatible totals | NOT RUN |
| Missing data | Absent state/year/category, blank metric, explicit zero, zero denominator; informative text, no false zero | NOT RUN |
| Trends | Multiple years show chronological data; missing years are gaps; single year clearly labeled | NOT RUN |
| Geography | All resolved state/UT locations checked; historical boundaries disclosed | NOT RUN |
| Tooltip | Actual state values, units, status, source and year agree with extract | NOT RUN |
| Navigation | All three directions work; global selection persists | NOT RUN |
| Reset | Revert restores saved Year, State, all parameters, selections; repeat after navigation | NOT RUN |
| Responsive | 1366×768 and 1440×900; no clipped controls, legends, tooltips or unreadable labels | NOT RUN |
| Published | Permissions, refresh/extract, reset and all interactions work in actual browser view | NOT RUN |

Required deliverables: verified input extracts and archived sources; validation.json;
.twbx with four sources and three connected dashboards; completed acceptance record;
public or access-controlled published workbook; brief viva walkthrough.
