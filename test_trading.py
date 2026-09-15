import unittest
from trading import snapshot, item_markets, api_city_name
from market_view import Catalog


class TradingTest(unittest.TestCase):
    def row(self,oid,loc,side,price,amount=3,seen=999,quality=1):
        return (str(oid),str(loc),'T4_MAIN_SWORD',quality,0,side,price,amount,seen)

    def test_real_bid_used_and_quantity_limited(self):
        rows=[self.row(1,7,'offer',100,8),self.row(2,1002,'request',150,2),
              self.row(3,1002,'offer',10000)]
        r=snapshot(rows,Catalog(),tax=.1,transport=5,now=1000)['routes'][0]
        self.assertEqual(r['origin'],'Thetford')
        self.assertEqual(r['destination'],'Lymhurst')
        self.assertEqual(r['net'],30)
        self.assertEqual(r['quantity'],2)

    def test_same_city_old_and_quality_mismatch_do_not_create_route(self):
        rows=[self.row(1,7,'offer',100),self.row(2,301,'request',300),
              self.row(3,1002,'request',400,seen=0),self.row(4,1002,'request',500,quality=2)]
        self.assertEqual(snapshot(rows,Catalog(),minutes=5,now=1000)['routes'],[])

    def test_portal_alias_does_not_double_quantity(self):
        rows=[self.row(1,7,'offer',100),self.row(1,301,'offer',100,seen=998),
              self.row(2,1002,'request',200,20)]
        r=snapshot(rows,Catalog(),now=1000)['routes'][0]
        self.assertEqual(r['quantity'],3)

    def test_black_market_is_separate_from_caerleon(self):
        rows=[self.row(1,3005,'offer',100),self.row(2,3003,'request',200)]
        r=snapshot(rows,Catalog(),now=1000)['routes'][0]
        self.assertEqual((r['origin'],r['destination']),('Caerleon','Mercado Negro'))

    def test_invalid_assumptions_rejected(self):
        with self.assertRaises(ValueError):
            snapshot([],Catalog(),tax=1.1)

    def test_api_only_side_creates_route_with_unknown_quantity(self):
        """API amplia a cobertura de rotas, mas nunca inventa volume: quantity fica None."""
        rows=[self.row(1,7,'offer',100)]
        api={('T4_MAIN_SWORD',1):{'1002':{'request':dict(price=200,seen=1000,amount=None,source='API')}}}
        r=snapshot(rows,Catalog(),tax=.08,now=1000,api=api)['routes'][0]
        self.assertEqual((r['origin'],r['destination']),('Thetford','Lymhurst'))
        self.assertIsNone(r['quantity'])
        self.assertAlmostEqual(r['net'],200*.92-100)

    def test_known_quantity_route_preferred_over_unknown_on_net_tie(self):
        """Mesmo lucro em duas cidades de destino: a rota com volume confirmado pelo
        fluxo vence o desempate contra a rota só com preço da API (volume desconhecido)."""
        rows=[self.row(1,7,'offer',100),self.row(2,1002,'request',200,amount=5)]
        api={('T4_MAIN_SWORD',1):{'3005':{'request':dict(price=200,seen=1000,amount=None,source='API')}}}
        r=snapshot(rows,Catalog(),tax=.08,now=1000,api=api)['routes'][0]
        self.assertEqual(r['destination'],'Lymhurst')
        self.assertEqual(r['quantity'],3)

    def test_item_markets_works_for_any_code_regardless_of_equipment(self):
        rows=[('1','7','T4_PLANKS',1,0,'offer',50,100,999),
              ('2','1002','T4_PLANKS',1,0,'request',70,40,999),
              ('3','1002','T4_PLANKS',2,0,'request',999,40,999),
              ('4','7','T4_PLANKS',1,0,'offer',999,100,0)]
        markets=item_markets(rows,'T4_PLANKS',1,0,now=1000,minutes=15)
        self.assertEqual(markets['7']['offer'],dict(price=50,amount=100,seen=999))
        self.assertEqual(markets['1002']['request'],dict(price=70,amount=40,seen=999))
        self.assertNotIn('offer',markets.get('1002',{}))

    def test_item_markets_empty_for_unknown_code(self):
        rows=[self.row(1,7,'offer',100)]
        self.assertEqual(item_markets(rows,'T4_PLANKS',1,0,now=1000,minutes=15),{})

    def test_api_city_name_translates_only_black_market(self):
        self.assertEqual(api_city_name('Mercado Negro'),'Black Market')
        self.assertEqual(api_city_name('Martlock'),'Martlock')
        self.assertEqual(api_city_name('Caerleon'),'Caerleon')
