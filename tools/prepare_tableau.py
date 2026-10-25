#!/usr/bin/env python3
"""Validate independently verified extracts and emit separate Tableau data sources.

No web scraping, imputation, aggregation across incompatible grains, or sample data.
Python 3.12+, standard library only.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

METRICS = ('accidents', 'fatalities')
FIELDS = ['year', 'state', 'category', *METRICS, 'source_id']
TABLES = ('state_totals', 'vehicle_categories', 'causes', 'road_types')
STATES = '''Andaman and Nicobar Islands|Andhra Pradesh|Arunachal Pradesh|Assam|Bihar|Chandigarh|Chhattisgarh|Dadra and Nagar Haveli|Daman and Diu|Dadra and Nagar Haveli and Daman and Diu|Delhi|Goa|Gujarat|Haryana|Himachal Pradesh|Jammu and Kashmir|Jharkhand|Karnataka|Kerala|Ladakh|Lakshadweep|Madhya Pradesh|Maharashtra|Manipur|Meghalaya|Mizoram|Nagaland|Odisha|Puducherry|Punjab|Rajasthan|Sikkim|Tamil Nadu|Telangana|Tripura|Uttar Pradesh|Uttarakhand|West Bengal'''.split('|')


def read_table(path, table, sources):
    result, keys = [], set()
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f'{path}: expected columns {FIELDS}')
        for number, row in enumerate(reader, 2):
            label = f'{path}:{number}'
            if set(row) != set(FIELDS) or any(v is None for v in row.values()):
                raise ValueError(f'{label}: malformed CSV record')
            if row['state'] not in STATES:
                raise ValueError(f'{label}: unknown state; normalize explicitly, exclude national totals')
            year = int(row['year'])
            if not 1950 <= year <= 2100:
                raise ValueError(f'{label}: invalid reporting year')
            if not row['category'].strip() or (table == 'state_totals' and row['category'] != 'All'):
                raise ValueError(f'{label}: invalid category (state_totals requires All)')
            key = (year, row['state'], row['category'])
            if key in keys:
                raise ValueError(f'{label}: duplicate grain {key}')
            keys.add(key)
            source = sources.get(row['source_id'])
            if not source or source.get('table') != table or source.get('verified') is not True:
                raise ValueError(f'{label}: missing verified provenance for this table')
            for name in METRICS:
                value = row[name]
                if value and (not value.isascii() or not value.isdecimal()):
                    raise ValueError(f'{label}: {name} must be a nonnegative integer or blank')
            # Counts can exceed accidents (multiple deaths per accident); do not cap severity.
            result.append(row)
    return result


def prepare(input_dir, output_dir):
    manifest = json.loads((input_dir / 'sources.json').read_text())
    sources = {}
    for source in manifest:
        required = ('source_id', 'table', 'title', 'url', 'locator', 'retrieved_on',
                    'definition', 'coverage', 'sha256', 'verified')
        if any(k not in source or source[k] in ('', None) for k in required):
            raise ValueError('Each source requires complete provenance metadata')
        if source['source_id'] in sources or source['table'] not in TABLES:
            raise ValueError('Duplicate source ID or unknown table')
        if not source['url'].startswith('https://'):
            raise ValueError('Source URL must use HTTPS')
        if len(source['sha256']) != 64 or any(c not in '0123456789abcdef' for c in source['sha256']):
            raise ValueError('Expected SHA-256 of archived original source document/query export')
        sources[source['source_id']] = source
    tables = {table: read_table(input_dir / f'{table}.csv', table, sources) for table in TABLES}
    if not tables['state_totals']:
        raise ValueError('No verified state totals: refusing to emit an empty dashboard data source')
    # Validate all inputs before replacing output files.
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for table, rows in tables.items():
        with (output_dir / f'{table}.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda r: (int(r['year']), r['state'], r['category'])))
        summary[table] = {'rows': len(rows), 'years': sorted({int(r['year']) for r in rows}),
                          'states': len({r['state'] for r in rows})}
    # Scaffold supports explicit unavailable marks for absent state-year-category records.
    years = sorted({r['year'] for rows in tables.values() for r in rows}, key=int)
    with (output_dir / 'scaffold.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['table', 'year', 'state', 'category'])
        for table, rows in tables.items():
            categories = sorted({r['category'] for r in rows}) or (['All'] if table == 'state_totals' else [])
            for year in years:
                for state in STATES:
                    for category in categories:
                        writer.writerow([table, year, state, category])
    (output_dir / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n')
    summary['input_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(input_dir.iterdir()) if p.is_file()}
    (output_dir / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/input'))
    parser.add_argument('--output', type=Path, default=Path('data/tableau'))
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.input, args.output), indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Validation failed: {exc}\n')
