"""Busca no catálogo completo de itens negociáveis; consulta de preços somente ao selecionar."""
import tkinter as tk
from tkinter import ttk
from market_view import QUALITY, folded, item_search_text, item_tier, item_enchant
from ui_design import close_on_escape


def search_catalog(codes, catalog, query, tier='Todos', enchant='Todos'):
    """Filtra códigos do catálogo por texto, tier e encantamento, ordenados por nome."""
    words = folded(query).split()
    matches = [c for c in codes
               if (not words or all(w in item_search_text(c, catalog.item(c)) for w in words))
               and (tier == 'Todos' or item_tier(c) == tier)
               and (enchant == 'Todos' or item_enchant(c) == enchant)]
    return sorted(matches, key=lambda c: (catalog.item(c), c))


class CatalogSearch:
    def choose_market_item(self):
        dialog=tk.Toplevel(self.root)
        dialog.title('Pesquisar itens do mercado');dialog.geometry('900x600');dialog.transient(self.root)
        frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Busque qualquer item negociável (equipamento, recurso, refinado, consumível, montaria...) '
                             'por nome, código, tier ou encantamento. Preços consultados nas oito cidades após selecionar.',
                  wraplength=850).pack(anchor='w')
        controls=ttk.Frame(frame);controls.pack(fill='x',pady=8)
        query=tk.StringVar(value=self.filters['query'].get())
        entry=ttk.Entry(controls,textvariable=query,width=40);entry.pack(side='left');entry.focus_set()
        ttk.Label(controls,text='Tier').pack(side='left',padx=(12,4))
        tier=tk.StringVar(value='Todos')
        ttk.Combobox(controls,textvariable=tier,values=['Todos']+list('12345678'),width=6,state='readonly').pack(side='left')
        ttk.Label(controls,text='Encantamento').pack(side='left',padx=(12,4))
        enchant=tk.StringVar(value='Todos')
        ttk.Combobox(controls,textvariable=enchant,values=['Todos','0','1','2','3','4'],width=6,state='readonly').pack(side='left')
        ttk.Label(controls,text='Qualidade').pack(side='left',padx=(12,4))
        quality=tk.StringVar(value='1 · Normal')
        ttk.Combobox(controls,textvariable=quality,values=[f'{q} · {name}' for q,name in QUALITY.items()],width=14,state='readonly').pack(side='left')
        status=ttk.Label(frame);status.pack(anchor='w',pady=6)
        if self.catalog.errors:
            status.config(text='Catálogo indisponível: '+', '.join(self.catalog.errors))
        table=self.make_table(frame,None,[('Item',420),('Código',300)])
        codes=self.catalog.market_codes
        state={'matches':[],'shown':0,'timer':None}
        def more():
            end=min(state['shown']+100,len(state['matches']))
            for code in state['matches'][state['shown']:end]:
                table.insert('', 'end',iid=code,values=(self.catalog.item(code),code))
            state['shown']=end
            status.config(text=f"{len(state['matches'])} encontrados · {end} exibidos. Use Carregar mais para continuar.")
        def search():
            state['timer']=None
            state['matches']=search_catalog(codes,self.catalog,query.get(),tier.get(),enchant.get())
            state['shown']=0
            children=table.get_children()
            if children:table.delete(*children)
            more()
        def schedule(*args):
            if state['timer'] is not None:dialog.after_cancel(state['timer'])
            state['timer']=dialog.after(180,search)
        def close():
            if state['timer'] is not None:dialog.after_cancel(state['timer'])
            dialog.destroy()
        def select(event=None):
            selected=table.selection()
            if not selected:return
            self.select_catalog_item(selected[0],int(quality.get().split(' · ')[0]))
            close()
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=8)
        ttk.Button(buttons,text='Consultar preços',command=select).pack(side='left')
        ttk.Button(buttons,text='Carregar mais',command=more).pack(side='left',padx=8)
        table.bind('<Double-1>',select);entry.bind('<Return>',lambda e:search())
        query.trace_add('write',schedule)
        tier.trace_add('write',lambda *a:search());enchant.trace_add('write',lambda *a:search())
        dialog.protocol('WM_DELETE_WINDOW',close)
        close_on_escape(dialog,close)
        search()

    def select_catalog_item(self,code,quality):
        enchant=int(code.split('@',1)[1]) if '@' in code else 0
        self.selected_variant=(code,quality,enchant)
        self.catalog_selection=self.selected_variant
        self.price_api.request(self.selected_variant)
        self.notebook.select(self.overview)
        self.draw_chart()
