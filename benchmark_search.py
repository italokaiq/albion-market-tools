import time,json,statistics
from monitor import database
from market_view import Catalog,filtered_orders
from recipes import RecipeCatalog
c=Catalog();r=RecipeCatalog(c);con=database(':memory:');now=time.time()
codes=r.codes[:2000]
con.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)',[(str(i),'7',codes[i%len(codes)],1,i%5,'offer',1000,10,now-i%3600) for i in range(50000)])
results={}
for query in ['', 'cajado t4', 'T5.1', 'bolsa']:
 times=[]
 for _ in range(4):
  start=time.perf_counter();out=filtered_orders(con,c,now,60,query);times.append((time.perf_counter()-start)*1000)
 results[query]={'ms':round(statistics.median(times),2),'count':len(out)}
times=[]
for _ in range(4):
 start=time.perf_counter();out=r.search('cajado t4');times.append((time.perf_counter()-start)*1000)
results['recipe']={'ms':round(statistics.median(times),2),'count':len(out)}
print(json.dumps(results))
con.close()
