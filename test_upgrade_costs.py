import unittest
from upgrade_costs import extract


class UpgradeCostsTest(unittest.TestCase):
    def test_extracts_one_step_per_level_with_materials(self):
        source = {'items': {'weapon': [{'@uniquename': 'T4_MAIN_SWORD', 'enchantments': {'enchantment': [
            {'@enchantmentlevel': '1', 'upgraderequirements': {'upgraderesource': {'@uniquename': 'T4_RUNE', '@count': '288'}}},
            {'@enchantmentlevel': '2', 'upgraderequirements': {'upgraderesource': {'@uniquename': 'T4_SOUL', '@count': '288'}}},
            {'@enchantmentlevel': '3', 'upgraderequirements': {'upgraderesource': {'@uniquename': 'T4_RELIC', '@count': '288'}}},
            {'@enchantmentlevel': '4'},  # sem upgraderequirements: não pode ser alcançado por upgrade
        ]}}]}}
        steps = extract(source)
        self.assertEqual(set(steps), {'T4_MAIN_SWORD@1', 'T4_MAIN_SWORD@2', 'T4_MAIN_SWORD@3'})
        self.assertEqual(steps['T4_MAIN_SWORD@1'], dict(base='T4_MAIN_SWORD', level=1,
            materials=[dict(resource='T4_RUNE', count=288.0)]))
        self.assertEqual(steps['T4_MAIN_SWORD@2']['materials'][0]['resource'], 'T4_SOUL')
        self.assertEqual(steps['T4_MAIN_SWORD@3']['materials'][0]['resource'], 'T4_RELIC')

    def test_level_without_upgraderequirements_is_skipped(self):
        source = {'items': {'weapon': [{'@uniquename': 'T4_MAIN_SWORD', 'enchantments': {'enchantment': [
            {'@enchantmentlevel': '4'},
        ]}}]}}
        self.assertEqual(extract(source), {})

    def test_missing_categories_do_not_raise(self):
        self.assertEqual(extract({'items': {}}), {})

    def test_equipmentitem_kind_is_covered(self):
        source = {'items': {'equipmentitem': [{'@uniquename': 'T4_HEAD_PLATE_SET1', 'enchantments': {'enchantment':
            {'@enchantmentlevel': '1', 'upgraderequirements': {'upgraderesource': {'@uniquename': 'T4_RUNE', '@count': '96'}}}}}]}}
        steps = extract(source)
        self.assertEqual(steps['T4_HEAD_PLATE_SET1@1']['materials'][0]['count'], 96.0)
