# V2 web validation — 1 November 2026

Primary product: seven connected web dashboards built with React/TypeScript/ECharts,
FastAPI and DuckDB. Tested against the built `web/dist`, not development-only pages.
Web tests do not certify Tableau, native Safari/Edge, Windows/macOS or public hosting.

## Executed checks

| Check | Actual result |
| --- | --- |
| Frozen npm install, strict TypeScript check and production build | PASS (`npm ci`, `npm run build`) |
| JavaScript calculation regression tests | PASS, 9 tests (retained original calculation module) |
| Python tests | PASS, 53 tests: 20 API, 7 snapshot/independent-analysis, 9 original pipeline, 17 Tableau structural regressions |
| Official PDF hashes / original extraction | PASS, three pinned PDFs; 251 original reconciliations |
| Expanded extraction | PASS, 6,732 rows / 17 families / 394 printed-column reconciliations; row-sum/grain checks |
| Independent SQL analysis | PASS, annual totals, compatible cohort, user shares, time bands and 27 priority-rule sensitivity cases |
| Notebook code cells | Executed using Python; Jupyter UI/kernel integration not tested here |
| Production browser journeys — Chromium | PASS on Linux |
| Production browser journeys — WebKit | PASS on Linux; this is Playwright WebKit, not native macOS Safari |
| Firefox | NOT EXECUTED successfully: browser launch fails in this container's graphics/nested sandbox; CI check configured |
| Native Windows/macOS startup, Edge and Safari | NOT RUN here; three-OS CI configured, remote result must be checked |
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

- 100 warm mixed-family API requests: p95 **16.82 ms**.
- Initial usable view including animation: **651.54 ms**.
- 10 warm year changes including animation: p95 **460.41 ms**.

These meet the local targets of 3 seconds initial / 500 ms warm interaction. They are
not measurements of real Internet connections or lower-power phones. Vite still warns
about the single chart-library bundle (~846 KB minified / 279 KB gzip); runtime gzip is
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

GitHub Actions is configured to build/test on Ubuntu, Windows and macOS and to exercise
Chromium plus separate Firefox/WebKit Linux jobs. Inspect actual job outcomes after
push; this document does not treat configuration as an executed result. Native Tableau
acceptance stays in ACCEPTANCE.md. The supporting draft still uses the original sources;
the V2 handoff provides new CSVs and construction instructions, not a claim of a finished
native V2 workbook.
