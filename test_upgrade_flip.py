import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from upgrade_flip import evaluate_paths, best_flip, UpgradeCosts

# Passos reais do T4_MAIN_SWORD (verificados em recipes_source.json).
STEPS = {
    'T4_MAIN_SWORD@1': dict(base='T4_MAIN_SWORD', level=1, materials=[dict(resource='T4_RUNE', count=288.0)]),
    'T4_MAIN_SWORD@2': dict(base='T4_MAIN_SWORD', level=2, materials=[dict(resource='T4_SOUL', count=288.0)]),
    'T4_MAIN_SWORD@3': dict(base='T4_MAIN_SWORD', level=3, materials=[dict(resource='T4_RELIC', count=288.0)]),
}

def p(price, seen=1000, amount=None, source='API'):
    return dict(price=price, seen=seen, amount=amount, source=source)


class EvaluatePathsTest(unittest.TestCase):
    def test_matches_real_afm_totals_for_full_chain(self):
        """Preços reais vistos na AFM: rúnica 5, alma 71, relíquia 479 — total
        documentado por eles para 0->3 foi 159.840; para 2->3, 137.952."""
        prices = {
            ('T4_MAIN_SWORD', 1, 'offer'): p(0),
            ('T4_RUNE', 1, 'offer'): p(5),
            ('T4_SOUL', 1, 'offer'): p(71),
            ('T4_RELIC', 1, 'offer'): p(479),
        }
        paths = evaluate_paths('T4_MAIN_SWORD', 3, 1, prices, STEPS)
        by_start = {path['start_level']: path for path in paths}
        self.assertAlmostEqual(by_start[0]['total_cost'], 159840)
        self.assertAlmostEqual(by_start[0]['upgrade_cost'], 159840)  # buy_price=0 aqui

    def test_partial_chain_from_higher_start_level(self):
        prices = {
            ('T4_MAIN_SWORD@2', 1, 'offer'): p(1000),
            ('T4_RELIC', 1, 'offer'): p(479),
        }
        paths = evaluate_paths('T4_MAIN_SWORD', 3, 1, prices, STEPS)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0]['start_level'], 2)
        self.assertAlmostEqual(paths[0]['total_cost'], 1000 + 288 * 479)

    def test_missing_intermediate_price_excludes_only_starts_that_need_it(self):
        prices = {
            ('T4_MAIN_SWORD', 1, 'offer'): p(100),
            ('T4_MAIN_SWORD@1', 1, 'offer'): p(200),
            ('T4_RUNE', 1, 'offer'): p(5),
            # falta T4_SOUL: começar em 0 ou 1 precisa dele (etapa 1->2); começar em 2 não precisa.
            ('T4_MAIN_SWORD@2', 1, 'offer'): p(2000),
            ('T4_RELIC', 1, 'offer'): p(479),
        }
        paths = evaluate_paths('T4_MAIN_SWORD', 3, 1, prices, STEPS)
        starts = {path['start_level'] for path in paths}
        self.assertEqual(starts, {2})

    def test_no_prices_returns_empty(self):
        self.assertEqual(evaluate_paths('T4_MAIN_SWORD', 3, 1, {}, STEPS), [])

    def test_starting_at_target_level_has_no_upgrade_cost(self):
        prices = {('T4_MAIN_SWORD@3', 1, 'offer'): p(50000)}
        paths = evaluate_paths('T4_MAIN_SWORD', 3, 1, prices, STEPS)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0]['start_level'], 3)
        self.assertEqual(paths[0]['upgrade_cost'], 0)
        self.assertEqual(paths[0]['total_cost'], 50000)

    def test_buy_order_fee_applies_to_every_leg(self):
        prices = {
            ('T4_MAIN_SWORD@2', 1, 'request'): p(1000),
            ('T4_RELIC', 1, 'request'): p(479),
        }
        paths = evaluate_paths('T4_MAIN_SWORD', 3, 1, prices, STEPS, buy_side='request', buy_fee_rate=0.025)
        expected = 1000 * 1.025 + 288 * 479 * 1.025
        self.assertAlmostEqual(paths[0]['total_cost'], expected)


