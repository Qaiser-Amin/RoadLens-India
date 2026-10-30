#!/usr/bin/env python3
"""Validate draft TWB/TWBX XML against a caller-supplied Tableau XSD.

Requires lxml for this optional diagnostic command only. Schema validation cannot
compile Tableau formulas, resolve geographic names or test desktop interactions.
Keep the schema's imported XSD files alongside it. Network resolution is disabled.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema',required=True,type=Path)
    parser.add_argument('--workbook',type=Path,default=Path(__file__).resolve().parents[1]/'tableau/RoadLens-India-DRAFT.twbx')
    parser.add_argument('--report',type=Path,help='Write a hash-bound record after successful validation')
    parser.add_argument('--schema-url',help='Optional provenance URL; this command does not fetch it')
    args=parser.parse_args()
    try:
        from lxml import etree
    except ImportError:
        parser.exit(2,'Install the optional validator dependency: python -m pip install lxml\n')
    xml_parser=etree.XMLParser(no_network=True,resolve_entities=False)
    try:
        schema=etree.XMLSchema(etree.parse(str(args.schema.resolve()),xml_parser))
        if args.workbook.suffix.lower()=='.twbx':
            with zipfile.ZipFile(args.workbook) as archive:
                names=[n for n in archive.namelist() if n.lower().endswith('.twb')]
                if len(names)!=1:
                    parser.exit(2,'Expected exactly one TWB inside the packaged workbook\n')
                document=etree.parse(BytesIO(archive.read(names[0])),xml_parser)
        else:
            document=etree.parse(str(args.workbook),xml_parser)
        if not schema.validate(document):
            for error in schema.error_log:
                print(f'Line {error.line}: {error.message}')
            parser.exit(1,'Workbook failed the supplied XML schema\n')
        print(f'PASS: {args.workbook.name} matches {args.schema.name}')
        print('Tableau Desktop loading, formula compilation and interactions remain unverified.')
        if args.report:
            record={
                'checked_at_utc':datetime.now(timezone.utc).isoformat(),
                'result':'PASS — supplied XML schema only',
                'workbook':args.workbook.name,
                'workbook_sha256':hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
                'schema':args.schema.name,
                'schema_sha256':hashlib.sha256(args.schema.read_bytes()).hexdigest(),
                'schema_source_url':args.schema_url,
                'schema_supporting_files_sha256':{
                    p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(args.schema.parent.glob('*.xsd')) if p!=args.schema
                },
                'tableau_desktop_retest':'NOT RUN',
                'limits':'External community-hosted schema; not a Tableau engine, formula, geography or interaction test.',
            }
            args.report.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    except (OSError,zipfile.BadZipFile,etree.XMLSyntaxError,etree.XMLSchemaError) as error:
        parser.exit(2,f'Validation could not complete: {error}\n')


if __name__=='__main__':main()
