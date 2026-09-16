import time
import tkinter as tk
import unittest
from monitor import database, Feed
from dashboard import Dashboard


class UseRouteTest(unittest.TestCase):
    """use_route() copia uma rota selecionada para a calculadora de flipping,
    escalando o transporte por unidade (campo do painel principal) pela
    quantidade da rota. Encontrado nesta revisão: um transporte inválido
    travava a cópia sem nenhum aviso ao usuário."""

    def setUp(self):
        self.root = tk.Tk(); self.root.withdraw()
        self.app = Dashboard(self.root, database(':memory:'), Feed(), start_feed=False)
        code = next(c for c in self.app.catalog.market_codes if c.startswith('T4_MAIN_SWORD'))
        self.app.selected_variant = (code, 1, 0)
        self.app.catalog_selection = None
        self.app.current_snapshot = dict(routes=[dict(
            code=code, quality=1, enchantment=0, quality_name='Normal',
            origin='Lymhurst', destination='Bridgewatch',
            buy=dict(price=1000, seen=time.time(), amount=5),
            sell=dict(price=2000, seen=time.time(), amount=5), quantity=5, net=900)], variants=[])

    def tearDown(self):
        self.app.close()

    def test_invalid_transport_field_does_not_crash_and_falls_back_to_zero(self):
        for bad in ('abc', '', '  ', '1.2.3'):
            self.app.transport.set(bad)
            self.app.calculators.use_route()  # não deve levantar
            self.assertEqual(self.app.calculators.flip_fields['transport'].get(), '0')
            self.assertIn('Transporte por unidade inválido', self.app.calculators.flip_note.cget('text'))

    def test_valid_transport_field_still_scales_by_quantity(self):
        self.app.transport.set('3,5')  # vírgula decimal, formato aceito no resto do app
        self.app.calculators.use_route()
        self.assertEqual(self.app.calculators.flip_fields['transport'].get(), '17.5')
        self.assertNotIn('inválido', self.app.calculators.flip_note.cget('text'))
        self.assertEqual(self.app.calculators.flip_fields['buy'].get(), '1000')
        self.assertEqual(self.app.calculators.flip_fields['sell'].get(), '2000')


if __name__ == '__main__':
    unittest.main()