class BestFlipTest(unittest.TestCase):
    def base_prices(self):
        return {
            ('T4_MAIN_SWORD', 1, 'offer'): p(1000, seen=900),
            ('T4_RUNE', 1, 'offer'): p(5, seen=950),
            ('T4_SOUL', 1, 'offer'): p(71, seen=920),
            ('T4_RELIC', 1, 'offer'): p(479, seen=980),
        }

    def test_none_when_no_paths(self):
        best, paths = best_flip('T4_MAIN_SWORD', 3, 1, {}, STEPS, sell_price=200000, sell_seen=1000)
        self.assertIsNone(best)
        self.assertEqual(paths, [])

    def test_none_when_no_sell_price(self):
        best, paths = best_flip('T4_MAIN_SWORD', 3, 1, self.base_prices(), STEPS, sell_price=None, sell_seen=None)
        self.assertIsNone(best)
        self.assertTrue(paths)

    def test_profitable_flip_computed_with_tax(self):
        cost = 1000 + 288 * 5 + 288 * 71 + 288 * 479  # = 159840 + 1000 = 160840
        sell_price = 300000
        best, _ = best_flip('T4_MAIN_SWORD', 3, 1, self.base_prices(), STEPS,
                             sell_price=sell_price, sell_seen=1000, premium=False)
        self.assertAlmostEqual(best['total_cost'], cost)
        self.assertAlmostEqual(best['revenue'], sell_price * 0.92)
        self.assertAlmostEqual(best['net'], sell_price * 0.92 - cost)
        self.assertGreater(best['net'], 0)

    def test_premium_nets_more_than_non_premium(self):
        prices = self.base_prices()
        premium, _ = best_flip('T4_MAIN_SWORD', 3, 1, prices, STEPS, sell_price=300000, sell_seen=1000, premium=True)
        normal, _ = best_flip('T4_MAIN_SWORD', 3, 1, prices, STEPS, sell_price=300000, sell_seen=1000, premium=False)
        self.assertGreater(premium['net'], normal['net'])

    def test_sell_order_adds_setup_fee(self):
        prices = self.base_prices()
        immediate, _ = best_flip('T4_MAIN_SWORD', 3, 1, prices, STEPS, sell_price=300000, sell_seen=1000, sell_immediate=True)
        ordered, _ = best_flip('T4_MAIN_SWORD', 3, 1, prices, STEPS, sell_price=300000, sell_seen=1000, sell_immediate=False)
        self.assertLess(ordered['net'], immediate['net'])

    def test_picks_cheapest_path_among_multiple_start_levels(self):
        prices = self.base_prices()
        prices[('T4_MAIN_SWORD@1', 1, 'offer')] = p(400000)  # caro demais, não deve vencer
        prices[('T4_MAIN_SWORD@2', 1, 'offer')] = p(500000)  # caro demais, não deve vencer
        prices[('T4_MAIN_SWORD@3', 1, 'offer')] = p(600000)  # caro demais, não deve vencer
        best, paths = best_flip('T4_MAIN_SWORD', 3, 1, prices, STEPS, sell_price=300000, sell_seen=1000)
        self.assertEqual(best['start_level'], 0)
        self.assertEqual(len(paths), 4)  # niveis 0,1,2,3 todos com preco completo


class UpgradeCostsTest(unittest.TestCase):
    def test_loads_real_file_and_resolves_known_step(self):
        uc = UpgradeCosts()
        self.assertEqual(uc.error, '')
        self.assertIn('T4_MAIN_SWORD@1', uc.steps)
        self.assertEqual(uc.max_level('T4_MAIN_SWORD'), 3)

    def test_missing_file_sets_error_without_raising(self):
        with TemporaryDirectory() as tmp:
            uc = UpgradeCosts(Path(tmp) / 'nope.json')
            self.assertEqual(uc.steps, {})
            self.assertNotEqual(uc.error, '')

    def test_max_level_zero_for_unknown_base(self):
        uc = UpgradeCosts()
        self.assertEqual(uc.max_level('NOT_A_REAL_ITEM'), 0)
