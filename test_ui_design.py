import tkinter as tk
import unittest
from ui_design import close_on_escape


class CloseOnEscapeTest(unittest.TestCase):
    """Nenhuma tela do app fechava com Esc antes desta revisão — achado real
    ao auditar navegação por teclado. Nota: testar isso com o diálogo real
    dentro de uma janela .transient() de um root escondido (root.withdraw(),
    usado em todo o resto da suíte para rodar sem piscar janela na tela) não
    funciona — é uma peculiaridade conhecida do Tk/Windows onde uma janela
    transient de um pai nunca mapeado não recebe foco de teclado sintético,
    mesmo via focus_force(). Confirmado manualmente que o app real (root
    sempre visível) não tem esse problema. Este teste cobre close_on_escape
    isoladamente, sem .transient(), onde a entrega do evento é confiável."""

    def setUp(self):
        self.root = tk.Tk(); self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def press_escape(self, window):
        """focus_set() sozinho é suficiente na maioria das vezes, mas o foco
        de teclado sintético do Tk pode ficar com o processo anterior por um
        instante logo após destruir outra janela na mesma suíte — daí o
        focus_force()+lift() e uma segunda rodada de update() antes de
        desistir, em vez de um teste que só passa dependendo da ordem."""
        window.lift(); window.focus_force(); window.focus_set()
        self.root.update()
        window.event_generate('<Escape>')
        self.root.update(); self.root.update()

    def test_escape_calls_the_given_close_function(self):
        window = tk.Toplevel(self.root)
        calls = []
        close_on_escape(window, lambda: calls.append(True))
        self.press_escape(window)
        self.assertEqual(calls, [True])

    def test_escape_destroys_the_window_when_no_close_function_given(self):
        window = tk.Toplevel(self.root)
        close_on_escape(window)
        self.press_escape(window)
        self.assertFalse(window.winfo_exists())


if __name__ == '__main__':
    unittest.main()
