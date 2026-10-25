# Official MoRTH extraction and verification

Downloaded on 2026-10-25 over verified HTTPS from the Ministry of Road Transport and
Highways. The previous `/sites/default/files/` URLs return the new website's HTML shell.
The current download paths were discovered from the official reports API at
`https://morth.nic.in/backend/api/reports?per_page=100`.
The extracts use the 2022 and 2023 reports; they are not a claim to the latest published
report or current-year accident data.

| Official report | Local PDF | SHA-256 |
| --- | --- | --- |
| [Road Accidents in India 2022](https://morth.nic.in/backend/documents/uploaded/1755600426_RA_2022_30_Oct.pdf) | data/sources/road-accidents-india-2022.pdf | d1908170c4e25153539d82244f0fe269805a577b71e42259a53a57422dd8d8ed |
| [Road Accidents in India 2023](https://morth.nic.in/backend/documents/uploaded/Road-Accident-in-India-2023-Publications.pdf) | data/sources/road-accidents-india-2023.pdf | 901505420d5b387052ac51e36b4bdce0274f6326b614f9ebcee6e7954d45b5b0 |

## Delivered coverage

All files have year, state, category, accidents, fatalities, source_id. Counts remain
integers; missing metrics are blank, never filled with zero. There are 36 reporting
states/UTs. Header names are normalized; source locators and definitions are in
`data/input/sources.json`.

| CSV | Years | Records | Official tables |
| --- | --- | --- | --- |
| state_totals.csv | 2020–2023 | 144 | 2023 Annexures 2, 3; PDF pages 141,143 |
| vehicle_categories.csv | 2022–2023 | 648 | Annexure 29 in both reports; PDF 181–182 (2022),204–205 (2023) |
| causes.csv | 2022–2023 | 432 | Annexure 35 in both reports; PDF 193–194 (2022),220–222 (2023) |
| road_types.csv | 2020–2023 | 432 | 2023 Annexures 9,10,14,15,19; PDF 151–152,166–167,171–172 |

Each vehicle_categories record is a **road-user fatality** category, including
pedestrians. Accident counts for these road users are not supplied by Annexure 29.
Do not attach accident counts from the impacting-vehicle tables to these fatalities.
Two-wheeler fatalities total 74,897 (2022) and 77,539 (2023). Accident counts and
severity for the road-user categories are unavailable for both years.

National reported totals in the 2023 Annexures 2–3 are:

| Year | Accidents | Persons killed |
| --- | --- | --- |
| 2020 | 372,181 | 138,383 |
| 2021 | 412,432 | 153,972 |
| 2022 | 461,312 | 168,491 |
| 2023 | 480,583 | 172,890 |

These are source-reported totals, not an assertion of complete reporting coverage.
Missing Ladakh 2020 and unqualified dash symbols remain unavailable in state rows.

## Verification performed

- Both actual PDF byte hashes match the pinned source revisions. HTML responses fail.
- Each selected annexure includes every expected serial row exactly once.
- All selected count columns reconcile to the corresponding printed table total.
- For road users, male plus female counts reconcile to each supplied total.
- Within the 2023 report, complete road-user, violation and road-type category counts
  reconcile with state totals for every state where those metrics are comparable.
- **251 reconciliation checks passed**, recorded in
  `data/sources/extraction-validation.json`. Gender subtotal checks additionally passed.
- Selected original pages were rendered and visually inspected, including the 2022
  and 2023 road-user tables, 2023 violation table, and state totals.
- All 9 independent pipeline validation tests passed. No Tableau interactions have
  been tested. This verifies extraction consistency, not the accuracy of the underlying
  police/state reporting or completeness of unreported incidents.

## Explicit source caveats and transformations

1. The 2022 report has a redundant all-NA Daman & Diu row. Its footnote says Daman &
   Diu is included in Dadra & Nagar Haveli from 2020. Use the merged union-territory
   name and exclude only the redundant all-NA row. No counts are summed or invented.
2. The 2022 traffic-violation table prints zero for Jammu & Kashmir jumping-red-light
   accidents, but its footnote explicitly says that count is not reported. The extract
   uses blank for that accident cell; this override is recorded in validation evidence.
3. In the 2023 road-user table, some Kerala “Other” figures are included in Pedestrian.
   Do not interpret that category's historical movement as a clean like-for-like trend.
4. Ladakh is missing in 2020 and lacks some ranks. Missing ranks are not count values.
5. Unqualified dashes are conservatively left blank. Explicit numeric zeros remain zero.
6. State/UT spellings are normalized to the canonical names used by the pipeline;
   Orissa → Odisha, A&N → Andaman and Nicobar Islands, J&K → Jammu and Kashmir.
7. The scaffold includes historical jurisdiction names for unavailable-data displays;
   it is not a historical boundary roster. Do not interpret every scaffold row as an
   active jurisdiction, or claim 100% national coverage from its row count.
8. No causes or road-user category observations are supplied for 2020–2021. The
   workbook must display unavailable for those slices, not extrapolate from 2022–2023.

## Reproduce

From `/workspace/RoadLens-India`, with Python 3.12+ and Poppler `pdftotext` installed:

```sh
python tools/fetch_morth.py
python tools/extract_morth.py
python tools/prepare_tableau.py
python -m unittest discover -s tests -v
```

These commands have run successfully here. Existing PDF hashes are rechecked before
reuse. Extraction is restricted to the two supported report revisions and fails on
unexpected layout or reconciliation results. Review source revisions before changing
a pinned hash. PDFs are retained locally but ignored by Git; the CSV inputs and JSON
provenance/evidence can be versioned. Generated Tableau CSVs are reproducible outputs.

Next: build the workbook in Tableau following TABLEAU_BUILD.md, complete the acceptance
record there, and publish. Neither a downloaded report nor these extraction checks
establishes that the Tableau dashboards work.
