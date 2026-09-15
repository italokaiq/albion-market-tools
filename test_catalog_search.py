import tkinter as tk
import unittest
from dashboard import Dashboard
from monitor import database, save_order, Feed
from catalog_search import search_catalog

class CatalogIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        self.app=Dashboard(self.root,database(':memory:'),Feed(),start_feed=False)
    def tearDown(self):self.app.close()

    def test_catalog_selection_without_orders_survives_refresh(self):
        self.app.select_catalog_item('T4_MAIN_SWORD',2)
        self.app.update_overview(self.app.current_snapshot,[],1000)
        self.assertEqual(self.app.selected_variant,('T4_MAIN_SWORD',2,0))
        labels=[self.app.chart.itemcget(i,'text') for i in self.app.chart.find_all() if self.app.chart.type(i)=='text']
        self.assertTrue(any('Boa' in label for label in labels))
        self.assertEqual(labels.count('sem dado'),16)
        self.assertEqual(self.app.current_snapshot['routes'],[])

    def test_unavailable_route_does_not_show_previous_profit(self):
        c=self.app.calculators
        c.flip_fields['buy'].set('100');c.flip_fields['sell'].set('200');c.refresh()
        self.assertTrue(c.flip_table.get_children())
        self.app.select_catalog_item('T4_MAIN_SWORD',1)
        self.app.open_route_summary()
        self.assertFalse(c.flip_table.get_children())
        self.assertIn('não informa quantidade',c.flip_note.cget('text'))

    def test_catalog_dialog_opens_with_results(self):
        self.app.choose_market_item()
        dialogs=[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)]
        self.assertEqual(len(dialogs),1)
        self.root.update_idletasks()
        dialogs[0].destroy()

    def test_catalog_covers_non_equipment_items(self):
        self.assertIn('T4_PLANKS',self.app.catalog.market_codes)
        self.assertIn('T4_PLANKS@1',self.app.catalog.market_codes)

    def test_search_finds_resources_not_just_equipment(self):
        codes=self.app.catalog.market_codes
        matches=search_catalog(codes,self.app.catalog,'tabuas')
        self.assertIn('T4_PLANKS',matches)

    def test_non_equipment_item_shows_real_prices_despite_equipment_only_default(self):
        self.assertTrue(self.app.equipment_only.get())
        save_order(self.app.con,dict(Id=1,LocationId=7,ItemTypeId='T4_PLANKS',QualityLevel=1,
                                      EnchantmentLevel=0,AuctionType='offer',UnitPriceSilver=50,Amount=100))
        save_order(self.app.con,dict(Id=2,LocationId=1002,ItemTypeId='T4_PLANKS',QualityLevel=1,
                                      EnchantmentLevel=0,AuctionType='request',UnitPriceSilver=70,Amount=40))
        self.app.refresh()
        self.app.select_catalog_item('T4_PLANKS',1)
        self.app.draw_chart()
        rows={self.app.city_compare.item(r,'values')[0]:self.app.city_compare.item(r,'values') for r in self.app.city_compare.get_children()}
        self.assertEqual(rows['Thetford'][1],'50,00')
        self.assertEqual(rows['Lymhurst'][3],'70,00')
        self.assertIn('Melhor margem estimada',self.app.selected_margin.cget('text'))

    def test_route_simulation_falls_back_to_chart_margin_with_unknown_volume(self):
        """Sem rota do fluxo (volume conhecido), a simulação usa a mesma margem do gráfico, via API."""
        c=self.app.calculators
        self.app.select_catalog_item('T4_MAIN_SWORD',1)
        self.app.price_api.cache[('T4_MAIN_SWORD',1)]={
            '7':{'offer':dict(price=100,seen=__import__('time').time(),amount=None,source='API')},
            '1002':{'request':dict(price=200,seen=__import__('time').time(),amount=None,source='API')}}
        self.app.open_route_summary()
        self.assertEqual(c.flip_fields['buy'].get(),'100')
        self.assertEqual(c.flip_fields['sell'].get(),'200')
        self.assertIn('Simulação de referência',c.flip_note.cget('text'))
        self.assertIn('Volume desconhecido',c.flip_note.cget('text'))
        self.assertTrue(c.flip_table.get_children())
        c.flip_fields['quantity'].set('999999')
        c.refresh()
        self.assertTrue(c.flip_table.get_children(),'quantidade grande não deveria travar quando o volume e desconhecido')

    def test_search_filters_by_tier_and_enchantment(self):
        codes=self.app.catalog.market_codes
        matches=search_catalog(codes,self.app.catalog,'espada',tier='4',enchant='2')
        self.assertTrue(matches)
        self.assertTrue(all(c.startswith('T4_') and c.endswith('@2') for c in matches))
        wrong_tier=search_catalog(codes,self.app.catalog,'espada',tier='5',enchant='2')
        self.assertTrue(all(not c.startswith('T4_') for c in wrong_tier))
