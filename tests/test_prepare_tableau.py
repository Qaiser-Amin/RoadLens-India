"""Synthetic parser fixtures only. These tests do not validate Tableau behavior."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).parents[1] / 'tools/prepare_tableau.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'out'
        sources = []
        for table in p.TABLES:
            sources.append(dict(source_id=table, table=table, title='SYNTHETIC TEST ONLY',
                url='https://example.invalid/test', locator='fixture', retrieved_on='2026-10-25',
                definition='synthetic parser fixture', coverage='test only', sha256='0'*64, verified=True))
            self.write(table, [])
        (self.root / 'sources.json').write_text(json.dumps(sources))
        self.write('state_totals', [['2022', 'Kerala', 'All', '100', '20', 'state_totals']])

    def write(self, table, rows):
        with (self.root / f'{table}.csv').open('w', newline='') as f:
            w = csv.writer(f)
            w.writerow(p.FIELDS)
            w.writerows(rows)

    def run_pipeline(self):
        return p.prepare(self.root, self.output)

    def test_valid_separate_sources(self):
        self.write('vehicle_categories', [['2022', 'Kerala', 'Two-wheelers', '', '10', 'vehicle_categories']])
        result = self.run_pipeline()
        self.assertEqual(result['state_totals']['rows'], 1)
        self.assertEqual(result['vehicle_categories']['rows'], 1)
        with (self.output / 'vehicle_categories.csv').open() as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row['accidents'], '')
        self.assertEqual(row['fatalities'], '10')
        self.assertTrue((self.output / 'scaffold.csv').exists())

    def test_duplicate_grain_rejected(self):
        row = ['2022', 'Kerala', 'All', '100', '20', 'state_totals']
        self.write('state_totals', [row, row])
        with self.assertRaisesRegex(ValueError, 'duplicate grain'):
            self.run_pipeline()
        self.assertFalse(self.output.exists())

    def test_unverified_rejected(self):
        path = self.root / 'sources.json'
        sources = json.loads(path.read_text())
        sources[0]['verified'] = False
        path.write_text(json.dumps(sources))
        with self.assertRaisesRegex(ValueError, 'verified provenance'):
            self.run_pipeline()

    def test_missing_differs_from_zero(self):
        self.write('state_totals', [['2022', 'Kerala', 'All', '0', '', 'state_totals']])
        self.run_pipeline()
        with (self.output / 'state_totals.csv').open() as f:
            row = next(csv.DictReader(f))
        self.assertEqual((row['accidents'], row['fatalities']), ('0', ''))

    def test_national_total_rejected(self):
        self.write('state_totals', [['2022', 'India', 'All', '100', '20', 'state_totals']])
        with self.assertRaisesRegex(ValueError, 'unknown state'):
            self.run_pipeline()

    def test_invalid_counts(self):
        for bad in ('-1', '1.2', 'NA', '1,000'):
            with self.subTest(bad=bad):
                self.write('state_totals', [['2022', 'Kerala', 'All', bad, '20', 'state_totals']])
                with self.assertRaisesRegex(ValueError, 'nonnegative integer'):
                    self.run_pipeline()

    def test_no_false_severity_cap(self):
        self.write('state_totals', [['2022', 'Kerala', 'All', '1', '3', 'state_totals']])
        self.assertEqual(self.run_pipeline()['state_totals']['rows'], 1)

    def test_empty_input_fails(self):
        self.write('state_totals', [])
        with self.assertRaisesRegex(ValueError, 'No verified state totals'):
            self.run_pipeline()

    def test_unknown_provenance(self):
        self.write('state_totals', [['2022', 'Kerala', 'All', '1', '1', 'missing']])
        with self.assertRaisesRegex(ValueError, 'verified provenance'):
            self.run_pipeline()


if __name__ == '__main__':
    unittest.main()
