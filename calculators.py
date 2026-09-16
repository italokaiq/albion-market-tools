import json
import time
import tkinter as tk
from tkinter import ttk, simpledialog
from economics import flipping, crafting
from trading import CITIES, selected_item_margin
from ui_design import disclosure,result_table,fill_results
from craft_prices import CraftPrices
from history import History
from recipe_library import RecipeLibrary
from paths import data_path


def money(v):
    return f'{v:,.2f}'.replace(',','_').replace('.',',').replace('_','.')


class Calculators(CraftPrices):
    def __init__(self,app):
        self.app=app
        self.saved=data_path('receita_craft.json')
        self.history=History()
        self.library=RecipeLibrary()
        self.flip_fields={}
        self.craft_fields={}
        self.materials=[]
        from recipes import RecipeCatalog
        self.recipes=RecipeCatalog(app.catalog)
        self.recipe_code=None
        self.production_planner=None
        self.upgrade_flip_planner=None
        self.flip_observation=None
        self.init_prices()
        self.flip=ttk.Frame(app.notebook,padding=12)
        app.notebook.add(self.flip,text='Calculadora de flipping')
        shell=ttk.Frame(app.notebook)
        app.notebook.add(shell,text='Calculadora de craft')
        canvas=tk.Canvas(shell,highlightthickness=0,background='#171310')
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
            ttk.Label(block,text=label,foreground='#B3A78C').pack(anchor='w',pady=(0,5))
            v=tk.StringVar(value=default);target[key]=v
            if options:
                widget=ttk.Combobox(line,textvariable=v,values=options,state='readonly',width=18)
            else:
                widget=ttk.Entry(line,textvariable=v,width=14)
            widget.pack(in_=block,fill='x')

    def make_flip(self):
        ttk.Label(self.flip,text='Calcule a operação antes de comprar.',font=('Segoe UI',12),foreground='#B3A78C').pack(anchor='w',pady=(0,12))
        self.fields(self.flip,self.flip_fields,[('buy','Compra/un.','',None),('sell','Venda/un.','',None),('quantity','Quantidade','1',None)])
        self.fields(self.flip,self.flip_fields,[('buy_mode','Comprar','Imediata',['Imediata','Ordem de compra']),('sell_mode','Vender','Imediata',['Imediata','Ordem de venda'])])
        advanced=disclosure(self.flip,'Transporte e recriação de ordens')
        self.fields(advanced,self.flip_fields,[('transport','Transporte total','0',None),('buy_relists','Recriações compra','0',None),('sell_relists','Recriações venda','0',None)])
        route_buttons=ttk.Frame(self.flip);route_buttons.pack(anchor='w')
        ttk.Button(route_buttons,text='Usar rota selecionada',command=self.use_route).pack(side='left')
        ttk.Button(route_buttons,text='Registrar operação',command=self.record_flip).pack(side='left',padx=8)
        ttk.Button(route_buttons,text='Flip de upgrade de encantamento',command=self.open_upgrade_flip_planner).pack(side='left',padx=8)
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
                  wraplength=1050,font=('Segoe UI',11,'bold'),foreground='#D4AF37').pack(anchor='w',pady=(0,12))
        chooser=ttk.Frame(self.craft);chooser.pack(fill='x',pady=(0,10))
        ttk.Button(chooser,text='Escolher equipamento pelo nome',command=self.choose_equipment).pack(side='left')
        ttk.Button(chooser,text='Comparar compra, refino e cidades',command=self.open_production_planner).pack(side='left',padx=8)
        self.recipe_title=ttk.Label(chooser,text='Selecione para preencher a receita.',foreground='#B3A78C',wraplength=650)
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
        for label,callback in [('Adicionar material',self.add_material),('Buscar preços recentes',self.load_prices),('Salvar receita como...',self.save_recipe_as),('Minhas receitas',self.open_recipe_library),('Registrar operação',self.record_craft)]:
            ttk.Button(buttons,text=label,command=callback).pack(side='left',padx=(0,8))
        self.craft_note=ttk.Label(self.craft,text='Informe a receita do jogo. Preços ausentes bloqueiam o cálculo; não são tratados como zero.',wraplength=1180)
        self.craft_note.pack(anchor='w')
        self.price_status=ttk.Label(self.craft,text='Preços digitados manualmente são informados por você, não verificados pelo app.',wraplength=1000,foreground='#B3A78C')
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
        name=ttk.Label(outer,text='',foreground='#B3A78C');name.pack(anchor='w')
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
        listing=tk.Listbox(panel,background='#221D17',foreground='#EDE6D6',selectbackground='#6B4F23',font=('Segoe UI',11),exportselection=False)
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

    def open_upgrade_flip_planner(self):
        if self.upgrade_flip_planner is None:
            from upgrade_flip_ui import UpgradeFlipPlanner
            self.upgrade_flip_planner=UpgradeFlipPlanner(self)
        self.upgrade_flip_planner.open()

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
        if route:
            quantity=route['quantity'] if route['quantity'] is not None else 1
            try:
                transport=str(float(self.app.transport.get().replace(',','.'))*quantity)
                transport_warning=''
            except ValueError:
                transport='0'
                transport_warning=' Transporte por unidade inválido no painel principal — usado 0 aqui; corrija o campo e copie a rota novamente.'
            for key,value in [('buy',route['buy']['price']),('sell',route['sell']['price']),('quantity',quantity),('buy_mode','Imediata'),('sell_mode','Imediata'),('transport',transport)]:
                self.flip_fields[key].set(value)
            self.flip_observation=(self.flip_fields['buy'].get(),self.flip_fields['sell'].get(),
                                   min(route['buy']['seen'],route['sell']['seen']),route['quantity'])
            unknown=' Volume desconhecido (via API): sem garantia de execução ou de lote disponível.' if route['quantity'] is None else ''
            self.flip_note.config(text=f"{route['code']} · {route['quality_name']} · {route['origin']} para {route['destination']} · Copiado às {time.strftime('%H:%M:%S')}. Preços válidos até o limite de idade configurado.{unknown}{transport_warning}")
            return
        self.use_reference_margin()

    def use_reference_margin(self):
        """Sem rota com volume conhecido do fluxo: usa a mesma margem do gráfico (pode incluir API, sem volume)."""
        variant=self.app.selected_markets()
        margin=None
        if variant:
            try:
                margin=selected_item_margin(variant['markets'],float(self.app.tax.get().replace(',','.'))/100,
                    float(self.app.transport.get().replace(',','.')),int(self.app.filters['minutes'].get())*60,time.time())
            except ValueError:margin=None
        if margin is None:
            self.flip_observation=None
            self.flip_fields['buy'].set('');self.flip_fields['sell'].set('')
            self.flip_note.config(text='Não há rota com preços e volume conhecidos para este item. A API não informa quantidade; consulte uma rota coletada ou informe preços manualmente.')
            return
        cities=dict(CITIES)
        buy_price=variant['markets'][margin['origin']]['offer']
        sell_price=variant['markets'][margin['destination']]['request']
        quantity=margin['quantity'] or 1
        for key,value in [('buy',buy_price['price']),('sell',sell_price['price']),('quantity',quantity),('buy_mode','Imediata'),('sell_mode','Imediata')]:
            self.flip_fields[key].set(value)
        self.flip_fields['transport'].set(str(float(self.app.transport.get().replace(',','.'))*quantity))
        self.flip_observation=(self.flip_fields['buy'].get(),self.flip_fields['sell'].get(),
                               min(buy_price['seen'],sell_price['seen']),margin['quantity'])
        unknown=' Volume desconhecido: preço vem da API, sem garantia de execução.' if margin['quantity'] is None else ''
        self.flip_note.config(text=f"Simulação de referência (mesma margem do gráfico): {cities.get(margin['origin'],margin['origin'])} → "
            f"{cities.get(margin['destination'],margin['destination'])} · Copiado às {time.strftime('%H:%M:%S')}.{unknown}")

    def record_flip(self):
        """Registra a operação calculada no histórico, com os mesmos valores usados no cálculo exibido."""
        f={k:v.get() for k,v in self.flip_fields.items()}
        try:
            result=flipping(buy=f['buy'],sell=f['sell'],quantity=f['quantity'],
                buy_order=f['buy_mode']!='Imediata',sell_order=f['sell_mode']!='Imediata',
                transport=f['transport'],buy_relists=f['buy_relists'],sell_relists=f['sell_relists'],
                premium=self.app.profile.get()=='Premium')
        except ValueError as e:
            self.flip_note.config(text='Não é possível registrar: '+str(e));return
        item=self.app.selected_variant
        predicted=dict(buy=f['buy'],sell=f['sell'],quantity=f['quantity'],transport=f['transport'],
            buy_mode=f['buy_mode'],sell_mode=f['sell_mode'],buy_relists=f['buy_relists'],sell_relists=f['sell_relists'],
            profile=self.app.profile.get(),net=result['net'],unit_net=result['unit_net'])
        try:
            self.history.add(dict(kind='flipping',item=item[0] if item else None,
                quality=item[1] if item else None,enchantment=item[2] if item else None,
                label=self.app.catalog.item(item[0]) if item else 'Item não identificado',predicted=predicted))
        except (OSError,ValueError) as e:
            self.flip_note.config(text='Não foi possível salvar o histórico: '+str(e));return
        self.flip_note.config(text=f'Operação registrada no histórico às {time.strftime("%H:%M:%S")}. '
            f'Lucro previsto: {money(result["net"])} prata. Confirme a execução depois em Histórico.')

    def migrate_legacy_recipe(self):
        """Importa a única receita salva no formato antigo (uma por vez) para a biblioteca, uma vez só."""
        if not self.saved.exists():return
        try:
            data=json.loads(self.saved.read_text(encoding='utf-8'))
            product=data.get('fields',{}).get('code','').strip()
            base_name=self.app.catalog.item(product) if product else 'Receita importada'
            existing=self.library.read()['recipes']
            name=base_name;n=2
            while name in existing:name=f'{base_name} ({n})';n+=1
            self.library.save(name,data['fields'],data['materials'])
            self.saved.rename(self.saved.with_suffix('.json.migrated'))
        except (OSError,ValueError,KeyError,TypeError):
            pass

    def save_recipe_as(self):
        default=self.app.catalog.item(self.craft_fields['code'].get()) if self.craft_fields['code'].get().strip() else ''
        name=simpledialog.askstring('Salvar receita','Nome para esta receita:',initialvalue=default,parent=self.app.root)
        if not name:return
        fields={k:v.get() for k,v in self.craft_fields.items()}
        materials=[{k:v.get() for k,v in m.items()} for _,m in self.materials]
        try:
            self.library.save(name,fields,materials)
            self.craft_note.config(text=f'Receita "{name}" salva na biblioteca. Preços não são salvos.')
        except (OSError,ValueError) as e:
            self.craft_note.config(text='Não foi possível salvar: '+str(e))

    def apply_saved_recipe(self,name):
        recipe=self.library.load(name)
        for k,v in recipe['fields'].items():
            if k in self.craft_fields:self.craft_fields[k].set(v)
        for row,m in list(self.materials):self.remove_material(row,m)
        for m in recipe['materials']:
            self.add_material()
            for k,v in m.items():
                if k in self.materials[-1][1]:self.materials[-1][1][k].set(v)
            self.materials[-1][1]['price'].set('')
        self.craft_fields['sell'].set('')
        self.craft_fields['station'].set('')
        self.craft_fields['rrr'].set('')
        self.recipe_code=None
        self.recipe_options.pack_forget()
        self.recipe_title.configure(text=f'Receita salva "{name}": '+self.app.catalog.item(self.craft_fields['code'].get()))
        self.craft_note.config(text='Receita carregada. Busque ou informe os preços atuais.')

    def open_recipe_library(self):
        self.migrate_legacy_recipe()
        dialog=tk.Toplevel(self.app.root);dialog.title('Minhas receitas salvas');dialog.geometry('640x440')
        dialog.transient(self.app.root)
        frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Receitas salvas neste computador. Preços não são salvos; busque-os novamente ao carregar.',
                  wraplength=600).pack(anchor='w')
        table=self.app.make_table(frame,None,[('Nome',230),('Produto',230),('Salva em',140)])
        status=ttk.Label(frame,wraplength=600);status.pack(anchor='w',pady=6)
        def refresh():
            try:recipes=self.library.read()['recipes']
            except (OSError,ValueError) as e:status.config(text=str(e));return
            rows=[]
            for name,r in sorted(recipes.items()):
                product=r.get('fields',{}).get('code','')
                label=self.app.catalog.item(product) if product else '—'
                when=r.get('saved_at','')[:16].replace('T',' ')
                rows.append((name,(name,label,when),'fresh'))
            from market_view import sync_table
            sync_table(table,rows)
            status.config(text=f'{len(recipes)} receita(s) salva(s).' if recipes else 'Nenhuma receita salva ainda.')
        def load_selected():
            selection=table.selection()
            if not selection:return
            try:
                self.apply_saved_recipe(selection[0]);dialog.destroy()
            except (OSError,ValueError,KeyError) as e:status.config(text=str(e))
        def rename_selected():
            selection=table.selection()
            if not selection:return
            new_name=simpledialog.askstring('Renomear receita','Novo nome:',initialvalue=selection[0],parent=dialog)
            if not new_name:return
            try:self.library.rename(selection[0],new_name);refresh()
            except (OSError,ValueError,KeyError) as e:status.config(text=str(e))
        def delete_selected():
            selection=table.selection()
            if not selection:return
            try:self.library.delete(selection[0]);refresh()
            except (OSError,ValueError,KeyError) as e:status.config(text=str(e))
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=8)
        ttk.Button(buttons,text='Carregar',command=load_selected).pack(side='left')
        ttk.Button(buttons,text='Renomear',command=rename_selected).pack(side='left',padx=8)
        ttk.Button(buttons,text='Remover',command=delete_selected).pack(side='left')
        table.bind('<Double-1>',lambda e:load_selected())
        refresh()

    def record_craft(self):
        """Registra a operação de craft calculada no histórico, com os mesmos valores usados no cálculo exibido."""
        f={k:v.get() for k,v in self.craft_fields.items()}
        materials=[{k:v.get() for k,v in m.items()} for _,m in self.materials if m['code'].get().strip()]
        try:
            result=crafting(materials=materials,crafts=f['crafts'],output_per_craft=f['output'],sell=f['sell'],
                return_rate=f['rrr'],buy_order=f['buy_mode']!='Imediata',sell_order=f['sell_mode']!='Imediata',
                station=f['station'],transport=f['transport'],other=f['other'],journal_credit=f['journal'],
                focus_points=f['focus'],focus_value=f['focus_value'],premium=self.app.profile.get()=='Premium')
        except ValueError as e:
            self.craft_note.config(text='Não é possível registrar: '+str(e));return
        predicted=dict(crafts=f['crafts'],output=result['output'],net=result['net'],cash=result['cash'],
            upfront=result['upfront'],revenue=result['revenue'],profile=self.app.profile.get())
        try:
            self.history.add(dict(kind='craft',product=f['code'],quality=f['quality'],
                label=self.app.catalog.item(f['code']) if f['code'].strip() else 'Item não identificado',
                predicted=predicted))
        except (OSError,ValueError) as e:
            self.craft_note.config(text='Não foi possível salvar o histórico: '+str(e));return
        self.craft_note.config(text=f'Operação registrada no histórico às {time.strftime("%H:%M:%S")}. '
            f'Lucro econômico previsto: {money(result["net"])} prata. Confirme a execução depois em Histórico.')

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
                    if volume is not None and f['buy_mode']=='Imediata' and f['sell_mode']=='Imediata' and float(f['quantity'].replace(',','.'))>volume:
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
            matches_known=known and f['buy']==known[0] and f['sell']==known[1] and f['buy_mode']=='Imediata' and f['sell_mode']=='Imediata'
            if matches_known and known[3] is not None:volume=f'Volume observado: até {known[3]} un.'
            elif matches_known:volume='Volume desconhecido (referência via API); sem garantia de execução.'
            else:volume='Volume disponível não confirmado.'
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
