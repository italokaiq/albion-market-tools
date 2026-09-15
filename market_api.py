"""Preços agregados da API Américas, separados de ordens com quantidade conhecida."""
import datetime as dt
import gzip
import json
import threading
import time
import urllib.parse
import urllib.request
from trading import CITIES

HOST='https://west.albion-online-data.com'


def parse_prices(rows,code,quality,now=None):
    now=time.time() if now is None else now
    if not isinstance(rows,list):raise ValueError('Formato inesperado da API')
    names={name:loc for loc,name in CITIES}
    names['Black Market']='3003'
    output={}
    for row in rows:
        if not isinstance(row,dict) or row.get('item_id')!=code or row.get('quality')!=quality:
            continue
        loc=names.get(row.get('city'))
        if not loc:continue
        for side,field in [('offer','sell_price_min'),('request','buy_price_max')]:
            try:
                price=int(row[field])
                date=row[field+'_date']
                if not isinstance(date,str):continue
                stamp=dt.datetime.fromisoformat(date.replace('Z','+00:00'))
                if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=dt.timezone.utc)
                seen=stamp.timestamp()
                if price<=0 or stamp.year<2000 or seen>now+300:continue
            except (ValueError,TypeError,KeyError,OverflowError):continue
            output.setdefault(loc,{})[side]=dict(price=price,seen=seen,amount=None,source='API')
    return output


def fetch_prices(code,quality):
    query=urllib.parse.urlencode({'locations':','.join(loc for loc,_ in CITIES),'qualities':str(quality)})
    url=f'{HOST}/api/v2/stats/prices/{urllib.parse.quote(code,safe="")}.json?{query}'
    request=urllib.request.Request(url,headers={'Accept-Encoding':'gzip','User-Agent':'AlbionMarketDesk/1.0'})
    with urllib.request.urlopen(request,timeout=15) as response:
        raw=response.read(4_000_001)
        if len(raw)>4_000_000:raise ValueError('Resposta da API excede o limite')
        if response.headers.get('Content-Encoding')=='gzip':raw=gzip.decompress(raw)
    return parse_prices(json.loads(raw),code,quality)


def fetch_many(codes):
    codes=sorted(set(codes))
    if not codes:return {}
    if len(codes)>40:raise ValueError('Consulte até 40 itens por receita.')
    query=urllib.parse.urlencode({'locations':','.join(loc for loc,_ in CITIES),'qualities':'1,2,3,4,5'})
    url=f'{HOST}/api/v2/stats/prices/{urllib.parse.quote(",".join(codes),safe=",")}.json?{query}'
    if len(url)>4000:raise ValueError('Receita excede o limite de consulta.')
    request=urllib.request.Request(url,headers={'Accept-Encoding':'gzip','User-Agent':'AlbionMarketDesk/1.0'})
    with urllib.request.urlopen(request,timeout=15) as response:
        raw=response.read(4_000_001)
        if len(raw)>4_000_000:raise ValueError('Resposta excede limite')
        if response.headers.get('Content-Encoding')=='gzip':raw=gzip.decompress(raw)
    rows=json.loads(raw)
    return {(code,q):parse_prices(rows,code,q) for code in codes for q in range(1,6)}


def combine_prices(live,api):
    """Prefere a observação mais recente de cada lado; não presume volume da API."""
    result={loc:{side:dict(p,source=p.get('source','Fluxo')) for side,p in sides.items()} for loc,sides in live.items()}
    for loc,sides in api.items():
        for side,price in sides.items():
            current=result.setdefault(loc,{}).get(side)
            if current is None or price['seen']>current['seen']:
                result[loc][side]=dict(price)
    return result


class PriceAPI:
    def __init__(self,enabled=True,service=None):
        self.enabled=enabled
        self.service=service
        self.cache={}
        self.messages={}
        self.attempts={}
        self.busy=False
        self.last_request=0
        self.lock=threading.Lock()

    def request(self,key):
        if not self.enabled or key is None:return
        code,quality,_=key
        k=(code,quality)
        with self.lock:
            now=time.time()
            if self.busy or now-self.attempts.get(k,0)<60 or now-self.last_request<2:return
            self.busy=True;self.last_request=now;self.attempts[k]=now
            self.messages[k]='Consultando preços nas oito cidades/mercados…'
        def work():
            try:
                data=self.service.get_many([code]).get((code,quality),{}) if self.service else fetch_prices(code,quality)
                with self.lock:
                    self.cache[k]=data
                    self.messages[k]=(f'API consultada às {time.strftime("%H:%M:%S")} · Quantidades da API não disponíveis.'
                                      if data else 'API consultada: nenhum preço disponível para este item e qualidade.')
            except Exception as error:
                with self.lock:
                    self.messages[k]=f'Não foi possível consultar a API ({type(error).__name__}). Nova tentativa em até 60s.'
            finally:
                with self.lock:self.busy=False
        threading.Thread(target=work,daemon=True).start()

    def read(self,key):
        if key is None:return {},'Selecione um equipamento para consultar as outras cidades.'
        with self.lock:
            k=key[:2]
            return self.cache.get(k,{}),self.messages.get(k,'Aguardando consulta de preços.')

    def all_prices(self):
        with self.lock:return dict(self.cache)
