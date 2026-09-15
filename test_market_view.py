import time
import unittest
import tkinter as tk
from monitor import database, save_order, Feed
from market_view import Catalog, filtered_orders, compare, freshness, sync_table, matches_item
from dashboard import Dashboard


class ComparisonTest(unittest.TestCase):
    def test_item_search_with_name_tier_and_accents(self):
        self.assertTrue(matches_item('espada T4','T4_MAIN_SWORD','Espada Larga do Adepto'))
        self.assertTrue(matches_item('anciao 8.2','T8_MAIN_SWORD@2','Espada do Ancião'))
        self.assertFalse(matches_item('espada T5','T4_MAIN_SWORD','Espada Larga do Adepto'))

    def test_equipment_visible_without_profitable_route(self):
        root=tk.Tk();root.withdraw();con=database(':memory:')
        save_order(con,dict(Id=1,LocationId=3003,ItemTypeId='T4_MAIN_SWORD',QualityLevel=1,
                            EnchantmentLevel=0,AuctionType='request',UnitPriceSilver=100,Amount=1))
        app=Dashboard(root,con,Feed(),start_feed=False)
        self.assertEqual(app.metrics['positive'].cget('text'),'0')
        self.assertEqual(len(app.top_routes.get_children()),1)
        values=app.top_routes.item(app.top_routes.get_children()[0],'values')
        self.assertEqual(values[1],'Sem oferta')
        self.assertEqual(values[3],'Sem rota')
        app.overview_mode.set('Oportunidades de flipping')
        app.update_overview(app.current_snapshot,[],time.time())
        self.assertEqual(len(app.top_routes.get_children()),0)
        self.assertIn('nenhuma rota',app.list_status.cget('text'))
        app.close()

    def test_filters_and_best_prices_keep_variants_separate(self):
        con = database(':memory:')
        base = dict(Id=1,LocationId=3005,ItemTypeId='T4_BAG',QualityLevel=1,
                    EnchantmentLevel=0,AuctionType='offer',UnitPriceSilver=100,Amount=2)
        for changes, seen in [({},990),({'Id':2,'UnitPriceSilver':90},995),
            ({'Id':3,'AuctionType':'request','UnitPriceSilver':80},980),
            ({'Id':4,'QualityLevel':2,'UnitPriceSilver':1},995),
            ({'Id':5,'LocationId':1002,'UnitPriceSilver':120},995),
            ({'Id':6,'UnitPriceSilver':2},1)]:
            save_order(con,dict(base,**changes),seen)
        catalog = Catalog()
        rows = filtered_orders(con,catalog,1000,5,quality='1')
        groups = dict(compare(rows))
        self.assertEqual(len(groups),2)
        self.assertEqual(groups[('T4_BAG',1,0,'3005')]['offer'][0],90)
        self.assertEqual(groups[('T4_BAG',1,0,'3005')]['request'][0],80)
        self.assertTrue(filtered_orders(con,catalog,1000,5,query=catalog.item('T4_BAG'),market='Caerleon'))
        self.assertEqual(filtered_orders(con,catalog,1000,5,tier='8'),[])
        con.close()

    def test_age_and_unknown_names(self):
        self.assertEqual(freshness(999,1000),'fresh')
        self.assertEqual(freshness(600,1000),'warm')
        self.assertEqual(freshness(0,1000),'old')
        self.assertEqual(Catalog().item('UNKNOWN'),'UNKNOWN')

    def test_dashboard_preserves_selection(self):
        root = tk.Tk()
        root.withdraw()
        con = database(':memory:')
        app = Dashboard(root,con,Feed(),start_feed=False)
        sync_table(app.table,[('one',('item','city','normal','Venda',10,1,'1s'),'fresh')])
        app.table.selection_set('one')
        sync_table(app.table,[('one',('item','city','normal','Venda',12,1,'2s'),'fresh')])
        self.assertEqual(app.table.selection(),('one',))
        self.assertEqual(app.table.item('one','values')[4],'12')
        app.close()

    def test_overview_chart_and_positive_route_without_excel(self):
        root = tk.Tk()
        root.withdraw()
        con = database(':memory:')
        order = dict(Id=1,LocationId=7,ItemTypeId='T4_MAIN_SWORD',QualityLevel=1,
                     EnchantmentLevel=0,AuctionType='offer',UnitPriceSilver=100,Amount=4)
        save_order(con,order)
        save_order(con,dict(order,Id=2,LocationId=1002,AuctionType='request',UnitPriceSilver=200))
        app = Dashboard(root,con,Feed(),start_feed=False)
        self.assertIsNone(app.exporter)
        self.assertEqual(app.metrics['positive'].cget('text'),'1')
        self.assertEqual(len(app.top_routes.get_children()),1)
        self.assertIsNone(app.selected_variant)
        self.assertEqual(len(app.chart.find_all()),1)
        self.assertEqual(app.chart.itemcget(app.chart.find_all()[0],'text'),
                         'Selecione um item para comparar.')
        from types import SimpleNamespace
        app.top_routes.selection_set(app.top_routes.get_children()[0])
        app.select_route(SimpleNamespace(widget=app.top_routes))
        self.assertEqual(app.selected_variant,('T4_MAIN_SWORD',1,0))
        self.assertGreater(len(app.chart.find_all()),10)
        app.update_overview(app.current_snapshot,app.current_snapshot['routes'],time.time())
        self.assertEqual(app.selected_variant,('T4_MAIN_SWORD',1,0))
        empty=dict(app.current_snapshot,variants=[],routes=[],observations=[])
        app.current_snapshot=empty
        app.update_overview(empty,[],time.time())
        self.assertIsNone(app.selected_variant)
        self.assertEqual(len(app.chart.find_all()),1)
        self.assertFalse(app.auto_excel.get())
        app.close()

    def test_craft_price_lookup_respects_quality_and_missing_data(self):
        root=tk.Tk();root.withdraw();con=database(':memory:')
        base=dict(Id=1,LocationId=7,ItemTypeId='T4_METALBAR',QualityLevel=1,
                  EnchantmentLevel=0,AuctionType='offer',UnitPriceSilver=100,Amount=20)
        save_order(con,base)
        save_order(con,dict(base,Id=2,ItemTypeId='T4_MAIN_SWORD',QualityLevel=2,
                            AuctionType='request',UnitPriceSilver=3000))
        app=Dashboard(root,con,Feed(),start_feed=False)
        calc=app.calculators
        calc.materials[0][1]['code'].set('T4_METALBAR')
        calc.craft_fields['code'].set('T4_MAIN_SWORD')
        calc.load_prices()
        self.assertEqual(calc.materials[0][1]['price'].get(),'100')
        self.assertEqual(calc.craft_fields['sell'].get(),'')
        calc.craft_fields['quality'].set('2');calc.load_prices()
        self.assertEqual(calc.craft_fields['sell'].get(),'3000')
        app.close()
