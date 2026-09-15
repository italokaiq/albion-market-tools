"""Exportação periódica fora da thread da interface. Arquivo substituído atomicamente."""
import json
import os
import subprocess
import threading
import time
from pathlib import Path

BASE = Path(__file__).parent
OUTPUT = BASE / 'outputs' / 'albion-americas'
WORKBOOK = OUTPUT / 'Mercado_Americas.xlsx'
NODE = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'


class Exporter:
    def __init__(self):
        self.busy = False
        self.status = 'Excel: aguardando primeira atualização.'
        self.last_attempt = 0
        self.lock = threading.Lock()

    def request(self, data, verify=False):
        with self.lock:
            if self.busy:
                return False
            self.busy = True
            self.last_attempt = time.time()
        threading.Thread(target=self.write,args=(data,verify),daemon=True).start()
        return True

    def write(self, data, verify=False):
        try:
            OUTPUT.mkdir(parents=True,exist_ok=True)
            source = OUTPUT/'snapshot.json'
            source.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            self.status = 'Excel: gerando planilha…'
            args = [str(NODE),str(BASE/'build_excel.mjs'),str(source)]
            if verify:
                args.append('--verify')
            result = subprocess.run(args,cwd=BASE,capture_output=True,timeout=180,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (OUTPUT/'export.log').write_bytes(result.stdout+result.stderr)
            if result.returncode:
                raise RuntimeError('Falha ao gerar Excel; consulte export.log na pasta da planilha.')
            self.status = 'Excel atualizado às '+time.strftime('%H:%M:%S')+' • Reabra o arquivo para ver os novos dados.'
        except PermissionError:
            self.status = 'Excel bloqueado. Feche o arquivo para permitir a próxima atualização.'
        except (OSError,subprocess.SubprocessError,RuntimeError) as exc:
            # O builder usa código 3 para arquivo em uso, sem substituir a versão anterior.
            if 'result' in locals() and result.returncode == 3:
                self.status = 'Excel aberto ou bloqueado. Feche o arquivo; nova tentativa automática em 60s.'
            else:
                self.status = 'Excel: '+str(exc)
        finally:
            self.busy = False
