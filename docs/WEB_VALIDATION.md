# Web application validation

The web app is separate from the Tableau workbook. Web tests do not certify Tableau
parameters, filters, sets, actions, publishing, or device layouts.

## Implemented

Three connected dashboard views, shared year/state filters, SVG map selection and
keyboard activation, dynamic counts and weighted severity, measure switching, Top-N
ranking, hover statistics, state comparison, combined-set risk classification,
threshold control, dynamic subtitles, reset, source metadata, CSV export and responsive
laptop/mobile layouts. Charts and map render from actual data, with no runtime CDN.

## Results

Passed in Chromium on 2026-10-25, including CSV download, risk-threshold membership
changes and missing severity at mobile width. No JavaScript errors or page-level
horizontal overflow occurred at the tested desktop and mobile widths. Desktop and
mobile screenshots were visually inspected during development.

## Automated checks

- 9 JavaScript calculation tests: filter intersection, paired weighted severity,
  missing versus zero, measure-dependent ranking, combined risk sets and independent
  reconciliation of real 2023 counts, risk-union completeness, inclusion of Kerala in
  the accident set, and intersection-first sorting with incomplete members.
- 9 Python extraction-pipeline validation tests.
- Browser tests in `tests/browser_smoke.py` exercise the actual app in Chromium:
  year, state map, cross-dashboard selection, missing slices, measure switch,
  Top 5/15 rankings, four-year trend, risk threshold, multi-state comparison,
  reset, source dialog and viewport overflow at 1366×768 and 390×844.

251 upstream source reconciliation checks remain documented in DATA_VERIFICATION.md.
All Tableau interaction checks remain NOT RUN in ACCEPTANCE.md.

## Risk table correction

The risk table lists every state in the union of High Accidents and High Severity;
it is not limited to Top-N by the selected display measure. Combined-risk members
appear first, followed by single-set members and unclassified high-accident members.
At defaults (2023, all states, Top 10 accidents, severity threshold 50), it lists
17 states, including Kerala, with Uttar Pradesh first. The browser smoke test checks
these default results and the 29 members in its All-years/Top-15/threshold-20 scenario.
The Tableau generator now defines the same union membership for Combined Risk Ranking;
its native rendering, set evaluation and actions still require testing in Tableau.
