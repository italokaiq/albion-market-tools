import unittest
from market_api import parse_prices,combine_prices,PriceAPI


class MarketAPITest(unittest.TestCase):
    def test_open_offer_needs_no_completed_sale(self):
        row=dict(item_id='T4_BAG',quality=1,city='Thetford',sell_price_min=123,
                 sell_price_min_date='2026-09-14T10:00:00',buy_price_max=0,buy_price_max_date=None)
        data=parse_prices([row],'T4_BAG',1,now=1789380010)
        self.assertEqual(data['7']['offer']['price'],123)
        self.assertNotIn('request',data['7'])
        row['sell_price_min_date']=None
        self.assertEqual(parse_prices([row],'T4_BAG',1,now=1789380010),{})
    def test_preserves_source_date_and_unknown_quantity(self):
        rows=[dict(item_id='T4_BAG',quality=1,city='Black Market',sell_price_min=0,
                   sell_price_min_date='0001-01-01T00:00:00',buy_price_max=100,
                   buy_price_max_date='2026-09-14T10:00:00')]
        values=parse_prices(rows,'T4_BAG',1,now=1800000000)
        self.assertNotIn('offer',values['3003'])
        price=values['3003']['request']
        self.assertEqual(price['seen'],1789380000)
        self.assertIsNone(price['amount'])
        self.assertEqual(parse_prices(rows,'T4_BAG',2,now=1800000000),{})

    def test_merge_chooses_newest_per_side_without_mutation(self):
        live={'7':{'offer':dict(price=100,seen=200,amount=3)}}
        api={'7':{'offer':dict(price=50,seen=100,amount=None,source='API'),
                  'request':dict(price=80,seen=150,amount=None,source='API')}}
        merged=combine_prices(live,api)
        self.assertEqual(merged['7']['offer']['price'],100)
        self.assertIsNone(merged['7']['request']['amount'])
        self.assertNotIn('source',live['7']['offer'])
        api['7']['offer']['seen']=300
        self.assertEqual(combine_prices(live,api)['7']['offer']['price'],50)

    def test_bad_date_and_future_date_rejected(self):
        row=dict(item_id='T4_BAG',quality=1,city='Thetford',sell_price_min=10,
                 sell_price_min_date='invalid',buy_price_max=30,buy_price_max_date='2099-01-01T00:00:00Z')
        self.assertEqual(parse_prices([row],'T4_BAG',1,now=1800000000),{})

    def test_cache_separates_item_and_quality(self):
        api=PriceAPI(enabled=False)
        api.cache[('T4_BAG',1)]={'7':{}}
        self.assertEqual(api.read(('T4_BAG',2,0))[0],{})
        api.request(('T4_BAG',1,0))
        self.assertFalse(api.busy)
