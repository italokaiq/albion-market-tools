import json
import tkinter as tk
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dashboard import Dashboard
from monitor import database, Feed
from recipe_library import RecipeLibrary


class RecipeLibraryUITest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk();self.root.withdraw()
        self.app = Dashboard(self.root, database(':memory:'), Feed(), start_feed=False)
        self.tmp = TemporaryDirectory()
        self.app.calculators.library = RecipeLibrary(Path(self.tmp.name) / 'receitas_salvas.json')
        self.app.calculators.saved = Path(self.tmp.name) / 'receita_craft.json'

    def tearDown(self):
        self.app.close();self.tmp.cleanup()

    def test_save_recipe_as_stores_current_fields_and_materials(self):
        c = self.app.calculators
        c.apply_recipe('T4_MAIN_SWORD', 0)
        c.craft_fields['station'].set('500')
        from unittest.mock import patch
        with patch('calculators.simpledialog.askstring', return_value='Minha espada'):
            c.save_recipe_as()
        recipe = c.library.load('Minha espada')
        self.assertEqual(recipe['fields']['code'], 'T4_MAIN_SWORD')
        self.assertEqual(recipe['fields']['station'], '500')
        self.assertEqual(len(recipe['materials']), 2)
        self.assertIn('salva na biblioteca', c.craft_note.cget('text'))

    def test_save_recipe_as_cancelled_does_not_save(self):
        c = self.app.calculators
        from unittest.mock import patch
        with patch('calculators.simpledialog.askstring', return_value=None):
            c.save_recipe_as()
        self.assertEqual(c.library.read()['recipes'], {})

    def test_apply_saved_recipe_fills_fields_and_clears_prices(self):
        c = self.app.calculators
        c.library.save('Guardada', dict(code='T4_MAIN_SWORD', crafts='3', sell='999', station='111', rrr='20'),
            [dict(code='T4_METALBAR', quantity='16.0', price='50', returns=True)])
        c.apply_saved_recipe('Guardada')
        self.assertEqual(c.craft_fields['code'].get(), 'T4_MAIN_SWORD')
        self.assertEqual(c.craft_fields['crafts'].get(), '3')
        self.assertEqual(c.craft_fields['sell'].get(), '')
        self.assertEqual(c.craft_fields['station'].get(), '')
        self.assertEqual(len(c.materials), 1)
        self.assertEqual(c.materials[0][1]['code'].get(), 'T4_METALBAR')
        self.assertEqual(c.materials[0][1]['price'].get(), '')

    def test_open_recipe_library_lists_saved_recipes(self):
        c = self.app.calculators
        c.library.save('Uma', dict(code='T4_MAIN_SWORD'), [])
        c.open_recipe_library()
        dialogs = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(dialogs), 1)
        dialogs[0].destroy()

    def test_migrate_legacy_recipe_imports_and_renames_old_file(self):
        c = self.app.calculators
        legacy = dict(fields=dict(code='T4_MAIN_SWORD', crafts='1'),
                      materials=[dict(code='T4_METALBAR', quantity='16.0', returns=True)])
        c.saved.write_text(json.dumps(legacy), encoding='utf-8')
        c.migrate_legacy_recipe()
        self.assertFalse(c.saved.exists())
        self.assertTrue(c.saved.with_suffix('.json.migrated').exists())
        recipes = c.library.read()['recipes']
        self.assertEqual(len(recipes), 1)
        imported = next(iter(recipes.values()))
        self.assertEqual(imported['fields']['code'], 'T4_MAIN_SWORD')

    def test_migrate_legacy_recipe_is_noop_without_old_file(self):
        c = self.app.calculators
        c.migrate_legacy_recipe()
        self.assertEqual(c.library.read()['recipes'], {})

    def test_construction_never_calls_migration(self):
        """Regressão: criar Calculators não pode ter efeito colateral em arquivo real do usuário
        (já aconteceu uma vez: rodar a suíte migrou o receita_craft.json real)."""
        from unittest.mock import patch
        with patch('calculators.Calculators.migrate_legacy_recipe') as migrate:
            root2 = tk.Tk();root2.withdraw()
            app2 = Dashboard(root2, database(':memory:'), Feed(), start_feed=False)
            app2.close()
        migrate.assert_not_called()
