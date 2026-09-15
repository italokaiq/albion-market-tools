"""Consulta de craft sem bloquear Tk e sem aplicar respostas a receitas trocadas."""
import queue
import threading
import time
from price_lookup import observed_price
from trading import CITIES
from market_view import age_text


class CraftPrices:
    def init_prices(self):
        self.price_jobs=queue.Queue()
        self.price_busy=False
        self.price_last=0
        self.price_marks={}
        self.price_details={}
        self.craft_api={}

    def price_context(self):
        return tuple(self.craft_fields[k].get() for k in ('code','city','destination','quality','buy_mode','sell_mode'))+tuple(m['code'].get() for _,m in self.materials)

    def price_targets(self):
        ids={name:id for id,name in CITIES}
        f={k:v.get() for k,v in self.craft_fields.items()}
        targets=[(self.craft_fields['sell'],f['code'].strip().upper(),int(f['quality']),ids[f['destination']],
                  'request' if f['sell_mode']=='Imediata' else 'offer')]
        targets += [(m['price'],m['code'].get().strip().upper(),1,ids[f['city']],
                    'offer' if f['buy_mode']=='Imediata' else 'request') for _,m in self.materials if m['code'].get().strip()]
        return targets

    def apply_prices(self,protected=None):
        now=time.time();ctx=self.price_context()
        targets=self.price_targets()
        codes=sorted({code for _,code,_,_,_ in targets if code})
        max_age=int(self.app.filters['minutes'].get())*60
        rows=self.app.con.execute(
            'SELECT id,location,item,quality,enchantment,side,price,amount,seen FROM orders '
            'WHERE item IN ('+','.join('?' for _ in codes)+') AND seen>=? AND amount>0',
            [*codes,now-max_age]).fetchall() if codes else []
        details=[];missing=[]
        for var,code,q,city,side in targets:
            if protected is not None and var.get()!=protected.get(str(var)):continue
            price=observed_price(rows,self.craft_api,code,q,city,side,now,int(self.app.filters['minutes'].get())*60)
            mark=self.price_marks.get(str(var))
            manual=bool(var.get().strip()) and (mark is None or var.get()!=mark[1])
            if price:var.set(str(price['price']))
            elif not manual:var.set('')
            self.price_marks.pop(str(var),None)
            self.price_details.pop(str(var),None)
            if price:
                self.price_marks[str(var)]=(var,var.get(),price['seen'],ctx)
                self.price_details[str(var)]=dict(price)
                volume='volume desconhecido' if price['amount'] is None else f"qtd. observada {price['amount']}"
                details.append(f"{self.app.catalog.item(code)}: {price['source']}, {age_text(price['seen'],now)}, {volume}")
            else:
                label=self.app.catalog.item(code) if code else 'produto final'
                missing.append(label)
                if manual:details.append(f'{label}: valor manual preservado, não verificado pela coleta.')
        self.craft_note.config(text=('Sem preço recente: '+', '.join(missing)+'. ' if missing else '')+'Preços de referência; confira quantidade antes de negociar.')
        self.price_status.config(text='\n'.join(details))
        self.update_price_status()

    def update_price_status(self):
        """Idades e limite visíveis acompanham o relógio, sem nova consulta."""
        now=time.time();minutes=int(self.app.filters['minutes'].get())
        lines=[f'Preços anunciados observados · limite: {minutes} min. Não exigem venda concluída.']
        for var,code,q,city,side in self.price_targets():
            if not code:continue
            label=self.app.catalog.item(code)
            mark=self.price_marks.get(str(var))
            price=self.price_details.get(str(var))
            if mark and var.get()==mark[1] and price:
                volume='volume desconhecido' if price['amount'] is None else f"qtd. observada {price['amount']}"
                order='oferta de venda' if side=='offer' else 'pedido de compra'
                lines.append(f"{label}: {order}, {price['source']}, {age_text(price['seen'],now)}, {volume}.")
            elif var.get().strip():
                lines.append(f'{label}: valor manual preservado, não verificado pela coleta.')
            else:
                remote=self.craft_api.get((code,q),{}).get(city,{}).get(side)
                if remote and now-remote['seen']>minutes*60:
                    lines.append(f"{label}: preço da API descartado — idade {age_text(remote['seen'],now)}, limite {minutes} min.")
                else:lines.append(f'{label}: sem preço recente para a cidade, qualidade e tipo de ordem selecionados.')
        self.price_status.config(text='\n'.join(lines))

    def load_prices(self):
        try:
            self.apply_prices()
            targets=self.price_targets()
        except (ValueError,KeyError):
            self.craft_note.config(text='Selecione cidades e qualidade válidas.');return
        if not self.app.export_enabled:return
        if self.price_busy or time.time()-self.price_last<60:
            self.craft_note.config(text=self.craft_note.cget('text')+' API: aguarde até 60s entre consultas.');return
        codes={code for _,code,_,_,_ in targets if code}
        if not codes:return
        ctx=self.price_context();protected={str(v):v.get() for v,_,_,_,_ in targets}
        self.price_busy=True;self.price_last=time.time()
        self.craft_note.config(text='Consultando preços reais dos materiais e do produto na API das Américas…')
        def work():
            try:self.price_jobs.put((ctx,protected,self.app.market_service.get_many(codes),None))
            except Exception as error:self.price_jobs.put((ctx,protected,None,type(error).__name__))
        threading.Thread(target=work,daemon=True).start()

    def poll_prices(self):
        try:
            ctx,protected,data,error=self.price_jobs.get_nowait()
            self.price_busy=False
            if ctx==self.price_context():
                if error:self.craft_note.config(text=f'API indisponível ({error}). Preços do fluxo foram preservados; campos ausentes continuam vazios.')
                else:self.craft_api=data;self.apply_prices(protected)
        except queue.Empty:pass
        ctx=self.price_context();expired=False
        for key,(var,value,seen,original) in list(self.price_marks.items()):
            if var.get()!=value:
                del self.price_marks[key]
                self.price_status.config(text='Há preços editados manualmente. Eles não foram verificados pela coleta; busque novamente para usar preços observados.')
            elif ctx!=original or time.time()-seen>int(self.app.filters['minutes'].get())*60:
                var.set('');del self.price_marks[key];expired=True
        if expired:
            self.price_status.config(text='Preços copiados expiraram ou a receita/cidade mudou. Busque novamente.')
        self.update_price_status()
