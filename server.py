#!/usr/bin/env python3
"""RoadLens local development server. Python standard library only."""
import argparse
import csv
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
TABLES = ('state_totals', 'vehicle_categories', 'causes', 'road_types')

def dataset():
    result = {}
    for table in TABLES:
        with (ROOT / 'data/input' / f'{table}.csv').open(newline='') as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row['year'] = int(row['year'])
            for metric in ('accidents', 'fatalities'):
                row[metric] = int(row[metric]) if row[metric] != '' else None
        result[table] = rows
    result['sources'] = json.loads((ROOT / 'data/input/sources.json').read_text())
    return result

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/api/data':
            content = json.dumps(dataset(), allow_nan=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif url.path == '/api/download':
            table = parse_qs(url.query).get('table', [''])[0]
            if table not in TABLES:
                self.send_error(400, 'Choose a valid dataset')
                return
            content = (ROOT / 'data/input' / f'{table}.csv').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="{table}.csv"')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            super().do_GET()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'RoadLens running on port {args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
