"""Resolução de caminhos que funciona igual rodando como script e empacotado em .exe.

Um .exe de arquivo único (PyInstaller --onefile) extrai os recursos
empacotados para uma pasta temporária a cada execução — `__file__` dentro
dela aponta para essa pasta, que é apagada ao fechar o programa. Catálogos
somente leitura (empacotados) usam `resource_path`; dados do usuário que
precisam sobreviver entre execuções (banco, preferências, histórico, logs)
usam `data_path`, que aponta para a pasta do próprio .exe, nunca para a
pasta temporária.
"""
import sys
from pathlib import Path

_FROZEN = bool(getattr(sys, 'frozen', False))
_HERE = Path(__file__).resolve().parent


def resource_path(name):
    base = Path(getattr(sys, '_MEIPASS', _HERE)) if _FROZEN else _HERE
    return base / name


def data_path(name):
    base = Path(sys.executable).resolve().parent if _FROZEN else _HERE
    return base / name
