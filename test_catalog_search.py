import tkinter as tk
import unittest
from dashboard import Dashboard
from monitor import database, Feed

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
