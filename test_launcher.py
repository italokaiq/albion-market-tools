import tkinter as tk
import unittest
from launcher import set_dpi_aware, apply_dpi_scaling


class DpiAwarenessTest(unittest.TestCase):
    """Sem monitor de alta densidade real para testar contra, mas garante que
    as duas chamadas de API do Windows nunca travam o app (aqui ou numa
    máquina sem essas APIs) e que a escala aplicada é um número positivo e
    plausível, não um valor inválido silenciosamente aceito."""

    def test_set_dpi_aware_never_raises(self):
        set_dpi_aware()

    def test_apply_dpi_scaling_never_raises_and_sets_a_positive_scale(self):
        root = tk.Tk(); root.withdraw()
        try:
            apply_dpi_scaling(root)
            scale = root.tk.call('tk', 'scaling')
            self.assertGreater(float(scale), 0)
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
