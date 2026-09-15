import json
import threading
import time
import tkinter as tk
import os
import math
from tkinter import ttk
from market_view import Catalog, QUALITY, age_text, freshness, filtered_orders, compare, sync_table
from trading import snapshot, CITIES, selected_item_margin
from market_api import PriceAPI, combine_prices
from catalog_search import CatalogSearch
from paths import data_path


def silver(value):
    return f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


class Dashboard(CatalogSearch):
    def __init__(self, root, con, feed, start_feed=True):
        self.root, self.con, self.feed = root, con, feed
        self.catalog = Catalog()
        self.settings_path = data_path('preferencias.json')
        try:
            self.saved_settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
            if not isinstance(self.saved_settings,dict):
                self.saved_settings = {}
        except (OSError,ValueError):
            self.saved_settings = {}
        self.exporter = None
        self.export_enabled = start_feed
        self.current_snapshot = None
        self.current_rows = []
        from market_service import MarketService
        self.market_service=MarketService()
        self.price_api=PriceAPI(enabled=start_feed,service=self.market_service)
        root.title('Albion • Mercado Américas')
        root.geometry('1440x900')
        root.minsize(1100, 740)
        style = ttk.Style()
        style.theme_use('clam')
        root.configure(background='#101B2B')
        style.configure('.',background='#101B2B',foreground='#E1EAF5',font=('Segoe UI',10))
        style.configure('TEntry',fieldbackground='#203249',foreground='#FFFFFF')
        style.configure('TCombobox',fieldbackground='#203249',foreground='#FFFFFF')
        style.map('TCombobox',fieldbackground=[('readonly','#203249')],foreground=[('readonly','#FFFFFF')])
        style.configure('Treeview', rowheight=30, font=('Segoe UI', 10),background='#16263A',fieldbackground='#16263A',foreground='#DFEAF7')
        style.configure('Treeview.Heading',background='#28485A',foreground='#FFFFFF',font=('Segoe UI',10,'bold'))
        style.map('Treeview',background=[('selected','#315775')],foreground=[('selected','#FFFFFF')])
        style.configure('TNotebook.Tab',padding=(14,8))
        style.map('TNotebook.Tab',background=[('selected','#28485A')])
        style.layout('Pages.TNotebook.Tab',[])
        style.configure('Pages.TNotebook',borderwidth=0)
        style.configure('TButton',padding=(12,7),background='#233246',foreground='#E1EAF5',borderwidth=0)
        style.map('TButton',background=[('active','#31475D')])
        style.configure('Quiet.TButton',background='#101B2B',foreground='#A3B5CB')
        style.configure('Nav.TButton',anchor='w',padding=(15,11),background='#101B2B',foreground='#A3B5CB')
        style.configure('Active.Nav.TButton',background='#244239',foreground='#B4E8D1')
        style.configure('TEntry',padding=6)
        sidebar=ttk.Frame(root,padding=(18,25),width=185)
        sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        ttk.Label(sidebar,text='ALBION',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(sidebar,text='Market desk',foreground='#93A5BA').pack(anchor='w',pady=(2,30))
        self.sidebar=sidebar
        frame = ttk.Frame(root, padding=(16,22))
        frame.pack(fill='both', expand=True)
        self.page_title=ttk.Label(frame,text='Oportunidades de flipping',font=('Segoe UI',24,'bold'))
        self.page_title.pack(anchor='w')
        self.status = ttk.Label(frame, wraplength=1250)
        self.status.pack(anchor='w', pady=10)
        self.price_origin=ttk.Label(frame,wraplength=1150,foreground='#A3B5CB')
        self.price_origin.pack(anchor='w',pady=(0,6))
        self.market_filters=ttk.Frame(frame)
        self.market_filters.pack(fill='x',pady=(4,8))
        self.filters = {}
        from ui_design import disclosure
        advanced=None
        for specs in (
            [('query', 'Nome ou código do item', None, 32), ('market', 'Cidade ou ID do mercado', None, 25),
             ('minutes', 'Idade máxima (min)', ['5','15','30','60','240','1440'], 8)],
            [('tier', 'Tier', ['Todos']+list('12345678'), 7),
             ('enchant', 'Encantamento', ['Todos','0','1','2','3','4'], 7),
             ('quality', 'Qualidade', ['Todas']+[f'{k} · {v}' for k,v in QUALITY.items()], 20),
             ('side', 'Ordens', ['Todas','Venda','Compra'], 9)]):
            if specs[0][0]=='tier':
                advanced=disclosure(self.market_filters,'Mais filtros')
            line = ttk.Frame(advanced if advanced is not None else self.market_filters)
            line.pack(fill='x', pady=5)
            for key, label, options, width in specs:
                ttk.Label(line, text=label).pack(side='left', padx=(0,5))
                var = tk.StringVar(value='15' if key=='minutes' else options[0] if options else '')
                self.filters[key] = var
                widget = (ttk.Combobox(line, textvariable=var, values=options, width=width, state='readonly')
                          if options else ttk.Entry(line, textvariable=var, width=width))
                widget.pack(side='left', padx=(0,18))
        controls = ttk.Frame(advanced)
        controls.pack(fill='x',pady=5)
        self.equipment_only = tk.BooleanVar(value=True)
        self.auto_excel = tk.BooleanVar(value=False)
        self.profile = tk.StringVar(value=self.saved_settings.get('profile','Sem Premium'))
        if self.profile.get() not in ('Premium','Sem Premium'):
            self.profile.set('Sem Premium')
        self.tax = tk.StringVar(value='4' if self.profile.get()=='Premium' else '8')
        self.transport = tk.StringVar(value=str(self.saved_settings.get('transport','0')))
        ttk.Label(sidebar,text='CONTA',foreground='#73879D',font=('Segoe UI',9,'bold')).pack(side='bottom',anchor='w',pady=5)
        profile=ttk.Combobox(sidebar,textvariable=self.profile,values=('Premium','Sem Premium'),state='readonly',width=15)
        profile.pack(side='bottom',fill='x',pady=8)
        profile.bind('<<ComboboxSelected>>',lambda event:self.tax.set('4' if self.profile.get()=='Premium' else '8'))
        ttk.Checkbutton(controls,text='Somente equipamentos',variable=self.equipment_only).pack(side='left')
        for label,var in [('Taxa venda (%)',self.tax),('Transporte por un.',self.transport)]:
            ttk.Label(controls,text=label).pack(side='left',padx=6)
            ttk.Entry(controls,textvariable=var,width=7,state='readonly' if var is self.tax else 'normal').pack(side='left')
        self.positive_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls,text='Só rotas com margem positiva',variable=self.positive_only).pack(side='left',padx=8)
        ttk.Button(controls,text='Limpar filtros',command=self.clear_filters).pack(side='left',padx=3)
        self.export_status = ttk.Label(frame,text='',wraplength=1150,foreground='#94A8BD')
        self.export_status.pack(anchor='w',pady=(0,8))
        notebook = ttk.Notebook(frame,style='Pages.TNotebook')
        self.notebook = notebook
        notebook.pack(fill='both', expand=True)
        self.overview = ttk.Frame(notebook,padding=12)
        notebook.add(self.overview,text='Visão geral')
        cards = ttk.Frame(self.overview)
        cards.pack(fill='x',pady=(0,10))
        self.metrics = {}
        for key,label in [('items','Equipamentos / variantes'),('markets','Mercados com dados'),
                          ('positive','Rotas com margem positiva'),('best','Melhor margem / unidade')]:
            card = ttk.Frame(cards,padding=8)
            card.pack(side='left',fill='x',expand=True)
            ttk.Label(card,text=label,foreground='#A3B5CB').pack(anchor='w')
            number = ttk.Label(card,text='—',font=('Segoe UI',19,'bold'),foreground='#8EDFC3')
            number.pack(anchor='w')
            self.metrics[key] = number
        split = ttk.Panedwindow(self.overview,orient='horizontal')
        split.pack(fill='both',expand=True)
        left,right=ttk.Frame(split),ttk.Frame(split)
        split.add(left,weight=3);split.add(right,weight=2)
        list_controls=ttk.Frame(left)
        list_controls.pack(fill='x',pady=5)
        self.overview_mode=tk.StringVar(value='Equipamentos coletados')
        ttk.Combobox(list_controls,textvariable=self.overview_mode,
                     values=('Equipamentos coletados','Oportunidades de flipping'),state='readonly',width=27).pack(side='left')
        self.list_status=ttk.Label(left,text='',wraplength=620,foreground='#A3B5CB')
        self.list_status.pack(anchor='w',pady=5)
        self.top_routes = self.make_table(left,None,[('Equipamento',230),('Comprar em',110),('Vender em',120),('Margem/un.',100),('Qtd.',55)])
        self.api_status=ttk.Label(right,text='',wraplength=480,foreground='#A3B5CB')
        self.api_status.pack(anchor='w',padx=12,pady=5)
        self.chart = tk.Canvas(right,background='#16263A',highlightthickness=0,width=480,height=260)
        self.chart.pack(fill='x',padx=(12,0))
        self.selected_margin=ttk.Label(right,text='',wraplength=460,font=('Segoe UI',10,'bold'))
        self.selected_margin.pack(fill='x',padx=12,pady=8)
        self.chart.bind('<Configure>',lambda event:self.draw_chart())
        self.selected_variant = None
        self.catalog_selection = None
        ttk.Button(list_controls,text='Buscar no catálogo',command=self.choose_market_item).pack(side='left',padx=8)
        ttk.Button(right,text='Simular rota selecionada',command=lambda:self.open_route_summary()).pack(anchor='w',padx=12)
        ttk.Label(right,text='Comparação por cidade',foreground='#A3B5CB').pack(anchor='w',padx=12,pady=(10,2))
        self.city_compare = self.make_table(right,None,[('Cidade',105),('Comprar por',95),('Idade/origem compra',150),
                                                          ('Vender por',95),('Idade/origem venda',150)])
        self.top_routes.bind('<<TreeviewSelect>>',self.select_route)
        self.matrix = self.make_table(notebook,'Preços por cidade',
            [('Equipamento',310),('Qualidade',110),('Preço',120)]+[(c[1],115) for c in CITIES])
        self.routes = self.make_table(notebook,'Onde comprar e vender',
            [('Equipamento',300),('Qualidade',110),('Comprar em',140),('Compra/un.',100),
             ('Vender em',140),('Venda/un.',100),('Após custos/un.',115),('Qtd. limite',90),('Idade',85)])
        self.routes.bind('<<TreeviewSelect>>',self.select_route)
        self.matrix.bind('<Double-1>',self.select_matrix)
        self.table = self.make_table(notebook, 'Ordens observadas',
            [('Item / código',340),('Mercado',170),('Qualidade',110),('Ordem',80),
             ('Prata / un.',100),('Quantidade',90),('Idade',85)])
        self.comparison = self.make_table(notebook, 'Comparar mercados',
            [('Item / código',340),('Qualidade',110),('Mercado',160),
             ('Menor venda',105),('Qtd.',60),('Idade venda',95),
             ('Maior compra',105),('Qtd.',60),('Idade compra',95)])
        from calculators import Calculators
        self.calculators = Calculators(self)
        self.filters['minutes'].trace_add('write',lambda *args:self.calculators.refresh())
        for page in (self.calculators.flip,self.calculators.craft):
            freshness_controls=ttk.Frame(page)
            freshness_controls.pack(fill='x',before=page.winfo_children()[0],pady=(0,8))
            ttk.Label(freshness_controls,text='Idade máxima dos preços (min)').pack(side='left',padx=(0,8))
            ttk.Combobox(freshness_controls,textvariable=self.filters['minutes'],
                         values=('5','15','30','60','240','1440'),state='readonly',width=8).pack(side='left')
        from history_ui import HistoryView
        self.history_view = HistoryView(self)
        self.nav_buttons={}
        pages=list(notebook.tabs())
        labels=[('MERCADO',[(0,'Explorar equipamentos')]),
                ('FLIPPING',[(2,'Encontrar rotas'),(5,'Simular operação')]),
                ('PRODUÇÃO',[(6,'Planejar craft')]),
                ('HISTÓRICO',[(7,'Operações registradas')])]
        self.page_names={0:'Oportunidades de flipping',2:'Rotas de compra e venda',5:'Simular flipping',
                         6:'Planejar craft',1:'Preços por cidade',4:'Comparar preços',3:'Ordens coletadas',
                         7:'Histórico de operações'}
        for section,links in labels:
            ttk.Label(sidebar,text=section,foreground='#73879D',font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(14,6))
            for index,label in links:
                button=ttk.Button(sidebar,text=label,style='Nav.TButton',command=lambda p=pages[index]:notebook.select(p))
                button.pack(fill='x',pady=2)
                self.nav_buttons[index]=button
        advanced_nav=disclosure(sidebar,'Dados avançados')
        for index,label in [(1,'Preços por cidade'),(4,'Comparar preços'),(3,'Ordens coletadas')]:
            button=ttk.Button(advanced_nav,text=label,style='Nav.TButton',command=lambda p=pages[index]:notebook.select(p))
            button.pack(fill='x',pady=2);self.nav_buttons[index]=button
        notebook.bind('<<NotebookTabChanged>>',self.page_changed)
        self.page_changed()
        self.footer = ttk.Label(frame)
        self.footer.pack(anchor='w', pady=8)
        ttk.Label(frame,text='Fonte: AODP · Preços observados, sujeitos a alteração · Sem Office',foreground='#73879D').pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW', self.close)
        if start_feed:
            threading.Thread(target=feed.run, daemon=True).start()
        self.refresh()

    def make_table(self, notebook, title, specs):
        pane = ttk.Frame(notebook)
        if title is None:
            pane.pack(fill='both',expand=True)
        else:
            notebook.add(pane, text=title)
        table = ttk.Treeview(pane, columns=list(range(len(specs))), show='headings')
        for i,(label,width) in enumerate(specs):
            table.heading(i,text=label)
            table.column(i,width=width,minwidth=60,anchor='w')
        table.tag_configure('fresh',foreground='#A9E3C4')
        table.tag_configure('warm',foreground='#F4D08B')
        table.tag_configure('old',foreground='#F4A9A9')
        y = ttk.Scrollbar(pane,orient='vertical',command=table.yview)
        x = ttk.Scrollbar(pane,orient='horizontal',command=table.xview)
        table.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        table.grid(row=0,column=0,sticky='nsew')
        y.grid(row=0,column=1,sticky='ns')
        x.grid(row=1,column=0,sticky='ew')
        pane.rowconfigure(0,weight=1)
        pane.columnconfigure(0,weight=1)
        return table

    def page_changed(self,event=None):
        index=self.notebook.index(self.notebook.select())
        explanations={
            0:'Preços anunciados observados: fluxo AODP; gráfico também consulta a API Américas. Margens são calculadas, não vendas realizadas.',
            1:'Preços anunciados observados no fluxo AODP. Comprar por = menor oferta de venda; vender por = maior pedido de compra.',
            2:'Rotas calculadas com ofertas e pedidos observados no fluxo AODP. Disponibilidade atual e execução não são garantidas.',
            3:'Ordens observadas no jogo e compartilhadas pelo AODP. A idade indica quando o app recebeu a observação, não uma venda.',
            4:'Comparação de ofertas de venda e pedidos de compra observados no fluxo AODP; não é histórico de negócios concluídos.',
            5:'Preços copiados de uma rota são observados; preços digitados são manuais, não verificados. Lucro é uma estimativa.',
            6:'Consulta de ofertas e pedidos via AODP (fluxo e API Américas). Valores manuais são identificados; custos e lucros são calculados.',
            7:'Operações que você registrou manualmente nas calculadoras. Lucro previsto vem do cálculo exibido; lucro realizado só existe após você confirmar o que comprou/vendeu de fato.'}
        self.price_origin.configure(text=explanations[index])
        self.page_title.configure(text=self.page_names[index])
        for key,button in self.nav_buttons.items():
            button.configure(style='Active.Nav.TButton' if key==index else 'Nav.TButton')
        if index==7:self.history_view.refresh()
        if index in (5,6,7):
            self.market_filters.pack_forget()
            self.export_status.pack_forget()
        else:
            self.market_filters.pack(fill='x',pady=(4,8),before=self.notebook)
            self.export_status.pack(anchor='w',pady=(0,8),before=self.notebook)

    def refresh(self):
        now = time.time()
        f = {k:v.get() for k,v in self.filters.items()}
        rows = filtered_orders(self.con,self.catalog,now,int(f['minutes']),f['query'],f['market'],
                    '' if f['tier']=='Todos' else f['tier'],
                    '' if f['enchant']=='Todos' else f['enchant'],
                    '' if f['quality']=='Todas' else f['quality'].split(' · ')[0])
        self.current_rows = rows
        money = lambda n: f'{n:,}'.replace(',','.')
        name = lambda code,e: f'{self.catalog.item(code)} [.{e}] • {code}'
        display = [r for r in rows if f['side']=='Todas' or r[5]==('offer' if f['side']=='Venda' else 'request')]
        entries = []
        for oid,loc,item,q,e,side,price,amount,seen in display[:500]:
            entries.append((json.dumps([oid,loc]), (name(item,e),self.catalog.market(loc),QUALITY.get(q,str(q)),
                'Venda' if side=='offer' else 'Compra',money(price),amount,age_text(seen,now)),freshness(seen,now)))
        sync_table(self.table,entries)
        groups = compare(rows)
        entries = []
        for (item,q,e,loc),sides in groups[:1000]:
            values = [name(item,e),QUALITY.get(q,str(q)),self.catalog.market(loc)]
            for side in ('offer','request'):
                best = sides.get(side)
                values.extend((money(best[0]),best[1],age_text(best[2],now)) if best else ('—','—','—'))
            oldest = min(best[2] for best in sides.values())
            entries.append((json.dumps([item,q,e,loc]),values,freshness(oldest,now)))
        sync_table(self.comparison,entries)
        try:
            tax = float(self.tax.get().replace(',','.'))/100
            transport = float(self.transport.get().replace(',','.'))
            if not math.isfinite(tax) or not math.isfinite(transport):
                raise ValueError()
            data = snapshot(rows,self.catalog,int(f['minutes']),tax,transport,self.equipment_only.get(),now,api=self.price_api.all_prices())
            data['filters'] = f
            self.current_snapshot = data
            matrix_entries = []
            for v in data['variants'][:500]:
                for side,label in [('offer','Comprar por'),('request','Vender por')]:
                    available = [m[side]['seen'] for m in v['markets'].values() if side in m]
                    if not available:
                        continue
                    prices = [money(v['markets'][id][side]['price']) if side in v['markets'].get(id,{}) else '—' for id,_ in CITIES]
                    matrix_entries.append((json.dumps([v['code'],v['quality'],v['enchantment'],side]),
                        [name(v['code'],v['enchantment']),v['quality_name'],label]+prices,freshness(min(available),now)))
            sync_table(self.matrix,matrix_entries)
            visible_routes = [r for r in data['routes'] if not self.positive_only.get() or r['net']>0]
            sync_table(self.routes,[(json.dumps([r['code'],r['quality'],r['enchantment']]),
                [name(r['code'],r['enchantment']),r['quality_name'],r['origin'],money(r['buy']['price']),
                 r['destination'],money(r['sell']['price']),silver(r['net']),r['quantity'],
                 age_text(min(r['buy']['seen'],r['sell']['seen']),now)],
                 freshness(min(r['buy']['seen'],r['sell']['seen']),now)) for r in visible_routes[:500]])
            self.update_overview(data,visible_routes,now)
            self.export_status.config(text=f'Rotas imediatas: {self.profile.get()} • Taxa de venda {self.tax.get()}% • Ordens e craft: use as calculadoras.')
        except ValueError:
            self.current_snapshot = None
            sync_table(self.routes,[])
            sync_table(self.top_routes,[])
            for metric in self.metrics.values():
                metric.config(text='—')
            self.draw_chart()
            self.export_status.config(text='Informe taxa de 0 a 100% e transporte não negativo para calcular as rotas.')
        last = 'nenhuma' if self.feed.last is None else age_text(self.feed.last,now)+' atrás'
        warning = ' • Sem mensagens há mais de 60s' if self.feed.last and now-self.feed.last>60 else ''
        catalog_warning = ' • Catálogo indisponível: '+', '.join(self.catalog.errors) if self.catalog.errors else ''
        self.status.config(text=f'Américas · {self.feed.status}{warning} · Atualizado {last}{catalog_warning}')
        self.footer.config(text=f'Ordens: {min(500,len(display))} de {len(display)} • Comparações: '
            f'{min(1000,len(groups))} de {len(groups)} • Mais itens disponíveis pelos filtros')
        self.calculators.refresh()
        self.price_api.request(self.selected_variant)
        self.timer = self.root.after(1500,self.refresh)

    def export_now(self):
        if self.current_snapshot is not None:
            if self.exporter is None:
                from excel_export import Exporter
                self.exporter = Exporter()
            self.exporter.request(self.current_snapshot)

    def open_excel_folder(self):
        from excel_export import OUTPUT
        OUTPUT.mkdir(parents=True,exist_ok=True)
        os.startfile(OUTPUT)

    def clear_filters(self):
        for key,var in self.filters.items():
            var.set({'minutes':'15','tier':'Todos','enchant':'Todos','quality':'Todas','side':'Todas'}.get(key,''))

    def update_overview(self,data,routes,now):
        self.metrics['items'].config(text=str(len(data['variants'])))
        self.metrics['markets'].config(text=f"{len({o['city_id'] for o in data['observations']})} / {len(CITIES)}")
        positive=[r for r in data['routes'] if r['net']>0]
        self.metrics['positive'].config(text=str(len(positive)))
        self.metrics['best'].config(text=silver(positive[0]['net']) if positive else '—')
        entries=[(json.dumps([r['code'],r['quality'],r['enchantment']]),
            [f"{r['name']} {r['code'].split('_')[0]}.{r['enchantment']} · {r['quality_name']}",r['origin'],r['destination'],silver(r['net']),r['quantity']],
            freshness(min(r['buy']['seen'],r['sell']['seen']),now)) for r in routes[:100]]
        if self.overview_mode.get()=='Equipamentos coletados':
            headings=['Equipamento','Comprar por','Vender por','Melhor rota / un.','Mercados']
            route_map={(r['code'],r['quality'],r['enchantment']):r for r in data['routes']}
            entries=[]
            for v in data['variants'][:500]:
                key=(v['code'],v['quality'],v['enchantment'])
                offers=[m['offer']['price'] for m in v['markets'].values() if 'offer' in m]
                bids=[m['request']['price'] for m in v['markets'].values() if 'request' in m]
                seen=min(p['seen'] for m in v['markets'].values() for p in m.values())
                route=route_map.get(key)
                entries.append((json.dumps(key),
                    [f"{v['name']} {v['code'].split('_')[0]}.{v['enchantment']} · {v['quality_name']}",
                     silver(min(offers)) if offers else 'Sem oferta',silver(max(bids)) if bids else 'Sem compra',
                     silver(route['net']) if route else 'Sem rota',len(v['markets'])],freshness(seen,now)))
            self.list_status.config(text=f"{min(500,len(data['variants']))} de {len(data['variants'])} variantes com dados recentes. Selecione para comparar. "
                'O filtro de margem positiva vale apenas para oportunidades.' if entries else
                'Nenhum equipamento com dados nos filtros atuais. Limpe a pesquisa, amplie a idade ou aguarde novas coletas.')
        else:
            headings=['Equipamento','Comprar em','Vender em','Margem/un.','Qtd.']
            self.list_status.config(text=f'{len(routes)} oportunidades nos filtros atuais (até 100 exibidas).' if entries else
                ('Há equipamentos coletados, mas nenhuma rota atende ao filtro de margem. Selecione Equipamentos coletados para pesquisar preços.'
                 if data['variants'] else 'Nenhum equipamento com dados nos filtros atuais.'))
        for index,title in enumerate(headings):self.top_routes.heading(index,text=title)
        sync_table(self.top_routes,entries)
        keys={(v['code'],v['quality'],v['enchantment']) for v in data['variants']}
        if self.selected_variant not in keys and self.selected_variant!=self.catalog_selection:
            self.selected_variant=None
        self.draw_chart()

    def select_route(self,event):
        selected=event.widget.selection()
        if selected:
            self.catalog_selection=None
            self.selected_variant=tuple(json.loads(selected[0]))
            self.price_api.request(self.selected_variant)
            self.draw_chart()

    def select_matrix(self,event):
        selected=self.matrix.selection()
        if selected:
            self.catalog_selection=None
            self.selected_variant=tuple(json.loads(selected[0])[:3])
            self.price_api.request(self.selected_variant)
            self.notebook.select(self.overview)
            self.draw_chart()

    def open_route_summary(self):
        self.calculators.use_route()
        self.notebook.select(self.calculators.flip)
        self.calculators.refresh()

    def selected_markets(self):
        """Preços por cidade do item selecionado (fluxo + API), única fonte usada pelo gráfico e pela simulação."""
        data=self.current_snapshot
        variant=next((v for v in data['variants'] if (v['code'],v['quality'],v['enchantment'])==self.selected_variant),None) if data else None
        if variant is None and self.selected_variant is not None and self.selected_variant==self.catalog_selection:
            code,quality,enchant=self.selected_variant
            from trading import item_markets
            markets=item_markets(self.current_rows,code,quality,enchant,time.time(),int(self.filters['minutes'].get()))
            variant=dict(code=code,quality=quality,enchantment=enchant,name=self.catalog.item(code),
                         quality_name=QUALITY.get(quality,str(quality)),markets=markets)
        api_prices,api_message=self.price_api.read(self.selected_variant)
        self.api_status.configure(text=api_message)
        if variant is None:
            return None
        return dict(variant,markets=combine_prices(variant['markets'],api_prices))

    def draw_chart(self):
        canvas=self.chart
        canvas.delete('all')
        w=max(canvas.winfo_width(),400);h=max(canvas.winfo_height(),260)
        variant=self.selected_markets()
        if variant is None:
            self.selected_margin.configure(text='')
            sync_table(self.city_compare,[])
            canvas.create_text(20,30,anchor='nw',width=w-40,fill='#CFDCEC',font=('Segoe UI',12),
                text='Selecione um item para comparar.')
            return
        canvas.create_text(15,10,anchor='nw',width=w-30,fill='#FFFFFF',font=('Segoe UI',11,'bold'),
            text=f"{variant['name']} {variant['code'].split('_')[0]}.{variant['enchantment']} · {variant['quality_name']}")
        markets=variant['markets']
        try:
            margin=selected_item_margin(markets,float(self.tax.get().replace(',','.'))/100,
                float(self.transport.get().replace(',','.')),int(self.filters['minutes'].get())*60,time.time())
            if margin:
                cities=dict(CITIES)
                volume='Volume desconhecido (API)' if margin['quantity'] is None else f"Volume observado: até {margin['quantity']} un."
                self.selected_margin.configure(text=f"Melhor margem estimada: {silver(margin['net'])} prata/un.\n"
                    f"{cities.get(margin['origin'],margin['origin'])} → {cities.get(margin['destination'],margin['destination'])} · Retorno sobre custo: {margin['roi']*100:.1f}%\n"
                    f"{self.profile.get()} · Imposto {self.tax.get()}% + transporte {self.transport.get()} prata/un.\n{volume} · Compra e venda imediatas, sem garantia de execução.",
                    foreground='#8EDFC3' if margin['net']>0 else '#F0AAAA')
            else:self.selected_margin.configure(text='Margem indisponível: faltam oferta de venda e pedido de compra recentes em cidades diferentes.',foreground='#A3B5CB')
        except ValueError:
            self.selected_margin.configure(text='Margem indisponível: confira imposto e transporte.',foreground='#F0AAAA')
        now=time.time();max_age=int(self.filters['minutes'].get())*60
        def cell(price):
            if not price:return '—','sem dado'
            old=now-price['seen']>max_age
            return (('*' if old else '')+silver(price['price']),
                    f"{age_text(price['seen'],now)} · {price.get('source','Fluxo')}"+(' (vencido)' if old else ''))
        compare_rows=[]
        for loc,city in CITIES:
            sides=markets.get(loc,{})
            buy_price,buy_age=cell(sides.get('offer'))
            sell_price,sell_age=cell(sides.get('request'))
            has_fresh=any(p and now-p['seen']<=max_age for p in (sides.get('offer'),sides.get('request')))
            compare_rows.append((loc,(city,buy_price,buy_age,sell_price,sell_age),'fresh' if has_fresh else 'old'))
        sync_table(self.city_compare,compare_rows)
        canvas.create_text(15,46,anchor='nw',fill='#6EADD4',font=('Segoe UI',9),text='Azul: comprar')
        canvas.create_text(135,46,anchor='nw',fill='#74D3AB',font=('Segoe UI',9),text='Verde: vender')
        canvas.create_text(15,62,anchor='nw',fill='#A5A1A0',font=('Segoe UI',9),width=w-30,
                           text='Cinza: preço antigo, fora do limite de idade (*)')
        prices=[v['price'] for m in markets.values() for v in m.values()]
        maximum=max(prices,default=1)
        row_height=max(24,min(44,(h-100)/8))
        left=125;right=max(left+50,w-155)
        for i,(loc,city) in enumerate(CITIES):
            y=80+i*row_height
            canvas.create_text(10,y+5,anchor='w',fill='#C5D5E7',font=('Segoe UI',9),text=city)
            for j,(side,color) in enumerate([('offer','#6EADD4'),('request','#74D3AB')]):
                price=markets.get(loc,{}).get(side)
                yy=y+j*11
                if price:
                    old=time.time()-price['seen']>int(self.filters['minutes'].get())*60
                    if old:color='#A5A1A0'
                    length=(right-left)*price['price']/maximum
                    canvas.create_rectangle(left,yy,left+max(length,1),yy+8,fill=color,outline='')
                    canvas.create_text(right+7,yy+4,anchor='w',fill=color,font=('Segoe UI',8),
                        text=f"{silver(price['price'])} · {age_text(price['seen'],time.time())}{'*' if old else ''} {price.get('source','Fluxo')}")
                else:
                    canvas.create_text(right+7,yy+4,anchor='w',fill='#8295AD',font=('Segoe UI',8),text='sem dado')

    def close(self):
        if self.calculators.production_planner is not None:self.calculators.production_planner.close()
        self.root.after_cancel(self.timer)
        if self.export_enabled and self.current_snapshot is not None:
            try:
                from persistence import write_settings
                write_settings(self.settings_path,{'profile':self.profile.get(),'tax':self.tax.get(),'transport':self.transport.get()})
            except OSError:
                pass
        self.feed.close()
        self.con.close()
        self.root.destroy()
