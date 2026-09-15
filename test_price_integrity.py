import time
import tkinter as tk
import unittest
from unittest.mock import patch
from dashboard import Dashboard
from monitor import database,Feed,save_order
from price_lookup import observed_price
from ui_design import fill_results


class IntegrityTest(unittest.TestCase):
    def test_screenshot_ages_rejected_and_limit_change_clears_prices(self):
        c=self.app.calculators;now=time.time()
        c.materials[0][1]['code'].set('T4_PLANKS')
        c.add_material();c.materials[1][1]['code'].set('T4_METALBAR')
        c.craft_api={
            ('T4_PLANKS',1):{'7':{'offer':dict(price=308,seen=now-12480,amount=None,source='API')}},
            ('T4_METALBAR',1):{'7':{'offer':dict(price=326,seen=now-4380,amount=None,source='API')}}}
        c.apply_prices()
        self.assertEqual([m['price'].get() for _,m in c.materials],['',''])
        self.assertIn('descartado',c.price_status.cget('text'))
        self.app.filters['minutes'].set('240');c.apply_prices()
        self.assertEqual([m['price'].get() for _,m in c.materials],['308','326'])
        self.app.filters['minutes'].set('30')
        self.assertEqual([m['price'].get() for _,m in c.materials],['',''])
        self.assertIn('limite 30 min',c.price_status.cget('text'))

    def test_displayed_age_advances_without_fetch(self):
        c=self.app.calculators;now=time.time()
        c.craft_fields['code'].set('T4_BAG')
        c.craft_api={('T4_BAG',1):{'7':{'request':dict(price=100,seen=now-120,amount=None,source='API')}}}
        c.apply_prices()
        with patch('craft_prices.time.time',return_value=now+60):c.poll_prices()
        self.assertIn('3min',c.price_status.cget('text'))

    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        self.con=database(':memory:')
        self.app=Dashboard(self.root,self.con,Feed(),start_feed=False)
    def tearDown(self):self.app.close()

    def test_missing_station_and_return_are_not_zero(self):
        fields=self.app.calculators.craft_fields
        self.assertEqual(fields['station'].get(),'')
        self.assertEqual(fields['rrr'].get(),'')

    def test_changing_city_invalidates_observed_price(self):
        c=self.app.calculators
        save_order(self.con,dict(Id=1,LocationId=7,ItemTypeId='T4_BAG',QualityLevel=1,EnchantmentLevel=0,
                                AuctionType='request',UnitPriceSilver=5000,Amount=2))
        c.craft_fields['code'].set('T4_BAG');c.load_prices()
        self.assertEqual(c.craft_fields['sell'].get(),'5000')
        c.craft_fields['destination'].set('Lymhurst');c.poll_prices()
        self.assertEqual(c.craft_fields['sell'].get(),'')

    def test_api_expired_price_rejected_and_volume_not_invented(self):
        now=time.time();api={('T4_BAG',1):{'7':{'offer':dict(price=100,seen=now-1000,amount=None,source='API')}}}
        self.assertIsNone(observed_price([],api,'T4_BAG',1,'7','offer',now,60))
        api[('T4_BAG',1)]['7']['offer']['seen']=now
        self.assertIsNone(observed_price([],api,'T4_BAG',1,'7','offer',now,60)['amount'])

    def test_late_api_does_not_overwrite_manual_edit(self):
        c=self.app.calculators;c.craft_fields['code'].set('T4_BAG')
        protected={str(c.craft_fields['sell']):''}
        c.craft_fields['sell'].set('7000')
        c.craft_api={('T4_BAG',1):{'7':{'request':dict(price=100,seen=time.time(),amount=None,source='API')}}}
        c.apply_prices(protected)
        self.assertEqual(c.craft_fields['sell'].get(),'7000')

    def test_negative_results_are_not_green(self):
        t=self.app.calculators.flip_table
        fill_results(t,[('Lucro','100,00','80,00')])
        fill_results(t,[('Lucro','-100,00','-80,00')])
        self.assertEqual(t.item('0','tags'),('loss',))

    def test_missing_lookup_preserves_manual_price(self):
        c=self.app.calculators
        c.craft_fields['code'].set('T4_BAG')
        c.craft_fields['sell'].set('7000')
        c.load_prices()
        self.assertEqual(c.craft_fields['sell'].get(),'7000')
        self.assertIn('manual preservado',c.price_status.cget('text'))

    def test_missing_lookup_clears_previous_observation(self):
        c=self.app.calculators
        c.craft_fields['code'].set('T4_BAG')
        c.craft_api={('T4_BAG',1):{'7':{'request':dict(price=100,seen=time.time(),amount=None,source='API')}}}
        c.apply_prices()
        c.craft_api={}
        c.apply_prices()
        self.assertEqual(c.craft_fields['sell'].get(),'')

    def test_manual_edit_keeps_other_flip_price_expiration(self):
        c=self.app.calculators
        now=time.time()
        c.flip_fields['buy'].set('100')
        c.flip_fields['sell'].set('200')
        c.flip_observation=('100','200',now,10)
        c.flip_fields['buy'].set('110')
        c.refresh()
        self.assertIsNotNone(c.flip_observation)
        with patch('calculators.time.time',return_value=now+901):c.refresh()
        self.assertEqual(c.flip_fields['buy'].get(),'110')
        self.assertEqual(c.flip_fields['sell'].get(),'')
        self.assertFalse(c.flip_table.get_children())
