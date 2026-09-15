import unittest
from catalog_items import extract


class CatalogItemsTest(unittest.TestCase):
    def test_equipment_enchantments_become_at_suffix(self):
        source = {'items': {
            'weapon': [{'@uniquename': 'T4_MAIN_SWORD',
                        'enchantments': {'enchantment': [
                            {'@enchantmentlevel': '1'}, {'@enchantmentlevel': '2'}]}}],
            'equipmentitem': [{'@uniquename': 'T4_HEAD_PLATE_SET1'}],
        }}
        codes = extract(source)
        self.assertEqual(codes, ['T4_HEAD_PLATE_SET1', 'T4_MAIN_SWORD',
                                  'T4_MAIN_SWORD@1', 'T4_MAIN_SWORD@2'])

    def test_refined_resource_levels_become_at_suffix_not_raw_names(self):
        source = {'items': {'simpleitem': [
            {'@uniquename': 'T4_PLANKS'}, {'@uniquename': 'T4_PLANKS_LEVEL1'},
            {'@uniquename': 'T4_PLANKS_LEVEL2'}, {'@uniquename': 'T4_PLANKS_LEVEL3'},
            {'@uniquename': 'T4_PLANKS_LEVEL4'}, {'@uniquename': 'T4_WOOD'}]}}
        codes = extract(source)
        self.assertEqual(codes, ['T4_PLANKS', 'T4_PLANKS@1', 'T4_PLANKS@2',
                                  'T4_PLANKS@3', 'T4_PLANKS@4', 'T4_WOOD'])

    def test_non_tradable_categories_are_excluded(self):
        source = {'items': {
            'journalitem': [{'@uniquename': 'T4_JOURNAL_WOOD'}],
            'labourercontract': [{'@uniquename': 'T4_LABOURER_CONTRACT_WOOD'}],
            'trashitem': [{'@uniquename': 'T1_TRASH'}],
            'mountskin': [{'@uniquename': 'SKIN_HORSE_FOUNDER_ASIA_GOLD'}],
            'simpleitem': [{'@uniquename': 'T4_ORE'}],
        }}
        self.assertEqual(extract(source), ['T4_ORE'])

    def test_missing_categories_do_not_raise(self):
        self.assertEqual(extract({'items': {}}), [])
