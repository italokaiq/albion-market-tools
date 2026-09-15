import unittest
from concurrent.futures import ThreadPoolExecutor
from market_service import MarketService

class MarketServiceTest(unittest.TestCase):
    def test_concurrent_consumers_share_response_without_mutating_source_dates(self):
        calls=[]
        def fetch(codes):
            calls.append(codes)
            return {(c,1):{'7':{'offer':dict(price=123,seen=100,amount=None,source='API')}} for c in codes}
        service=MarketService(fetcher=fetch)
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda _:service.get_many(['T4_BAG']),range(3)))
        self.assertEqual(len(calls),1)
        results[0][('T4_BAG',1)]['7']['offer']['price']=999
        self.assertEqual(results[1][('T4_BAG',1)]['7']['offer']['price'],123)
        self.assertEqual(results[2][('T4_BAG',1)]['7']['offer']['seen'],100)
    def test_expiration_batching_and_spacing(self):
        clock=[0.0];calls=[];delays=[]
        def sleep(seconds):delays.append(seconds);clock[0]+=seconds
        def fetch(codes):calls.append(codes);return {}
        service=MarketService(fetcher=fetch,clock=lambda:clock[0],sleeper=sleep)
        service.get_many([str(i) for i in range(41)])
        self.assertEqual([len(c) for c in calls],[40,1])
        self.assertEqual(delays,[2])
        service.get_many(['0']);self.assertEqual(len(calls),2)
        clock[0]=100;service.get_many(['0']);self.assertEqual(len(calls),3)
    def test_failure_does_not_create_fake_price(self):
        def fetch(codes):raise OSError('offline')
        service=MarketService(fetcher=fetch)
        with self.assertRaises(OSError):service.get_many(['T4_BAG'])
        self.assertEqual(len(service.cache),0)
