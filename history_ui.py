"""Tela de histórico: operações registradas pelo usuário, previsto x realizado.

Nada é inferido: uma operação só entra aqui quando o usuário clica em
"Registrar operação" nas calculadoras, com os valores exibidos naquele
momento. "Realizado" só existe depois que o próprio usuário confirma o que
comprou/vendeu de fato — o app nunca presume execução.
"""
import time
import tkinter as tk
from tkinter import ttk
from economics import flipping
from history import History
from market_view import sync_table


def money(v):
    return f'{v:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def flip_entry_from_row(buy, sell, quantity, transport, buy_mode, sell_mode, profile):
    """Uma operação já concluída: previsto e realizado ficam iguais, calculados uma vez."""
    result = flipping(buy=buy, sell=sell, quantity=quantity, transport=transport,
        buy_order=buy_mode != 'Imediata', sell_order=sell_mode != 'Imediata', premium=profile == 'Premium')
    predicted = dict(buy=buy, sell=sell, quantity=quantity, transport=transport,
        buy_mode=buy_mode, sell_mode=sell_mode, buy_relists='0', sell_relists='0',
        profile=profile, net=result['net'], unit_net=result['unit_net'])
    return predicted, dict(predicted)


def craft_entry_from_row(crafts, output_per_craft, spent, received, profile):
    """Modelo simples (recebido - gasto), igual ao usado em 'Confirmar execução' do craft."""
    crafts_n = float(str(crafts).replace(',', '.'))
    output_n = float(str(output_per_craft).replace(',', '.'))
    spent_n = float(str(spent).replace(',', '.'))
    received_n = float(str(received).replace(',', '.'))
    net = received_n - spent_n
    predicted = dict(crafts=str(crafts), output=crafts_n * output_n, net=net, cash=net,
        upfront=spent_n, revenue=received_n, profile=profile)
    return predicted, dict(spent=spent_n, received=received_n, net=net)


