"""Flip de upgrade: comprar um item num encantamento mais baixo, subir com
rúnicas/almas/relíquias (determinístico — sem chance envolvida, ao contrário
de rerolar qualidade) e comparar contra comprar/vender o item pronto.

Sem custo em prata da Fundição de Artefatos em si — só o preço de mercado dos
recursos de upgrade, e as mesmas taxas de compra/venda já usadas no resto do
app. Nunca presume preço ausente como zero; um nível sem todos os preços
necessários simplesmente não entra na comparação.
"""
import json
from economics import SALES_TAX, SETUP_FEE
from paths import resource_path


class UpgradeCosts:
    def __init__(self, path=None):
        try:
            self.steps = json.loads((path or resource_path('upgrade_costs.json')).read_text(encoding='utf-8'))
            self.error = ''
        except (OSError, ValueError):
            self.steps = {}
            self.error = 'Catálogo de upgrade de encantamento indisponível.'

    def max_level(self, base):
        return max((v['level'] for v in self.steps.values() if v['base'] == base), default=0)


def evaluate_paths(base, target_level, quality, prices, steps, buy_side='offer', buy_fee_rate=0.0):
    """Um caminho por nível inicial (0..target_level) com todos os preços necessários.

    prices: {(code, quality_do_item_ou_1_para_recurso, side): dict(price, seen, amount, source)}
    steps: saída de upgrade_costs (UpgradeCosts.steps ou upgrade_costs.extract()).
    """
    paths = []
    for start in range(0, target_level + 1):
        start_code = base if start == 0 else f'{base}@{start}'
        buy = prices.get((start_code, quality, buy_side))
        if not buy:
            continue
        materials = []
        total = buy['price'] * (1 + buy_fee_rate)
        seen = buy['seen']
        complete = True
        for level in range(start + 1, target_level + 1):
            step = steps.get(f'{base}@{level}')
            if not step:
                complete = False
                break
            for material in step['materials']:
                price = prices.get((material['resource'], 1, buy_side))
                if not price:
                    complete = False
                    break
                cost = price['price'] * material['count'] * (1 + buy_fee_rate)
                materials.append(dict(level=level, resource=material['resource'], count=material['count'],
                    unit_price=price['price'], cost=cost))
                total += cost
                seen = min(seen, price['seen'])
            if not complete:
                break
        if not complete:
            continue
        paths.append(dict(start_level=start, buy_price=buy['price'], buy_source=buy['source'],
            materials=materials, upgrade_cost=total - buy['price'] * (1 + buy_fee_rate),
            total_cost=total, seen=seen))
    return paths


def best_flip(base, target_level, quality, prices, steps, sell_price, sell_seen, premium=False,
              buy_immediate=True, sell_immediate=True, buy_order_fee=False):
    """Melhor caminho de obtenção comparado contra vender o item no nível alvo.

    Retorna (melhor_dict_ou_None, todos_os_caminhos). melhor_dict inclui net/margin;
    None quando não há nenhum caminho com preços completos, ou preço de venda ausente.
    """
    buy_side = 'offer' if buy_immediate else 'request'
    buy_fee_rate = SETUP_FEE if buy_order_fee else 0.0
    paths = evaluate_paths(base, target_level, quality, prices, steps, buy_side, buy_fee_rate)
    if not paths or sell_price is None:
        return None, paths
    cheapest = min(paths, key=lambda p: p['total_cost'])
    tax = SALES_TAX['Premium' if premium else 'Sem Premium']
    setup = SETUP_FEE if not sell_immediate else 0.0
    revenue = sell_price * (1 - tax - setup)
    net = revenue - cheapest['total_cost']
    best = dict(cheapest, revenue=revenue, net=net,
                margin=(net / cheapest['total_cost']) if cheapest['total_cost'] else 0.0,
                sell_price=sell_price, sell_seen=sell_seen)
    return best, paths
