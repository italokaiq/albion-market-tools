"""Verifica se há uma versão mais nova do programa publicada no GitHub.

Nunca baixa nem substitui o executável em execução — sobrescrever um binário
rodando é arriscado (pode corromper a instalação) e foge do princípio deste
app de nunca fazer algo irreversível sem o usuário decidir. Só informa a
versão mais recente disponível e o link da release; baixar e trocar o
arquivo continua manual, como já é hoje.
"""
import json
import re
import urllib.request
from paths import resource_path

REPO = 'italokaiq/albion-market-tools'
RELEASES_URL = f'https://api.github.com/repos/{REPO}/releases/latest'
HEADERS = {'User-Agent': 'AlbionMarketDesk/1.0', 'Accept': 'application/vnd.github+json'}
VERSION_FORMAT = re.compile(r'^\d+\.\d+\.\d+$')


def current_version():
    try:
        return resource_path('VERSION').read_text(encoding='utf-8').strip()
    except OSError:
        return None


def parse_version(text):
    """'v1.2.3' ou '1.2.3' -> (1,2,3); levanta ValueError fora desse formato."""
    text = text.strip()
    if text[:1] in ('v', 'V'):
        text = text[1:]
    if not VERSION_FORMAT.match(text):
        raise ValueError(f'Formato de versão inesperado: {text!r}')
    return tuple(int(p) for p in text.split('.'))


def fetch_latest_release(timeout=15):
    request = urllib.request.Request(RELEASES_URL, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def check_for_update(fetcher=fetch_latest_release):
    """Nunca baixa o binário — só compara versões e devolve o link da release."""
    local = current_version()
    try:
        release = fetcher()
    except (OSError, ValueError) as error:
        return dict(ok=False, error=str(error), local_version=local)
    remote_tag = release.get('tag_name', '')
    url = release.get('html_url', '')
    try:
        remote_parsed = parse_version(remote_tag)
    except ValueError as error:
        return dict(ok=False, error=str(error), local_version=local, remote_version=remote_tag)
    try:
        local_parsed = parse_version(local) if local else None
    except ValueError:
        local_parsed = None
    return dict(ok=True, local_version=local, remote_version=remote_tag, url=url,
                update_available=local_parsed is None or remote_parsed > local_parsed)
