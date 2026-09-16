"""Inicialização e diagnóstico local, sem transmissão de dados de suporte."""
import json
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import sys
from paths import resource_path, data_path

def diagnostic(check_updates=False):
    files={}
    for name in ('items.json','world.json','recipes.json','recipes_source.json','market_items.json','upgrade_costs.json'):
        try:
            data=json.loads(resource_path(name).read_text(encoding='utf8'))
            expected=list if name in ('items.json','world.json','market_items.json') else dict
            files[name]='OK' if isinstance(data,expected) and bool(data) else 'Formato inválido'
        except (OSError,ValueError):files[name]='Ausente ou inválido'
    from app_update import current_version
    report={'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,'catalogos':files,
            'versao':current_version() or 'desconhecida',
            'servidor':'Américas','rede':'não testada','precos':'não incluídos no diagnóstico'}
    if check_updates:
        from catalog_updater import check_updates as check_catalog_updates
        from app_update import check_for_update
        report['rede']='testada (checagem de tamanho dos catálogos remotos e versão do programa)'
        try:
            updates=check_catalog_updates()
            report['atualizacoes']={name:('mudou' if r.get('changed') else 'igual') if r.get('ok')
                else f"falha: {r.get('error')}" for name,r in updates.items()}
        except Exception as error:
            report['atualizacoes']={'erro':str(error)}
        try:
            update=check_for_update()
            report['atualizacao_programa']=(f"nova versão disponível: {update['remote_version']} ({update['url']})"
                if update['ok'] and update['update_available'] else 'em dia' if update['ok']
                else f"falha: {update['error']}")
        except Exception as error:
            report['atualizacao_programa']=f'falha: {error}'
    return report

def set_dpi_aware():
    """Sem isso, o Windows trata a janela como não ciente de DPI e a estica em
    bitmap nas telas de alta densidade — tudo fica borrado. Chamado antes do
    primeiro tk.Tk(); silenciosamente ignorado fora do Windows ou em versões
    sem essas APIs (não há nada de errado em rodar sem isso, só fica borrado)."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

def apply_dpi_scaling(root):
    """Depois de marcar o processo como ciente de DPI, o Tk ainda usa sua
    própria escala interna (só reflete o DPI do monitor primário no início);
    ajusta para o fator de escala real do Windows para texto/widgets do
    tamanho certo em vez de minúsculos numa tela de alta densidade."""
    try:
        import ctypes
        scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        if scale > 0:
            root.tk.call('tk', 'scaling', scale * 96 / 72)
    except (AttributeError, OSError, ValueError, ZeroDivisionError):
        pass

def main():
    if '--diagnostico' in sys.argv:
        report=diagnostic(check_updates='--verificar-atualizacoes' in sys.argv)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if all(v=='OK' for v in report['catalogos'].values()) and sys.version_info>=(3,12) else 1
    folder=data_path('logs');folder.mkdir(exist_ok=True)
    logger=logging.getLogger('albion');logger.setLevel(logging.ERROR)
    handler=RotatingFileHandler(folder/'erros.log',maxBytes=1_000_000,backupCount=2,encoding='utf8')
    logger.addHandler(handler)
    try:
        if sys.version_info<(3,12):raise RuntimeError('Instale Python 3.12 ou superior com suporte a Tkinter.')
        set_dpi_aware()
        import tkinter as tk
        from tkinter import messagebox
        from monitor import App
        root=tk.Tk();apply_dpi_scaling(root);notified=[False];application=[]
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
