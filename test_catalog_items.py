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

    def test_occasionally_traded_categories_are_included(self):
        """Diários, contratos, bandeiras de cerco, esconderijo, troféus e tokens: a AFM
        (ferramenta estabelecida, mesma fonte AODP) trata como pesquisáveis, e contratos
        de trabalhador têm histórico real de negociação verificado contra a API."""
        source = {'items': {
            'journalitem': [{'@uniquename': 'T4_JOURNAL_WOOD'}],
            'labourercontract': [{'@uniquename': 'T4_LABOURER_CONTRACT_WOOD'}],
            'trashitem': [{'@uniquename': 'T1_TRASH'}],
            'hideoutitem': [{'@uniquename': 'UNIQUE_HIDEOUT'}],
            'siegebanner': [{'@uniquename': 'T4_SIEGE_BANNER'}],
            'killtrophy': [{'@uniquename': 'UNIQUE_FURNITUREITEM_KILLTROPHY_OPENWORLD_LARGE'}],
            'rewardtoken': [{'@uniquename': 'QUESTITEM_TOKEN_SMUGGLER'}],
        }}
        self.assertEqual(extract(source), ['QUESTITEM_TOKEN_SMUGGLER', 'T1_TRASH',
            'T4_JOURNAL_WOOD', 'T4_LABOURER_CONTRACT_WOOD', 'T4_SIEGE_BANNER',
            'UNIQUE_FURNITUREITEM_KILLTROPHY_OPENWORLD_LARGE', 'UNIQUE_HIDEOUT'])

    def test_non_tradable_categories_are_excluded(self):
        source = {'items': {
            'mountskin': [{'@uniquename': 'SKIN_HORSE_FOUNDER_ASIA_GOLD'}],
            'trackingitem': [{'@uniquename': 'T4_TRACKINGITEM'}],
            'transformationweapon': [{'@uniquename': 'T4_2H_TRANSFORMATIONWEAPON'}],
            'crystalleagueitem': [{'@uniquename': 'CRYSTALLEAGUE_TOKEN'}],
            'simpleitem': [{'@uniquename': 'T4_ORE'}],
        }}
        self.assertEqual(extract(source), ['T4_ORE'])

    def test_missing_categories_do_not_raise(self):
        self.assertEqual(extract({'items': {}}), [])

    def test_explicit_tradable_false_is_excluded_from_normal_kinds(self):
        """Achado real: itens internos de game master, banners de guildhall e caixas
        de recompensa placeholder tinham @tradable="false" e poluíam a busca sem
        nunca ter preço. Ausência do atributo continua incluída (padrão dos dados)."""
        source = {'items': {
            'weapon': [{'@uniquename': 'T4_MAIN_SWORD'}, {'@uniquename': 'UNIQUE_INTERNAL_GM', '@tradable': 'false'}],
            'equipmentitem': [{'@uniquename': 'T4_HEAD_PLATE_SET1', '@tradable': 'true'}],
        }}
        self.assertEqual(extract(source), ['T4_HEAD_PLATE_SET1', 'T4_MAIN_SWORD'])

    def test_consumablefrominventoryitem_requires_explicit_tradable_true(self):
        """Ao contrário dos demais kinds, este é majoritariamente não negociável
        (itens de progressão/vaidade pessoais) — aqui a ausência do atributo
        não basta, só @tradable="true" explícito inclui o item."""
        source = {'items': {'consumablefrominventoryitem': [
            {'@uniquename': 'T4_SKILLBOOK_GATHER_FIBER', '@tradable': 'true'},
            {'@uniquename': 'UNIQUE_FOCUSPOTION_TUTORIAL_01', '@tradable': 'false'},
            {'@uniquename': 'UNIQUE_NO_ATTRIBUTE_AT_ALL'},
        ]}}
        self.assertEqual(extract(source), ['T4_SKILLBOOK_GATHER_FIBER'])
