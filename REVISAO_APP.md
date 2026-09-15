# Revisão do aplicativo — 15/09/2026 (parte 7)

## Gráfico de histórico de preço (24h/3d/7d/30d)

Sugestão do usuário, comparando com o gráfico de médias que o próprio jogo mostra. Verificado antes de implementar: a API das Américas (mesmo host já usado, `west.albion-online-data.com`) tem um endpoint `/stats/history/` separado do de preços atuais, com `avg_price` e `item_count` por intervalo (`time-scale` aceita 1/6/24 horas, confirmado na documentação pública).

- `price_history.py`: `fetch_history()`/`parse_history()` (mesma robustez a linhas malformadas do resto do app) e uma classe `PriceHistory` com o mesmo padrão de `PriceAPI` — throttle de 60s por chave, cache, thread em segundo plano, mensagens de status.
- Nova aba "Histórico de preço" na Visão geral, ao lado da comparação por cidade já existente: seletor de período (24h/3d/7d/30d) e cidade, desenhado como gráfico de linha no mesmo estilo visual do resto do app.
- **Dois bugs reais encontrados e corrigidos durante o desenvolvimento, ambos por testar contra a API de verdade em vez de só mockar**: (1) a integração inicial passava o ID da cidade (ex. "3008") para a API, que espera o nome ("Martlock") — a consulta nunca vinha vazia por acaso, vinha vazia porque o parâmetro estava errado; (2) o Mercado Negro precisa do nome em inglês "Black Market" para essa consulta (confirmado comparando os locais retornados pela API com e sem filtro) — a tradução para português usada na interface (`trading.CITIES`) não funciona como parâmetro. Corrigido com `trading.api_city_name()`, testado com uma consulta real trazendo dados de Martlock e do Mercado Negro.
- Rotulado como "preço médio anunciado observado" — a documentação pública não garante se é venda confirmada ou média de anúncios, então o app trata com a mesma cautela de sempre.

Validação: 153 testes passaram.

# Revisão do aplicativo — 15/09/2026 (parte 6)

## Atualizador de catálogo

Mais um item da lista original resolvido: "Atualização do catálogo: as receitas públicas têm data de coleta; falta um atualizador com validação e aviso de mudanças."

- URLs confirmadas por tamanho exato de arquivo contra o repositório real (não adivinhadas): `items.json`/`world.json` do app vêm de `formatted/` no ao-bin-dumps; `recipes_source.json` vem do `items.json` da raiz do repositório.
- `catalog_updater.py`: checagem barata via HEAD/Content-Length (`check_updates`), download+validação+gravação atômica com backup (`download_and_apply`), e regeneração de `recipes.json`/`market_items.json` a partir do novo `recipes_source.json` (`regenerate_derived`, reaproveitando `recipes.extract()`/`catalog_items.extract()` já testados). `persistence.py` ganhou `write_bytes()` para isso — grava bytes crus, sem reserializar como JSON indentado (o que infla arquivos de dezenas de MB).
- `atualizar_catalogo.cmd` para rodar com um clique. `launcher.py --diagnostico --verificar-atualizacoes` expõe a checagem barata (sem baixar nada) como opção — o diagnóstico padrão continua sem tocar rede, como sempre.
- Testado de ponta a ponta contra a rede real: baixei os três catálogos de verdade, validei, gerei os derivados — mas sempre apontando para uma pasta temporária isolada, nunca os arquivos reais do app. Aprendizado da sessão anterior aplicado aqui desde o início.
- Não atualiza um `.exe` já empacotado (limitação arquitetural do `--onefile`, documentada); é preciso rodar `build_exe.cmd` de novo depois de atualizar o catálogo, se for redistribuir.

Validação: 137 testes passaram.

# Revisão do aplicativo — 15/09/2026 (parte 5)

## Biblioteca de receitas salvas

Último item da lista de limitações originais ("gestão de várias receitas salvas... O arquivo da receita atual não é uma biblioteca") resolvido.

