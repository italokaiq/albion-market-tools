from trading import city_id


def observed_price(rows,api,code,quality,city,side,now,max_age):
    candidates=[]
    for oid,loc,item,q,e,order_side,price,amount,seen in rows:
        if item==code and q==quality and city_id(loc)==city and order_side==side and amount>0 and price>0 and 0<=now-seen<=max_age:
            candidates.append(dict(price=price,seen=seen,amount=amount,source='Fluxo'))
    live=(min(candidates,key=lambda p:p['price']) if side=='offer' else max(candidates,key=lambda p:p['price'])) if candidates else None
    remote=api.get((code,quality),{}).get(city,{}).get(side)
    if remote and not 0<=now-remote['seen']<=max_age:remote=None
    if remote and (live is None or remote['seen']>live['seen']):return remote
    return live
