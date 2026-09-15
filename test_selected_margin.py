import unittest
from trading import selected_item_margin

class SelectedMarginTest(unittest.TestCase):
    def test_tax_transport_and_unknown_volume(self):
        markets={'7':{'offer':dict(price=100,seen=1000,amount=10)},'1002':{'request':dict(price=200,seen=1000,amount=None)}}
        r=selected_item_margin(markets,.08,10,60,1000)
        self.assertEqual(r['net'],74);self.assertIsNone(r['quantity'])
        self.assertAlmostEqual(r['roi'],74/110)
        self.assertIsNone(selected_item_margin(markets,.08,10,60,1061))
    def test_same_city_not_route_and_loss_is_visible(self):
        markets={'7':{'offer':dict(price=100,seen=1000,amount=10),'request':dict(price=200,seen=1000,amount=10)}}
        self.assertIsNone(selected_item_margin(markets,.08,0,60,1000))
        markets['1002']={'request':dict(price=50,seen=1000,amount=3)}
        r=selected_item_margin(markets,.08,0,60,1000)
        self.assertEqual(r['net'],-54);self.assertEqual(r['quantity'],3)
