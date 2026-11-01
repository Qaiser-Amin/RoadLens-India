# RoadLens V2 baseline QA — 1 November 2026

Scope: existing commit `c9a632b`, before any V2 application changes. The following
checks ran in the managed Linux environment. No Windows/macOS, Safari, production
hosting, or native Tableau verification was performed.

## Automated baseline

| Check | Actual result |
| --- | --- |
| `npm test` | 9 JavaScript tests passed |
| `python -m unittest discover -s tests -v` | 26 Python tests passed; includes structural Tableau checks, not native Tableau tests |
| Chromium `tests/browser_smoke.py` | Passed existing year/state/metric/Top-N/risk/compare/reset/export checks and 1366×768 / 390×844 overflow checks |
| Native Tableau loading/actions | Not verified; prior load failures remain documented in ACCEPTANCE.md |

The existing tests passing does not establish that the application has no bugs.
Additional exploratory browser checks reproduced the following gaps.

## Reproduced findings

| ID | Finding | Reproduction and evidence | V2 acceptance requirement |
| --- | --- | --- | --- |
| QA-01 | Keyboard map selection loses focus | Focus Kerala SVG path, press Enter. The KPI updates, but `document.activeElement.tagName` becomes `BODY`. | Retain focus on the selected mark or move it to a deliberate, announced target. Test repeated keyboard navigation. |
| QA-02 | Invalid risk threshold and applied rule disagree | Set threshold to `-1`, then blur. Input still displays `-1` and `checkValidity()` is false, while the table subtitle still applies severity ≥ 50. No inline explanation appears. | Reject with a visible error or restore the last valid value; never display a different rule from the one used in calculations. Test blank, negative, excessive and non-finite values. |
| QA-03 | Map hover statistics lack keyboard-focus equivalence | Focus Kerala path. The custom tooltip is hidden; its accessible name is only “Select Kerala”. | Expose equivalent statistics through focus/accessible description and an accessible data table. |
| QA-04 | Narrow viewport has horizontal overflow | At 320×720, after default reset, document scrollWidth is 332px. Existing smoke checks only 390px and desktop widths. | No page-level overflow at required widths starting at 320px; large comparison tables may scroll inside labeled regions. |

These findings were recorded without fixing the application because the user requested
a build plan before implementation. They should become regression tests and fixes in
Phase 1. Medium-priority usability findings may reveal additional issues during a full
accessibility audit; the list is not exhaustive.

## Data review

- Current facts: 1,656 original rows for 36 reporting states/UTs. State totals/road
  types cover 2020–2023; road-user fatalities/traffic violations cover 2022–2023.
- All 648 road-user rows have unavailable accident counts. Those fatalities cannot
  be paired with accident counts from a different reporting definition.
- Injuries, fatal-crash outcomes, collision type, weather, road features, junctions,
  monthly counts, time bands and demographic tables exist in the archived 2023 MoRTH
  report, but have not been extracted into the application.
- The ministry's report catalog also lists Road Accident in India 2024. That report
  was identified during research; it has not been downloaded/extracted/verified as
  part of this planning pass.
- Source consistency issue for investigation: 2023 Annexure 29 totals pedestrian
  fatalities at 35,221, while Annexure 29(a) totals 35,203. The Kerala entries differ
  by 18 (1,147 versus 1,129); Annexure 29 has a Kerala category-attribution footnote.
  Preserve both source definitions and investigate before reconciling the new matrix.
  This does not invalidate the existing within-table extraction checks.
- These are aggregate state tables. They do not support precise road-segment hotspots,
  route recommendations, live alerts, or arbitrary joint filters across dimensions.

## Release gate for V2

No known unresolved critical/high defects; every required scenario executed with
recorded outcomes; independently reconciled numerical results; accessible filter and
chart interactions; supported-browser/device checks; honest unavailable-data behavior;
and a verified deployed build. Lower-priority exceptions require an explicit record.
A native Tableau deliverable needs separate native acceptance; its XML tests are not
substitutes. No finite test suite proves universal absence of bugs.
