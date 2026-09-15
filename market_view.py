"""Nomes, filtros e comparação de observações; sem inferir ordens ausentes."""
import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

QUALITY = {1: 'Normal', 2: 'Boa', 3: 'Excepcional', 4: 'Excelente', 5: 'Obra-prima'}


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD', str(text).casefold())
                   if not unicodedata.combining(c))


@lru_cache(maxsize=32768)
def item_search_text(code,name):
    tier=code.split('_')[0]
    enchant=code.split('@',1)[1] if '@' in code else '0'
    return folded(f'{name} {code} {tier}.{enchant}')


def matches_item(query,code,name):
    return all(word in item_search_text(code,name) for word in folded(query).split())


def item_tier(code):
    match = re.match(r'T(\d+)_', code)
    return match[1] if match else ''


def item_enchant(code):
    return code.split('@', 1)[1] if '@' in code else '0'


class Catalog:
    def __init__(self):
        base = Path(__file__).parent
        self.names, self.markets = {}, {}
        self.market_codes = []
        self.errors = []
        for filename in ('items', 'world'):
            try:
                rows = json.loads((base / (filename + '.json')).read_bytes())
                for row in rows:
                    if filename == 'items':
                        names = row.get('LocalizedNames') or {}
                        self.names[row['UniqueName']] = names.get('PT-BR') or names.get('EN-US') or row['UniqueName']
                    else:
                        key = row['Index']
                        self.markets[str(int(key)) if key.isdigit() else key] = row['UniqueName']
            except (OSError, ValueError, KeyError, TypeError):
                self.errors.append(filename)
        try:
            self.market_codes = json.loads((base / 'market_items.json').read_bytes())
            if not isinstance(self.market_codes, list) or not self.market_codes:
                raise ValueError('Catálogo de itens negociáveis vazio ou inválido.')
        except (OSError, ValueError, KeyError, TypeError):
            self.market_codes = []
            self.errors.append('market_items')

    def item(self, code):
        return self.names.get(code, self.names.get(code.split('@')[0], code))

    def market(self, code):
        if str(code) == '3003':
            return 'Mercado Negro'
        return self.markets.get(code, 'Mercado ' + code)


def age_text(seen, now):
    seconds = max(0, int(now-seen))
    if seconds < 60:
        return f'{seconds}s'
    if seconds < 3600:
        return f'{seconds//60}min'
    return f'{seconds//3600}h {(seconds%3600)//60}min'


def freshness(seen, now):
    age = max(0, now-seen)
    return 'fresh' if age <= 300 else 'warm' if age <= 900 else 'old'


def filtered_orders(con, catalog, now, minutes=15, query='', market='', tier='', enchant='', quality=''):
    rows = con.execute('SELECT id,location,item,quality,enchantment,side,price,amount,seen '
                       'FROM orders WHERE seen>=? AND amount>0 ORDER BY seen DESC',
                       (now-minutes*60,)).fetchall()
    result = []
    words=folded(query).split()
    market_query=folded(market)
    item_matches={}
    market_matches={}
    for row in rows:
        oid, loc, item, q, e, side, price, amount, seen = row
        if enchant and str(e) != enchant:
            continue
        if quality and str(q) != quality:
            continue
        if item not in item_matches:
            item_matches[item]=(not tier or item_tier(item)==tier) and (
                not words or all(word in item_search_text(item,catalog.item(item)) for word in words))
        if not item_matches[item]:continue
        if market_query:
            if loc not in market_matches:
                market_matches[loc]=market_query in folded(loc+' '+catalog.market(loc))
            if not market_matches[loc]:continue
        result.append(row)
    return result


def compare(rows):
    groups = {}
    for oid, loc, item, quality, enchant, side, price, amount, seen in rows:
        key = (item, quality, enchant, loc)
        group = groups.setdefault(key, {})
        best = group.get(side)
        better = best is None or (price < best[0] if side == 'offer' else price > best[0])
        if better:
            group[side] = (price, amount, seen)
        elif price == best[0]:
            # A idade da quantidade agregada é a da observação mais antiga.
            group[side] = (price, amount + best[1], min(seen, best[2]))
    return sorted(groups.items())


def sync_table(table, entries):
    """Atualiza por chave, preservando seleção e a linha no topo quando possível."""
    current = table.get_children()
    top = table.identify_row(1) or table.identify_row(30)
    position = table.yview()[0]
    desired = {key for key, values, tag in entries}
    existing=set(current)
    unchanged_order=tuple(key for key,_,_ in entries)==tuple(current)
    for key in current:
        if key not in desired:
            table.delete(key)
    for index, (key, values, tag) in enumerate(entries):
        if key in existing:
            if tuple(map(str, table.item(key, 'values'))) != tuple(map(str, values)) or table.item(key, 'tags') != (tag,):
                table.item(key, values=values, tags=(tag,))
            if not unchanged_order:table.move(key, '', index)
        else:
            table.insert('', index, iid=key, values=values, tags=(tag,))
    children = table.get_children()
    if top in children and position > 0:
        table.yview_moveto(children.index(top)/max(1, len(children)))
    else:
        table.yview_moveto(position)
