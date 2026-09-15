import unittest
import tkinter as tk
from recipes import RecipeCatalog
from market_view import Catalog
from monitor import database,Feed
from dashboard import Dashboard


class RecipeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.catalog=RecipeCatalog(Catalog())

    def test_search_and_enchanted_materials(self):
        self.assertIn('T4_MAIN_SWORD@1',self.catalog.search('espada t4.1'))
        r=self.catalog.recipes['T4_MAIN_SWORD@1'][0]
        self.assertEqual([(m['code'],m['quantity']) for m in r['materials']],
            [('T4_METALBAR_LEVEL1@1',16),('T4_LEATHER_LEVEL1@1',8)])

    def test_artifact_and_alternatives(self):
        alternatives=self.catalog.recipes['T4_2H_BOW_KEEPER@1']
        self.assertGreater(len(alternatives),1)
        self.assertTrue(alternatives[0]['materials'][0]['returns'])
        self.assertFalse(alternatives[0]['materials'][1]['returns'])
        self.assertNotIn('@1',alternatives[0]['materials'][1]['code'])

    def test_recipe_selection_replaces_inputs_without_reusing_prices(self):
        root=tk.Tk();root.withdraw()
        app=Dashboard(root,database(':memory:'),Feed(),start_feed=False)
        calc=app.calculators
        calc.craft_fields['sell'].set('999')
        calc.materials[0][1]['price'].set('888')
        calc.apply_recipe('T4_MAIN_SWORD@1')
        self.assertEqual(calc.craft_fields['code'].get(),'T4_MAIN_SWORD@1')
        self.assertEqual(calc.craft_fields['sell'].get(),'')
        self.assertEqual(len(calc.materials),2)
        self.assertEqual(calc.materials[0][1]['price'].get(),'')
        calc.apply_recipe('T4_2H_BOW_KEEPER',1)
        self.assertFalse(calc.materials[1][1]['returns'].get())
        self.assertEqual(calc.materials[1][1]['code'].get(),'T4_ARTEFACT_TOKEN_FAVOR_3')
        app.close()
