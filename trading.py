"""Matriz de cidades e rotas para compra e venda imediatas observadas."""
import time
from market_view import compare, QUALITY

# AODP lib/location.rb, inclusive separação do Mercado Negro e dos portais.
CITIES = [('7','Thetford'),('4002','Fort Sterling'),('2004','Bridgewatch'),
          ('3008','Martlock'),('1002','Lymhurst'),('3005','Caerleon'),
          ('3003','Mercado Negro'),('5003','Brecilien')]
ALIASES = {'301':'7','1301':'1002','2301':'2004','3301':'3008','4301':'4002','3013':'3005'}


def city_id(value):
    value = str(value).removesuffix('-Auction2')
    if value.isdigit():
        value = str(int(value))
    return ALIASES.get(value,value)


def equipment(code):
    return any('_'+part in code for part in ('MAIN_','2H_','OFF_','HEAD_','ARMOR_','SHOES_','BAG','CAPE'))


def snapshot(rows, catalog, minutes=15, tax=0, transport=0, equipment_only=True, now=None, api=None):
    now = time.time() if now is None else now
    if not 0 <= tax <= 1 or transport < 0:
        raise ValueError('Taxa deve ficar entre 0 e 100%; transporte não pode ser negativo.')
    valid_ids = dict(CITIES)
    unique = {}
    for row in rows:
        oid,loc,item,q,e,side,price,amount,seen = row
        loc = city_id(loc)
        if loc not in valid_ids or seen < now-minutes*60 or amount <= 0 or price <= 0:
            continue
        if equipment_only and not equipment(item):
            continue
        key = (oid,loc)
        if key not in unique or unique[key][-1] < seen:
            unique[key] = (oid,loc,item,q,e,side,price,amount,seen)
    variants = {}
    observations = []
    for (item,q,e,loc),sides in compare(list(unique.values())):
        key = (item,q,e)
        variant = variants.setdefault(key,dict(code=item,quality=q,enchantment=e,
            name=catalog.item(item),quality_name=QUALITY.get(q,str(q)),markets={}))
        variant['markets'][loc] = {side:dict(price=value[0],amount=value[1],seen=value[2])
                                  for side,value in sides.items()}
        for side,value in sides.items():
            observations.append(dict(code=item,name=catalog.item(item),quality=q,enchantment=e,
                city=valid_ids[loc],city_id=loc,side=side,price=value[0],amount=value[1],seen=value[2]))
    routes = []
    for v in variants.values():
        if api:
            from market_api import combine_prices
            v['markets']=combine_prices(v['markets'],api.get((v['code'],v['quality']),{}))
        candidates = []
        for origin, offers in v['markets'].items():
            if 'offer' not in offers:
                continue
            buy = offers['offer']
            if buy.get('amount') is None or not 0<=now-buy['seen']<=minutes*60:continue
            for destination, bids in v['markets'].items():
                if origin == destination or 'request' not in bids:
                    continue
                sell = bids['request']
                if sell.get('amount') is None or not 0<=now-sell['seen']<=minutes*60:continue
                net = sell['price']*(1-tax)-buy['price']-transport
                candidates.append(dict(code=v['code'],name=v['name'],quality=v['quality'],
                    quality_name=v['quality_name'],enchantment=v['enchantment'],
                    origin=valid_ids[origin],destination=valid_ids[destination],buy=buy,sell=sell,
                    quantity=min(buy['amount'],sell['amount']),net=net,
                    margin=net/buy['price']))
        if candidates:
            routes.append(max(candidates,key=lambda r:(r['net'],r['quantity'],r['origin'],r['destination'])))
    routes.sort(key=lambda r:(-r['net'],r['code'],r['quality']))
    return dict(generated=now,minutes=minutes,tax=tax,transport=transport,
                equipment_only=equipment_only,cities=CITIES,
                variants=sorted(variants.values(),key=lambda v:(v['name'],v['code'],v['quality'],v['enchantment'])),
                routes=routes,observations=observations)

def selected_item_margin(markets,tax,transport,max_age,now):
    """Melhor margem unitária entre cidades, somente com observações recentes."""
    import math
    if not all(math.isfinite(v) for v in (tax,transport)) or not 0<=tax<1 or transport<0:
        raise ValueError('Informe imposto válido e transporte não negativo.')
    candidates=[]
    def recent(p):return p and p['price']>0 and 0<=now-p['seen']<=max_age
    for origin,sides in markets.items():
        buy=sides.get('offer')
        if not recent(buy):continue
        for destination,other in markets.items():
            sell=other.get('request')
            if origin==destination or not recent(sell):continue
            net=sell['price']*(1-tax)-buy['price']-transport
            volume=None if buy.get('amount') is None or sell.get('amount') is None else min(buy['amount'],sell['amount'])
            candidates.append(dict(origin=origin,destination=destination,net=net,
                roi=net/(buy['price']+transport),quantity=volume))
    return max(candidates,key=lambda r:(r['net'],r['origin'],r['destination'])) if candidates else None
