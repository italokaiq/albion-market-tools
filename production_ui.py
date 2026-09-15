"""Planejador de compra, refino, craft e venda integrado à tela de craft."""
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from market_view import age_text
from price_lookup import observed_price
from production import refining_recipes,dependency_codes,plan_production,PRODUCTION_CITIES
from trading import CITIES
from calculators import money
from production_profiles import ProductionProfiles

class ProductionPlanner:
    def __init__(self,calculator):
        self.c=calculator;self.app=calculator.app;self.window=None;self.jobs=queue.Queue()
        self.recipes=refining_recipes();self.generation=0;self.busy=False;self.last_request=0
        self.data={};self.rows=[];self.settings={};self.timer=None
        self.api_error='';self.pending_fetch=False;self.last_age=None;self.last_price_update=None
        self.profiles=ProductionProfiles();self.profile_pending=False

    def signature(self):
        c=self.c
        return tuple(c.craft_fields[k].get() for k in ('code','crafts','output','quality','buy_mode','sell_mode'))+tuple((m['code'].get(),m['quantity'].get(),m['returns'].get()) for _,m in c.materials)+(self.app.profile.get(),)

    def close(self):
        if self.window is not None:
            self.save_stage();self.saved_shipping=self.shipping.get()
        if self.timer is not None:self.app.root.after_cancel(self.timer);self.timer=None
        if self.window is not None:self.window.destroy();self.window=None
        self.generation+=1

    def open(self):
        same_context=getattr(self,'context',None)==self.signature()
        saved_shipping=getattr(self,'saved_shipping','') if same_context else ''
        if same_context and self.window is not None:
            self.save_stage();saved_shipping=self.shipping.get()
        self.close();self.context=self.signature();self.rows=[]
        if not same_context:self.settings={}
        if not same_context:self.profile_pending=False
        self.f={k:v.get() for k,v in self.c.craft_fields.items()}
        self.materials=[dict(code=m['code'].get().strip().upper(),quantity=m['quantity'].get(),returns=m['returns'].get()) for _,m in self.c.materials if m['code'].get().strip()]
        self.by_code={}
        self.product=self.f['code'].strip().upper()
        if not self.product or not self.materials:
            self.c.craft_note.config(text='Escolha um equipamento e sua receita antes de comparar a cadeia.');return
        self.codes=dependency_codes(self.materials,self.recipes)|{self.product}
        self.window=tk.Toplevel(self.app.root);self.window.title('Planejar compra, refino, craft e venda');self.window.geometry('1150x800')
        self.window.minsize(1000,720)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        frame=ttk.Frame(self.window,padding=14);frame.pack(fill='both',expand=True)
        title=f"{self.app.catalog.item(self.product)} · {self.f['crafts']} crafts · Qualidade {self.f['quality']} · {self.app.profile.get()}"
        ttk.Label(frame,text=title,font=('Segoe UI',13,'bold')).pack(anchor='w')
        ttk.Label(frame,text=f"Materiais: {self.f['buy_mode']} · Venda: {self.f['sell_mode']} · Preços anunciados observados via AODP, não vendas concluídas.").pack(anchor='w')
        toolbar=ttk.Frame(frame);toolbar.pack(fill='x',pady=8)
        ttk.Button(toolbar,text='Atualizar preços e comparar',command=self.fetch).pack(side='left')
        ttk.Label(toolbar,text='Transporte (prata/un. por trecho entre cidades)').pack(side='left',padx=8)
        self.shipping=tk.StringVar(value=saved_shipping);ttk.Entry(toolbar,textvariable=self.shipping,width=10).pack(side='left')
        ttk.Label(toolbar,text='Idade máx. (min)').pack(side='left',padx=8)
        ttk.Combobox(toolbar,textvariable=self.app.filters['minutes'],values=('5','15','30','60','240','1440'),state='readonly',width=6).pack(side='left')
        self.status=ttk.Label(frame,wraplength=1080);self.status.pack(anchor='w',pady=5)
        summary=ttk.Frame(frame,padding=10);summary.pack(fill='x',pady=6)
        self.recommendation=ttk.Label(summary,text='Ainda sem recomendação — preencha os custos em Custos e retornos.',
                                       font=('Segoe UI',13,'bold'),wraplength=1020)
        self.recommendation.pack(anchor='w')
        ttk.Label(summary,text='O que falta / próximo passo',foreground='#B3A78C').pack(anchor='w',pady=(8,0))
        self.next_step=ttk.Label(summary,text='1. Consulte preços → 2. Confirme custos → 3. Compare as alternativas.',wraplength=1020)
        self.next_step.pack(anchor='w',pady=3)
        tabs=ttk.Notebook(frame);tabs.pack(fill='both',expand=True)
        self.tabs=tabs
        settings_shell=ttk.Frame(tabs);tabs.add(settings_shell,text='1. Custos e retornos')
        settings_canvas=tk.Canvas(settings_shell,highlightthickness=0,background='#171310')
        settings_scroll=ttk.Scrollbar(settings_shell,command=settings_canvas.yview)
        settings_canvas.configure(yscrollcommand=settings_scroll.set)
        settings_scroll.pack(side='right',fill='y');settings_canvas.pack(side='left',fill='both',expand=True)
        settings=ttk.Frame(settings_canvas,padding=10)
        settings_window=settings_canvas.create_window((0,0),window=settings,anchor='nw')
        settings.bind('<Configure>',lambda e:settings_canvas.configure(scrollregion=settings_canvas.bbox('all')))
        settings_canvas.bind('<Configure>',lambda e:settings_canvas.itemconfigure(settings_window,width=e.width))
        profile_bar=ttk.Frame(settings);profile_bar.pack(fill='x',pady=5)
        self.profile_name=tk.StringVar()
        self.profile_box=ttk.Combobox(profile_bar,textvariable=self.profile_name,width=28)
        self.profile_box.pack(side='left')
        ttk.Button(profile_bar,text='Salvar perfil',command=self.save_profile).pack(side='left',padx=5)
        ttk.Button(profile_bar,text='Carregar perfil',command=self.load_profile).pack(side='left')
        self.profile_message=ttk.Label(settings,wraplength=1000);self.profile_message.pack(anchor='w')
        self.refresh_profiles()
        ttk.Label(settings,text='Informe valores exibidos no jogo para cada cidade que deseja avaliar. Campos vazios excluem a etapa.\nRetorno (%) já deve incluir bônus local, bônus diário e Foco, se usado. Taxa da estação em prata por operação, não por nutrição.\nTransporte é um custo informado uniforme por unidade transferida. Ajuste para a sua logística. Foco/diários não são monetizados neste comparador.',wraplength=1020).pack(anchor='w')
        self.stages=['craft']+sorted(c for c in self.codes if c in self.recipes)
        self.stage=tk.StringVar(value='craft');stage_names=['Craft do equipamento']+[self.app.catalog.item(c)+' · '+c for c in self.stages[1:]]
        self.stage_box=ttk.Combobox(settings,values=stage_names,state='readonly',width=80);self.stage_box.current(0);self.stage_box.pack(anchor='w',pady=10)
        self.editors={};grid=ttk.Frame(settings);grid.pack(anchor='w')
        for col,label in enumerate(['Cidade','Retorno real (%)','Estação (prata/operação)']):ttk.Label(grid,text=label).grid(row=0,column=col,padx=8,pady=5)
        for row,(city,name) in enumerate(PRODUCTION_CITIES,1):
            ttk.Label(grid,text=name).grid(row=row,column=0,sticky='w',padx=8)
            variables=[tk.StringVar(value=v) for v in self.settings.get(('craft',city),('',''))];self.editors[city]=variables
            for col,var in enumerate(variables,1):ttk.Entry(grid,textvariable=var,width=24).grid(row=row,column=col,padx=8,pady=4)
        self.stage_box.bind('<<ComboboxSelected>>',self.change_stage)
        ttk.Button(settings,text='Confirmar custos e comparar',command=self.confirm_costs).pack(anchor='w',pady=10)
        self.route_table=self.app.make_table(tabs,'2. Craft e venda',[('Craftar em',140),('Vender em',140),('Lucro esperado',140),('Custo econômico',145),('Desembolso bruto¹',145),('Idade',85),('Cobertura de volume',150)])
        self.route_table.tag_configure('shortfall',foreground='#E8C766')
        ttk.Button(summary,text='Ver comparação',command=lambda:tabs.select(1)).pack(anchor='w')
        self.supply_table=self.app.make_table(tabs,'3. Comprar ou refinar',[('Material',235),('Entregar em',130),('Alternativa',130),('Comprar/refinar em',150),('Custo/un.',100),('Desembolso/un.¹',140)])
        self.market_table=self.app.make_table(tabs,'4. Preços observados',[('Item',290),('Cidade',130),('Lado',100),('Prata/un.',100),('Idade',85),('Fonte / volume',170)])
        detail_frame=ttk.Frame(frame);detail_frame.pack(fill='x',pady=6)
        self.detail=tk.Text(detail_frame,height=6,wrap='word',background='#221D17',foreground='#EDE6D6');self.detail.pack(side='left',fill='x',expand=True)
        detail_scroll=ttk.Scrollbar(detail_frame,command=self.detail.yview);detail_scroll.pack(side='right',fill='y');self.detail.configure(yscrollcommand=detail_scroll.set)
        self.detail.insert('1.0','Selecione uma rota para ver a cadeia de materiais.\n¹ Desembolso bruto sem reutilizar retornos. Retornos e custos unitários são expectativas; não garantem volume, execução ou lucro.');self.detail.config(state='disabled')
        self.route_table.bind('<<TreeviewSelect>>',self.show_route)
        self.result=None;self.last_render=None
        self.fetch();self.poll()

    def save_stage(self):
        for city,variables in self.editors.items():
            values=tuple(v.get().strip() for v in variables)
            if any(values):self.settings[(self.stage.get(),city)]=values
            else:self.settings.pop((self.stage.get(),city),None)

    def refresh_profiles(self):
        try:self.profile_box.configure(values=sorted(self.profiles.read()['profiles']))
        except (OSError,ValueError,TypeError) as error:self.profile_message.config(text='Não foi possível ler perfis: '+str(error))

    def save_profile(self):
        try:
            self.save_stage()
            self.profiles.save(self.profile_name.get(),self.context,self.settings,self.shipping.get())
            self.refresh_profiles();self.profile_message.config(text='Perfil salvo sem preços. A versão anterior fica no arquivo de backup.')
        except (OSError,ValueError,TypeError) as error:self.profile_message.config(text=str(error))

    def load_profile(self):
        try:
            settings,shipping,saved=self.profiles.load(self.profile_name.get(),self.context)
            self.settings=settings;self.shipping.set(shipping);self.profile_pending=True
            for city,variables in self.editors.items():
                for var,value in zip(variables,settings.get((self.stage.get(),city),('',''))):var.set(value)
            self.profile_message.config(text=f'Perfil salvo em {saved[:10]}. Confira os custos no jogo e clique Confirmar custos e comparar.')
            self.calculate()
        except (OSError,ValueError,TypeError,KeyError) as error:self.profile_message.config(text='Não foi possível carregar: '+str(error))

    def confirm_costs(self):
        self.profile_pending=False
        self.calculate()

    def change_stage(self,event=None):
        self.save_stage();self.stage.set(self.stages[self.stage_box.current()])
        for city,variables in self.editors.items():
            for var,value in zip(variables,self.settings.get((self.stage.get(),city),('',''))):var.set(value)

    def refresh_local_rows(self):
        marks=','.join('?' for _ in self.codes)
        self.rows=self.app.con.execute('SELECT * FROM orders WHERE item IN ('+marks+') AND seen>=?',[*self.codes,time.time()-int(self.app.filters['minutes'].get())*60]).fetchall()
        self.by_code={}
        for row in self.rows:self.by_code.setdefault(row[2],[]).append(row)

    def fetch(self):
        if self.context!=self.signature():self.status.config(text='Receita, lote ou perfil mudou. Reabra o comparador para atualizar.');return
        self.refresh_local_rows()
        self.calculate()
        if not self.app.export_enabled:return
        if self.busy or time.time()-self.last_request<60:
            self.pending_fetch=True
            self.status.config(text='Preços locais atualizados. Aguarde até 60s entre consultas da API.');return
        self.pending_fetch=False;self.api_error=''
        self.busy=True;self.last_request=time.time();generation=self.generation;codes=sorted(self.codes)
        self.status.config(text='Consultando produto, materiais e matérias-primas nas cidades das Américas…')
        def worker():
            data={}
            try:
                data=self.app.market_service.get_many(codes)
                self.jobs.put((generation,data,None))
            except Exception as error:self.jobs.put((generation,None,type(error).__name__))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        if self.window is None:return
        try:
            while True:
                generation,data,error=self.jobs.get_nowait();self.busy=False
                if generation!=self.generation:continue
                if error:
                    self.api_error='Falha na API: '+error+'.'
                    self.calculate()
                else:self.data=data;self.last_price_update=time.time();self.calculate()
        except queue.Empty:pass
        if self.context!=self.signature():
            self.result=None
            for table in (self.route_table,self.supply_table,self.market_table):
                if table.get_children():table.delete(*table.get_children())
            self.set_detail('Receita, lote ou perfil mudou. Reabra o comparador.')
            self.status.config(text='Comparação invalidada: reabra para usar a receita, lote e perfil atuais.')
            self.next_step.config(text='A receita, o lote ou o perfil mudou. Reabra o planejador para atualizar a comparação.')
        elif self.pending_fetch and not self.busy and time.time()-self.last_request>=60:self.fetch()
        elif self.app.export_enabled and not self.busy and time.time()-self.last_request>=60:self.fetch()
        elif self.last_age!=self.app.filters['minutes'].get() or self.last_render is None or time.time()-self.last_render>=5:
            self.refresh_local_rows();self.calculate()
        self.timer=self.app.root.after(1000,self.poll)

    def set_detail(self,text):
        self.detail.config(state='normal');self.detail.delete('1.0','end');self.detail.insert('1.0',text);self.detail.config(state='disabled')

    def timestamps_line(self):
        updated=time.strftime('%H:%M:%S',time.localtime(self.last_price_update)) if self.last_price_update else 'ainda não consultados'
        return f'Recalculado às {time.strftime("%H:%M:%S")} · Preços atualizados às {updated}.'

    def calculate(self):
        if self.window is None or self.context!=self.signature():return
        self.save_stage();now=time.time();self.last_render=now
        self.last_age=self.app.filters['minutes'].get()
        prices={};names=dict(CITIES);age=int(self.app.filters['minutes'].get())*60
        for code in self.codes:
            qualities={1,int(self.f['quality'])} if code==self.product else {1}
            for q in qualities:
                for city,_ in CITIES:
                    for side in ('offer','request'):
                        p=observed_price(self.by_code.get(code,[]),self.data,code,q,city,side,now,age)
                        if p:prices[(code,q,city,side)]=p
        from market_view import sync_table
        sync_table(self.market_table,[(str(key),(self.app.catalog.item(key[0])+f' · Q{key[1]}',names[key[2]],'Oferta' if key[3]=='offer' else 'Pedido',money(p['price']),age_text(p['seen'],now),p['source']+' / '+(str(p['amount']) if p['amount'] is not None else 'desconhecido')),'fresh') for key,p in sorted(prices.items())])
        try:
            if self.profile_pending:raise ValueError('Confirme se os custos do perfil continuam atuais antes de comparar.')
            recipe=self.c.recipes.recipes.get(self.product,[])
            index=self.c.recipe_options.current()
            silver=recipe[index]['silver'] if recipe and index>=0 else 0
            valid={}
            for key,value in self.settings.items():
                if all(value):valid[key]=value
            self.result=plan_production(self.materials,self.recipes,prices,self.product,int(self.f['quality']),self.f['crafts'],self.f['output'],valid,self.shipping.get(),self.app.profile.get()=='Premium',self.f['buy_mode']!='Imediata',self.f['sell_mode']!='Imediata',silver)
        except ValueError as error:
            self.next_step.config(text=str(error)+' Preencha os campos em Custos e retornos; zero só deve ser informado se for sua condição real.')
            self.result=None;self.status.config(text=self.timestamps_line()+' '+self.api_error+' '+str(error)+' Preços disponíveis na aba 4.')
            for table in (self.route_table,self.supply_table):
                if table.get_children():table.delete(*table.get_children())
            self.set_detail('Preencha custos válidos para comparar. Nenhum custo ausente é tratado como zero.');return
        routes=self.result['routes'];supply=self.result['supply']
        def volume_coverage_text(r):
            return 'Completa' if not r['shortfalls'] else f"Parcial: {len(r['shortfalls'])} item(ns) sem volume suficiente"
        def route_tag(r):
            if r['shortfalls']:return 'shortfall'
            return 'fresh' if r['net']>0 else 'old'
        sync_table(self.route_table,[(r['city']+':'+r['destination'],(names[r['city']],names[r['destination']],money(r['net']),money(r['cost']),money(r['cash']),age_text(r['seen'],now),volume_coverage_text(r)),route_tag(r)) for r in routes])
        sync_table(self.supply_table,[(str(i),(self.app.catalog.item(r['material']),names[r['destination']],r['method'],names[r['city']],money(r['cost']),money(r['cash'])),'fresh') for i,r in enumerate(supply)])
        count=sum(('craft',city) in valid for city,_ in PRODUCTION_CITIES)
        ref_count=sum(key[0]!='craft' for key in valid)
        missing=self.result['missing']
        if count==0:
            self.recommendation.config(text='Ainda sem recomendação.',foreground='#B3A78C')
            self.next_step.config(text='Confirme retorno e custo da estação em pelo menos uma cidade de craft. As outras cidades permanecem fora da avaliação.')
        elif missing:
            self.recommendation.config(text='Ainda sem recomendação.',foreground='#B3A78C')
            self.next_step.config(text='Faltam preços para: '+', '.join(self.app.catalog.item(c) for c in missing)+'. Consulte Preços observados ou atualize a coleta.')
        elif not routes:
            self.recommendation.config(text='Ainda sem recomendação.',foreground='#B3A78C')
            self.next_step.config(text='Não há preço de venda recente para concluir a comparação. Confira qualidade, modo de venda e idade máxima.')
        else:
            best=routes[0]
            coverage='Parcial' if count<7 else 'Craft: sete cidades configuradas'
            shortfall_note=''
            if best['shortfalls']:
                items=', '.join(f"{self.app.catalog.item(s['material'])} (precisa {s['required']:g}, disponível {s['available']:g} em {names[s['city']]})" for s in best['shortfalls'])
                shortfall_note=f' Atenção: a melhor opção não tem volume observado suficiente para {items}. Divida a compra entre cidades ou reduza o lote.'
            if best['net']>0:
                self.recommendation.config(text=f"Melhor opção avaliada: craft em {names[best['city']]} → vender em {names[best['destination']]} · "
                    f"lucro econômico esperado {money(best['net'])} prata"+(' · cobertura de volume parcial' if best['shortfalls'] else ''),
                    foreground='#D4AF37')
            else:
                self.recommendation.config(text=f"Nenhuma opção avaliada tem lucro positivo. A menos ruim: craft em {names[best['city']]} → "
                    f"vender em {names[best['destination']]} · {money(best['net'])} prata.",foreground='#D9827E')
            self.next_step.config(text=f"{coverage} · {count}/7 cidades de craft · {ref_count}/{(len(self.stages)-1)*7} etapas/cidades de refino configuradas. "
                +'Selecione uma rota abaixo para conferir a cadeia de custos. Cobertura de preços pode ser incompleta.'
                +shortfall_note)
        self.status.config(text=self.timestamps_line()+' '+self.api_error+f' {len(prices)} preços dentro de {age//60} min · {count}/7 cidades de craft configuradas · {ref_count} etapas/cidades de refino configuradas · {len(routes)} rotas calculáveis. Melhor apenas entre opções com dados e custos preenchidos.')
        if self.route_table.selection():self.show_route()
        elif routes:
            r=routes[0]
            self.route_table.selection_set(r['city']+':'+r['destination'])
            self.show_route()
        else:self.set_detail('Sem rota calculável. Informe retorno e estação para ao menos uma cidade de craft e confira os preços da aba 4. Para comparar refino, configure também as etapas de material. Nenhuma cidade excluída é presumida pior.')

    def show_route(self,event=None):
        selection=self.route_table.selection()
        if not selection or not self.result:return
        route=next((r for r in self.result['routes'] if r['city']+':'+r['destination']==selection[0]),None)
        if route is None:return
        names=dict(CITIES);lines=[]
        def show(option,qty,depth=0):
            lines.append('  '*depth+f"{qty:g} × {self.app.catalog.item(option['code'])}: {option['method']} em {names[option['city']]} · custo econômico/un. {money(option['cost'])}")
            for m,child in option['children']:show(child,qty*m['quantity']/option['output'],depth+1)
        for m,option in route['choices']:show(option,float(self.f['crafts'])*float(m['quantity']))
        lines.append(f"Craft: {names[route['city']]} → Venda: {names[route['destination']]} · {route['sale']['source']} · volume {route['sale']['amount'] if route['sale']['amount'] is not None else 'desconhecido'}")
        if route['shortfalls']:
            lines.append('Cobertura de volume insuficiente nesta rota:')
            for s in route['shortfalls']:
                lines.append(f"  {self.app.catalog.item(s['material'])} em {names[s['city']]}: precisa {s['required']:g}, volume observado {s['available']:g}. "
                              'Divida a compra entre cidades/ordens ou reduza o lote.')
        lines.append('Quantidades brutas sem reutilizar retornos. Confirme disponibilidade no jogo; custos incluem transporte informado, taxas e retorno esperado.')
        self.set_detail('\n'.join(lines))
