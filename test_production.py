import time
import tkinter as tk
import unittest
from production import refining_recipes,dependency_codes,plan_production
from monitor import database,Feed
from dashboard import Dashboard

class ProductionTest(unittest.TestCase):
    def price(self,value):return dict(price=value,seen=time.time(),amount=None,source='API')
    def base(self):
        mats=[dict(code='BAR',quantity=2,returns=True)]
        recipes={'BAR':[dict(materials=[dict(code='ORE',quantity=2,returns=True),dict(code='LOW',quantity=1,returns=True)],output=1,silver=0)]}
        prices={('BAR',1,'7','offer'):self.price(100),('ORE',1,'7','offer'):self.price(10),('LOW',1,'7','offer'):self.price(20),('PRODUCT',1,'1002','request'):self.price(300)}
        return mats,recipes,prices
    def run_plan(self,settings,premium=True,**kw):
        mats,recipes,prices=self.base()
        return plan_production(mats,recipes,prices,'PRODUCT',1,1,1,settings,0,premium=premium,**kw)
    def test_refine_chain_and_taxes(self):
        settings={('BAR','7'):(0,5),('craft','7'):(0,10)}
        result=self.run_plan(settings)
        self.assertEqual(result['routes'][0]['cost'],100)
        self.assertEqual(result['routes'][0]['net'],188)
        self.assertEqual(result['routes'][0]['choices'][0][1]['method'],'Refinar')
        self.assertEqual(self.run_plan(settings,premium=False)['routes'][0]['net'],176)
    def test_missing_refine_cost_uses_buy_and_missing_craft_blocks(self):
        self.assertEqual(self.run_plan({})['routes'],[])
        r=self.run_plan({('craft','7'):(0,10)})['routes'][0]
        self.assertEqual(r['cost'],210)
        self.assertEqual(r['choices'][0][1]['method'],'Comprar refinado')
    def test_return_reduces_economic_cost_not_gross_cash(self):
        r=self.run_plan({('BAR','7'):(50,5),('craft','7'):(50,10)})['routes'][0]
        self.assertEqual(r['cost'],35)
        self.assertEqual(r['cash'],100)
    def test_missing_lower_tier_cannot_be_zero(self):
        mats,recipes,prices=self.base();del prices[('LOW',1,'7','offer')]
        r=plan_production(mats,recipes,prices,'PRODUCT',1,1,1,{('BAR','7'):(0,0),('craft','7'):(0,0)},0)
        self.assertEqual(r['routes'][0]['choices'][0][1]['method'],'Comprar refinado')
    def test_order_fees_both_sides(self):
        mats,recipes,prices=self.base()
        prices={(*key[:3],'request' if key[3]=='offer' else 'offer'):v for key,v in prices.items()}
        r=plan_production(mats,recipes,prices,'PRODUCT',1,1,1,{('craft','7'):(0,0)},0,premium=True,buy_order=True,sell_order=True)['routes'][0]
        self.assertAlmostEqual(r['cost'],205)
        self.assertAlmostEqual(r['net'],75.5)
    def test_real_refining_catalog_enchantment_and_lower_tiers(self):
        recipes=refining_recipes()
        r=recipes['T4_PLANKS_LEVEL1@1'][0]
        self.assertEqual([m['code'] for m in r['materials']],['T4_WOOD_LEVEL1@1','T3_PLANKS'])
        self.assertEqual([m['quantity'] for m in r['materials']],[2,1])
        codes=dependency_codes([dict(code='T4_PLANKS_LEVEL1@1')],recipes)
        self.assertIn('T2_WOOD',codes)
    def test_shipping_and_best_sale_city(self):
        mats,recipes,prices=self.base();prices[('PRODUCT',1,'7','request')]=self.price(290)
        result=plan_production(mats,recipes,prices,'PRODUCT',1,1,1,{('craft','7'):(0,0)},100,premium=True)
        self.assertEqual(result['routes'][0]['destination'],'7')
    def test_planner_window_invalidation_and_expiration(self):
        root=tk.Tk();root.withdraw();app=Dashboard(root,database(':memory:'),Feed(),start_feed=False)
        try:
            c=app.calculators;c.apply_recipe('T4_MAIN_AXE');c.open_production_planner();p=c.production_planner
            p.shipping.set('0');p.editors['7'][0].set('0');p.editors['7'][1].set('0')
            now=time.time()
            p.data={(code,1):{'7':{'offer':dict(price=100,seen=now-10000,amount=None,source='API')}} for code in p.codes}
            p.calculate();self.assertEqual(len(p.market_table.get_children()),0)
            c.craft_fields['crafts'].set('2');p.poll()
            self.assertIsNone(p.result)
            self.assertIn('invalidada',p.status.cget('text'))
        finally:app.close()

class ProductionRegressionTest(unittest.TestCase):
    price=ProductionTest.price
    base=ProductionTest.base
    def test_return_does_not_refund_order_fee_or_shipping(self):
        mats,recipes,prices=self.base()
        prices={(*key[:3],'request' if key[3]=='offer' else 'offer'):v for key,v in prices.items()}
        r=plan_production(mats,{},prices,'PRODUCT',1,1,1,{('craft','1002'):(50,0)},10,premium=True,buy_order=True,sell_order=True)['routes'][0]
        # 2 * (100 purchase + 2.5 fee + 10 transport - 50 returned inventory).
        self.assertAlmostEqual(r['cost'],125)
        self.assertAlmostEqual(r['cash'],225)
    def test_missing_first_material_does_not_hide_other_comparisons(self):
        mats,recipes,prices=self.base()
        mats.insert(0,dict(code='MISSING',quantity=1,returns=True))
        r=plan_production(mats,recipes,prices,'PRODUCT',1,1,1,{},0)
        self.assertTrue(r['supply'])
        self.assertEqual(r['routes'],[])
        self.assertIn('MISSING',r['missing'])
    def test_decimal_comma_is_valid_for_material_quantity(self):
        mats,recipes,prices=self.base();mats[0]['quantity']='2,5'
        r=plan_production(mats,{},prices,'PRODUCT',1,1,1,{('craft','7'):(0,0)},0)
        self.assertEqual(r['routes'][0]['cash'],250)
    def test_empty_recipe_rejected(self):
        with self.assertRaises(ValueError):plan_production([],{}, {},'PRODUCT',1,1,1,{},0)
    def test_api_failure_stays_visible_and_cached_prices_survive_reopen(self):
        root=tk.Tk();root.withdraw();app=Dashboard(root,database(':memory:'),Feed(),start_feed=False)
        try:
            c=app.calculators;c.apply_recipe('T4_MAIN_AXE');c.open_production_planner();p=c.production_planner
            p.shipping.set('0');p.editors['7'][0].set('15');p.editors['7'][1].set('10')
            p.data={('T4_PLANKS',1):{'7':{'offer':self.price(100)}}}
            p.jobs.put((p.generation,None,'URLError'));p.poll();p.calculate()
            self.assertIn('Falha na API',p.status.cget('text'))
            p.open()
            self.assertEqual(p.shipping.get(),'0')
            self.assertEqual(p.editors['7'][0].get(),'15')
            self.assertIn(('T4_PLANKS',1),p.data)
        finally:app.close()