class HistoryView:
    def __init__(self, app):
        self.app = app
        self.history = History()
        self.tab = ttk.Frame(app.notebook, padding=12)
        app.notebook.add(self.tab, text='Histórico')
        ttk.Label(self.tab, text='Operações registradas por você nas calculadoras. Nada aqui é inferido do fluxo ou da API.',
                  foreground='#A3B5CB', wraplength=1150).pack(anchor='w', pady=(0, 10))
        cards = ttk.Frame(self.tab)
        cards.pack(fill='x', pady=(0, 10))
        self.metrics = {}
        for key, label in [('total', 'Operações registradas'), ('confirmed', 'Confirmadas'),
                            ('predicted', 'Lucro previsto total'), ('realized', 'Lucro realizado total')]:
            card = ttk.Frame(cards, padding=8)
            card.pack(side='left', fill='x', expand=True)
            ttk.Label(card, text=label, foreground='#A3B5CB').pack(anchor='w')
            number = ttk.Label(card, text='—', font=('Segoe UI', 16, 'bold'), foreground='#8EDFC3')
            number.pack(anchor='w')
            self.metrics[key] = number
        self.table = app.make_table(self.tab, None, [('Data', 135), ('Tipo', 75), ('Item', 250),
            ('Detalhe', 230), ('Lucro previsto', 120), ('Lucro realizado', 120), ('Status', 150)])
        buttons = ttk.Frame(self.tab)
        buttons.pack(fill='x', pady=8)
        ttk.Button(buttons, text='Confirmar execução', command=self.open_confirm).pack(side='left')
        ttk.Button(buttons, text='Remover', command=self.remove_selected).pack(side='left', padx=8)
        ttk.Button(buttons, text='Registrar várias operações', command=self.open_bulk_entry).pack(side='left', padx=8)
        ttk.Button(buttons, text='Atualizar', command=self.refresh).pack(side='left')
        self.status = ttk.Label(self.tab, wraplength=1150, foreground='#A3B5CB')
        self.status.pack(anchor='w', pady=4)
        self.entries_by_id = {}
        self.refresh()

    def refresh(self):
        try:
            entries = self.history.read()['entries']
        except (OSError, ValueError) as error:
            self.status.config(text='Não foi possível ler o histórico: ' + str(error))
            return
        self.entries_by_id = {e['id']: e for e in entries}
        rows = []
        predicted_total = realized_total = 0
        confirmed = 0
        for e in entries:
            predicted_net = e['predicted']['net']
            predicted_total += predicted_net
            if e['realized']:
                confirmed += 1
                realized_total += e['realized']['net']
            when = time.strftime('%d/%m %H:%M', time.localtime(_parse(e['recorded_at'])))
            if e['kind'] == 'flipping':
                p = e['predicted']
                detail = f"{p['quantity']} un. · {p['buy_mode']}/{p['sell_mode']}"
            else:
                p = e['predicted']
                detail = f"{p['crafts']} crafts · {int(p['output'])} itens"
            realized_text = money(e['realized']['net']) if e['realized'] else '—'
            status = 'Confirmada' if e['realized'] else 'Prevista, sem confirmação'
            rows.append((e['id'], (when, 'Flipping' if e['kind'] == 'flipping' else 'Craft',
                e.get('label', '—'), detail, money(predicted_net), realized_text, status),
                'fresh' if e['realized'] else 'warm'))
        sync_table(self.table, rows)
        self.metrics['total'].config(text=str(len(entries)))
        self.metrics['confirmed'].config(text=f'{confirmed}/{len(entries)}')
        self.metrics['predicted'].config(text=money(predicted_total))
        self.metrics['realized'].config(text=money(realized_total) if confirmed else '—')
        self.status.config(text='' if entries else
            'Nenhuma operação registrada ainda. Use "Registrar operação" nas calculadoras de flipping e craft.')

    def remove_selected(self):
        selection = self.table.selection()
        if not selection:
            self.status.config(text='Selecione uma operação para remover.');return
        try:
            self.history.delete(selection[0])
        except (OSError, ValueError, KeyError) as error:
            self.status.config(text='Não foi possível remover: ' + str(error));return
        self.refresh()

    def open_confirm(self):
        selection = self.table.selection()
        if not selection:
            self.status.config(text='Selecione uma operação para confirmar a execução.');return
        entry = self.entries_by_id.get(selection[0])
        if entry is None:
            return
        if entry['kind'] == 'flipping':
            self._confirm_flip(entry)
        else:
            self._confirm_craft(entry)

    def _confirm_flip(self, entry):
        p = entry['predicted']
        dialog = tk.Toplevel(self.app.root)
        dialog.title('Confirmar execução da operação')
        dialog.geometry('420x360')
        dialog.transient(self.app.root)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Informe o que você realmente comprou e vendeu. O lucro realizado é recalculado com a mesma fórmula da calculadora.',
                  wraplength=380).pack(anchor='w', pady=(0, 10))
        fields = {}
        specs = [('buy', 'Compra/un.', p['buy']), ('sell', 'Venda/un.', p['sell']),
                 ('quantity', 'Quantidade', p['quantity']), ('transport', 'Transporte total', p['transport']),
                 ('buy_relists', 'Recriações compra', p['buy_relists']), ('sell_relists', 'Recriações venda', p['sell_relists'])]
        for key, label, default in specs:
            row = ttk.Frame(frame);row.pack(fill='x', pady=3)
            ttk.Label(row, text=label, width=18).pack(side='left')
            var = tk.StringVar(value=str(default));fields[key] = var
            ttk.Entry(row, textvariable=var).pack(side='left', fill='x', expand=True)
        modes = {}
        for key, label, default in [('buy_mode', 'Comprar', p['buy_mode']), ('sell_mode', 'Vender', p['sell_mode'])]:
            row = ttk.Frame(frame);row.pack(fill='x', pady=3)
            ttk.Label(row, text=label, width=18).pack(side='left')
            var = tk.StringVar(value=default);modes[key] = var
            ttk.Combobox(row, textvariable=var, values=['Imediata', 'Ordem de compra' if key == 'buy_mode' else 'Ordem de venda'],
                         state='readonly').pack(side='left', fill='x', expand=True)
        message = ttk.Label(frame, wraplength=380, foreground='#F0AAAA');message.pack(anchor='w', pady=6)
        def confirm():
            try:
                result = flipping(buy=fields['buy'].get(), sell=fields['sell'].get(), quantity=fields['quantity'].get(),
                    buy_order=modes['buy_mode'].get() != 'Imediata', sell_order=modes['sell_mode'].get() != 'Imediata',
                    transport=fields['transport'].get(), buy_relists=fields['buy_relists'].get(),
                    sell_relists=fields['sell_relists'].get(), premium=p['profile'] == 'Premium')
            except ValueError as error:
                message.config(text=str(error));return
            realized = dict(buy=fields['buy'].get(), sell=fields['sell'].get(), quantity=fields['quantity'].get(),
                transport=fields['transport'].get(), buy_mode=modes['buy_mode'].get(), sell_mode=modes['sell_mode'].get(),
                buy_relists=fields['buy_relists'].get(), sell_relists=fields['sell_relists'].get(),
                net=result['net'], unit_net=result['unit_net'])
            try:
                self.history.confirm(entry['id'], realized)
            except (OSError, ValueError, KeyError) as error:
                message.config(text=str(error));return
            dialog.destroy();self.refresh()
        ttk.Button(frame, text='Confirmar', command=confirm).pack(anchor='e', pady=8)

    def _confirm_craft(self, entry):
        p = entry['predicted']
        dialog = tk.Toplevel(self.app.root)
        dialog.title('Confirmar execução do craft')
        dialog.geometry('420x260')
        dialog.transient(self.app.root)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Informe quanto você realmente gastou (materiais, estação e demais custos) e recebeu com a venda. '
                              'O lucro realizado é a diferença simples entre esses dois valores — não é o mesmo cálculo econômico da previsão, '
                              'que também considera recursos devolvidos.', wraplength=380).pack(anchor='w', pady=(0, 10))
        spent = tk.StringVar(value=str(p['upfront']));received = tk.StringVar(value=str(p['revenue']))
        for label, var in [('Prata total gasta', spent), ('Prata total recebida na venda', received)]:
            row = ttk.Frame(frame);row.pack(fill='x', pady=4)
            ttk.Label(row, text=label, width=22).pack(side='left')
            ttk.Entry(row, textvariable=var).pack(side='left', fill='x', expand=True)
        message = ttk.Label(frame, wraplength=380, foreground='#F0AAAA');message.pack(anchor='w', pady=6)
        def confirm():
            try:
                s = float(spent.get().replace(',', '.'));r = float(received.get().replace(',', '.'))
            except ValueError:
                message.config(text='Informe valores numéricos válidos.');return
            try:
                self.history.confirm(entry['id'], dict(spent=s, received=r, net=r - s))
            except (OSError, ValueError, KeyError) as error:
                message.config(text=str(error));return
            dialog.destroy();self.refresh()
        ttk.Button(frame, text='Confirmar', command=confirm).pack(anchor='e', pady=8)

    def open_bulk_entry(self):
        """Registra várias operações já concluídas de uma vez: previsto e realizado
        ficam iguais, calculados a partir dos valores informados — não há distinção
        de 'antes/depois' para algo que já aconteceu."""
        dialog = tk.Toplevel(self.app.root)
        dialog.title('Registrar várias operações')
        dialog.geometry('1000x600')
        dialog.transient(self.app.root)
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'Para operações já concluídas: previsto e realizado ficam iguais, com os valores '
                              f'que você informar aqui. Perfil atual: {self.app.profile.get()}. Linhas em branco são ignoradas.',
                  wraplength=960).pack(anchor='w', pady=(0, 8))
        tabs = ttk.Notebook(frame)
        tabs.pack(fill='both', expand=True)
        flip_rows, flip_rows_frame = self._bulk_rows_area(tabs, 'Flipping',
            [('item', 'Item', 18, ''), ('buy', 'Compra/un.', 10, ''), ('sell', 'Venda/un.', 10, ''),
             ('quantity', 'Qtd.', 7, '1'), ('transport', 'Transporte total', 12, '0')],
            [('buy_mode', 'Comprar', ['Imediata', 'Ordem de compra'], 'Imediata'),
             ('sell_mode', 'Vender', ['Imediata', 'Ordem de venda'], 'Imediata')])
        craft_rows, craft_rows_frame = self._bulk_rows_area(tabs, 'Craft',
            [('item', 'Item', 18, ''), ('crafts', 'Crafts', 7, '1'), ('output', 'Itens/craft', 10, '1'),
             ('spent', 'Prata gasta', 12, ''), ('received', 'Prata recebida', 12, '')], [])
        self.bulk_flip_rows,self.bulk_craft_rows = flip_rows,craft_rows  # acessível para testes de integração
        for _ in range(5):
            self._add_bulk_row(flip_rows, flip_rows_frame,
                [('item', 18, ''), ('buy', 10, ''), ('sell', 10, ''), ('quantity', 7, '1'), ('transport', 12, '0')],
                [('buy_mode', ['Imediata', 'Ordem de compra'], 'Imediata'), ('sell_mode', ['Imediata', 'Ordem de venda'], 'Imediata')])
            self._add_bulk_row(craft_rows, craft_rows_frame,
                [('item', 18, ''), ('crafts', 7, '1'), ('output', 10, '1'), ('spent', 12, ''), ('received', 12, '')], [])
        status = ttk.Label(frame, wraplength=960);status.pack(anchor='w', pady=6)
        self.bulk_status = status  # acessível para testes de integração
        def submit():
            added, errors = 0, []
            for outer, f in list(flip_rows):
                item = f['item'].get().strip();buy = f['buy'].get().strip();sell = f['sell'].get().strip()
                if not item and not buy and not sell:continue
                try:
                    predicted, realized = flip_entry_from_row(buy, sell, f['quantity'].get(), f['transport'].get(),
                        f['buy_mode'].get(), f['sell_mode'].get(), self.app.profile.get())
                except ValueError as error:
                    errors.append(f'{item or "(sem nome)"}: {error}');continue
                try:
                    entry_id = self.history.add(dict(kind='flipping', item=None, quality=None, enchantment=None,
                        label=item or 'Item não identificado', predicted=predicted))
                    self.history.confirm(entry_id, realized)
                except (OSError, ValueError) as error:
                    errors.append(f'{item}: {error}');continue
                outer.destroy();flip_rows.remove((outer, f));added += 1
            for outer, f in list(craft_rows):
                item = f['item'].get().strip();spent_text = f['spent'].get().strip();received_text = f['received'].get().strip()
                if not item and not spent_text and not received_text:continue
                try:
                    predicted, realized = craft_entry_from_row(f['crafts'].get(), f['output'].get(), spent_text,
                        received_text, self.app.profile.get())
                except ValueError:
                    errors.append(f'{item or "(sem nome)"}: informe números válidos em crafts, itens/craft, gasto e recebido.');continue
                try:
                    entry_id = self.history.add(dict(kind='craft', product=None, quality=None,
                        label=item or 'Item não identificado', predicted=predicted))
                    self.history.confirm(entry_id, realized)
                except (OSError, ValueError) as error:
                    errors.append(f'{item}: {error}');continue
                outer.destroy();craft_rows.remove((outer, f));added += 1
            self.refresh()
            if errors:
                status.config(text=(f'{added} registrada(s). ' if added else 'Nada registrado. ')
                    + 'Corrija: ' + ' | '.join(errors), foreground='#F0AAAA')
            elif added:
                status.config(text=f'{added} operação(ões) registrada(s) e confirmada(s).', foreground='#8EDFC3')
            else:
                status.config(text='Nenhuma linha preenchida.', foreground='#A3B5CB')
        self.submit_bulk = submit  # acessível para testes de integração
        ttk.Button(frame, text='Registrar tudo', command=submit).pack(anchor='e', pady=4)

    def _bulk_rows_area(self, tabs, title, entry_specs, combo_specs):
        tab = ttk.Frame(tabs, padding=8)
        tabs.add(tab, text=title)
        header = ttk.Frame(tab);header.pack(fill='x')
        for key, label, width, default in entry_specs:
            ttk.Label(header, text=label, width=width, foreground='#A3B5CB').pack(side='left', padx=(0, 3))
        for key, label, values, default in combo_specs:
            ttk.Label(header, text=label, width=13, foreground='#A3B5CB').pack(side='left', padx=(0, 3))
        rows = []
        entry_key_specs = [(k, w, d) for k, _, w, d in entry_specs]
        combo_key_specs = [(k, v, d) for k, _, v, d in combo_specs]
        canvas = tk.Canvas(tab, highlightthickness=0, background='#101B2B')
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        add_button = ttk.Button(tab, text='+ linha', command=lambda: self._add_bulk_row(rows, rows_frame, entry_key_specs, combo_key_specs))
        add_button.pack(anchor='w', pady=4)
        scrollbar.pack(side='right', fill='y');canvas.pack(side='left', fill='both', expand=True)
        rows_frame = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=rows_frame, anchor='nw')
        rows_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        return rows, rows_frame

    def _add_bulk_row(self, rows, rows_frame, entry_specs, combo_specs):
        outer = ttk.Frame(rows_frame);outer.pack(fill='x', pady=1)
        fields = {}
        for key, width, default in entry_specs:
            fields[key] = tk.StringVar(value=default)
            ttk.Entry(outer, textvariable=fields[key], width=width).pack(side='left', padx=(0, 3))
        for key, values, default in combo_specs:
            fields[key] = tk.StringVar(value=default)
            ttk.Combobox(outer, textvariable=fields[key], values=values, state='readonly', width=13).pack(side='left', padx=(0, 3))
        entry = (outer, fields)
        ttk.Button(outer, text='×', width=2, command=lambda: (outer.destroy(), rows.remove(entry))).pack(side='left')
        rows.append(entry)


def _parse(iso_text):
    import datetime as dt
    return dt.datetime.fromisoformat(iso_text).timestamp()
