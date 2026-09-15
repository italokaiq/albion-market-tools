import json
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from economics import flipping, crafting
from trading import city_id, CITIES
from market_view import age_text
from ui_design import disclosure,result_table,fill_results
from craft_prices import CraftPrices


def money(v):
    return f'{v:,.2f}'.replace(',','_').replace('.',',').replace('_','.')


class Calculators(CraftPrices):
    def __init__(self,app):
        self.app=app
        self.saved=Path(__file__).with_name('receita_craft.json')
        self.flip_fields={}
        self.craft_fields={}
        self.materials=[]
        from recipes import RecipeCatalog
        self.recipes=RecipeCatalog(app.catalog)
        self.recipe_code=None
        self.production_planner=None
        self.flip_observation=None
        self.init_prices()
        self.flip=ttk.Frame(app.notebook,padding=12)
        app.notebook.add(self.flip,text='Calculadora de flipping')
        shell=ttk.Frame(app.notebook)
        app.notebook.add(shell,text='Calculadora de craft')
        canvas=tk.Canvas(shell,highlightthickness=0,background='#101B2B')
        scrollbar=ttk.Scrollbar(shell,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        self.craft=ttk.Frame(canvas,padding=12)
        window=canvas.create_window((0,0),window=self.craft,anchor='nw')
        self.craft.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(window,width=event.width))
        self.make_flip()
        self.make_craft()
        self.craft_fields['crafts'].trace_add('write',lambda *args:self.craft_fields['station'].set(''))

    def fields(self,parent,target,specs):
        line=ttk.Frame(parent);line.pack(fill='x',pady=7)
        for index,(key,label,default,options) in enumerate(specs):
            block=ttk.Frame(line,padding=(0,0,16,0))
            block.grid(row=0,column=index,sticky='ew');line.columnconfigure(index,weight=1,uniform='field')
            ttk.Label(block,text=label,foreground='#A3B5CB').pack(anchor='w',pady=(0,5))
            v=tk.StringVar(value=default);target[key]=v
            if options:
                widget=ttk.Combobox(line,textvariable=v,values=options,state='readonly',width=18)
            else:
                widget=ttk.Entry(line,textvariable=v,width=14)
            widget.pack(in_=block,fill='x')

    def make_flip(self):
        ttk.Label(self.flip,text='Calcule a operação antes de comprar.',font=('Segoe UI',12),foreground='#A3B5CB').pack(anchor='w',pady=(0,12))
        self.fields(self.flip,self.flip_fields,[('buy','Compra/un.','',None),('sell','Venda/un.','',None),('quantity','Quantidade','1',None)])
        self.fields(self.flip,self.flip_fields,[('buy_mode','Comprar','Imediata',['Imediata','Ordem de compra']),('sell_mode','Vender','Imediata',['Imediata','Ordem de venda'])])
        advanced=disclosure(self.flip,'Transporte e recriação de ordens')
        self.fields(advanced,self.flip_fields,[('transport','Transporte total','0',None),('buy_relists','Recriações compra','0',None),('sell_relists','Recriações venda','0',None)])
        ttk.Button(self.flip,text='Usar rota selecionada',command=self.use_route).pack(anchor='w')
        self.flip_note=ttk.Label(self.flip,text='',wraplength=1150)
        self.flip_note.pack(anchor='w',pady=5)
        self.flip_result=ttk.Label(self.flip,text='',font=('Segoe UI',11),wraplength=1000)
        self.flip_result.pack(anchor='w',pady=8)
        self.flip_table=result_table(self.flip)
        info=disclosure(self.flip,'Como as taxas são calculadas')
        ttk.Label(info,text='Ordem de compra: 2,5% com ou sem Premium.\n'
                  'Ordem de venda: Premium 4% + 2,5% = 6,5%; sem Premium 8% + 2,5% = 10,5%.\n'
                  'Compra imediata: sem taxa de ordem. Venda imediata: 4% ou 8%, sem taxa de ordem.\n'
                  'Recriações usam o mesmo preço e quantidade. Ordens dependem de preenchimento futuro.',wraplength=950).pack(anchor='w',pady=5)

    def make_craft(self):
        ttk.Label(self.craft,text='1  Escolha o equipamento     →     2  Consulte preços e confirme custos     →     3  Compare cidades',
                  wraplength=1050,font=('Segoe UI',11,'bold'),foreground='#8EDFC3').pack(anchor='w',pady=(0,12))
        chooser=ttk.Frame(self.craft);chooser.pack(fill='x',pady=(0,10))
        ttk.Button(chooser,text='Escolher equipamento pelo nome',command=self.choose_equipment).pack(side='left')
        ttk.Button(chooser,text='Comparar compra, refino e cidades',command=self.open_production_planner).pack(side='left',padx=8)
        self.recipe_title=ttk.Label(chooser,text='Selecione para preencher a receita.',foreground='#A3B5CB',wraplength=650)
        self.recipe_title.pack(side='left',padx=12)
        self.alternative=tk.StringVar(value='Receita 1')
        self.recipe_options=ttk.Combobox(self.craft,textvariable=self.alternative,state='readonly',width=45)
        self.recipe_options.bind('<<ComboboxSelected>>',lambda e:self.apply_recipe(self.recipe_code,self.recipe_options.current()))
        self.fields(self.craft,self.craft_fields,[('code','Código produzido','',None),('crafts','Crafts','1',None),('output','Itens/craft','1',None),('sell','Venda/un.','',None)])
        cities=[name for _,name in CITIES]
        self.fields(self.craft,self.craft_fields,[('city','Comprar materiais em','Thetford',cities),('destination','Vender em','Thetford',cities),('quality','Qualidade final','1',['1','2','3','4','5'])])
        self.fields(self.craft,self.craft_fields,[('buy_mode','Materiais','Imediata',['Imediata','Ordem de compra']),('sell_mode','Venda final','Imediata',['Imediata','Ordem de venda']),('rrr','Retorno no jogo (%)','',None)])
        self.fields(self.craft,self.craft_fields,[('station','Estação total (prata)','',None)])
        advanced=disclosure(self.craft,'Estação, transporte, diários e Foco')
        self.fields(advanced,self.craft_fields,[('transport','Transporte total','0',None),('other','Outros custos','0',None)])
        self.fields(advanced,self.craft_fields,[('journal','Crédito líquido diários','0',None),('focus','Foco total','0',None),('focus_value','Prata/ponto de Foco','0',None)])
        materials=ttk.Frame(self.craft);materials.pack(fill='x',pady=4)
        self.material_container=materials
        ttk.Label(materials,text='Materiais por craft',font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(8,6))
        self.add_material()
        buttons=ttk.Frame(self.craft);buttons.pack(fill='x',pady=4)
        for label,callback in [('Adicionar material',self.add_material),('Buscar preços recentes',self.load_prices),('Salvar receita',self.save_recipe),('Carregar receita',self.load_recipe)]:
            ttk.Button(buttons,text=label,command=callback).pack(side='left',padx=(0,8))
        self.craft_note=ttk.Label(self.craft,text='Informe a receita do jogo. Preços ausentes bloqueiam o cálculo; não são tratados como zero.',wraplength=1180)
        self.craft_note.pack(anchor='w')
        self.price_status=ttk.Label(self.craft,text='Preços digitados manualmente são informados por você, não verificados pelo app.',wraplength=1000,foreground='#A3B5CB')
        self.price_status.pack(anchor='w',pady=4)
        self.craft_result=ttk.Label(self.craft,text='',wraplength=1180,font=('Segoe UI',11))
        self.craft_result.pack(anchor='w',pady=5)
        self.craft_table=result_table(self.craft)
        info=disclosure(self.craft,'Entenda o retorno e os custos')
        ttk.Label(info,text='Ordem de compra de materiais: 2,5% com ou sem Premium.\n'
                  'Ordem de venda: Premium 4% + 2,5% = 6,5%; sem Premium 8% + 2,5% = 10,5%.\n'
                  'Compra imediata: sem taxa de ordem. Venda imediata: 4% ou 8%, sem taxa de ordem.\n'
                  'Retorno: use o percentual exibido no jogo. Artefatos não retornam.\n'
                  'Estação: custo total em prata, não a tarifa por nutrição. Recursos retornados são estoque, não prata recebida.',wraplength=950).pack(anchor='w')

    def add_material(self):
        outer=ttk.Frame(self.material_container);outer.pack(fill='x',pady=3)
        name=ttk.Label(outer,text='',foreground='#A3B5CB');name.pack(anchor='w')
        row=ttk.Frame(outer);row.pack(fill='x')
        fields={}
        for key,label,width,default in [('code','Código',28,''),('quantity','Qtd/craft',10,'1'),('price','Prata/un.',12,'')]:
            ttk.Label(row,text=label).pack(side='left',padx=(0,5))
            fields[key]=tk.StringVar(value=default)
            ttk.Entry(row,textvariable=fields[key],width=width).pack(side='left',padx=(0,10))
        fields['returns']=tk.BooleanVar(value=False)
        ttk.Checkbutton(row,text='Retorna',variable=fields['returns']).pack(side='left')
        def display_name(*args):
            code=fields['code'].get().strip().upper()
            name.configure(text=self.app.catalog.item(code) if code else '')
        fields['code'].trace_add('write',display_name)
        ttk.Button(row,text='Remover',command=lambda:self.remove_material(outer,fields)).pack(side='left',padx=8)
        self.materials.append((outer,fields))

    def choose_equipment(self):
        dialog=tk.Toplevel(self.app.root);dialog.title('Escolher equipamento');dialog.geometry('800x460')
        dialog.transient(self.app.root)
        frame=ttk.Frame(dialog,padding=18);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Busque pelo nome, tier ou encantamento. Ex.: espada T4.1').pack(anchor='w')
        query=tk.StringVar()
        entry=ttk.Entry(frame,textvariable=query);entry.pack(fill='x',pady=10);entry.focus_set()
        panel=ttk.Frame(frame);panel.pack(fill='both',expand=True)
        listing=tk.Listbox(panel,background='#16263A',foreground='#DFEAF7',selectbackground='#315775',font=('Segoe UI',11),exportselection=False)
        bar=ttk.Scrollbar(panel,command=listing.yview);listing.configure(yscrollcommand=bar.set)
        listing.pack(side='left',fill='both',expand=True);bar.pack(side='right',fill='y')
        status=ttk.Label(frame);status.pack(anchor='w',pady=8)
        matches=[]
        def search(*args):
            matches[:]=self.recipes.search(query.get())
            listing.delete(0,'end')
            for code in matches[:100]:listing.insert('end',self.recipes.label(code))
            status.configure(text=self.recipes.error or f'{len(matches)} encontrados; até 100 exibidos. Refine a busca para ver outros.')
        def choose(event=None):
            selected=listing.curselection()
            if selected:
                self.apply_recipe(matches[selected[0]])
                dialog.destroy()
                self.open_production_planner()
        listing.bind('<Double-1>',choose);listing.bind('<Return>',choose)
        ttk.Button(frame,text='Usar equipamento e carregar receita',command=choose).pack(anchor='e')
        query.trace_add('write',search);search()

    def open_production_planner(self):
        if self.production_planner is None:
            from production_ui import ProductionPlanner
            try:self.production_planner=ProductionPlanner(self)
            except (OSError,ValueError,KeyError,TypeError) as error:
                self.craft_note.config(text='Catálogo de refino indisponível. A calculadora manual continua disponível. '+str(error))
                return
        self.production_planner.open()

    def apply_recipe(self,code,index=0):
        alternatives=self.recipes.recipes.get(code,[])
        if not alternatives or not 0<=index<len(alternatives):
            self.craft_note.configure(text='Receita não disponível; use os campos manuais.')
            return
        self.recipe_code=code
        recipe=alternatives[index]
        self.recipe_title.configure(text=self.recipes.label(code))
        self.recipe_options.configure(values=[f'Receita {i+1}: '+', '.join(self.app.catalog.item(m['code']) for m in r['materials']) for i,r in enumerate(alternatives)])
        self.recipe_options.current(index)
        if len(alternatives)>1:self.recipe_options.pack(fill='x',before=self.material_container,pady=5)
        else:self.recipe_options.pack_forget()
        self.craft_fields['code'].set(code)
        self.craft_fields['output'].set(str(recipe['output']))
        self.craft_fields['sell'].set('')
        self.craft_fields['rrr'].set('')
        self.craft_fields['station'].set('')
        for row,m in list(self.materials):self.remove_material(row,m)
        for material in recipe['materials']:
            self.add_material()
            for key,value in material.items():self.materials[-1][1][key].set(value)
        self.craft_note.configure(text='Receita carregada. Clique em Buscar preços recentes; confira retorno e custos da estação.'+
            (f" Custo adicional da receita: {recipe['silver']} prata/craft; inclua em Outros custos." if recipe['silver'] else ''))
        self.refresh()

    def remove_material(self,row,fields):
        row.destroy();self.materials.remove((row,fields))

    def use_route(self):
        data=self.app.current_snapshot
        route=next((r for r in data['routes'] if (r['code'],r['quality'],r['enchantment'])==self.app.selected_variant),None) if data else None
        if route:
            latest=self.app.price_api.all_prices().get((route['code'],route['quality']),{})
            ids={name:city for city,name in CITIES}
            for field,city_name,side in [('buy','origin','offer'),('sell','destination','request')]:
                remote=latest.get(ids[route[city_name]],{}).get(side)
                if remote and remote['seen']>route[field]['seen']:
                    route=None
                    break
        if route is None:
            self.flip_observation=None
            self.flip_fields['buy'].set('');self.flip_fields['sell'].set('')
            self.flip_note.config(text='Não há rota com preços e volume conhecidos para este item. A API não informa quantidade; consulte uma rota coletada ou informe preços manualmente.')
            return
        for key,value in [('buy',route['buy']['price']),('sell',route['sell']['price']),('quantity',route['quantity']),('buy_mode','Imediata'),('sell_mode','Imediata')]:
            self.flip_fields[key].set(value)
        self.flip_fields['transport'].set(str(float(self.app.transport.get().replace(',','.'))*route['quantity']))
        self.flip_observation=(self.flip_fields['buy'].get(),self.flip_fields['sell'].get(),
                               min(route['buy']['seen'],route['sell']['seen']),route['quantity'])
        self.flip_note.config(text=f"{route['code']} · {route['quality_name']} · {route['origin']} para {route['destination']} · Copiado às {time.strftime('%H:%M:%S')}. Preços válidos até o limite de idade configurado.")

    def save_recipe(self):
        data=dict(fields={k:v.get() for k,v in self.craft_fields.items()},materials=[{k:v.get() for k,v in m.items()} for _,m in self.materials])
        try:
            from persistence import write_settings
            write_settings(self.saved,data)
            self.craft_note.config(text='Receita salva neste computador. Ao carregar, busque os preços novamente.')
        except OSError as e:self.craft_note.config(text=str(e))

    def load_recipe(self):
        try:
            data=json.loads(self.saved.read_text(encoding='utf-8'))
            for k,v in data['fields'].items():
                if k in self.craft_fields:self.craft_fields[k].set(v)
            for row,m in list(self.materials):self.remove_material(row,m)
            for m in data['materials']:
                self.add_material()
                for k,v in m.items():
                    if k in self.materials[-1][1]:self.materials[-1][1][k].set(v)
                self.materials[-1][1]['price'].set('')
            self.craft_fields['sell'].set('')
            self.craft_fields['station'].set('')
            self.craft_fields['rrr'].set('')
            self.recipe_code=None
            self.recipe_options.pack_forget()
            self.recipe_title.configure(text='Receita salva: '+self.app.catalog.item(self.craft_fields['code'].get()))
            self.craft_note.config(text='Receita carregada. Busque ou informe os preços atuais.')
        except (OSError,ValueError,KeyError,TypeError) as e:self.craft_note.config(text='Não foi possível carregar: '+str(e))

    def refresh(self):
        self.poll_prices()
        try:
            f={k:v.get() for k,v in self.flip_fields.items()}
            if self.flip_observation:
                buy,sell,seen,volume=self.flip_observation
                observed_buy=f['buy']==buy
                observed_sell=f['sell']==sell
                if time.time()-seen>int(self.app.filters['minutes'].get())*60:
                    if observed_buy:self.flip_fields['buy'].set('')
                    if observed_sell:self.flip_fields['sell'].set('')
                    self.flip_observation=None
                    if observed_buy or observed_sell:
                        raise ValueError('Os preços da rota expiraram. Selecione uma rota recente; edições manuais foram preservadas.')
                if observed_buy and observed_sell:
                    if f['buy_mode']=='Imediata' and f['sell_mode']=='Imediata' and float(f['quantity'].replace(',','.'))>volume:
                        raise ValueError(f'Quantidade acima do volume observado ({volume}). Reduza o lote ou obtenha novas ordens.')
                else:
                    if not observed_buy and not observed_sell:self.flip_observation=None
                    self.flip_note.config(text='Preços editados manualmente. Esta comparação usa os valores informados por você.')
            args=dict(buy=f['buy'],sell=f['sell'],quantity=f['quantity'],buy_order=f['buy_mode']!='Imediata',sell_order=f['sell_mode']!='Imediata',transport=f['transport'],buy_relists=f['buy_relists'],sell_relists=f['sell_relists'])
            results=[]
            for premium,label in [(True,'Premium'),(False,'Sem Premium')]:
                r=flipping(**args,premium=premium)
                results.append(r)
            fill_results(self.flip_table,[(label,fmt(results[0][key]),fmt(results[1][key])) for key,label,fmt in [
                ('net','Lucro líquido calculado',money),('unit_net','Lucro por unidade',money),('roi','Retorno sobre o custo',lambda v:f'{v:.1%}'),
                ('cost','Investimento inicial (inclui transporte)',money),('revenue','Receita bruta de venda',money),
                ('break_even','Venda de equilíbrio / un.',money),('sale_tax','Imposto sobre a venda',money),
                ('buy_fee','Criação de ordem de compra',money),('sell_fee','Criação de ordem de venda',money)]])
            known=self.flip_observation
            volume=f'Volume observado: até {known[3]} un.' if known and f['buy']==known[0] and f['sell']==known[1] and f['buy_mode']=='Imediata' and f['sell_mode']=='Imediata' else 'Volume disponível não confirmado.'
            self.flip_result.config(text=f"Lote: {f['quantity']} un. · Transporte total: {money(float(f['transport'].replace(',','.')))} prata · {volume}\nResultado estimado; ordens dependem de execução.")
        except ValueError as e:
            self.flip_result.config(text=str(e));fill_results(self.flip_table,[])
        try:
            f={k:v.get() for k,v in self.craft_fields.items()}
            materials=[]
            for _,m in self.materials:
                if m['code'].get().strip():materials.append({k:v.get() for k,v in m.items()})
            args=dict(materials=materials,crafts=f['crafts'],output_per_craft=f['output'],sell=f['sell'],return_rate=f['rrr'],buy_order=f['buy_mode']!='Imediata',sell_order=f['sell_mode']!='Imediata',station=f['station'],transport=f['transport'],other=f['other'],journal_credit=f['journal'],focus_points=f['focus'],focus_value=f['focus_value'])
            lines=[]
            for premium,label in [(True,'Premium'),(False,'Sem Premium')]:
                r=crafting(**args,premium=premium)
                lines.append(r)
            fill_results(self.craft_table,[(label,money(lines[0][key]),money(lines[1][key])) for key,label in [
                ('net','Lucro econômico esperado'),('cash','Saldo calculado após venda'),('upfront','Desembolso inicial'),
                ('gross','Materiais brutos'),('returned','Recursos devolvidos (valor esperado)'),('unit_cost','Custo econômico / un.'),
                ('break_even','Venda de equilíbrio / un.'),('sale_tax','Imposto sobre a venda'),('sell_fee','Criação de ordem de venda')]])
            self.craft_result.config(text=f"Produção: {int(r['output'])} itens · Compra de materiais: criação de ordem {money(r['buy_fee'])}")
        except ValueError as e:
            self.craft_result.config(text=str(e));fill_results(self.craft_table,[])
