"""Perfis versionados, sem preços, com gravação atômica e backup anterior."""
import json
from pathlib import Path
from datetime import datetime,timezone
from economics import number
from persistence import write_settings
from paths import data_path

class ProductionProfiles:
    def __init__(self,path=None):
        self.path=Path(path) if path else data_path('perfis_producao.json')

    def read(self):
        if not self.path.exists():return {'version':1,'profiles':{}}
        data=json.loads(self.path.read_text(encoding='utf8'))
        if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('profiles'),dict):
            raise ValueError('Formato de perfis não suportado. O arquivo original foi preservado.')
        return data

    @staticmethod
    def context(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)

    def save(self,name,context,settings,shipping):
        name=name.strip()
        if not name or len(name)>80:raise ValueError('Informe um nome de até 80 caracteres.')
        terms=[]
        for (stage,city),values in settings.items():
            rrr,fee=values
            if rrr:number(rrr,'retorno',0,99.99)
            if fee:number(fee,'estação')
            terms.append([stage,city,str(rrr),str(fee)])
        if shipping:number(shipping,'transporte')
        data=self.read()
        data['profiles'][name]=dict(context=self.context(context),settings=terms,shipping=shipping,
            saved_at=datetime.now(timezone.utc).isoformat())
        write_settings(self.path,data)

    def load(self,name,context):
        profile=self.read()['profiles'][name]
        if not isinstance(profile,dict) or not isinstance(profile.get('settings'),list) or not isinstance(profile.get('shipping'),str) or not isinstance(profile.get('saved_at'),str):
            raise ValueError('Perfil inválido. O arquivo original foi preservado.')
        if profile.get('context')!=self.context(context):
            raise ValueError('Este perfil pertence a outra receita, lote, qualidade ou modo de negociação. Use a configuração correspondente.')
        terms={}
        for entry in profile['settings']:
            if not isinstance(entry,list) or len(entry)!=4 or not all(isinstance(v,str) for v in entry):
                raise ValueError('Custos do perfil inválidos. O arquivo original foi preservado.')
            stage,city,rrr,fee=entry
            if rrr:number(rrr,'retorno',0,99.99)
            if fee:number(fee,'estação')
            terms[(stage,city)]=(rrr,fee)
        shipping=profile['shipping']
        if shipping:number(shipping,'transporte')
        return terms,shipping,profile['saved_at']
