"""Verifica e baixa atualizações dos catálogos públicos do ao-bin-dumps.

Fontes confirmadas por tamanho exato de arquivo em 15/09/2026 (não é uma
URL adivinhada): items.json/world.json do app vêm de formatted/ no
repositório; recipes_source.json vem do items.json da raiz (dump completo
dos dados do jogo, usado para extrair receitas e o catálogo de itens
negociáveis).

Nunca substitui um catálogo por um download que falhe na validação básica
de formato; a versão anterior fica em .bak, como as demais preferências do
app. Roda a partir do código-fonte (python catalog_updater.py); não
atualiza um .exe já empacotado — recursos embutidos num --onefile não são
persistíveis, então é preciso gerar um novo .exe depois (build_exe.cmd).
"""
import json
import urllib.request
from paths import resource_path
from persistence import write_bytes

BASE_URL = 'https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master'
SOURCES = {
    'items.json': (f'{BASE_URL}/formatted/items.json', list),
    'world.json': (f'{BASE_URL}/formatted/world.json', list),
    'recipes_source.json': (f'{BASE_URL}/items.json', dict),
}
HEADERS = {'User-Agent': 'AlbionMarketDesk/1.0'}


def remote_size(url, timeout=15):
    """Content-Length via HEAD, sem baixar o corpo — checagem barata de rotina."""
    request = urllib.request.Request(url, method='HEAD', headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        length = response.headers.get('Content-Length')
        return int(length) if length else None


def fetch(url, timeout=90):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def validate(name, raw, expected_type):
    data = json.loads(raw)
    if not isinstance(data, expected_type) or not data:
        raise ValueError(f'{name}: formato inesperado ou vazio.')
    if name == 'recipes_source.json' and 'items' not in data:
        raise ValueError(f'{name}: chave "items" ausente na resposta.')
    return data


def check_updates(sizer=remote_size):
    """Compara tamanho remoto x local sem baixar o conteúdo inteiro.

    Tamanho igual não garante conteúdo idêntico, mas tamanho diferente é
    sinal confiável de mudança — suficiente para um aviso de rotina.
    """
    report = {}
    for name, (url, _) in SOURCES.items():
        local_path = resource_path(name)
        local_size = local_path.stat().st_size if local_path.exists() else None
        try:
            size = sizer(url)
            report[name] = dict(ok=True, remote_size=size, local_size=local_size,
                                 changed=(size is None or size != local_size))
        except (OSError, ValueError) as error:
            report[name] = dict(ok=False, error=str(error), local_size=local_size)
    return report


def download_and_apply(names=None, fetcher=fetch):
    """Baixa, valida e só então grava (atômico, com backup) cada catálogo pedido."""
    names = list(SOURCES) if names is None else list(names)
    results = {}
    for name in names:
        url, expected_type = SOURCES[name]
        try:
            raw = fetcher(url)
            validate(name, raw, expected_type)
            write_bytes(resource_path(name), raw)
            results[name] = dict(ok=True, size=len(raw))
        except (OSError, ValueError) as error:
            results[name] = dict(ok=False, error=str(error))
    return results


def regenerate_derived():
    """Regera recipes.json e market_items.json a partir do recipes_source.json atual."""
    import recipes as recipes_module
    import catalog_items
    source = json.loads(resource_path('recipes_source.json').read_text(encoding='utf-8'))
    recipe_data = recipes_module.extract(source)
    write_bytes(resource_path('recipes.json'), json.dumps(recipe_data, ensure_ascii=False).encode('utf-8'))
    codes = catalog_items.extract(source)
    write_bytes(resource_path('market_items.json'), json.dumps(codes, ensure_ascii=False).encode('utf-8'))
    return len(recipe_data), len(codes)


def _main():
    import sys
    check_only = '--check' in sys.argv
    print('Verificando tamanho dos catálogos remotos (checagem rápida, sem baixar o conteúdo)...')
    report = check_updates()
    changed = []
    for name, result in report.items():
        if not result['ok']:
            print(f'  {name}: falha ao verificar ({result["error"]})')
        elif result['changed']:
            print(f'  {name}: tamanho local {result["local_size"]} != remoto {result["remote_size"]} — pode ter mudado.')
            changed.append(name)
        else:
            print(f'  {name}: sem mudança de tamanho detectada.')
    if check_only:
        return 1 if changed else 0
    if not changed:
        print('Nada para atualizar.')
        return 0
    print(f'Baixando e validando: {", ".join(changed)}...')
    results = download_and_apply(changed)
    failed = [n for n, r in results.items() if not r['ok']]
    for name, r in results.items():
        if r['ok']:
            print(f'  {name}: atualizado ({r["size"]} bytes). Versão anterior preservada em {name}.bak.')
        else:
            print(f'  {name}: FALHOU ({r["error"]}). Arquivo local preservado, nada foi sobrescrito.')
    if results.get('recipes_source.json', {}).get('ok'):
        print('Regerando recipes.json e market_items.json a partir do novo recipes_source.json...')
        n_recipes, n_codes = regenerate_derived()
        print(f'  {n_recipes} equipamentos/encantamentos com receita, {n_codes} códigos de itens negociáveis.')
    print('Pronto. Se você distribui um .exe, rode build_exe.cmd de novo para incluir os catálogos atualizados.')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(_main())
