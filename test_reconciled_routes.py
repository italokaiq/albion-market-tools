import unittest
from market_view import Catalog
from trading import snapshot,selected_item_margin

class ReconciledRoutesTest(unittest.TestCase):
    def test_newer_api_invalidates_old_profitable_route_without_inventing_volume(self):
        rows=[('1','7','T6_2H_HAMMER',1,0,'offer',79993,1,1000),
              ('2','3003','T6_2H_HAMMER',1,0,'request',140531,1,1000)]
        api={('T6_2H_HAMMER',1):{'3003':{'request':dict(price=15790,seen=1100,amount=None,source='API')}}}
        before=snapshot(rows,Catalog(),60,.08,0,True,1200)
        self.assertGreater(before['routes'][0]['net'],0)
        after=snapshot(rows,Catalog(),60,.08,0,True,1200,api=api)
        self.assertEqual(after['routes'],[])
        markets=after['variants'][0]['markets']
        margin=selected_item_margin(markets,.08,0,3600,1200)
        self.assertAlmostEqual(margin['net'],-65466.2)
        self.assertEqual(markets['3003']['request']['source'],'API')
    def test_older_api_does_not_replace_newer_flow(self):
        rows=[('1','7','T4_BAG',1,0,'offer',100,2,1000),('2','1002','T4_BAG',1,0,'request',200,3,1000)]
        api={('T4_BAG',1):{'1002':{'request':dict(price=1,seen=900,amount=None,source='API')}}}
        result=snapshot(rows,Catalog(),15,.08,0,True,1100,api=api)
        self.assertEqual(result['routes'][0]['quantity'],2)
        self.assertEqual(result['routes'][0]['net'],84)
