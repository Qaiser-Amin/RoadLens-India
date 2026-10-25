#!/usr/bin/env python3
"""Extract pinned MoRTH tables using Poppler pdftotext; verify before writing CSVs.

Only supported report revisions are accepted. No inferred accident denominator is
attached to road-user deaths. Annexure figures and footnotes remain authoritative.
"""
import csv
import json
from pathlib import Path
import re
import subprocess

from fetch_morth import ROOT, REPORTS, report_path, verify
from prepare_tableau import FIELDS

# Serial order in the pinned 2023 annexures, not alphabetical order.
ORDER = '''Andhra Pradesh|Arunachal Pradesh|Assam|Bihar|Chhattisgarh|Goa|Gujarat|Haryana|Himachal Pradesh|Jharkhand|Karnataka|Kerala|Madhya Pradesh|Maharashtra|Manipur|Meghalaya|Mizoram|Nagaland|Odisha|Punjab|Rajasthan|Sikkim|Tamil Nadu|Telangana|Tripura|Uttarakhand|Uttar Pradesh|West Bengal|Andaman and Nicobar Islands|Chandigarh|Dadra and Nagar Haveli and Daman and Diu|Delhi|Jammu and Kashmir|Ladakh|Lakshadweep|Puducherry'''.split('|')
ORDER_2022 = ORDER[:31] + ['Daman and Diu'] + ORDER[31:]
TOKEN = re.compile(r'(?<!\S)(?:\d[\d,]*(?:\.\d+)?|NA|-)(?!\S)')

# PDF page numbers, distinct from printed page numbers. Table column numbers are
# printed in each annexure. Ignore ranks, percentage shares, and injury measures.
SPECS = {
    (2023, 141): ([3, 4, 5, 6], [7]),
    (2023, 143): ([3, 4, 5, 6], [7]),
    (2023, 151): ([3, 4, 5, 6], [7]),
    (2023, 152): ([3, 4, 5, 6], [7]),
    (2023, 166): ([3, 4, 5, 6], [7]),
    (2023, 167): ([3, 4, 5, 6], [7]),
    (2023, 171): ([7, 8, 9, 10], [11]),
    (2023, 172): ([12, 13, 14, 15], [16, 21]),
    (2023, 204): ([5, 8, 11, 15, 18], [12]),
    (2023, 205): ([21, 24, 27, 30], []),
    (2023, 220): ([3, 5, 10, 11], [4, 6]),
    (2023, 221): ([15, 16, 20, 21], []),
    (2023, 222): ([25, 26, 30, 31], []),
    (2022, 181): ([5, 8, 11, 15, 18], [12]),
    (2022, 182): ([21, 24, 27, 30], []),
    (2022, 193): ([3, 5, 10, 11, 15, 16], [4, 6]),
    (2022, 194): ([20, 21, 25, 26, 30, 31], []),
}


def count(value):
    # Conservative handling: an unqualified dash is not asserted to mean zero.
    if value in ('NA', '-', ''):
        return ''
    clean = value.replace(',', '')
    if not clean.isascii() or not clean.isdecimal():
        raise ValueError(f'Invalid count cell: {value!r}')
    return int(clean)


