"""Amplia a cobertura de rotas consultando a API em lote para os itens que o
fluxo local já observou, além do que o fluxo sozinho capta.

O fluxo AODP ao vivo é uma fatia fina e enviesada (mais gente anuncia venda
do que publica ordem de compra); a API agrega dados de todos os
colaboradores. Sem isso, praticamente nenhuma rota de duas cidades aparece
mesmo com milhares de ordens no fluxo — medido: de ~490 variantes só ~1%
tinham oferta e pedido em cidades diferentes via fluxo puro, contra ~80%
para os mesmos itens via API.
"""
import threading
import time


class RouteEnrichment:
    def __init__(self, service, enabled=True):
        self.service = service
        self.enabled = enabled
        self.cache = {}
        self.busy = False
        self.last_request = 0
        self.message = 'Aguardando primeira consulta em lote.'
        self.lock = threading.Lock()

    def request(self, codes):
        if not self.enabled or not codes:
            return
        with self.lock:
            if self.busy or time.time() - self.last_request < 60:
                return
            self.busy = True
            self.last_request = time.time()
            self.message = f'Consultando a API para ampliar a cobertura de {len(codes)} itens observados…'
        def work():
            try:
                result = self.service.get_many(codes)
                with self.lock:
                    for key, data in result.items():
                        self.cache[key] = data
                    self.message = f'Cobertura ampliada às {time.strftime("%H:%M:%S")} para {len(codes)} itens.'
            except Exception as error:
                with self.lock:
                    self.message = f'Falha ao ampliar cobertura via API ({type(error).__name__}). Nova tentativa em até 60s.'
            finally:
                with self.lock:
                    self.busy = False
        threading.Thread(target=work, daemon=True).start()

    def all_prices(self):
        with self.lock:
            return dict(self.cache)
