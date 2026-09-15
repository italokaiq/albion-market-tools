"""Catálogo completo de códigos negociáveis no mercado, com variantes de encantamento.

Cobre armas, equipamentos, recursos/refinados, consumíveis, monturas, mobília e
sementes de fazenda do ao-data/ao-bin-dumps. Categorias não negociadas no mercado
(diários, contratos de trabalhador, tokens de recompensa, lixo, monturas cosméticas
etc.) ficam de fora.
"""
import json
import re
from pathlib import Path
from recipes import many

TRADABLE_KINDS = ('weapon', 'equipmentitem', 'simpleitem', 'consumableitem',
                   'mount', 'furnitureitem', 'farmableitem')
LEVEL_SUFFIX = re.compile(r'_LEVEL[1-4]$')


def extract(source):
    codes = set()
    names_by_kind = {}
    for kind in TRADABLE_KINDS:
        entries = many(source['items'].get(kind))
        names_by_kind[kind] = {item['@uniquename'] for item in entries}
        for item in entries:
            base = item['@uniquename']
            if LEVEL_SUFFIX.search(base):
                continue
            codes.add(base)
            for enchantment in many(item.get('enchantments', {}).get('enchantment')):
                level = enchantment.get('@enchantmentlevel')
                if level and level != '0':
                    codes.add(base + '@' + level)
    for name in names_by_kind.get('simpleitem', ()):
        match = LEVEL_SUFFIX.search(name)
        if match:
            codes.add(name[:match.start()] + '@' + match.group()[-1])
    return sorted(codes)


if __name__ == '__main__':
    source = json.loads(Path('recipes_source.json').read_text(encoding='utf-8'))
    codes = extract(source)
    Path('market_items.json').write_text(json.dumps(codes, ensure_ascii=False), encoding='utf-8')
    print(f'{len(codes)} códigos de itens negociáveis no catálogo')