def parse_page(text, year, page):
    selected, ranks = SPECS[year, page]
    lines = text.splitlines()
    header_idx = next(i for i, line in enumerate(lines)
                      if re.match(r'^\s*1\s+2\s+\d+\s+\d+\s+\d+', line))
    columns = [int(x) for x in re.findall(r'\d+', lines[header_idx])][2:]
    rows, reported_totals = {}, None
    for line in lines[header_idx + 1:]:
        if re.match(r'^\s*Total\s', line):
            values = [m.group() for m in TOKEN.finditer(line)]
            total_columns = [c for c in columns if c not in ranks]
            if len(values) != len(total_columns):
                raise ValueError(f'{year} PDF p{page}: unexpected total column count')
            reported_totals = dict(zip(total_columns, values))
            break
        match = re.match(r'^\s*(\d{1,2})\s+', line)
        if not match:
            continue  # wrapped state names contain no count cells
        serial = int(match.group(1))
        values = [m.group() for m in TOKEN.finditer(line)][1:]
        if serial in rows:
            raise ValueError('Duplicate table serial number')
        if year == 2023 and serial == 34:
            # Ladakh has blank ranks, not missing measure cells.
            if page == 204:
                values.insert(9, 'NA')
            elif page == 220:
                values.insert(1, 'NA')
                values.insert(3, 'NA')
        if page in (141, 143, 151, 152, 166, 167):
            # Relevant years precede optional ranks/share columns.
            if len(values) < 4:
                raise ValueError('Missing year columns')
            row = dict(zip(columns[:4], values[:4]))
        else:
            if len(values) == len(columns) - 1 and columns[-1] in ranks:
                values.append('NA')
            if len(values) != len(columns):
                raise ValueError(f'{year} PDF p{page}, row {serial}: unexpected column count')
            row = dict(zip(columns, values))
        rows[serial] = row
    expected_serials = set(range(1, 38 if year == 2022 else 37))
    if set(rows) != expected_serials or reported_totals is None:
        raise ValueError(f'{year} PDF p{page}: incomplete table')
    checks = []
    for column in selected:
        total = sum(count(row[column]) or 0 for row in rows.values())
        expected = count(reported_totals[column])
        if total != expected:
            raise ValueError(f'{year} PDF p{page} column {column}: sum {total} != {expected}')
        checks.append(dict(report=year, pdf_page=page, column=column,
                           state_sum=total, printed_total=expected, passed=True))
    if page in (181, 182, 204, 205):
        for serial, row in rows.items():
            for total_col in selected:
                male, female, total = [count(row[c]) for c in (total_col - 2, total_col - 1, total_col)]
                if all(v != '' for v in (male, female, total)) and male + female != total:
                    raise ValueError('Road-user sex subtotals do not reconcile')
    return rows, checks


