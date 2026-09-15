"""Inicialização e diagnóstico local, sem transmissão de dados de suporte."""
import json
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import sys
from paths import resource_path, data_path

def diagnostic():
    files={}
    for name in ('items.json','world.json','recipes.json','recipes_source.json','market_items.json'):
        try:
            data=json.loads(resource_path(name).read_text(encoding='utf8'))
            expected=list if name in ('items.json','world.json','market_items.json') else dict
            files[name]='OK' if isinstance(data,expected) and bool(data) else 'Formato inválido'
        except (OSError,ValueError):files[name]='Ausente ou inválido'
    return {'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'catalogos':files,
            'servidor':'Américas','rede':'não testada','precos':'não incluídos no diagnóstico'}

def main():
    if '--diagnostico' in sys.argv:
        report=diagnostic()
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if all(v=='OK' for v in report['catalogos'].values()) and sys.version_info>=(3,12) else 1
    folder=data_path('logs');folder.mkdir(exist_ok=True)
    logger=logging.getLogger('albion');logger.setLevel(logging.ERROR)
    handler=RotatingFileHandler(folder/'erros.log',maxBytes=1_000_000,backupCount=2,encoding='utf8')
    logger.addHandler(handler)
    try:
        if sys.version_info<(3,12):raise RuntimeError('Instale Python 3.12 ou superior com suporte a Tkinter.')
        import tkinter as tk
        from tkinter import messagebox
        from monitor import App
        root=tk.Tk();notified=[False];application=[]
        def report(kind,value,tb):
            logger.error('Falha de interface',exc_info=(kind,value,tb))
            if not notified[0]:
                notified[0]=True
                root.withdraw()
                try:
                    messagebox.showerror('Não foi possível concluir a ação','Ocorreu uma falha e o app será encerrado para evitar resultados desatualizados.\nReabra pelo iniciar.cmd. Detalhes: logs/erros.log',parent=root)
                finally:root.after_idle(application[0].close if application else root.destroy)
        root.report_callback_exception=report
        application.append(App(root));root.mainloop();return 1 if notified[0] else 0
    except Exception:
        logger.exception('Falha na inicialização')
        print('Não foi possível iniciar. Consulte logs/erros.log ou execute diagnosticar.cmd.')
        return 1
    finally:handler.close();logger.removeHandler(handler)

if __name__=='__main__':raise SystemExit(main())
