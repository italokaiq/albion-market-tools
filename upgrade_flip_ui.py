"""Tela de flip de upgrade: comprar um item num encantamento mais baixo, subir
com rúnicas/almas/relíquias e comparar contra vender o item pronto no nível
alvo. Upgrade é determinístico — sem reroll de qualidade, sem chance
envolvida — e nunca presume preço ausente como zero.
"""
import time
import tkinter as tk
from tkinter import ttk
from market_view import age_text, sync_table
from trading import CITIES
from upgrade_flip import UpgradeCosts, best_flip


def money(v):
    return f'{v:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


class UpgradeFlipPlanner:
    def __init__(self, calculator):
        self.c = calculator
        self.app = calculator.app
        self.costs = UpgradeCosts()
        self.window = None
        self.base = None
        self.result = None
        self.paths = []

    def open(self):
        if self.window is not None:
            self.window.destroy()
        self.window = tk.Toplevel(self.app.root)
        self.window.title('Flip de upgrade de encantamento')
        self.window.geometry('980x680')
        self.window.minsize(800, 600)
        self.window.transient(self.app.root)
        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Comprar um item num encantamento mais baixo, subir com rúnicas/almas/relíquias '
                              '(sem chance envolvida — sempre o mesmo custo em recursos) e comparar contra o preço de venda no nível alvo.',
                  wraplength=940).pack(anchor='w', pady=(0, 8))
        if self.costs.error:
            ttk.Label(frame, text=self.costs.error, foreground='#D9827E').pack(anchor='w', pady=4)

        chooser = ttk.Frame(frame)
        chooser.pack(fill='x', pady=6)
        ttk.Button(chooser, text='Escolher equipamento pelo nome', command=self.choose_item).pack(side='left')
        self.item_label = ttk.Label(chooser, text='Selecione um equipamento.', foreground='#B3A78C', wraplength=650)
        self.item_label.pack(side='left', padx=12)

        controls = ttk.Frame(frame)
        controls.pack(fill='x', pady=6)
        ttk.Label(controls, text='Nível alvo').pack(side='left', padx=(0, 4))
        self.target_level = tk.StringVar(value='3')
        self.target_box = ttk.Combobox(controls, textvariable=self.target_level, values=['1', '2', '3'],
                                        state='readonly', width=4)
        self.target_box.pack(side='left', padx=(0, 12))
        ttk.Label(controls, text='Qualidade').pack(side='left', padx=(0, 4))
        self.quality = tk.StringVar(value='1')
        ttk.Combobox(controls, textvariable=self.quality, values=['1', '2', '3', '4', '5'],
                     state='readonly', width=4).pack(side='left', padx=(0, 12))
        ttk.Label(controls, text='Cidade').pack(side='left', padx=(0, 4))
        self.city_name = tk.StringVar(value='Caerleon')
        ttk.Combobox(controls, textvariable=self.city_name, values=[name for _, name in CITIES],
                     state='readonly', width=14).pack(side='left', padx=(0, 12))
        ttk.Label(controls, text='Comprar').pack(side='left', padx=(0, 4))
        self.buy_mode = tk.StringVar(value='Imediata')
        ttk.Combobox(controls, textvariable=self.buy_mode, values=['Imediata', 'Ordem de compra'],
                     state='readonly', width=15).pack(side='left', padx=(0, 12))
        ttk.Label(controls, text='Vender').pack(side='left', padx=(0, 4))
        self.sell_mode = tk.StringVar(value='Imediata')
        ttk.Combobox(controls, textvariable=self.sell_mode, values=['Imediata', 'Ordem de venda'],
                     state='readonly', width=15).pack(side='left')

        ttk.Button(frame, text='Consultar preços e comparar', command=self.fetch).pack(anchor='w', pady=8)
        self.status = ttk.Label(frame, wraplength=940, foreground='#B3A78C')
        self.status.pack(anchor='w', pady=4)
        self.recommendation = ttk.Label(frame, text='', font=('Segoe UI', 12, 'bold'), wraplength=940)
        self.recommendation.pack(anchor='w', pady=6)

        self.table = self.app.make_table(frame, None, [('Começar em', 100), ('Comprar por', 120),
            ('Custo de upgrade', 140), ('Custo total', 130), ('Idade', 90)])
        self.table.bind('<<TreeviewSelect>>', self.show_detail)
        detail_frame = ttk.Frame(frame)
        detail_frame.pack(fill='x', pady=6)
        self.detail = tk.Text(detail_frame, height=6, wrap='word', background='#221D17', foreground='#EDE6D6')
        self.detail.pack(side='left', fill='x', expand=True)
        detail_scroll = ttk.Scrollbar(detail_frame, command=self.detail.yview)
        detail_scroll.pack(side='right', fill='y')
        self.detail.configure(yscrollcommand=detail_scroll.set)
        self.set_detail('Escolha um equipamento e clique em Consultar preços.')

    def set_detail(self, text):
        self.detail.config(state='normal')
        self.detail.delete('1.0', 'end')
        self.detail.insert('1.0', text)
        self.detail.config(state='disabled')

    def choose_item(self):
        dialog = tk.Toplevel(self.window)
        dialog.title('Escolher equipamento')
        dialog.geometry('700x460')
        dialog.transient(self.window)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Só equipamentos com upgrade de encantamento definido (armas e itens de equipamento).').pack(anchor='w')
        query = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=query)
        entry.pack(fill='x', pady=8)
        entry.focus_set()
        listing = tk.Listbox(frame, background='#221D17', foreground='#EDE6D6', selectbackground='#6B4F23',
                              font=('Segoe UI', 11), exportselection=False)
        listing.pack(fill='both', expand=True)
        bases = sorted({v['base'] for v in self.costs.steps.values()})
        matches = []
        def search(*a):
            from market_view import folded, item_search_text
            words = folded(query.get()).split()
            matches[:] = [b for b in bases if not words or
                          all(w in item_search_text(b, self.app.catalog.item(b)) for w in words)]
            listing.delete(0, 'end')
            for code in matches[:100]:
                listing.insert('end', f'{self.app.catalog.item(code)} · {code}')
        def choose(event=None):
            selected = listing.curselection()
            if not selected:
                return
            self.select_item(matches[selected[0]])
            dialog.destroy()
        listing.bind('<Double-1>', choose)
        entry.bind('<Return>', lambda e: choose())
        query.trace_add('write', search)
        ttk.Button(frame, text='Selecionar', command=choose).pack(anchor='e', pady=8)
        search()

    def select_item(self, base):
        self.base = base
        self.result = None
        self.paths = []
        max_level = self.costs.max_level(base)
        levels = [str(n) for n in range(1, max_level + 1)] or ['—']
        self.target_box.configure(values=levels)
        if levels != ['—']:
            self.target_level.set(levels[-1])
        self.item_label.configure(text=f'{self.app.catalog.item(base)} · {base} · sobe até .{max_level}')
        sync_table(self.table, [])
        self.set_detail('Clique em Consultar preços para comparar os caminhos.')

    def fetch(self):
        if not self.base:
            self.status.config(text='Escolha um equipamento primeiro.')
            return
        try:
            target = int(self.target_level.get())
            quality = int(self.quality.get())
        except ValueError:
            self.status.config(text='Nível alvo e qualidade inválidos.')
            return
        if target < 1 or target > self.costs.max_level(self.base):
            self.status.config(text='Este equipamento não sobe até esse nível.')
            return
        codes = {self.base}
        for level in range(1, target + 1):
            codes.add(f'{self.base}@{level}')
            step = self.costs.steps.get(f'{self.base}@{level}')
            if step:
                codes.update(m['resource'] for m in step['materials'])
        self.status.config(text=f'Consultando preços para {len(codes)} itens…')
        self.window.update_idletasks()
        data = self.app.market_service.get_many(sorted(codes))
        city_id = {name: cid for cid, name in CITIES}[self.city_name.get()]
        max_age = int(self.app.filters['minutes'].get()) * 60
        now = time.time()
        prices = {}
        for code in codes:
            for q in range(1, 6):
                sides = data.get((code, q), {}).get(city_id, {})
                for side, value in sides.items():
                    if 0 <= now - value['seen'] <= max_age:
                        prices[(code, q, side)] = value
        buy_side = 'offer' if self.buy_mode.get() == 'Imediata' else 'request'
        sell_side = 'request' if self.sell_mode.get() == 'Imediata' else 'offer'
        sell_key = (f'{self.base}@{target}', quality, sell_side)
        sell = prices.get(sell_key)
        best, paths = best_flip(self.base, target, quality, prices, self.costs.steps,
            sell['price'] if sell else None, sell['seen'] if sell else None,
            premium=self.app.profile.get() == 'Premium',
            buy_immediate=self.buy_mode.get() == 'Imediata', sell_immediate=self.sell_mode.get() == 'Imediata',
            buy_order_fee=self.buy_mode.get() != 'Imediata')
        self.result = best
        self.paths = paths
        self.render(prices, buy_side, target, quality)

    def render(self, prices, buy_side, target, quality):
        now = time.time()
        rows = []
        for path in self.paths:
            rows.append((str(path['start_level']),
                (f".{path['start_level']}", money(path['buy_price']), money(path['upgrade_cost']),
                 money(path['total_cost']), age_text(path['seen'], now)),
                'fresh' if path['start_level'] == (self.result or {}).get('start_level') else 'warm'))
        sync_table(self.table, rows)
        if not self.paths:
            self.status.config(text='Nenhum caminho com todos os preços disponíveis (compra do item e dos recursos de upgrade necessários).')
            self.recommendation.config(text='')
            self.set_detail('Sem dados suficientes. Confira a cidade escolhida e a idade máxima configurada na tela principal.')
            return
        sell_key = (f'{self.base}@{target}', quality, 'request' if self.sell_mode.get() == 'Imediata' else 'offer')
        sell = prices.get(sell_key)
        if self.result:
            color = '#8EDFC3' if self.result['net'] > 0 else '#D9827E'
            self.recommendation.config(
                text=f"Mais barato: comprar em .{self.result['start_level']} por {money(self.result['buy_price'])} "
                     f"e subir até .{target} · custo total {money(self.result['total_cost'])} · venda estimada {money(self.result['sell_price'])} "
                     f"· lucro estimado {money(self.result['net'])}", foreground=color)
            self.status.config(text=f"{len(self.paths)} caminho(s) com preço completo dentro de "
                f"{self.app.filters['minutes'].get()} min. {self.app.profile.get()}.")
        elif sell is None:
            self.recommendation.config(text=f'Sem preço de venda para .{target} nesta cidade — só a comparação de custo de obtenção abaixo.', foreground='#B3A78C')
            self.status.config(text=f'{len(self.paths)} caminho(s) de obtenção calculados, sem preço de venda para comparar lucro.')
        self.table.selection_set(str(self.paths[0]['start_level']) if not self.result else str(self.result['start_level']))
        self.show_detail()

    def show_detail(self, event=None):
        selection = self.table.selection()
        if not selection or not self.paths:
            return
        path = next((p for p in self.paths if str(p['start_level']) == selection[0]), None)
        if not path:
            return
        lines = [f"Começar em .{path['start_level']}: comprar por {money(path['buy_price'])} ({path['buy_source']})"]
        for m in path['materials']:
            lines.append(f"  .{m['level']-1} → .{m['level']}: {m['count']:g} × {self.app.catalog.item(m['resource'])} "
                          f"a {money(m['unit_price'])} = {money(m['cost'])}")
        lines.append(f"Custo total: {money(path['total_cost'])}")
        lines.append('Upgrade é determinístico (sem chance envolvida). Sem custo em prata da Fundição de Artefatos em si — só o preço dos recursos.')
        self.set_detail('\n'.join(lines))
