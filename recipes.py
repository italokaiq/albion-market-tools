"""Catálogo local de receitas de equipamentos do ao-data/ao-bin-dumps."""
import json
from pathlib import Path
from market_view import folded, item_search_text


def many(value):
    return value if isinstance(value,list) else [value] if isinstance(value,dict) else []


def extract(source):
    recipes={}
    for kind in ('weapon','equipmentitem'):
        for item in many(source['items'].get(kind)):
            base=item['@uniquename']
            versions=[(base,item)]+[(base+'@'+e['@enchantmentlevel'],e)
                for e in many(item.get('enchantments',{}).get('enchantment'))]
            for code,version in versions:
                alternatives=[]
                for req in many(version.get('craftingrequirements')):
                    if req.get('@swaptransaction')=='true':continue
                    materials=[]
                    for resource in many(req.get('craftresource')):
                        resource_code=resource['@uniquename']
                        enchant=resource.get('@enchantmentlevel','0')
                        if enchant!='0':resource_code+='@'+enchant
                        materials.append(dict(code=resource_code,quantity=float(resource['@count']),
                            returns=resource.get('@maxreturnamount')!='0' and '_ARTEFACT_' not in resource_code))
                    if materials:
                        alternatives.append(dict(materials=materials,output=1,silver=float(req.get('@silver',0))))
                if alternatives:recipes[code]=alternatives
    return recipes


class RecipeCatalog:
    def __init__(self,catalog):
        from paths import resource_path
        self.catalog=catalog
        self.error=''
        try:self.recipes=json.loads(resource_path('recipes.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):
            self.recipes={};self.error='Catálogo de receitas indisponível. Você pode preencher a receita manualmente.'
        self.codes=sorted(self.recipes,key=lambda c:(catalog.item(c),c))

    def search(self,query):
        words=folded(query).split()
        if not words:return list(self.codes)
        return [c for c in self.codes if all(word in item_search_text(c,self.catalog.item(c)) for word in words)]

    def label(self,code):
        tier=code.split('_')[0];enchant=code.split('@')[1] if '@' in code else '0'
        return f'{self.catalog.item(code)} · {tier}.{enchant} · {code}'


if __name__=='__main__':
    source=json.loads(Path('recipes_source.json').read_text(encoding='utf-8'))
    data=extract(source)
    Path('recipes.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    print(f'{len(data)} equipamentos/encantamentos com receita')