- `recipe_library.py`: mesmo padrão de `production_profiles.py`/`history.py` — versionado, gravação atômica com backup, nomes até 80 caracteres, renomear rejeita nome duplicado.
- **Salvar receita como...** (pede um nome) e **Minhas receitas** (lista, carrega, renomeia, remove) substituem os antigos botões de slot único "Salvar receita"/"Carregar receita".
- Migração automática e não-destrutiva: se existir uma `receita_craft.json` do formato antigo, ela é importada para a biblioteca (nomeada pelo item do produto) na primeira vez que **Minhas receitas** é aberto, e o arquivo antigo é renomeado para `.json.migrated` (preservado, não apagado).
- **Bug real encontrado e corrigido durante o desenvolvimento**: a primeira versão chamava a migração no construtor de `Calculators`, então rodar a suíte de testes migrou silenciosamente o `receita_craft.json` real do usuário (o resultado ficou correto — nada foi perdido — mas o efeito colateral em arquivo real ao simplesmente construir um objeto era um bug sério). Corrigido movendo a migração para dentro de `open_recipe_library()`, chamada apenas quando o usuário abre a tela de verdade. Adicionado teste de regressão (`test_construction_never_calls_migration`) que trava esse comportamento. Verificado manualmente (hash MD5 antes/depois) que rodar a suíte completa não altera mais nenhum arquivo real do usuário.

Validação: 125 testes passaram.

# Revisão do aplicativo — 15/09/2026 (parte 4)

## Executável autônomo (.exe real)

Primeiro item da lista de maturidade de produto resolvido: "instalador independente: executar sem instalar Python manualmente".

