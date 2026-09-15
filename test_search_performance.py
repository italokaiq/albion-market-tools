"""Regressão da busca otimizada contra a regra original, em banco isolado."""
import re
import unittest
from itertools import product
from market_view import Catalog, filtered_orders, folded
from monitor import database

class SearchEquivalenceTest(unittest.TestCase):
    def test_all_filters_match_reference_without_truncation(self):
        con=database(':memory:');catalog=Catalog();now=10000
        codes=['T4_MAIN_SWORD','T4_MAIN_SWORD@1','T5_BAG','T8_2H_FIRESTAFF@2','UNKNOWN']
        rows=[(str(i),loc,code,q,e,'offer',100,2,now-age)
              for i,(loc,code,q,e,age) in enumerate(product(['7','3005','1002'],codes,[1,2],[0,1,2],[10,600,4000]))]
        con.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)',rows)
        ordered=con.execute('SELECT * FROM orders WHERE seen>=? AND amount>0 ORDER BY seen DESC',(now-900,)).fetchall()
        def reference(query,market,tier,enchant,quality):
            result=[]
            for row in ordered:
                _,loc,code,q,e,*_=row
                t=code.split('_')[0];enc=code.split('@',1)[1] if '@' in code else '0'
                text=folded(f'{catalog.item(code)} {code} {t}.{enc}')
                if not all(w in text for w in folded(query).split()):continue
                if folded(market) not in folded(loc+' '+catalog.market(loc)):continue
                match=re.match(r'T(\d+)_',code)
                if tier and (not match or match[1]!=tier):continue
                if enchant and str(e)!=enchant:continue
                if quality and str(q)!=quality:continue
                result.append(row)
            return result
        try:
            for filters in product(['','espada','T4.1','ANCIÃO','unknown','sem resultado'],['','Caerleon','7'],['','4'],['','0','1'],['','2']):
                with self.subTest(filters=filters):
                    self.assertEqual(filtered_orders(con,catalog,now,15,*filters),reference(*filters))
        finally:con.close()
