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

- 6 JavaScript calculation tests: filter intersection, paired weighted severity,
  missing versus zero, measure-dependent ranking, combined risk sets and independent
  reconciliation of real 2023 counts.
- 9 Python extraction-pipeline validation tests.
- Browser tests in `tests/browser_smoke.py` exercise the actual app in Chromium:
  year, state map, cross-dashboard selection, missing slices, measure switch,
  Top 5/15 rankings, four-year trend, risk threshold, multi-state comparison,
  reset, source dialog and viewport overflow at 1366×768 and 390×844.

251 upstream source reconciliation checks remain documented in DATA_VERIFICATION.md.
All Tableau interaction checks remain NOT RUN in ACCEPTANCE.md.
