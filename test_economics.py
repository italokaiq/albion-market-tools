import unittest
from economics import flipping,crafting


class EconomicsTest(unittest.TestCase):
    def test_order_rates_for_both_profiles_and_calculators(self):
        for premium, tax, expected_net in [(True, 80, 845), (False, 160, 765)]:
            with self.subTest(premium=premium):
                flip = flipping(1000, 2000, premium=premium, buy_order=True, sell_order=True)
                craft = crafting([dict(code='MATERIAL', quantity=1, price=1000, returns=False)],
                                 1, 1, 2000, 0, premium=premium, buy_order=True, sell_order=True)
                for result in [flip, craft]:
                    self.assertEqual(result['buy_fee'], 25)
                    self.assertEqual(result['sell_fee'], 50)
                    self.assertEqual(result['sale_tax'], tax)
                    self.assertEqual(result['net'], expected_net)

    def test_flip_immediate_premium_comparison(self):
        p=flipping(100,150,10,premium=True)
        n=flipping(100,150,10,premium=False)
        self.assertEqual(p['net'],440)
        self.assertEqual(n['net'],380)
        self.assertEqual(p['buy_fee'],0)

    def test_orders_setup_both_sides_and_recreation(self):
        r=flipping(100,150,10,premium=True,buy_order=True,sell_order=True,sell_relists=1)
        self.assertEqual(r['buy_fee'],25)
        self.assertEqual(r['sell_fee'],75)
        self.assertEqual(r['net'],340)
        zero=flipping(100,r['break_even'],10,premium=True,buy_order=True,sell_order=True,sell_relists=1)
        self.assertAlmostEqual(zero['net'],0)

    def test_craft_artifact_no_return_upfront_vs_economic(self):
        r=crafting([dict(code='T4_METALBAR',quantity=10,price=100,returns=True),
                    dict(code='ARTIFACT',quantity=1,price=500,returns=False)],
                   2,1,2500,50,premium=True,station=100,sell_order=True)
        self.assertEqual(r['gross'],3000)
        self.assertEqual(r['returned'],1000)
        self.assertEqual(r['upfront'],3100)
        self.assertEqual(r['effective'],2100)
        self.assertEqual(r['net'],2575)
        self.assertEqual(r['cash'],1575)

    def test_missing_price_and_impossible_return(self):
        with self.assertRaises(ValueError):flipping('',100)
        with self.assertRaises(ValueError):flipping(100,200,quantity=1.5)
        with self.assertRaises(ValueError):crafting([],1,1,100,100)
