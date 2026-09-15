import time
import unittest
from route_enrichment import RouteEnrichment


class FakeService:
    def __init__(self, data=None, error=None):
        self.data = data or {}
        self.error = error
        self.calls = []

    def get_many(self, codes):
        self.calls.append(list(codes))
        if self.error:
            raise self.error
        return self.data


class RouteEnrichmentTest(unittest.TestCase):
    def wait_for(self, condition, timeout=2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return True
            time.sleep(0.02)
        return False

    def test_disabled_never_calls_service(self):
        service = FakeService()
        re_ = RouteEnrichment(service, enabled=False)
        re_.request(['T4_BAG'])
        time.sleep(0.1)
        self.assertEqual(service.calls, [])

    def test_empty_codes_never_calls_service(self):
        service = FakeService()
        re_ = RouteEnrichment(service)
        re_.request([])
        time.sleep(0.1)
        self.assertEqual(service.calls, [])

    def test_request_populates_cache(self):
        expected = {('T4_BAG', 1): {'7': {'offer': dict(price=100, amount=None, seen=1.0, source='API')}}}
        service = FakeService(data=expected)
        re_ = RouteEnrichment(service)
        re_.request(['T4_BAG'])
        self.wait_for(lambda: re_.all_prices() == expected)
        self.assertEqual(re_.all_prices(), expected)
        self.assertIn('Cobertura ampliada', re_.message)

    def test_throttled_to_once_per_60_seconds(self):
        service = FakeService(data={})
        re_ = RouteEnrichment(service)
        re_.request(['A'])
        self.wait_for(lambda: len(service.calls) == 1)
        re_.request(['A', 'B'])
        time.sleep(0.1)
        self.assertEqual(len(service.calls), 1)

    def test_error_sets_message_without_raising(self):
        service = FakeService(error=OSError('sem rede'))
        re_ = RouteEnrichment(service)
        re_.request(['T4_BAG'])
        self.wait_for(lambda: 'Falha' in re_.message)
        self.assertIn('OSError', re_.message)
        self.assertEqual(re_.all_prices(), {})

    def test_cache_accumulates_across_requests(self):
        service = FakeService(data={('A', 1): {'7': {}}})
        re_ = RouteEnrichment(service)
        re_.request(['A'])
        self.wait_for(lambda: re_.all_prices())
        service.data = {('B', 1): {'7': {}}}
        re_.last_request = 0  # simula passagem dos 60s
        re_.request(['B'])
        self.wait_for(lambda: ('B', 1) in re_.all_prices())
        self.assertIn(('A', 1), re_.all_prices())
        self.assertIn(('B', 1), re_.all_prices())

    def test_never_touches_real_network(self):
        """Regressão: com o serviço injetado, a rede real nunca deve ser chamada."""
        from unittest.mock import patch
        with patch('urllib.request.urlopen', side_effect=AssertionError('rede real chamada')):
            service = FakeService(data={})
            re_ = RouteEnrichment(service)
            re_.request(['T4_BAG'])
            self.wait_for(lambda: re_.message != 'Aguardando primeira consulta em lote.')
