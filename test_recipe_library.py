import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from recipe_library import RecipeLibrary


class RecipeLibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.lib = RecipeLibrary(Path(self.tmp.name) / 'receitas_salvas.json')

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_without_file(self):
        self.assertEqual(self.lib.read(), {'version': 1, 'recipes': {}})

    def test_save_and_load_roundtrip(self):
        fields = dict(code='T4_MAIN_AXE', crafts='1')
        materials = [dict(code='T4_PLANKS', quantity='8.0', returns=True)]
        self.lib.save('Machado T4', fields, materials)
        recipe = self.lib.load('Machado T4')
        self.assertEqual(recipe['fields'], fields)
        self.assertEqual(recipe['materials'], materials)
        self.assertIn('saved_at', recipe)

    def test_save_rejects_empty_or_long_name(self):
        with self.assertRaises(ValueError):
            self.lib.save('   ', {}, [])
        with self.assertRaises(ValueError):
            self.lib.save('x' * 81, {}, [])

    def test_save_overwrites_same_name(self):
        self.lib.save('Foo', dict(a=1), [])
        self.lib.save('Foo', dict(a=2), [])
        self.assertEqual(self.lib.load('Foo')['fields'], dict(a=2))
        self.assertEqual(len(self.lib.read()['recipes']), 1)

    def test_load_missing_raises(self):
        with self.assertRaises(KeyError):
            self.lib.load('nope')

    def test_delete_removes_entry(self):
        self.lib.save('A', {}, []);self.lib.save('B', {}, [])
        self.lib.delete('A')
        self.assertEqual(list(self.lib.read()['recipes']), ['B'])

    def test_delete_missing_raises(self):
        with self.assertRaises(KeyError):
            self.lib.delete('nope')

    def test_rename_moves_entry_and_keeps_content(self):
        self.lib.save('Old', dict(code='X'), [])
        self.lib.rename('Old', 'New')
        self.assertNotIn('Old', self.lib.read()['recipes'])
        self.assertEqual(self.lib.load('New')['fields'], dict(code='X'))

    def test_rename_to_existing_name_rejected(self):
        self.lib.save('A', {}, []);self.lib.save('B', {}, [])
        with self.assertRaises(ValueError):
            self.lib.rename('A', 'B')

    def test_rename_missing_raises(self):
        with self.assertRaises(KeyError):
            self.lib.rename('nope', 'New')

    def test_malformed_file_rejected_without_overwrite(self):
        self.lib.path.write_text('{"bad":true}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.lib.read()
        self.assertEqual(json.loads(self.lib.path.read_text(encoding='utf-8')), {'bad': True})

    def test_backup_created_on_second_write(self):
        self.lib.save('A', {}, [])
        self.lib.save('B', {}, [])
        self.assertTrue(self.lib.path.with_suffix('.json.bak').exists())
