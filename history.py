"""Histórico de operações registradas pelo usuário: lucro previsto e realizado.

Nada aqui é inferido do fluxo ou da API — cada entrada é gravada porque o
usuário clicou em "Registrar operação" com os valores calculados naquele
momento, e a confirmação de execução exige que o próprio usuário informe o
que realmente comprou/vendeu. Gravação atômica com backup da versão
anterior, como as demais preferências do app.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from persistence import write_settings


class History:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).with_name('historico.json')

    def read(self):
        if not self.path.exists():
            return {'version': 1, 'entries': []}
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('entries'), list):
            raise ValueError('Formato de histórico não suportado. O arquivo original foi preservado.')
        return data

    def add(self, entry):
        data = self.read()
        record = dict(entry, id=uuid.uuid4().hex,
                       recorded_at=datetime.now(timezone.utc).isoformat(), realized=None)
        data['entries'].insert(0, record)
        write_settings(self.path, data)
        return record['id']

    def confirm(self, entry_id, realized):
        data = self.read()
        for entry in data['entries']:
            if entry['id'] == entry_id:
                entry['realized'] = dict(realized, confirmed_at=datetime.now(timezone.utc).isoformat())
                write_settings(self.path, data)
                return
        raise KeyError('Operação não encontrada. O arquivo original foi preservado.')

    def delete(self, entry_id):
        data = self.read()
        remaining = [e for e in data['entries'] if e['id'] != entry_id]
        if len(remaining) == len(data['entries']):
            raise KeyError('Operação não encontrada. O arquivo original foi preservado.')
        data['entries'] = remaining
        write_settings(self.path, data)
