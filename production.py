"""Cadeia de produção: receitas reais e preços observados; custos ausentes bloqueiam opções."""
import json
from pathlib import Path
from functools import lru_cache
from recipes import many
from trading import CITIES
from economics import number, SALES_TAX, SETUP_FEE

PRODUCTION_CITIES=[(c,n) for c,n in CITIES if c!='3003']

def refining_recipes():
    source=json.loads(Path(__file__).with_name('recipes_source.json').read_text(encoding='utf8'))
    result={}
    for item in many(source['items'].get('simpleitem')):
        if item.get('@shopsubcategory1')!='refinedresources':continue
        code=item['@uniquename'];ench=item.get('@enchantmentlevel','0')
        if ench!='0':code+='@'+ench
        options=[]
        for req in many(item.get('craftingrequirements')):
            if req.get('@swaptransaction')=='true':continue
            materials=[]
            for m in many(req.get('craftresource')):
                mc=m['@uniquename'];me=m.get('@enchantmentlevel','0')
                if me!='0':mc+='@'+me
                materials.append(dict(code=mc,quantity=float(m['@count']),returns=m.get('@maxreturnamount')!='0'))
            # Compare the conventional recipe; faction-token substitutions need their own valuation.
            if materials and not any('TOKEN' in m['code'] for m in materials):
                options.append(dict(materials=materials,output=float(req.get('@amountcrafted',1)),silver=float(req.get('@silver',0))))
        if options:result[code]=options
    return result

def dependency_codes(materials,recipes):
    seen=set()
    def visit(code):
        if code in seen:return
        seen.add(code)
        for recipe in recipes.get(code,[]):
            for m in recipe['materials']:visit(m['code'])
    for m in materials:visit(m['code'])
    return seen

def plan_production(materials,recipes,prices,product,quality,crafts,output,settings,shipping,
                    premium=False,buy_order=False,sell_order=False,recipe_silver=0):
    """Custos econômicos por lote; retornos são estoque esperado, nunca caixa realizado."""
    crafts=number(crafts,'quantidade de crafts',1,integer=True)
    output=number(output,'itens por craft',1,integer=True)
    shipping=number(shipping,'transporte por unidade por trecho')
    if not materials:raise ValueError('Informe os materiais da receita.')
    materials=[dict(m,quantity=number(m['quantity'],'quantidade do material '+m['code'],.000001)) for m in materials]
    tax=SALES_TAX['Premium' if premium else 'Sem Premium'];buy_fee=SETUP_FEE if buy_order else 0
    buy_side='request' if buy_order else 'offer';sell_side='offer' if sell_order else 'request'
    cities=[c for c,_ in PRODUCTION_CITIES]
    def condition(stage,city):
        value=settings.get((stage,city))
        if value is None:return None
        return (number(value[0],'retorno (%)',0,99.99)/100,number(value[1],'estação por operação'))
    def price(code,q,city,side):return prices.get((code,q,city,side))
    @lru_cache(None)
    def options(code,destination,trail=()):
        if code in trail:raise ValueError('Ciclo na receita de refino: '+code)
        candidates=[]
        for city in cities:
            p=price(code,1,city,buy_side)
            transport=shipping if city!=destination else 0
            if p:
                candidates.append(dict(cost=p['price']*(1+buy_fee)+transport,
                    cash=p['price']*(1+buy_fee)+transport,method='Comprar refinado' if code in recipes else 'Comprar recurso',
                    city=city,code=code,children=[],seen=p['seen'],amount=p['amount'],price=p['price'],source=p['source'],return_value=p['price']))
            terms=condition(code,city)
            if not terms:continue
            rrr,station=terms
            for recipe in recipes.get(code,[]):
                children=[]
                for m in recipe['materials']:
                    choices=options(m['code'],city,trail+(code,))
                    if not choices:break
                    best=min(choices,key=lambda o:o['cost'])
                    children.append((m,best))
                else:
                    economic=sum(m['quantity']*(child['cost']-(child['return_value']*rrr if m['returns'] else 0)) for m,child in children)
                    cash=sum(m['quantity']*child['cash'] for m,child in children)
                    candidates.append(dict(cost=(economic+station+recipe['silver'])/recipe['output']+transport,
                        cash=(cash+station+recipe['silver'])/recipe['output']+transport,
                        method='Refinar',city=city,code=code,children=children,
                        seen=min(child['seen'] for _,child in children),amount=None,output=recipe['output'],
                        return_value=(economic+station+recipe['silver'])/recipe['output']))
        return candidates
    rows=[];supply=[];sales=[];missing=[]
    for city in cities:
        terms=condition('craft',city)
        choices=[]
        for m in materials:
            candidates=options(m['code'],city)
            for kind in ('Comprar refinado','Comprar recurso','Refinar'):
                subset=[o for o in candidates if o['method']==kind]
                if subset:supply.append(dict(destination=city,material=m['code'],**min(subset,key=lambda o:o['cost'])))
            if not candidates:missing.append(m['code']);continue
            choices.append((m,min(candidates,key=lambda o:o['cost'])))
        if not terms or len(choices)!=len(materials):continue
        rrr,station=terms
        economic=crafts*(sum(m['quantity']*(o['cost']-(o['return_value']*rrr if m['returns'] else 0)) for m,o in choices)+station+recipe_silver)
        cash=crafts*(sum(float(m['quantity'])*o['cash'] for m,o in choices)+station+recipe_silver)
        material_shortfalls=[dict(material=m['code'],method=o['method'],city=o['city'],required=m['quantity']*crafts,available=o['amount'])
            for m,o in choices if o.get('amount') is not None and o['amount']<m['quantity']*crafts]
        for dest,_ in CITIES:
            p=price(product,quality,dest,sell_side)
            if not p:continue
            transport=crafts*output*shipping if city!=dest else 0
            revenue=p['price']*crafts*output
            net=revenue*(1-tax-(SETUP_FEE if sell_order else 0))-economic-transport
            shortfalls=list(material_shortfalls)
            if p.get('amount') is not None and p['amount']<crafts*output:
                shortfalls.append(dict(material=product,method='Venda',city=dest,required=crafts*output,available=p['amount']))
            rows.append(dict(city=city,destination=dest,net=net,cost=economic+transport,
                cash=cash+transport,revenue=revenue,choices=choices,sale=p,shortfalls=shortfalls,
                seen=min([p['seen']]+[o['seen'] for _,o in choices])))
    for city,_ in CITIES:
        p=price(product,quality,city,sell_side)
        if p:sales.append(dict(city=city,price=p['price'],net=p['price']*(1-tax-(SETUP_FEE if sell_order else 0)),**{k:p[k] for k in ('seen','amount','source')}))
    return dict(routes=sorted(rows,key=lambda r:-r['net']),supply=supply,sales=sorted(sales,key=lambda s:-s['net']),missing=sorted(set(missing)))
