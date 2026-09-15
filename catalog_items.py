"""Catálogo completo de códigos negociáveis no mercado, com variantes de encantamento.

Cobre armas, equipamentos, recursos/refinados, consumíveis, monturas, mobília,
sementes de fazenda, diários, contratos de trabalhador, bandeiras de cerco,
itens de esconderijo, troféus de morte e tokens de recompensa do
ao-data/ao-bin-dumps. Categorias claramente não comercializáveis (dumps
cosméticos de montaria, itens de rastreamento, itens de arma de
transformação, itens da Liga de Cristal) ficam de fora.

Comparado em 15/09/2026 contra o catálogo pesquisável do Albion Free Market
(albionfreemarket.com, ~11.968 itens — ferramenta estabelecida há anos, mesma
fonte de dados AODP): diários e contratos de trabalhador apareciam lá como
categoria pesquisável, mas tinham sido excluídos daqui por suposição de que
não eram negociáveis. Verificado contra a API real antes de incluir: diários
nunca têm preço observado (permanecem "sem dado" na busca, o que é correto
e honesto), mas contratos de trabalhador têm histórico real de negociação
(preço observado em mais de uma cidade nos últimos 30 dias).
"""
import json
import re
from pathlib import Path
from recipes import many

TRADABLE_KINDS = ('weapon', 'equipmentitem', 'simpleitem', 'consumableitem',
                   'mount', 'furnitureitem', 'farmableitem', 'journalitem',
                   'labourercontract', 'hideoutitem', 'siegebanner', 'killtrophy',
                   'rewardtoken', 'trashitem')
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
