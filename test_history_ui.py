import tkinter as tk
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dashboard import Dashboard
from monitor import database, Feed
from history import History


class HistoryUITest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk();self.root.withdraw()
        self.app = Dashboard(self.root, database(':memory:'), Feed(), start_feed=False)
        self.tmp = TemporaryDirectory()
        path = Path(self.tmp.name) / 'historico.json'
        self.app.calculators.history = History(path)
        self.app.history_view.history = History(path)

    def tearDown(self):
        self.app.close();self.tmp.cleanup()

    def test_record_flip_appends_entry_with_calculated_profit(self):
        c = self.app.calculators
        c.flip_fields['buy'].set('100');c.flip_fields['sell'].set('200');c.flip_fields['quantity'].set('10')
        self.app.selected_variant = ('T4_BAG', 1, 0)
        c.record_flip()
        entries = self.app.history_view.history.read()['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['kind'], 'flipping')
        self.assertEqual(entries[0]['item'], 'T4_BAG')
        self.assertIsNone(entries[0]['realized'])
        self.assertIn('Operação registrada', c.flip_note.cget('text'))

    def test_record_flip_rejects_invalid_input_without_saving(self):
        c = self.app.calculators
        c.flip_fields['buy'].set('');c.flip_fields['sell'].set('200')
        c.record_flip()
        self.assertEqual(self.app.history_view.history.read()['entries'], [])
        self.assertIn('Não é possível registrar', c.flip_note.cget('text'))

    def test_record_craft_appends_entry(self):
        c = self.app.calculators
        c.apply_recipe('T4_MAIN_SWORD', 0)
        c.craft_fields['sell'].set('5000');c.craft_fields['rrr'].set('24');c.craft_fields['station'].set('500')
        c.materials[0][1]['price'].set('100');c.materials[1][1]['price'].set('80')
        c.record_craft()
        entries = self.app.history_view.history.read()['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['kind'], 'craft')
        self.assertEqual(entries[0]['product'], 'T4_MAIN_SWORD')

    def test_history_view_refresh_shows_predicted_and_realized_totals(self):
        hv = self.app.history_view
        entry_id = hv.history.add(dict(kind='flipping', item='T4_BAG', quality=1, enchantment=0,
            label='Bolsa', predicted=dict(buy='100', sell='200', quantity='10', transport='0',
                buy_mode='Imediata', sell_mode='Imediata', buy_relists='0', sell_relists='0',
                profile='Sem Premium', net=840, unit_net=84)))
        hv.refresh()
        self.assertEqual(hv.metrics['total'].cget('text'), '1')
        self.assertEqual(hv.metrics['confirmed'].cget('text'), '0/1')
        hv.history.confirm(entry_id, dict(buy='110', sell='190', quantity='10', transport='0',
            buy_mode='Imediata', sell_mode='Imediata', buy_relists='0', sell_relists='0', net=123, unit_net=12.3))
        hv.refresh()
        self.assertEqual(hv.metrics['confirmed'].cget('text'), '1/1')
        self.assertIn('123', hv.metrics['realized'].cget('text'))
        rows = [hv.table.item(i, 'values') for i in hv.table.get_children()]
        self.assertEqual(rows[0][-1], 'Confirmada')

    def test_confirm_dialog_opens_for_selected_flip_entry(self):
        hv = self.app.history_view
        entry_id = hv.history.add(dict(kind='flipping', item='T4_BAG', quality=1, enchantment=0,
            label='Bolsa', predicted=dict(buy='100', sell='200', quantity='10', transport='0',
                buy_mode='Imediata', sell_mode='Imediata', buy_relists='0', sell_relists='0',
                profile='Sem Premium', net=840, unit_net=84)))
        hv.refresh()
        hv.table.selection_set(entry_id)
        hv.open_confirm()
        dialogs = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(dialogs), 1)
        dialogs[0].destroy()

    def test_remove_selected_deletes_entry(self):
        hv = self.app.history_view
        entry_id = hv.history.add(dict(kind='craft', product='T4_MAIN_SWORD', quality='1', label='Espada',
            predicted=dict(crafts='1', output=1, net=100, cash=100, upfront=0, revenue=100, profile='Sem Premium')))
        hv.refresh()
        hv.table.selection_set(entry_id)
        hv.remove_selected()
        self.assertEqual(hv.history.read()['entries'], [])

    def test_history_tab_reachable_and_lazy_refreshed_on_selection(self):
        self.app.notebook.select(self.app.history_view.tab)
        self.app.page_changed()
        self.assertEqual(self.app.page_title.cget('text'), 'Histórico de operações')
