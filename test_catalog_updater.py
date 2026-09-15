import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import catalog_updater as cu


class CatalogUpdaterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.patcher = patch('catalog_updater.resource_path', lambda name: self.dir / name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def test_check_updates_flags_size_mismatch_and_matches(self):
        (self.dir / 'items.json').write_bytes(b'x' * 100)
        (self.dir / 'world.json').write_bytes(b'x' * 50)
        (self.dir / 'recipes_source.json').write_bytes(b'x' * 10)
        sizes = {cu.SOURCES['items.json'][0]: 999, cu.SOURCES['world.json'][0]: 50,
                 cu.SOURCES['recipes_source.json'][0]: 10}
        report = cu.check_updates(sizer=lambda url: sizes[url])
        self.assertTrue(report['items.json']['changed'])
        self.assertFalse(report['world.json']['changed'])
        self.assertFalse(report['recipes_source.json']['changed'])

    def test_check_updates_missing_local_file_counts_as_changed(self):
        report = cu.check_updates(sizer=lambda url: 123)
        self.assertTrue(report['items.json']['changed'])
        self.assertIsNone(report['items.json']['local_size'])

    def test_check_updates_reports_sizer_failure_without_raising(self):
        def failing(url):
            raise OSError('sem rede')
        report = cu.check_updates(sizer=failing)
        self.assertFalse(report['items.json']['ok'])
        self.assertIn('sem rede', report['items.json']['error'])

    def test_download_and_apply_writes_only_validated_files(self):
        good_items = json.dumps([{'UniqueName': 'X'}]).encode('utf-8')
        bad_world = b'{"not":"a list"}'
        def fetcher(url):
            return good_items if url == cu.SOURCES['items.json'][0] else bad_world
        results = cu.download_and_apply(['items.json', 'world.json'], fetcher=fetcher)
        self.assertTrue(results['items.json']['ok'])
        self.assertFalse(results['world.json']['ok'])
        self.assertEqual((self.dir / 'items.json').read_bytes(), good_items)
        self.assertFalse((self.dir / 'world.json').exists())

    def test_download_and_apply_rejects_recipes_source_without_items_key(self):
        def fetcher(url):
            return json.dumps({'notitems': {}}).encode('utf-8')
        results = cu.download_and_apply(['recipes_source.json'], fetcher=fetcher)
        self.assertFalse(results['recipes_source.json']['ok'])
        self.assertIn('items', results['recipes_source.json']['error'])
        self.assertFalse((self.dir / 'recipes_source.json').exists())

    def test_download_and_apply_preserves_previous_file_on_failed_validation(self):
        (self.dir / 'world.json').write_bytes(b'[1,2,3]')
        def fetcher(url):
            return b'not even json'
        cu.download_and_apply(['world.json'], fetcher=fetcher)
        self.assertEqual((self.dir / 'world.json').read_bytes(), b'[1,2,3]')

    def test_download_and_apply_backs_up_previous_version(self):
        (self.dir / 'items.json').write_bytes(b'[1]')
        def fetcher(url):
            return json.dumps([{'UniqueName': 'X'}]).encode('utf-8')
        cu.download_and_apply(['items.json'], fetcher=fetcher)
        self.assertEqual((self.dir / 'items.json.bak').read_bytes(), b'[1]')

    def test_regenerate_derived_uses_real_extract_logic(self):
        source = {'items': {
            'weapon': [{'@uniquename': 'T4_MAIN_SWORD', 'craftingrequirements': {
                '@silver': '0', 'craftresource': [{'@uniquename': 'T4_METALBAR', '@count': '16'}]}}],
            'simpleitem': [{'@uniquename': 'T4_ORE'}],
        }}
        (self.dir / 'recipes_source.json').write_text(json.dumps(source), encoding='utf-8')
        n_recipes, n_codes = cu.regenerate_derived()
        self.assertEqual(n_recipes, 1)
        self.assertIn('T4_MAIN_SWORD', json.loads((self.dir / 'recipes.json').read_text(encoding='utf-8')))
        codes = json.loads((self.dir / 'market_items.json').read_text(encoding='utf-8'))
        self.assertIn('T4_ORE', codes)
        self.assertEqual(n_codes, len(codes))

    def test_never_touches_real_network(self):
        """Regressão: com fetcher/sizer injetados, a rede real nunca deve ser chamada."""
        with patch('catalog_updater.urllib.request.urlopen', side_effect=AssertionError('rede real chamada')):
            cu.check_updates(sizer=lambda url: 1)
            cu.download_and_apply(['items.json'], fetcher=lambda url: b'[1]')
