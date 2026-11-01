# V2 verified data dictionary and provenance

Prepared snapshot: **6,732 fact rows, 17 separate dataset families, 394 expanded-column reconciliations**. Original extracts retain their separate checks in DATA_VERIFICATION.md.

## Fact contract

`dataset,year,state,category,category2` is the unique key. `ordinal` preserves source ordering. Counts are nullable nonnegative integers; fatalities count people and fatal_crashes count crash events. Blanks are unavailable, never imputed zeros. `source_id` resolves to the source register in catalog.json. Country totals are excluded from state rows.

| Dataset | Prepared years | Rows | Available counts | Physical PDF pages (2023 unless noted) |
| --- | --- | --- | --- | --- |
| totals: All reported accidents | 2020, 2021, 2022, 2023, 2024 | 180 | accidents, fatalities, injuries, fatal_crashes | Original source register; additions below |
| users: Victim road users | 2022, 2023, 2024 | 972 | fatalities | Original source register; additions below |
| violations: Reported traffic violations | 2022, 2023 | 432 | accidents, fatalities | Original source register; additions below |
| roads: Road classes | 2020, 2021, 2022, 2023 | 432 | accidents, fatalities | Original source register; additions below |
| outcomes: Crash injury outcomes | 2023, 2024 | 288 | accidents | 149 |
| collisions: Collision types | 2023 | 324 | accidents, fatalities, injuries | 173, 174, 175, 176, 177 |
| vehicles: Reported impacting vehicles / objects | 2023 | 324 | accidents, fatalities, injuries | 194, 195, 196, 197, 198 |
| weather: Weather conditions | 2023 | 180 | accidents, fatalities, injuries | 191, 192, 193 |
| features: Road features | 2023 | 288 | accidents, fatalities, injuries | 181, 182, 183, 184 |
| junctions: Junction types | 2023 | 180 | accidents, fatalities, injuries | 185, 186, 187 |
| controls: Traffic controls | 2023 | 180 | accidents, fatalities, injuries | 188, 189, 190 |
| environment: Road environment | 2023 | 180 | accidents, fatalities, injuries | 178, 179, 180 |
| urban: Urban and rural | 2023 | 72 | accidents, fatalities, injuries | 226 |
| months: Monthly accidents | 2023 | 432 | accidents, fatalities, injuries, fatal_crashes | 229, 230, 231, 232, 233, 234 |
| hours: Time of occurrence | 2023 | 324 | accidents | 236 |
| matrix: Victim / impacting-vehicle matrix | 2023 | 1440 | fatalities | 206, 207, 208, 209, 210 |
| demographics: Victim age and reported sex | 2023 | 504 | fatalities | 211, 212 |

## Source files

The downloader pins original bytes to these SHA-256 values. Large PDFs are ignored by Git.

- MoRTH Road Accidents in India 2022: https://morth.nic.in/backend/documents/uploaded/1755600426_RA_2022_30_Oct.pdf
  SHA-256: `d1908170c4e25153539d82244f0fe269805a577b71e42259a53a57422dd8d8ed`.

- MoRTH Road Accidents in India 2023: https://morth.nic.in/backend/documents/uploaded/Road-Accident-in-India-2023-Publications.pdf
  SHA-256: `901505420d5b387052ac51e36b4bdce0274f6326b614f9ebcee6e7954d45b5b0`.

- MoRTH Road Accidents in India 2024: https://morth.gov.in/backend/documents/uploaded/Road%20Accidents%20in%20India%20-%202024.pdf
  SHA-256: `70a2cf4a92c7074d13502a84ce25d606ce4655d4e7e79d49740c97fd908600ea`.

2024 totals use physical PDF pages 167–170; crash outcomes page 172; victim users pages 209–210. 2023 injuries/fatal crashes use pages 145/147; other newly extracted families list pages above. For retained 2020–2023 totals, road classes, violations and road users, consult the per-table original source IDs and locators. See the extractor for exact source-column mappings.

## Preserved source exceptions

- Annexure 29 reports 35,221 pedestrian fatalities; Annexure 29(a) reports 35,203. Kerala differs by 18 (1,147 versus 1,129); preserve both definitions.
- Impacting-vehicle category severity disabled pending source reconciliation.
- State summaries do not support precise hotspots or arbitrary joint category filters.
- Kerala impacting-bicycle entry: 2 accidents and 88 fatalities. Preserve the source values; derived severity for the entire impacting-vehicle family is disabled pending clarification.
- Junctions and traffic controls are junction-related subsets (2023 reported fatalities 34,354), not all-road totals.
- Victim/opponent data contains only five supported victim groups; its sum is not a national all-user total.
- The age bands are source labels; adjacent label endpoints must not be treated as individual-level ages. Only source-reported Male/Female categories are supplied.
- The coverage heatmap describes prepared extracts, not whether MoRTH has published other detailed years.

## Validation and reproduction

Run the README data rebuild commands with Poppler. The extractor rejects unexpected columns/serials, duplicated keys, invalid counts, unmatched totals, inconsistent month/outcome/time/matrix sums and unknown source IDs. It writes a checks manifest with report year, physical page, source column, extracted sum and printed total. Checksum validation and reconciliation are evidence of faithful extraction, not a guarantee that the original report has no errors.

The API queries one immutable CSV-derived DuckDB table at a time, constrained by dataset. No cross-fact joins occur. Its snapshot identifier is SHA-256 of facts.csv; exports and analysis results identify that snapshot. Python/SQL analysis uses a same-fact adjacent-year join only for a complete common-state comparison.

Historical boundaries and reporting definitions remain those of the source tables. The illustrative current GeoJSON cannot establish authoritative historical borders or precise incident locations.