- `paths.py`: módulo novo com `resource_path()` (catálogos embutidos, somente leitura) e `data_path()` (dados do usuário, sempre ao lado do `.exe` real — nunca dentro dele). Necessário porque um `.exe` de arquivo único do PyInstaller extrai os recursos para uma pasta temporária a cada execução; sem essa separação, todo dado gravado pelo usuário (banco, preferências, histórico, perfis) desapareceria a cada reinício.
- Todo `Path(__file__)...` usado para localizar arquivos de dado ou catálogo foi trocado por `resource_path`/`data_path`, nos módulos: `monitor.py` (banco), `dashboard.py` (preferências), `calculators.py` (receita atual), `production_profiles.py` (perfis), `history.py` (histórico), `market_view.py`/`recipes.py`/`production.py` (catálogos), `launcher.py` (diagnóstico e pasta de logs), `excel_export.py` (pasta de saída).
- `build_exe.cmd`: gera `dist\AlbionMercadoAmericas.exe` com PyInstaller (`--onefile`), embutindo os catálogos.
- Testado com o executável real, não só em teoria: build gerado, copiado para uma pasta vazia isolada do projeto, e executado de lá. `--diagnostico` confirmou os cinco catálogos embutidos lidos corretamente; rodando a janela principal, `mercado.sqlite3` e `logs\` apareceram corretamente ao lado do `.exe`, não na pasta temporária de extração.

Não incluído: assinatura de código, instalador com desinstalador (é um arquivo único, apagar remove o programa mas não os dados gravados ao lado dele), atualização automática do próprio app. `build/`, `dist/` e `*.spec` ficaram fora do controle de versão (artefatos de build, reproduzíveis via `build_exe.cmd`).

Validação: 106 testes passaram, incluindo a resolução de caminhos com e sem empacotamento (`test_paths.py`) e o ajuste do diagnóstico para não depender mais de um caminho fixo de módulo.

# Revisão do aplicativo — 15/09/2026 (parte 3)

## Histórico de operações: previsto x realizado

Item pendente identificado na avaliação de maturidade do produto ("faltam histórico de transações próprias... e gestão de várias receitas salvas") agora tem uma primeira versão:

- `history.py`: módulo novo, mesmo padrão de `production_profiles.py` — leitura/escrita atômica com backup, versão de formato, rejeição de arquivo malformado sem sobrescrever.
- Botão **Registrar operação** nas calculadoras de flipping e craft: grava os valores exibidos no cálculo (preços, quantidade, lucro previsto) usando as mesmas funções `flipping()`/`crafting()` já testadas — nenhuma lógica de cálculo duplicada.
- Nova aba **Histórico**: lista operações, resumo previsto x realizado, confirmação de execução real (flipping recalcula com a fórmula completa; craft usa a diferença simples entre gasto e recebido real, explicitamente rotulada como mais simples que a previsão econômica).
- `historico.json` é dado do usuário: entrou no `.gitignore`, nunca é lido/escrito pelos testes (que apontam para um arquivo temporário).

Não incluído nesta rodada: múltiplas receitas salvas / biblioteca de receitas, e qualquer tentativa de detectar execução automaticamente — o app continua sem acesso ao jogo, então confirmação sempre é manual.

Validação: 102 testes passaram (15 novos: histórico isolado e integração com a interface).

# Revisão do aplicativo — 15/09/2026 (parte 2)

## Coerência do craft/flipping e planejador mais proativo

- **Gráfico e simulação agora usam a mesma fonte de preços.** Antes, o gráfico podia calcular uma margem usando a API enquanto "Simular rota selecionada" exigia uma rota do fluxo local com volume conhecido — podiam divergir, ou a simulação simplesmente recusava um item com margem visível no gráfico. `Dashboard.selected_markets()` passou a ser a única função que monta os preços por cidade do item selecionado; tanto o gráfico quanto a simulação partem dela. Quando não há rota com volume conhecido, a calculadora de flipping agora oferece uma **simulação de referência** com a mesma margem do gráfico, claramente identificada como "volume desconhecido" e sem o limite de lote que se aplica a rotas confirmadas.
- **O planejador de produção atualiza sozinho.** Antes, ele buscava ordens locais e preços da API só na abertura ou quando o usuário clicava em "Atualizar preços e comparar"; o recálculo periódico (a cada 5s) reaproveitava dados antigos. Agora ele relê o banco local a cada recálculo e volta a consultar a API automaticamente a cada 60s (respeitando o mesmo limite de sempre), com o status distinguindo "Recalculado às" de "Preços atualizados às".
- **Cobertura de volume aparece junto da recomendação.** `plan_production` agora sinaliza quando a opção mais barata de um material (ou a venda do produto) tem volume observado menor que o necessário para o lote, em vez de ignorar essa informação silenciosamente. A tabela de rotas ganhou uma coluna "Cobertura de volume", e a rota selecionada detalha exatamente qual material falta e em qual cidade.
- **Recomendação em destaque.** O planejador ganhou um resumo de decisão no topo ("Melhor opção avaliada: craft em X → vender em Y · lucro esperado Z"), separado da lista do que falta configurar. A melhor rota é selecionada automaticamente ao recalcular, mostrando a cadeia de materiais sem exigir um clique a mais.

Validação: 87 testes passaram, incluindo simulação de referência com volume desconhecido, atualização automática de ordens locais e da API sem clique manual, e cobertura de volume insuficiente (material e produto final).

Itens de uma avaliação mais ampla que ficaram fora desta rodada, por exigir desenho próprio ou ferramentas que não tenho aqui (QA visual de DPI/redimensionamento, instalador, atualização automática do app, favoritos/histórico de operações): seguem pendentes, como já estava documentado.

## Busca e comparação em todo o catálogo; auditoria do craft

- A busca de itens (antes restrita a equipamentos) passou a cobrir todo o catálogo negociável do jogo — recursos, refinados, consumíveis, monturas, mobília e sementes —, com filtros próprios de tier e encantamento, não apenas embutidos no texto livre.
- Corrigido: o filtro "Somente equipamentos" (destinado à lista de rotas de flipping) também esvaziava a comparação do item individualmente selecionado na busca, mesmo havendo ordens recentes no banco para esse item. A consulta de preços por cidade de um item selecionado agora é sempre real, independente desse filtro.
- Adicionada tabela de comparação por cidade (preço, idade, origem) ao lado do gráfico já existente, para qualquer item selecionado.
- Auditoria funcional de ponta a ponta do craft (receita → preços → cálculo → planejador de produção → perfis) com dados reais de uma receita completa (T4_MAIN_SWORD) e ordens sintéticas: nenhum bug encontrado além do já corrigido acima. A suíte subiu de 71 para 81 testes.

# Revisão do aplicativo — 14/09/2026

## Corrigido nesta revisão

- Craft consulta preços de materiais e produto em lote pela API das Américas, em segundo plano, além do fluxo de ordens.
- O horário original da observação é preservado. Preços vencidos não entram no cálculo do craft.
- Cada preço consultado identifica fonte, idade e volume observado; volume ausente da API permanece desconhecido.
- Trocar cidade, receita, qualidade ou modo de negociação invalida os preços copiados. Respostas atrasadas não sobrescrevem edições do usuário.
- Estação e retorno não começam mais com zero implícito. O custo da estação fica na área principal. Alterar o lote exige informá-lo novamente.
- Transporte da rota é transferido à calculadora com conversão de custo unitário para total.
- Flipping com preços copiados não permite extrapolar o volume conhecido; preços vencidos são removidos da simulação.
- Prejuízos deixaram de aparecer em verde. Valores calculados e retorno esperado estão rotulados como tal.

## Fluxos disponíveis

Pesquisa de equipamentos coletados, gráfico de oito mercados, oportunidades com preços e quantidades do fluxo, comparação Premium/sem Premium, seleção de receitas por nome, receitas alternativas, consulta de materiais e produto, edição manual explícita e salvamento da receita atual. O app continua local e não exige Office.

## O que ainda falta integrar

1. **Estação e condições reais de craft:** tarifa total, retorno do local, Foco e especialização não estão disponíveis na API de preços. Precisam ser informados pelo usuário. Não é correto preenchê-los por suposição.
2. **Execução e liquidez:** o fluxo é parcial e a API não fornece volumes. Sem compras/vendas confirmadas, o app não conhece lucro realizado nem garante disponibilidade de um lote.
3. **Custos exatos de transação:** cálculos percentuais não reproduzem necessariamente tarifas mínimas, arredondamentos e preenchimentos parciais do jogo.
4. **Atualização do catálogo:** as receitas públicas têm data de coleta; falta um atualizador com validação e aviso de mudanças. A cobertura atual é de equipamentos, não todas as receitas de consumíveis e refino.
5. **Pesquisa geral sem coleta local:** a lista de mercado ainda depende dos itens recebidos no fluxo. O seletor de craft já pesquisa o catálogo completo de receitas; uma busca geral equivalente seria a próxima melhoria de navegação.
6. **Histórico e carteira:** faltam histórico de transações próprias, volume negociado confirmado e gestão de várias receitas salvas. O arquivo da receita atual não é uma biblioteca.

## Limite dos resultados

Os preços vêm de observações reais do AODP ou de valores explicitamente digitados pelo usuário. O app não insere dados de demonstração no banco de produção. Cálculos de lucro são previsões baseadas nesses dados; recursos devolvidos são estoque esperado, não prata já recebida. Os testes automatizados usam dados sintéticos isolados em memória para validar a matemática, sem alimentar o mercado exibido.

## Verificação

Suíte de testes para receitas, pesquisa, cálculos, qualidade, idade, origens, retorno de artefatos, quantidades, ausência de preços e interação dos controles. Consulta real da API validada com produto e materiais, retornando 61 preços; isso não garante atualização ou cobertura de todos os itens/cidades.

## Otimização da busca — 14/09/2026

- Normalização de nomes/códigos reutilizada em cache limitado a 32.768 entradas; preços não são armazenados nesse cache.
- Filtros textuais avaliados uma vez por item/cidade em cada busca, preservando termos, acentos, tier, encantamento e qualidade.
- Consulta do craft restrita aos códigos da receita e à idade máxima, apoiada por índice de item e data no SQLite.
- Tabelas não reposicionam linhas quando a ordem das chaves permanece igual.
- Não foram adicionados limites de resultados à busca nem reduzida a frequência de atualização.

Benchmark reproduzível: `python benchmark_search.py`. Base sintética de 50 mil ordens exclusivamente em memória, sem alimentar o app. Mediana de quatro execuções locais: busca de ordens 585–777 ms antes e 119–149 ms depois; receitas 109 ms antes e 7 ms depois. Os tempos variam conforme hardware e dados; não representam latência da API ou do dashboard inteiro.

Validação: 36 testes passaram, incluindo comparação de todos os registros e sua ordem com a regra anterior em 216 combinações de filtros. A indexação adicional tem pequeno custo de armazenamento e manutenção na gravação das ordens; sua finalidade é evitar varrer todo o histórico a cada consulta de craft.

## Revisão após integração do planejador

- Corrigido o crédito de recursos retornados: compra por ordem e transporte de entrada não são reembolsados pelo retorno. Recursos comprados retornam pelo valor do material, sem taxas; recursos produzidos são avaliados pelo custo econômico de produção antes do transporte de saída.
- Um material sem preço não interrompe mais as comparações dos demais materiais. A rota completa continua bloqueada enquanto faltar insumo.
- Quantidades de material com vírgula decimal são normalizadas antes de calcular custo e desembolso.
- Falhas da API permanecem visíveis durante as atualizações. Respostas de uma receita anterior não são aplicadas à receita atual.
- Reabrir o mesmo planejamento preserva custos e transporte durante a sessão. Preços em cache mantêm suas datas originais e passam novamente pelo filtro de idade.
- Consultas solicitadas durante o intervalo de espera ficam pendentes e são executadas quando o intervalo permite. O limite de idade alterado é considerado no próximo ciclo de atualização do planejador.
- Catálogo de refino ausente/inválido mostra mensagem e mantém a calculadora manual disponível.

Validação: suíte completa de 54 testes passou. Abrange matemática, busca/filtros, receitas, integração das janelas Tk, seleção, validade de preços, falhas simuladas de API e regressões acima. Não substitui validação de execução de ordens no jogo ou confirmação de custos atuais de estação/retorno. Nenhum preço de teste foi inserido no banco de produção.

## Origem de valores — revisão de todas as páginas

| Página | Preços de entrada | Valores derivados |
|---|---|---|
| Oportunidades | Ordens do fluxo AODP; gráfico complementado pela API Américas | Margem e rotas calculadas |
| Preços por cidade | Ofertas/pedidos do fluxo AODP | Menor oferta/maior pedido por mercado |
| Rotas | Ofertas/pedidos do fluxo com quantidade observada | Margem após imposto e transporte |
| Ordens coletadas | Observações recebidas do fluxo AODP | Idade desde recebimento |
| Comparar preços | Ofertas/pedidos do fluxo AODP | Melhores preços e volumes agrupados |
| Simular flipping | Rota observada ou valores manuais identificados | Taxas, investimento e lucro estimado |
| Craft | Fluxo/API ou valores manuais identificados | Custos, retornos esperados e lucro |
| Comparador de produção | Fluxo/API para recursos, refinados e produto | Cadeia de compra/refino/craft/venda com custos informados |

Nome adotado na interface: **preço anunciado observado**. Uma oferta de venda é o preço que um vendedor pediu; um pedido de compra é o preço oferecido por um comprador. Nenhum dos dois exige venda concluída. O app usa sell_price_min e buy_price_max da API, com suas datas; não usa uma média inventada para completar campos ausentes. Uma venda imediata usa pedidos de compra observados; uma ordem de venda usa ofertas concorrentes como referência, sem garantir execução.

AODP é coleta comunitária, não uma conexão direta do app a todos os mercados do jogo. Para contribuir com um item sem histórico de venda, execute o cliente AODP configurado para Américas e consulte suas ordens no mercado do jogo, na cidade e qualidade desejadas. A cobertura depende dessas observações. Consulte a [FAQ do cliente](https://pow.albion-online-data.com/client-faq) e a [documentação da API](https://pow.albion-online-data.com/api).

Preços manuais permanecem possíveis e identificados como não verificados; custo de estação, retorno, transporte e demais parâmetros não são obtidos automaticamente do jogo. Valores calculados não são preços coletados. Os testes usam banco em memória; não há inserção de preços de demonstração no banco usado pelo app. Datas ausentes/ inválidas na API são descartadas, sem substituição por data atual.

## Reorganização de experiência e consultas

- Navegação principal: Mercado, Flipping e Produção. Preços por cidade, comparação técnica e ordens ficam em Dados avançados, sem remover funcionalidades.
- Craft mostra a sequência equipamento → consulta/custos → comparação. O planejador destaca o próximo passo, materiais sem cobertura e número de cidades/etapas configuradas. Quando todas as opções calculáveis dão prejuízo, isso é explicitado.
- Gráfico, craft e planejador usam um MarketService compartilhado. Consultas de rede são serializadas em trabalhadores de fundo, em lotes de até 40 códigos, com intervalo mínimo de dois segundos. Resultados são reutilizados durante 60 segundos e o cache é limitado a 512 códigos. A validade de preços segue a data original da observação, nunca a data do cache. Consumidores recebem cópias para evitar contaminação entre telas.
- Testes de concorrência verificam que três consumidores do mesmo item geram uma consulta, preservam datas e não alteram o cache compartilhado. Falhas não geram valores substitutos.

Esta reorganização não representa certificação de produto pronto para distribuição comercial. Instalador/atualização assinada, backup e migração de versões, perfis persistentes de produção e testes de usabilidade com usuários externos ainda precisam de uma etapa própria.
