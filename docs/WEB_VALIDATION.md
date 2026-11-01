# V2 web validation — 1 November 2026

Primary product: seven connected web dashboards built with React/TypeScript/ECharts,
FastAPI and DuckDB. Tested against the built `web/dist`, not development-only pages.
The CI server/browser workflow ran on native Windows/macOS/Linux runners. These tests do not certify Tableau, native Safari/Edge or public hosting.

## Executed checks

| Check | Actual result |
| --- | --- |
| Frozen npm install, strict TypeScript check and production build | PASS (`npm ci`, `npm run build`) |
| JavaScript calculation regression tests | PASS, 9 tests (retained original calculation module) |
| Python tests | PASS, 54 tests: 20 API, 8 snapshot/independent-analysis, 9 original pipeline, 17 Tableau structural regressions |
| Official PDF hashes / original extraction | PASS, three pinned PDFs; 251 original reconciliations |
| Expanded extraction | PASS, 6,732 rows / 17 families / 394 printed-column reconciliations; row-sum/grain checks |
| Independent SQL analysis | PASS, annual totals, compatible cohort, user shares, time bands and 27 priority-rule sensitivity cases |
| Notebook code cells | Executed using Python; Jupyter UI/kernel integration not tested here |
| Production browser journeys — Chromium | PASS on Linux |
| Production browser journeys — WebKit | PASS on Linux; this is Playwright WebKit, not native macOS Safari |
| Firefox | PASS on the Ubuntu GitHub runner; launch unsupported in this managed container |
| Windows/macOS build, tests, server startup and Chromium journey | PASS in GitHub CI; native Safari/Edge GUI checks remain NOT RUN |
| Native Tableau loading/calculations/actions/publishing | NOT RUN; earlier generated draft remains unverified |
| Public hosted deployment | NOT DEPLOYED; local production server verified |

The production browser journeys execute:

- All seven navigation sections, each detailed family tab, 2023/2024 totals, state-map
  selection and preserved keyboard focus, focus tooltips, category and metric controls.
- Top 5/10/15 ranking table lengths, real collision and two-wheeler values, unavailable
  denominators and periods, custom-range selection and reload, two-state comparisons.
- Year playback through prepared years, its final stop, motion toggle, reduced-motion
  disabling, rapid year changes and final correct values.
- Default priority union of 17 states (Kerala included, Uttar Pradesh first), minimum
  denominator, invalid threshold with visible applied rule, zero threshold URL reload.
- Reset, filtered 36-row CSV, real PDF download, evidence/source caveats, aborted-query
  error state and retry recovery.
- Page overflow at widths 320, 390, 768, 1366 and 1440 on overview and priorities.
  Large tables/heatmaps may scroll inside their own region. No JavaScript errors.

Owned-server `tools/check_web.py` also verifies startup/readiness and propagates the
browser test's exit code, then terminates only the server it created.

## Performance

Measured with `tools/benchmark.py`; exact results are in `performance.json`.
Linux cloud container, loopback HTTP, 6,732-row snapshot, production build, no network
throttling; UI measurements include a conservative 400 ms animation completion allowance.

- 100 warm mixed-family API requests: p95 **15.63 ms**.
- Initial usable view including animation: **665.35 ms**.
- 10 warm year changes including animation: p95 **470.73 ms**.

These meet the local targets of 3 seconds initial / 500 ms warm interaction. They are
not measurements of real Internet connections or lower-power phones. Vite still warns
about the single chart-library bundle (~847 KB minified / 279 KB gzip); runtime gzip is
enabled. Code splitting is a possible later optimization, not a measured local blocker.

## Regressions and source exceptions

The four baseline findings in V2_BASELINE_QA.md are fixed and covered: keyboard focus,
inline threshold validation, focus statistics, and 320px page overflow. Validation also
caught and fixed non-finite threshold handling (422, not 500) and custom-range URL reload.

Source issues remain visible rather than being 'fixed' by editing official counts:
18-person pedestrian disagreement, impacting-bicycle anomaly with vehicle severity
disabled, and junction/control sub-universe. See V2_DATA.md. Derived severity uses paired
observations and incomplete cohorts are explicitly marked.

## Remaining verification and scope

No known critical/high web defect remains in the paths above. Finite tests cannot prove
that no bugs exist. Automated checks cover keyboard map interaction, accessible tables,
focus and reduced motion; a full assistive-technology/contrast audit is still separate.
The illustrative map has no asserted upstream redistribution licence or historical-border
authority; review geography/licensing before external publication.

Firefox was downloaded but could not launch correctly after sandbox/graphics diagnosis
(`RenderCompositorSWGL failed mapping default framebuffer`, nested uid-map failure).
WebKit needed locally extracted, signature-verified Debian libraries because the managed
image lacks its desktop dependencies; shared-library loading was checked before running
its actual journey. These are environment differences, not waived application tests.
Normal CI runners use Playwright's supported `--with-deps` installation.

The complete five-job GitHub Actions run passed on the initial V2 code commit
`0529d0ac622b23c2989c68e9c3b504818394934b`: Windows/macOS/Ubuntu production builds,
53 Python tests, nine JS tests, independent analysis and Chromium journeys, plus
Firefox and WebKit on Ubuntu. Actual API evidence is in ci-acceptance.json and at
https://github.com/Qaiser-Amin/RoadLens-India/actions/runs/41329027012.

Final visual QA subsequently improved mobile heatmap scrolling, prevented label overlap,
rounded chart-axis labels, stabilized matrix axis ordering and corrected age-band display
ordinals across the two PDF pages. Counts are unchanged. Local browser regressions and
the full Python suite are rerun for this patch; its separate CI run can be checked in
GitHub Actions. The baseline CI evidence above identifies its exact tested commit. Native Tableau
acceptance stays in ACCEPTANCE.md. The supporting draft still uses the original sources;
the V2 handoff provides new CSVs and construction instructions, not a claim of a finished
native V2 workbook.

Fresh-checkout QA also passed 53 Python tests and the production Chromium journey with Git CRLF conversion enabled. Snapshot/workbook byte-sensitive files have explicit Git attributes.
