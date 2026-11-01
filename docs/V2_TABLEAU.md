# V2 supporting Tableau handoff

The primary tested interface is the web app. The existing generated workbook uses
original 2020–2023 extracts and remains unverified inside Tableau; it is not the V2
web dashboard suite. Do not represent it as native-tested or published.

## Use verified V2 data safely

1. Download **Filtered CSV** from a completed web selection. Tableau → Connect → Text
   file → choose that CSV. It contains real fact rows with dataset/year/state/category,
   category2 and supported counts. Preserve blanks as nulls. The selected metric is a
   display choice: the CSV retains all supported raw measures for that same scope.
2. For broader exploration, connect to `data/analytics/facts.csv`. Duplicate/separate
   the data source for each family and apply a **data-source filter** on `dataset`
   before adding measures. Never sum counts across all families. `catalog.json` and
   V2_DATA.md define supported years, measures, secondary dimensions and source pages.
3. Assign State/Province geographic role to `state`, and constrain Country/Region to
   India. Resolve any geographic aliases explicitly; validate historical boundaries.
4. Start with totals, users, violations and roads in separate sources. Use the existing
   TABLEAU_BUILD.md blueprint for the three supporting dashboards; extend additional
   sheets using a single compatible family per view. Filter the matrix by victim and
   use category2 for opponent; do not join unrelated weather and time tables.

## Calculations and actions to create natively

- String parameter `Metric`: Accidents / Fatalities / Severity. Use a CASE calculation
  selecting SUM(accidents), SUM(fatalities), or paired severity. Disable unsupported
  choices or show an explicit unavailable indicator; impacting-vehicle severity is disabled.
- Paired accidents: `IF NOT ISNULL([fatalities]) AND NOT ISNULL([accidents]) THEN [accidents] END`.
  Paired fatalities uses the same condition. Severity is
  `100.0 * SUM([Paired fatalities]) / SUM([Paired accidents])` with a positive-denominator guard.
- Integer Top N parameter, allowed 5/10/15. Create a state Top set by SUM(accidents).
  Year/state context filters must execute before Top-N membership. Verify ties against
  the web app's deterministic state-name ordering rather than assuming ties are identical.
- Severity threshold parameter (default 50) and minimum accident denominator parameter
  (default 0). Create a severity set only where all selected annual pairs are complete,
  severity meets threshold and matched accidents meet minimum. Do not classify missing
  severity as zero. Keep separate union and intersection combined sets.
- Use the union to filter the priority table. Use intersection for the first class and
  sort by class then descending accidents. The default 2023 table must contain 17 states,
  including Kerala, with Uttar Pradesh first. Do not substitute Top-N fatalities.
- Configure shared Year and State filters for compatible sources only; retain local
  category filters. Map select/filter actions update related sheets and KPI cards.
- Add navigation objects, dynamic titles, informative tooltips and a tested reset/revert
  action. Use 1366×768 dashboard layouts, readable legends and clear unavailable sheets.
- Publish only from a workbook that opens/calculates correctly in the installed Tableau
  version. Inspect published permissions/data availability and re-run the interactions.

`docs/ACCEPTANCE.md` remains the native checklist. Opening the generated XML or passing
Python structural checks does not execute Tableau's calculation/rendering/action engine.
Save a native `.twbx` after those checks and record Tableau version and each actual result.
