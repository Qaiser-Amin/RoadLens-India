#!/usr/bin/env python3
"""Download two pinned official MoRTH PDFs with TLS and SHA-256 verification."""
import hashlib
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    2022: {
        'url': 'https://morth.nic.in/backend/documents/uploaded/1755600426_RA_2022_30_Oct.pdf',
        'sha256': 'd1908170c4e25153539d82244f0fe269805a577b71e42259a53a57422dd8d8ed',
    },
    2023: {
        'url': 'https://morth.nic.in/backend/documents/uploaded/Road-Accident-in-India-2023-Publications.pdf',
        'sha256': '901505420d5b387052ac51e36b4bdce0274f6326b614f9ebcee6e7954d45b5b0',
    },
}


def report_path(year):
    return ROOT / 'data' / 'sources' / f'road-accidents-india-{year}.pdf'


def verify(path, expected):
    if not path.read_bytes().startswith(b'%PDF'):
        raise ValueError(f'{path}: not a PDF (the old website URLs return HTML)')
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f'{path}: checksum mismatch; investigate official source revision')


def main():
    for year, meta in REPORTS.items():
        path = report_path(year)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            verify(path, meta['sha256'])
            print(f'{year}: existing official PDF checksum verified')
            continue
        temp = path.with_suffix('.download')
        try:
            with urllib.request.urlopen(meta['url'], timeout=60) as response, temp.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            verify(temp, meta['sha256'])
            temp.replace(path)
            print(f'{year}: downloaded and checksum verified')
        finally:
            temp.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
