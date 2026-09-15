import unittest
from trading import snapshot
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
