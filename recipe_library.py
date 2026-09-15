"""Biblioteca de receitas de craft salvas pelo usuário, com nome escolhido por ele.

Preços nunca são salvos junto — só código do produto, materiais e campos da
calculadora. Mesmo padrão de gravação atômica com backup usado em
production_profiles.py e history.py.
"""
import json
from datetime import datetime, timezone
from persistence import write_settings
from paths import data_path


class RecipeLibrary:
    def __init__(self, path=None):
        self.path = path or data_path('receitas_salvas.json')

    def read(self):
        if not self.path.exists():
            return {'version': 1, 'recipes': {}}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('recipes'), dict):
            raise ValueError('Formato de biblioteca de receitas não suportado. O arquivo original foi preservado.')
        return data

    def save(self, name, fields, materials):
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError('Informe um nome de até 80 caracteres.')
        data = self.read()
        data['recipes'][name] = dict(fields=fields, materials=materials,
            saved_at=datetime.now(timezone.utc).isoformat())
        write_settings(self.path, data)

    def load(self, name):
        recipes = self.read()['recipes']
        if name not in recipes:
            raise KeyError('Receita não encontrada. O arquivo original foi preservado.')
        recipe = recipes[name]
        if not isinstance(recipe.get('fields'), dict) or not isinstance(recipe.get('materials'), list):
            raise ValueError('Receita salva em formato inválido. O arquivo original foi preservado.')
        return recipe

    def delete(self, name):
        data = self.read()
        if name not in data['recipes']:
            raise KeyError('Receita não encontrada. O arquivo original foi preservado.')
        del data['recipes'][name]
        write_settings(self.path, data)

    def rename(self, old_name, new_name):
        new_name = new_name.strip()
        if not new_name or len(new_name) > 80:
            raise ValueError('Informe um nome de até 80 caracteres.')
        data = self.read()
        if old_name not in data['recipes']:
            raise KeyError('Receita não encontrada. O arquivo original foi preservado.')
        if new_name != old_name and new_name in data['recipes']:
            raise ValueError('Já existe uma receita salva com esse nome.')
        data['recipes'][new_name] = data['recipes'].pop(old_name)
        write_settings(self.path, data)
