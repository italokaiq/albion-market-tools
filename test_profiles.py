import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from production_profiles import ProductionProfiles
from persistence import write_settings
from launcher import diagnostic

class ProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'profiles.json';self.store=ProductionProfiles(self.path)
    def tearDown(self):self.temp.cleanup()
    def test_roundtrip_without_market_prices(self):
        context=('T4_MAIN_AXE','10',(('T4_PLANKS','8',True),))
        self.store.save('Machado',context,{('craft','7'):('15','100')},'2')
        settings,shipping,stamp=self.store.load('Machado',context)
        self.assertEqual(settings,{('craft','7'):('15','100')});self.assertEqual(shipping,'2')
        profile=self.store.read()['profiles']['Machado']
        self.assertEqual(set(profile),{'context','settings','shipping','saved_at'})
    def test_wrong_recipe_rejected(self):
        self.store.save('Um',('A',),{},'0')
        with self.assertRaises(ValueError):self.store.load('Um',('B',))

    def test_malformed_cost_entries_rejected(self):
        self.store.save('Um',('A',),{},'0')
        data=self.store.read();data['profiles']['Um']['settings']=[[[], '7', '0', '0']]
        self.path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):self.store.load('Um',('A',))

    def test_diagnostic_rejects_wrong_catalog_shape(self):
        for name in ('items.json','world.json','recipes.json','recipes_source.json','market_items.json'):
            (self.path.parent/name).write_text('{}')
        with patch('launcher.resource_path',lambda name:self.path.parent/name):
            report=diagnostic()
        self.assertEqual(report['catalogos']['items.json'],'Formato inválido')
    def test_backup_preserves_previous_profile(self):
        self.store.save('Um',('A',),{},'0');before=self.path.read_bytes()
        self.store.save('Dois',('B',),{},'1')
        self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(),before)
    def test_corrupt_file_is_not_overwritten(self):
        self.path.write_text('broken')
        with self.assertRaises(ValueError):self.store.save('Um',(),{},'0')
        self.assertEqual(self.path.read_text(),'broken')
    def test_failed_atomic_replace_preserves_previous_settings(self):
        write_settings(self.path,{'before':True})
        with patch('persistence.os.replace',side_effect=OSError('failure')):
            with self.assertRaises(OSError):write_settings(self.path,{'after':True})
        self.assertEqual(json.loads(self.path.read_text()),{'before':True})
        self.assertEqual(list(self.path.parent.glob('*.tmp')),[])
    def test_diagnostic_has_no_market_prices(self):
        report=diagnostic()
        self.assertTrue(all(v=='OK' for v in report['catalogos'].values()))
        self.assertEqual(report['rede'],'não testada')

    def test_loaded_profile_requires_cost_confirmation(self):
        import tkinter as tk
        from dashboard import Dashboard
        from monitor import database,Feed
        root=tk.Tk();root.withdraw();app=Dashboard(root,database(':memory:'),Feed(),start_feed=False)
        try:
            c=app.calculators;c.apply_recipe('T4_MAIN_AXE');c.open_production_planner()
            p=c.production_planner;p.profiles=self.store
            p.profile_name.set('Teste');p.shipping.set('0')
            p.editors['7'][0].set('15');p.editors['7'][1].set('100')
            p.save_profile();p.load_profile()
            self.assertTrue(p.profile_pending);self.assertIsNone(p.result)
            self.assertIn('Confirme',p.status.cget('text'))
            p.confirm_costs()
            self.assertFalse(p.profile_pending);self.assertIsNotNone(p.result)
            root.update_idletasks()
        finally:app.close()