def main():
    texts = {}
    for year, meta in REPORTS.items():
        path = report_path(year)
        verify(path, meta['sha256'])
        proc = subprocess.run(['pdftotext', '-layout', str(path), '-'],
                              check=True, capture_output=True, text=True)
        texts[year] = proc.stdout.split('\f')
    parsed, checks = {}, []
    for year, page in SPECS:
        parsed[year, page], evidence = parse_page(texts[year][page - 1], year, page)
        checks.extend(evidence)

    tables = {name: [] for name in ('state_totals', 'vehicle_categories', 'causes', 'road_types')}
    def cell(report, page, serial, column):
        return count(parsed[report, page][serial][column])

    def add(table, year, state, category, accidents, fatalities, source):
        tables[table].append(dict(zip(FIELDS, (year, state, category, accidents, fatalities, source))))

    for serial, state in enumerate(ORDER, 1):
        for offset, year in enumerate(range(2020, 2024)):
            add('state_totals', year, state, 'All', cell(2023,141,serial,3+offset),
                cell(2023,143,serial,3+offset), 'morth2023_totals')
            for category, accident_page, fatal_page, accident_col, fatal_col in [
                ('National highways (including expressways)',151,152,3,3),
                ('State highways',166,167,3,3),
                ('Other roads',171,172,7,12),
            ]:
                add('road_types', year, state, category,
                    cell(2023,accident_page,serial,accident_col+offset),
                    cell(2023,fatal_page,serial,fatal_col+offset), 'morth2023_roads')

    for year, pages, cause_parts in [
        (2022, [181,182], [(193,[('Over-speeding',3,5),('Drunken driving / alcohol and drugs',10,11),
                              ('Driving on wrong side',15,16)]),
                           (194,[('Jumping red light',20,21),('Use of mobile phone',25,26),('Others',30,31)])]),
        (2023, [204,205], [(220,[('Over-speeding',3,5),('Drunken driving / alcohol and drugs',10,11)]),
                           (221,[('Driving on wrong side',15,16),('Jumping red light',20,21)]),
                           (222,[('Use of mobile phone',25,26),('Others',30,31)])]),
    ]:
        order = ORDER_2022 if year == 2022 else ORDER
        for serial, state in enumerate(order, 1):
            if year == 2022 and serial == 32:
                # Explicit report footnote: Daman & Diu is included in D&N Haveli.
                # All cells in redundant Daman & Diu row must remain NA.
                for page in pages + [p for p, _ in cause_parts]:
                    if any(v != 'NA' for v in parsed[year,page][serial].values()):
                        raise ValueError('Unexpected non-NA data in redundant Daman & Diu row')
                continue
            categories = [(pages[0],[('Pedestrians',5),('Bicycles',8),('Two-wheelers',11),
                                     ('Auto rickshaws',15),('Cars, taxis, vans and LMV',18)]),
                          (pages[1],[('Trucks / lorries',21),('Buses',24),
                                     ('Other non-motor vehicles (E-rickshaw)',27),('Others',30)])]
            for page, category_cols in categories:
                for category, col in category_cols:
                    add('vehicle_categories',year,state,category,'',cell(year,page,serial,col),f'morth{year}_road_users')
            for page, category_cols in cause_parts:
                for category, ac, fc in category_cols:
                    accidents = cell(year,page,serial,ac)
                    if year == 2022 and state == 'Jammu and Kashmir' and category == 'Jumping red light':
                        # Source prints 0 but footnote explicitly says accidents not reported.
                        accidents = ''
                    add('causes',year,state,category,accidents,cell(year,page,serial,fc),f'morth{year}_violations')

    # Independent cross-table checks for the current year: all states, all categories.
    for state in ORDER:
        total = next(r for r in tables['state_totals'] if r['state']==state and r['year']==2023)
        for table in ('vehicle_categories','causes','road_types'):
            for metric in ('accidents','fatalities'):
                vals=[r[metric] for r in tables[table] if r['state']==state and r['year']==2023]
                if total[metric] != '' and all(v != '' for v in vals):
                    if sum(vals) != total[metric]:
                        raise ValueError(f'Cross-table disagreement: {state} {table} {metric}')
                    checks.append(dict(year=2023,state=state,table=table,metric=metric,
                                       category_sum=sum(vals),state_total=total[metric],passed=True))
    manifest=[]
    for year in (2022,2023):
        specs=[('road_users','vehicle_categories',
                'Annexure 29; PDF pp.181–182 (printed 164–165)' if year==2022 else
                'Annexure 29; PDF pp.204–205 (printed 175–176)',
                'Persons killed classified by road-user category, both sexes. Not impacting-vehicle accidents; accident denominator unavailable. In 2023 Kerala some Other figures are included in Pedestrian category.'),
               ('violations','causes',
                'Annexure 35; PDF pp.193–194 (printed 176–177)' if year==2022 else
                'Annexure 35; PDF pp.220–222 (printed 191–193)',
                'Accidents and persons killed classified by reported traffic-rule violation. Not a causal estimate. 2022 J&K jumping-red-light accident count left blank per explicit source footnote despite printed zero.')]
        if year==2023:
            specs += [('totals','state_totals','Annexures 2–3; PDF pp.141,143 (printed 112,114)',
                       'State/UT reported accidents and persons killed for 2020–2023. NA/dash retained as unavailable. Source footnotes document reconciled historical Tamil Nadu and West Bengal figures.'),
                      ('roads','road_types','Annexures 9–10,14–15,19; PDF pp.151–152,166–167,171–172',
                       'Accidents and persons killed on national highways (including expressways), state highways, other roads, 2020–2023. No state highways in Chandigarh or Delhi. NA/dash retained as unavailable.')]
        for suffix,table,locator,definition in specs:
            manifest.append(dict(source_id=f'morth{year}_{suffix}',table=table,
                title=f'MoRTH Road Accidents in India {year}',url=REPORTS[year]['url'],
                locator=locator,retrieved_on='2026-10-25',definition=definition,
                coverage=('36 current reporting states/UTs; 2020–2023' if suffix in ('totals','roads')
                          else f'36 reporting states/UTs; {year}; road-user categories, not impacting vehicles' if suffix=='road_users'
                          else f'36 reporting states/UTs; {year}; reported traffic violations')
                         + '; 2022 D&N Haveli includes Daman & Diu per report footnote; redundant all-NA row excluded.',
                sha256=REPORTS[year]['sha256'],verified=True,
                verification='Pinned official PDF, exact row coverage, selected-column sums reconciled to printed totals; road-user male+female totals reconciled; source pages visually spot-checked. Underlying state reporting not independently audited.'))
    out=ROOT/'data'/'input'
    out.mkdir(parents=True,exist_ok=True)
    # All parsing, reconciliations and provenance checks finish before inputs are replaced.
    for table,rows in tables.items():
        with (out/f'{table}.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS)
            writer.writeheader();writer.writerows(rows)
    (out/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    evidence={'report_checksums_verified':True,'checks':checks,
              'rows':{table:len(rows) for table,rows in tables.items()},
              'footnote_overrides':['2022 J&K jumping-red-light accidents: printed 0 -> blank (explicit not-reported footnote)'],
              'tableau_interactions_tested':False}
    (ROOT/'data'/'sources'/'extraction-validation.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'rows':evidence['rows'],'reconciliation_checks':len(checks),
                      'source_checksum_verification':'passed','tableau_interactions_tested':False},indent=2))


if __name__=='__main__':
    main()
