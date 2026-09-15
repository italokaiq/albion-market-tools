"""Serviço compartilhado: consultas serializadas, cache limitado e datas preservadas."""
from collections import OrderedDict
from copy import deepcopy
import threading
import time
from market_api import fetch_many

class MarketService:
    def __init__(self,fetcher=None,clock=None,sleeper=None):
        self.fetcher=fetcher or fetch_many
        self.clock=clock or time.monotonic;self.sleeper=sleeper or time.sleep
        self.lock=threading.Lock();self.cache=OrderedDict();self.last_request=None

    def get_many(self,codes):
        codes=sorted(set(codes))
        # Called from background workers only; one request stream for the whole app.
        with self.lock:
            now=self.clock()
            missing=[c for c in codes if c not in self.cache or now-self.cache[c][0]>=60]
            for start in range(0,len(missing),40):
                if self.last_request is not None:
                    delay=2-(self.clock()-self.last_request)
                    if delay>0:self.sleeper(delay)
                batch=missing[start:start+40];self.last_request=self.clock()
                data=self.fetcher(batch)
                for code in batch:
                    self.cache[code]=(self.clock(),{q:data.get((code,q),{}) for q in range(1,6)})
                    self.cache.move_to_end(code)
            result={}
            for code in codes:
                if code in self.cache:
                    self.cache.move_to_end(code)
                    result.update({(code,q):deepcopy(v) for q,v in self.cache[code][1].items()})
            while len(self.cache)>512:self.cache.popitem(last=False)
            return result
