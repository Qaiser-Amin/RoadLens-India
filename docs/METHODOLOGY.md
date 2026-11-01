# Methodology and university demonstration

## Questions and analytical method

1. What is the reported burden? Aggregate accident events, people killed/injured and
   fatal crashes separately, at state/year grain. Fatalities may exceed fatal crashes.
2. Who and what is involved? Compare victim road users separately from impacting
   vehicles. Use only the published joint matrix for victim/opponent questions.
3. Which conditions recur? Describe reported violations, weather and road features.
   Their independent marginal tables do not establish interaction or causation.
4. When and where? Examine months, three-hour time bands, road classes and urban/rural
   categories. State summaries cannot identify precise road-segment hotspots.
5. What merits investigation? Review Top-N accident states and the complete-pair
   high-severity set; show their union and mark their intersection first. Change the
   threshold/minimum accident denominator and inspect sensitivity before making a shortlist.

The data pipeline verifies downloaded report hashes, table structure, serial/state
identity, unique grain keys, nonnegative counts and published column totals. Original
extracts are preserved. V2 adds 394 column reconciliations and state-level checks of
monthly, crash-outcome, time-band and matrix row sums. These checks validate extraction
against the report; they cannot prove police reporting completeness or source accuracy.

## Metrics and missingness

`severity = 100 * SUM(paired fatalities) / SUM(paired accidents)`. A pair requires both
measures to be reported in the same fact row. Missing is NULL, and an explicit reported
zero remains zero. A zero denominator gives unavailable severity. National 2023 deaths
are 172,890; Lakshadweep's unqualified dash stays NULL, so the compatible severity
accident denominator is 480,582 rather than 480,583.

Each result exposes expected and observed metric rows. Some aggregate totals are
partial observed sums: inspect coverage before comparison. A period change in the API
requires complete, identically defined current/previous cohorts; unavailable comparisons
are explained. The independent analysis script also shows a deliberately matched
35-state death cohort for 2023–24, clearly labeling that cohort.

Counts for multiple years are cumulative. Ratios are weighted from matched counts,
never an average of state ratios. Priority membership requires complete annual pairs;
the minimum accident denominator applies to the severity set. Low counts below 100 are
flagged even when no minimum is requested. Rankings use deterministic state-name tie
breaks. Risk classes are exploratory rules, not official safety ratings.

## Reproducible findings

Run `analysis/reproduce.py` to refresh `analysis/results.json` from the committed
snapshot. Equivalent queries and a notebook are included. Current source totals show:

- Reported accidents: 480,583 in 2023 and 487,707 in 2024.
- Reported fatalities: 172,890 and 177,175. The matched 35-state death cohort changes
  by about +2.48%; the displayed raw totals alone do not establish increased per-trip risk.
- 2023 two-wheeler victim fatalities: 77,539, about 44.85% of the all-road reported
  fatality total. This is a share of deaths, not a two-wheeler crash probability.
- The 2023 time table includes 5,761 accidents with unknown time. Retain that category
  when describing temporal patterns.
- The default Top-10 / severity-50 priority union has 17 states. Counts and membership
  vary over 27 threshold/Top-N/minimum-denominator combinations in the analysis output.

2020–2021 pandemic disruption, reporting/definition changes and historical geography
must be considered when interpreting trends. No forecast is fitted to five annual
observations. No population, trip-volume or vehicle-kilometre denominator is supplied.

## Practical workflow

A state transport analyst can compare consistent periods, inspect high-burden collision
and road-user categories, shortlist states for further review, and export a scoped
CSV/PDF with provenance for a review meeting. A district team should then obtain local
incident records, exposure data and engineering inspection results before choosing an
intervention. Record the intervention, owner, date, baseline, intended outcome and review
period outside this aggregate observatory; evaluate it with appropriate comparison data.

For example, a large two-wheeler fatality share supports investigating helmet protection,
road design and enforcement needs. It does not demonstrate which intervention caused
an improvement. Police-reported speeding attribution similarly supports investigation,
not an estimate of the causal benefit of a speed-camera programme.

Production hosting needs HTTPS, a reviewed immutable data refresh and operational
monitoring. This release is a runnable local web build. Live alerts, precise hotspots,
route safety, incident ingestion and intervention tracking need additional suitable data
and services; they are not implemented features.

## Ten-minute viva walkthrough

1. Explain the accident/fatality/fatal-crash distinction using the four overview KPIs.
2. Change year and select Kerala on the map; show that KPIs, ranking and trend share scope.
3. Switch measure and Top-N, compare two states, then use a custom year range.
4. Open collision types and select a category. Switch to outcomes and explain their
   different classification unit.
5. Show victim users and the real opponent matrix; explain the preserved pedestrian
   discrepancy and why vehicle-category severity is disabled.
6. Show time bands, unknown time and weather, explaining why the marginals cannot be joined.
7. Open priorities; explain sets, union/intersection, thresholds, small denominators
   and the independent SQL sensitivity analysis.
8. Show unavailable 2024 detail, coverage heatmap and source checksums. Export filtered
   CSV and PDF, then reset. Turn motion off or demonstrate reduced-motion behavior.
9. Show the notebook/SQL and automated test record. Clearly distinguish tested web
   interactions from the unverified native Tableau draft.

The supporting Tableau blueprint demonstrates parameters, calculated fields, context
filters, sets, combined sets, sorting, actions and publishing steps. These must be
implemented/verified in native Tableau before claiming that part passed.
