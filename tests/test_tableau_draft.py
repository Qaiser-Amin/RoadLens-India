"""Structural/data checks only: these do NOT test Tableau's engine or UI."""
import csv
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tableau'

class TableauDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree=ET.parse(OUT/'RoadLens-India-DRAFT.twb').getroot()
        cls.sources={d.get('name'):d for d in cls.tree.findall('datasources/datasource')}
        cls.sheets={w.get('name'):w for w in cls.tree.findall('worksheets/worksheet')}
        cls.manifest=json.loads((OUT/'build-manifest.json').read_text())

    def test_package_has_matching_workbook_and_four_csvs(self):
        with zipfile.ZipFile(OUT/'RoadLens-India-DRAFT.twbx') as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(set(z.namelist()),{'RoadLens-India-DRAFT.twb',*[f'Data/{n}.csv' for n in ['Totals','Vehicles','Causes','Roads']]})
            self.assertEqual(z.read('RoadLens-India-DRAFT.twb'),(OUT/'RoadLens-India-DRAFT.twb').read_bytes())
            for name in ['Totals','Vehicles','Causes','Roads']:
                self.assertEqual(z.read(f'Data/{name}.csv'),(OUT/'Data'/f'{name}.csv').read_bytes())

    def test_four_sources_use_local_portable_paths_without_fact_joins(self):
        self.assertEqual(set(self.sources),{'Parameters','Totals','Vehicles','Causes','Roads'})
        for name,ds in self.sources.items():
            if name=='Parameters':continue
            c=ds.find('connection')
            self.assertEqual(c.get('class'),'textscan')
            self.assertEqual(c.get('directory'),'Data')
            self.assertEqual(c.get('filename'),name+'.csv')
            self.assertTrue((OUT/c.get('directory')/c.get('filename')).is_file())
            self.assertEqual(len(c.findall('relation')),1)
            self.assertEqual(c.find('relation').get('type'),'table')

    def test_all_calculation_references_resolve_locally_or_to_parameters(self):
        parameters={c.get('name') for c in self.sources['Parameters'].findall('column')}
        for name,ds in self.sources.items():
            if name=='Parameters':continue
            known={c.get('name') for c in ds.findall('column')}|{g.get('name') for g in ds.findall('group')}
            for calc in ds.findall('column/calculation'):
                formula=calc.get('formula')
                for p in re.findall(r'\[Parameters\]\.\[([^]]+)\]',formula):self.assertIn(f'[{p}]',parameters)
                formula=re.sub(r'\[Parameters\]\.\[[^]]+\]','',formula)
                for field in re.findall(r'\[[^]]+\]',formula):self.assertIn(field,known,(name,formula))

    def test_every_analytic_sheet_uses_shared_year_and_state_context_filters(self):
        self.assertEqual(len(self.sheets),26)
        for name,w in self.sheets.items():
            if self.manifest['worksheets'][name]['controls']:continue
            filters=w.findall('table/view/filter')
            for key in ['Year Filter','State Filter']:
                f=next(f for f in filters if key in f.get('column',''))
                self.assertEqual(f.get('context'),'true')
                self.assertEqual(f.find('groupfilter').get('member'),'true')
            if self.manifest['worksheets'][name]['category']:
                self.assertEqual(self.manifest['worksheets'][name]['source'],'Vehicles')

    def test_dashboard_zones_and_actions_reference_existing_targets(self):
        dashboards=self.tree.findall('dashboards/dashboard')
        self.assertEqual(len(dashboards),3)
        for d in dashboards:
            for z in d.findall('.//zone'):
                if z.get('name'):self.assertIn(z.get('name'),self.sheets)
            self.assertEqual(len(d.findall('.//zone[@type-v2="paramctrl"]')),7 if d.get('name').startswith('2') else 5)
        actions=self.tree.findall('actions/edit-parameter-action')
        self.assertEqual(len(actions),11)  # four state actions + seven reset actions
        for a in actions:self.assertIn(a.find('source').get('worksheet'),self.sheets)
        reset=[a for a in actions if a.find('source').get('worksheet')=='Reset']
        self.assertEqual(len(reset),7)
        nav=self.tree.findall('actions/nav-action')
        self.assertEqual({a.find('params/param').get('value') for a in nav},{d.get('name') for d in dashboards})

    def test_sets_are_dynamic_and_combined_by_intersection(self):
        ds=self.sources['Totals']
        self.assertEqual(ds.find("group[@name='[High Accidents]']/groupfilter").get('count'),'[Parameters].[Top N]')
        self.assertIn('[Parameters].[High Severity Threshold]',ds.find("group[@name='[High Severity]']/groupfilter").get('expression'))
        gf=ds.find("group[@name='[High Accidents AND High Severity]']/groupfilter")
        self.assertEqual(gf.get('function'),'intersection')
        self.assertEqual({c.get('field') for c in gf},{'[High Accidents]','[High Severity]'})

    def test_prepared_data_preserves_every_observation_and_only_adds_null_scaffold(self):
        for ds,table in [('Totals','state_totals'),('Vehicles','vehicle_categories'),('Causes','causes'),('Roads','road_types')]:
            with (ROOT/'data/input'/f'{table}.csv').open(newline='') as f:raw=list(csv.DictReader(f))
            with (OUT/'Data'/f'{ds}.csv').open(newline='') as f:prepared=list(csv.DictReader(f))
            lookup={(r['Year'],r['State'],r['Category']):r for r in prepared}
            self.assertEqual(len(lookup),len(prepared))
            original={(r['year'],r['state'],r['category']):r for r in raw}
            for key,r in original.items():
                p=lookup[key]
                self.assertEqual((p['Accidents'],p['Fatalities'],p['Source ID']),(r['accidents'],r['fatalities'],r['source_id']))
            for key,r in lookup.items():
                if key not in original:self.assertEqual((r['Accidents'],r['Fatalities'],r['Source ID']),('','',''))
            self.assertEqual(len({r['State'] for r in prepared}),36)

    def test_incompatible_two_wheeler_denominators_are_not_invented(self):
        with (OUT/'Data/Vehicles.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        self.assertTrue(all(r['Accidents']=='' for r in rows))
        self.assertEqual(sum(int(r['Fatalities']) for r in rows if r['Year']=='2023' and r['Category']=='Two-wheelers'),77539)
        self.assertTrue(all(r['Fatalities']=='' for r in rows if r['Year']=='2020'))
        self.assertIn('NOT OPENED OR TESTED IN TABLEAU',self.manifest['status'])



class CombinedRiskMembershipTests(unittest.TestCase):
    def test_combined_risk_sheet_shows_union_of_both_sets_not_measure_top_n(self):
        import xml.etree.ElementTree as ET
        root = ET.parse(Path(__file__).resolve().parents[1] / 'tableau' / 'RoadLens-India-DRAFT.twb').getroot()
        sheet = next(w for w in root.iter('worksheet') if w.get('name') == 'Combined Risk Ranking')
        unions = [g for g in sheet.iter('groupfilter') if g.get('function') == 'union']
        self.assertEqual(len(unions), 1)
        refs = {g.get('field') for g in unions[0] if g.get('function') == 'reference'}
        self.assertEqual(refs, {'[Totals].[High Accidents]', '[Totals].[High Severity]'})
        filters = sheet.find('table/view').findall('filter')
        self.assertFalse([g for f in filters for g in f.iter('groupfilter') if g.get('function') == 'end'])

if __name__=='__main__':unittest.main()
