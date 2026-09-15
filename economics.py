"""Cálculos em prata. Taxas percentuais estimadas, sem arredondamentos do servidor."""
import math

SALES_TAX = {'Premium': 0.04, 'Sem Premium': 0.08}
SETUP_FEE = 0.025


def number(value, label, minimum=0, maximum=None, integer=False):
    try:
        value = float(str(value).replace(',', '.'))
    except ValueError:
        raise ValueError(f'Informe {label}.') from None
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'Valor inválido: {label}.')
    if integer and not value.is_integer():
        raise ValueError(f'{label} deve ser inteiro.')
    return value


def flipping(buy, sell, quantity=1, premium=False, buy_order=False, sell_order=False,
             transport=0, buy_relists=0, sell_relists=0):
    buy = number(buy,'preço de compra',.000001)
    sell = number(sell,'preço de venda',.000001)
    qty = number(quantity,'quantidade',1,integer=True)
    transport = number(transport,'transporte total')
    br = number(buy_relists,'recriações de compra',integer=True)
    sr = number(sell_relists,'recriações de venda',integer=True)
    tax = SALES_TAX['Premium' if premium else 'Sem Premium']
    purchase = buy*qty
    revenue = sell*qty
    buy_fee = purchase*SETUP_FEE*(1+br) if buy_order else 0
    sale_setup_rate = SETUP_FEE*(1+sr) if sell_order else 0
    if tax+sale_setup_rate >= 1:
        raise ValueError('Taxas de venda atingem 100%; reduza as recriações.')
    sell_fee = revenue*sale_setup_rate
    sale_tax = revenue*tax
    cost = purchase+buy_fee+transport
    net = revenue-sale_tax-sell_fee-cost
    return dict(purchase=purchase,buy_fee=buy_fee,sell_fee=sell_fee,sale_tax=sale_tax,
                cost=cost,revenue=revenue,net=net,unit_net=net/qty,roi=net/cost,
                break_even=cost/qty/(1-tax-sale_setup_rate))


def crafting(materials, crafts, output_per_craft, sell, return_rate, premium=False,
             buy_order=False,sell_order=False,station=0,transport=0,other=0,
             journal_credit=0,focus_points=0,focus_value=0):
    crafts=number(crafts,'número de crafts',1,integer=True)
    output=number(output_per_craft,'itens por craft',1,integer=True)*crafts
    sell=number(sell,'preço de venda',.000001)
    rrr=number(return_rate,'retorno de recursos',0,99.99)/100
    if not materials:
        raise ValueError('Adicione os materiais da receita.')
    gross=returned=0
    for m in materials:
        price=number(m['price'],'preço do material '+m['code'],.000001)
        amount=number(m['quantity'],'quantidade do material '+m['code'],.000001)*crafts
        gross+=price*amount
        if m['returns']:
            returned+=price*amount*rrr
    station=number(station,'custo total da estação')
    transport=number(transport,'transporte total')
    other=number(other,'outros custos totais')
    journal_credit=number(journal_credit,'crédito líquido dos diários')
    focus=number(focus_points,'Foco total',integer=True)
    focus_cost=focus*number(focus_value,'valor de cada ponto de Foco')
    buy_fee=gross*SETUP_FEE if buy_order else 0
    upfront=gross+buy_fee+station+transport+other
    effective=upfront-returned+focus_cost-journal_credit
    tax=SALES_TAX['Premium' if premium else 'Sem Premium']
    setup=SETUP_FEE if sell_order else 0
    revenue=output*sell
    sale_tax=revenue*tax
    sell_fee=revenue*setup
    cash=revenue-sale_tax-sell_fee-upfront+journal_credit
    profit=revenue-sale_tax-sell_fee-effective
    return dict(gross=gross,returned=returned,buy_fee=buy_fee,upfront=upfront,
                effective=effective,unit_cost=effective/output,output=output,
                sale_tax=sale_tax,sell_fee=sell_fee,revenue=revenue,net=profit,
                cash=cash,focus_cost=focus_cost,
                break_even=max(0,effective/output/(1-tax-setup)))
