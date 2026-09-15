"""Busca no catálogo local completo; consulta de preços somente ao selecionar."""
import tkinter as tk
from tkinter import ttk
from market_view import QUALITY, folded, item_search_text
from trading import equipment

class CatalogSearch:
    def choose_market_item(self):
        dialog=tk.Toplevel(self.root)
        dialog.title('Pesquisar equipamentos');dialog.geometry('850x560');dialog.transient(self.root)
        frame=ttk.Frame(dialog,padding=16);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Busque por nome, código ou tier. Preços consultados após selecionar.').pack(anchor='w')
        query=tk.StringVar(value=self.filters['query'].get())
        entry=ttk.Entry(frame,textvariable=query);entry.pack(fill='x',pady=8);entry.focus_set()
        quality=tk.StringVar(value='1 · Normal')
        ttk.Combobox(frame,textvariable=quality,values=[f'{q} · {name}' for q,name in QUALITY.items()],state='readonly').pack(anchor='w')
        status=ttk.Label(frame);status.pack(anchor='w',pady=6)
        table=self.make_table(frame,None,[('Equipamento',420),('Código',300)])
        codes=sorted((c for c in self.catalog.names if equipment(c)),key=lambda c:(self.catalog.item(c),c))
        texts={c:item_search_text(c,self.catalog.item(c)) for c in codes}
        state={'matches':[],'shown':0,'timer':None}
        def more():
            end=min(state['shown']+100,len(state['matches']))
            for code in state['matches'][state['shown']:end]:
                table.insert('', 'end',iid=code,values=(self.catalog.item(code),code))
            state['shown']=end
            status.config(text=f"{len(state['matches'])} encontrados · {end} exibidos. Use Carregar mais para continuar.")
        def search():
            state['timer']=None
            words=folded(query.get()).split()
            state['matches']=[c for c in codes if all(w in texts[c] for w in words)]
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
        query.trace_add('write',schedule);dialog.protocol('WM_DELETE_WINDOW',close)
        search()

    def select_catalog_item(self,code,quality):
        enchant=int(code.split('@',1)[1]) if '@' in code else 0
        self.selected_variant=(code,quality,enchant)
        self.catalog_selection=self.selected_variant
        self.price_api.request(self.selected_variant)
        self.notebook.select(self.overview)
        self.draw_chart()
