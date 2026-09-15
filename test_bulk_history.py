import tkinter as tk
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dashboard import Dashboard
from monitor import database, Feed
from history import History
from history_ui import flip_entry_from_row, craft_entry_from_row


class FlipEntryFromRowTest(unittest.TestCase):
    def test_predicted_and_realized_are_identical(self):
        predicted, realized = flip_entry_from_row('100', '200', '10', '0', 'Imediata', 'Imediata', 'Sem Premium')
        self.assertEqual(predicted, realized)
        self.assertEqual(predicted['net'], (200 * .92) * 10 - 100 * 10)

    def test_premium_profile_uses_premium_tax(self):
        _, premium = flip_entry_from_row('100', '200', '1', '0', 'Imediata', 'Imediata', 'Premium')
        _, normal = flip_entry_from_row('100', '200', '1', '0', 'Imediata', 'Imediata', 'Sem Premium')
        self.assertGreater(premium['net'], normal['net'])

    def test_order_modes_add_setup_fees(self):
        _, immediate = flip_entry_from_row('100', '200', '1', '0', 'Imediata', 'Imediata', 'Sem Premium')
        _, ordered = flip_entry_from_row('100', '200', '1', '0', 'Ordem de compra', 'Ordem de venda', 'Sem Premium')
        self.assertLess(ordered['net'], immediate['net'])

    def test_invalid_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            flip_entry_from_row('', '200', '1', '0', 'Imediata', 'Imediata', 'Sem Premium')


class CraftEntryFromRowTest(unittest.TestCase):
    def test_net_is_received_minus_spent(self):
        predicted, realized = craft_entry_from_row('2', '1', '1000', '1500', 'Sem Premium')
        self.assertEqual(realized, dict(spent=1000.0, received=1500.0, net=500.0))
        self.assertEqual(predicted['net'], 500.0)
        self.assertEqual(predicted['output'], 2.0)

    def test_accepts_decimal_comma(self):
        predicted, realized = craft_entry_from_row('1', '1', '100,5', '200,25', 'Sem Premium')
        self.assertAlmostEqual(realized['net'], 99.75)

    def test_invalid_numbers_raise_value_error(self):
        with self.assertRaises(ValueError):
            craft_entry_from_row('1', '1', 'abc', '200', 'Sem Premium')


class BulkEntryDialogTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk();self.root.withdraw()
        self.app = Dashboard(self.root, database(':memory:'), Feed(), start_feed=False)
        self.tmp = TemporaryDirectory()
        self.app.history_view.history = History(Path(self.tmp.name) / 'historico.json')

    def tearDown(self):
        self.app.close();self.tmp.cleanup()

    def test_dialog_opens_with_five_prefilled_rows_per_tab(self):
        hv = self.app.history_view
        hv.open_bulk_entry()
        self.assertEqual(len(hv.bulk_flip_rows), 5)
        self.assertEqual(len(hv.bulk_craft_rows), 5)
        dialogs = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(dialogs), 1)
        dialogs[0].destroy()

    def test_submit_registers_filled_rows_and_skips_blank_ones(self):
        hv = self.app.history_view
        hv.open_bulk_entry()
        row0 = hv.bulk_flip_rows[0][1]
        row0['item'].set('Bolsa de teste');row0['buy'].set('100');row0['sell'].set('200');row0['quantity'].set('5')
        crow0 = hv.bulk_craft_rows[0][1]
        crow0['item'].set('Machado de teste');crow0['spent'].set('1000');crow0['received'].set('1800')
        hv.submit_bulk()
        entries = hv.history.read()['entries']
        self.assertEqual(len(entries), 2)
        flip_entry = next(e for e in entries if e['kind'] == 'flipping')
        craft_entry = next(e for e in entries if e['kind'] == 'craft')
        self.assertEqual(flip_entry['label'], 'Bolsa de teste')
        self.assertIsNotNone(flip_entry['realized'])
        self.assertEqual(flip_entry['predicted']['net'], flip_entry['realized']['net'])
        self.assertEqual(craft_entry['label'], 'Machado de teste')
        self.assertEqual(craft_entry['realized']['net'], 800.0)
        # linhas preenchidas somem do formulário; as 4 em branco continuam
        self.assertEqual(len(hv.bulk_flip_rows), 4)
        self.assertEqual(len(hv.bulk_craft_rows), 4)

    def test_submit_reports_error_without_losing_the_row(self):
        hv = self.app.history_view
        hv.open_bulk_entry()
        row0 = hv.bulk_flip_rows[0][1]
        row0['item'].set('Item ruim');row0['buy'].set('100')  # falta 'sell'
        hv.submit_bulk()
        self.assertEqual(hv.history.read()['entries'], [])
        self.assertEqual(len(hv.bulk_flip_rows), 5)  # linha com erro não é removida
        self.assertIn('Item ruim', hv.bulk_status.cget('text'))
        self.assertIn('Nada registrado', hv.bulk_status.cget('text'))

    def test_add_and_remove_row_buttons_change_row_count(self):
        hv = self.app.history_view
        hv.open_bulk_entry()
        before = len(hv.bulk_flip_rows)
        outer, fields = hv.bulk_flip_rows[0]
        outer.destroy();hv.bulk_flip_rows.remove((outer, fields))
        self.assertEqual(len(hv.bulk_flip_rows), before - 1)

    def test_all_blank_rows_report_nothing_to_register(self):
        hv = self.app.history_view
        hv.open_bulk_entry()
        hv.submit_bulk()
        self.assertEqual(hv.history.read()['entries'], [])
