import unittest
from monitor import database, save_order


class OrdersTest(unittest.TestCase):
    def setUp(self):
        self.con = database(':memory:')
        self.order = dict(Id=1, LocationId=3003, ItemTypeId='T4_BAG',
                          QualityLevel=1, EnchantmentLevel=0,
                          AuctionType='offer', UnitPriceSilver=16432, Amount=5)

    def tearDown(self):
        self.con.close()

    def test_update_preserves_silver_units_and_deduplicates(self):
        save_order(self.con, self.order, 100)
        save_order(self.con, dict(self.order, Amount=3), 200)
        self.assertEqual(self.con.execute('SELECT price,amount,seen FROM orders').fetchall(),
                         [(16432, 3, 200)])

    def test_zero_quantity_removes_order(self):
        save_order(self.con, self.order)
        save_order(self.con, dict(self.order, Amount=0))
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM orders').fetchone()[0], 0)

    def test_invalid_price_is_rejected(self):
        with self.assertRaises(ValueError):
            save_order(self.con, dict(self.order, UnitPriceSilver=-1))


if __name__ == '__main__':
    unittest.main()
