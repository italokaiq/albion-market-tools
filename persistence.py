"""Persistência atômica de configurações com backup da versão anterior."""
import json
import os
import shutil
import tempfile
from pathlib import Path

def write_settings(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8') as stream:
            json.dump(data,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
        if path.exists():shutil.copy2(path,path.with_suffix(path.suffix+'.bak'))
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.remove(temp)
