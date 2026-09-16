"""Custo de upgrade de encantamento (rúnica/alma/relíquia), extraído direto dos
dados do jogo — cada nível tem um requisito exato de recurso e quantidade,
sem custo em prata da Fundição de Artefatos em si (só o preço dos recursos).

Encantamento .4 não pode ser alcançado por upgrade — só craftando direto com
material .4 — então não aparece aqui (o jogo não define upgraderequirements
para esse nível).
"""
import json
from pathlib import Path
from recipes import many

UPGRADABLE_KINDS = ('weapon', 'equipmentitem')


def extract(source):
    steps = {}
    for kind in UPGRADABLE_KINDS:
        for item in many(source['items'].get(kind)):
            base = item['@uniquename']
            for enchantment in many(item.get('enchantments', {}).get('enchantment')):
                level = enchantment.get('@enchantmentlevel')
                requirements = enchantment.get('upgraderequirements')
                if not level or not requirements:
                    continue
                materials = [dict(resource=r['@uniquename'], count=float(r['@count']))
                             for r in many(requirements.get('upgraderesource'))]
                if materials:
                    steps[f'{base}@{level}'] = dict(base=base, level=int(level), materials=materials)
    return steps


if __name__ == '__main__':
    source = json.loads(Path('recipes_source.json').read_text(encoding='utf-8'))
    steps = extract(source)
    Path('upgrade_costs.json').write_text(json.dumps(steps, ensure_ascii=False), encoding='utf-8')
    print(f'{len(steps)} passos de upgrade de encantamento')
