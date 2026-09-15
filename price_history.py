"""Histórico de preço médio por período, via API das Américas.

Mesma cautela do resto do app: isto é o preço médio anunciado/observado
por intervalo, não uma confirmação de vendas concluídas — a documentação
pública da API não garante a distinção, então tratamos como anúncio,
igual ao restante do app.
"""
import datetime as dt
import gzip
import json
import threading
import time
import urllib.parse
import urllib.request

HOST = 'https://west.albion-online-data.com'

PERIODS = {
    '24h': dict(label='24 horas', hours=24, scale=1),
    '3d': dict(label='3 dias', hours=24 * 3, scale=6),
    '7d': dict(label='7 dias', hours=24 * 7, scale=24),
    '30d': dict(label='30 dias', hours=24 * 30, scale=24),
}


def fetch_history(code, quality, city, period, now=None):
    if period not in PERIODS:
        raise ValueError('Período inválido: ' + period)
    spec = PERIODS[period]
    now = now if now is not None else dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(hours=spec['hours'])
    query = urllib.parse.urlencode({
        'locations': city, 'qualities': str(quality), 'time-scale': str(spec['scale']),
        'date': f'{start.month}-{start.day}-{start.year}',
        'end_date': f'{now.month}-{now.day}-{now.year}',
    })
    url = f'{HOST}/api/v2/stats/history/{urllib.parse.quote(code, safe="")}.json?{query}'
    request = urllib.request.Request(url, headers={'Accept-Encoding': 'gzip', 'User-Agent': 'AlbionMarketDesk/1.0'})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Resposta da API excede o limite')
        if response.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
    return parse_history(raw, city)


def parse_history(raw, city):
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError('Formato inesperado da API')
    entry = next((r for r in rows if isinstance(r, dict) and r.get('location') == city), None)
    if not entry:
        return []
    points = []
    for row in entry.get('data', []):
        try:
            timestamp = dt.datetime.fromisoformat(str(row['timestamp']))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
            price = int(row['avg_price'])
            amount = int(row['item_count'])
            if price <= 0:
                continue
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        points.append(dict(seen=timestamp.timestamp(), price=price, amount=amount))
    points.sort(key=lambda p: p['seen'])
    return points


class PriceHistory:
    def __init__(self, enabled=True, fetcher=fetch_history):
        self.enabled = enabled
        self.fetcher = fetcher
        self.cache = {}
        self.messages = {}
        self.attempts = {}
        self.busy = set()
        self.lock = threading.Lock()

    def request(self, code, quality, city, period):
        if not self.enabled or not code or not city:
            return
        key = (code, quality, city, period)
        with self.lock:
            now = time.time()
            if key in self.busy or now - self.attempts.get(key, 0) < 60:
                return
            self.busy.add(key)
            self.attempts[key] = now
            self.messages[key] = f'Consultando histórico de {PERIODS[period]["label"]}…'

        def work():
            try:
                points = self.fetcher(code, quality, city, period)
                with self.lock:
                    self.cache[key] = points
                    self.messages[key] = (f'Histórico consultado às {time.strftime("%H:%M:%S")}.' if points
                        else 'API consultada: sem histórico de preço anunciado para este item/cidade/período.')
            except Exception as error:
                with self.lock:
                    self.messages[key] = f'Não foi possível consultar o histórico ({type(error).__name__}). Nova tentativa em até 60s.'
            finally:
                with self.lock:
                    self.busy.discard(key)
        threading.Thread(target=work, daemon=True).start()

    def read(self, code, quality, city, period):
        if not code or not city:
            return [], 'Selecione um item e uma cidade para ver o histórico.'
        key = (code, quality, city, period)
        with self.lock:
            return self.cache.get(key, []), self.messages.get(key, 'Aguardando consulta de histórico.')
