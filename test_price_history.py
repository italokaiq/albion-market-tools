import json
import time
import unittest
from price_history import parse_history, PriceHistory, PERIODS


class ParseHistoryTest(unittest.TestCase):
    def test_filters_by_location_and_sorts(self):
        raw = json.dumps([
            {'location': 'Caerleon', 'data': [{'avg_price': 400, 'item_count': 10, 'timestamp': '2026-09-14T00:00:00'}]},
            {'location': 'Martlock', 'data': [
                {'avg_price': 300, 'item_count': 5, 'timestamp': '2026-09-14T12:00:00'},
                {'avg_price': 290, 'item_count': 7, 'timestamp': '2026-09-14T00:00:00'}]},
        ]).encode('utf-8')
        points = parse_history(raw, 'Martlock')
        self.assertEqual([p['price'] for p in points], [290, 300])
        self.assertEqual(points[0]['amount'], 7)

    def test_missing_location_returns_empty(self):
        raw = json.dumps([{'location': 'Caerleon', 'data': [{'avg_price': 1, 'item_count': 1, 'timestamp': '2026-09-14T00:00:00'}]}]).encode('utf-8')
        self.assertEqual(parse_history(raw, 'Martlock'), [])

    def test_empty_response_returns_empty(self):
        self.assertEqual(parse_history(b'[]', 'Martlock'), [])

    def test_skips_rows_with_zero_or_negative_price(self):
        raw = json.dumps([{'location': 'Martlock', 'data': [
            {'avg_price': 0, 'item_count': 1, 'timestamp': '2026-09-14T00:00:00'},
            {'avg_price': -5, 'item_count': 1, 'timestamp': '2026-09-14T01:00:00'},
            {'avg_price': 100, 'item_count': 1, 'timestamp': '2026-09-14T02:00:00'}]}]).encode('utf-8')
        points = parse_history(raw, 'Martlock')
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]['price'], 100)

    def test_skips_rows_with_missing_or_bad_fields(self):
        raw = json.dumps([{'location': 'Martlock', 'data': [
            {'avg_price': 'oops', 'item_count': 1, 'timestamp': '2026-09-14T00:00:00'},
            {'item_count': 1, 'timestamp': '2026-09-14T01:00:00'},
            {'avg_price': 50, 'item_count': 2, 'timestamp': 'not-a-date'},
            {'avg_price': 50, 'item_count': 2, 'timestamp': '2026-09-14T03:00:00'}]}]).encode('utf-8')
        points = parse_history(raw, 'Martlock')
        self.assertEqual(len(points), 1)

    def test_rejects_non_list_payload(self):
        with self.assertRaises(ValueError):
            parse_history(b'{"not":"a list"}', 'Martlock')


class FetchHistoryTest(unittest.TestCase):
    def test_invalid_period_rejected(self):
        from price_history import fetch_history
        with self.assertRaises(ValueError):
            fetch_history('T4_BAG', 1, 'Martlock', 'nope')


class PriceHistoryTest(unittest.TestCase):
    def wait_for(self, condition, timeout=2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return True
            time.sleep(0.02)
        return False

    def test_disabled_never_calls_fetcher(self):
        calls = []
        ph = PriceHistory(enabled=False, fetcher=lambda *a: calls.append(a) or [])
        ph.request('T4_BAG', 1, 'Martlock', '7d')
        time.sleep(0.1)
        self.assertEqual(calls, [])

    def test_read_before_request_gives_default_message(self):
        ph = PriceHistory(fetcher=lambda *a: [])
        points, message = ph.read('T4_BAG', 1, 'Martlock', '7d')
        self.assertEqual(points, [])
        self.assertIn('Aguardando', message)

    def test_request_populates_cache_and_message(self):
        expected = [dict(seen=1.0, price=100, amount=5)]
        ph = PriceHistory(fetcher=lambda code, q, city, period: expected)
        ph.request('T4_BAG', 1, 'Martlock', '7d')
        self.wait_for(lambda: ph.read('T4_BAG', 1, 'Martlock', '7d')[0] == expected)
        points, message = ph.read('T4_BAG', 1, 'Martlock', '7d')
        self.assertEqual(points, expected)
        self.assertIn('consultado', message)

    def test_request_throttles_within_60_seconds(self):
        calls = []
        ph = PriceHistory(fetcher=lambda code, q, city, period: calls.append(1) or [])
        ph.request('T4_BAG', 1, 'Martlock', '7d')
        self.wait_for(lambda: len(calls) == 1)
        ph.request('T4_BAG', 1, 'Martlock', '7d')
        time.sleep(0.1)
        self.assertEqual(len(calls), 1)

    def test_different_period_is_a_separate_key_not_throttled(self):
        calls = []
        ph = PriceHistory(fetcher=lambda code, q, city, period: calls.append(period) or [])
        ph.request('T4_BAG', 1, 'Martlock', '7d')
        ph.request('T4_BAG', 1, 'Martlock', '30d')
        self.wait_for(lambda: len(calls) == 2)
        self.assertEqual(set(calls), {'7d', '30d'})

    def test_fetch_error_sets_message_without_raising(self):
        def failing(*a):
            raise OSError('sem rede')
        ph = PriceHistory(fetcher=failing)
        ph.request('T4_BAG', 1, 'Martlock', '7d')
        self.wait_for(lambda: 'consultar' in ph.read('T4_BAG', 1, 'Martlock', '7d')[1])
        points, message = ph.read('T4_BAG', 1, 'Martlock', '7d')
        self.assertEqual(points, [])
        self.assertIn('Não foi possível consultar', message)

    def test_read_without_code_or_city_does_not_crash(self):
        ph = PriceHistory(fetcher=lambda *a: [])
        self.assertEqual(ph.read(None, 1, 'Martlock', '7d'), ([], 'Selecione um item e uma cidade para ver o histórico.'))
        self.assertEqual(ph.read('T4_BAG', 1, '', '7d'), ([], 'Selecione um item e uma cidade para ver o histórico.'))

    def test_periods_cover_the_four_documented_windows(self):
        self.assertEqual(set(PERIODS), {'24h', '3d', '7d', '30d'})
