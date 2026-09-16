# Revisão do aplicativo — 16/09/2026 (parte 14)

## Revisão geral do app: bug real encontrado no fluxo de flipping

Pedido direto do usuário: "revise todo o app e veja se tem algum bug ou erros de execução". Abordagem: baseline estático (pyflakes/compile/suíte completa, todos limpos) seguido de um teste funcional de ponta a ponta numa janela `Dashboard` real, contra o banco de produção real (não mock), cobrindo todas as 8 abas, busca/seleção de item, todas as janelas de idade máxima, todos os períodos do histórico de preço, as duas calculadoras com entradas inválidas/zero/negativas/vazias/com vírgula decimal, planejador de produção, flip de upgrade, histórico (inclusive registro em lote), biblioteca de receitas e redimensionamento em 5 tamanhos de janela. Tudo passou sem exceção não tratada.

Isso não bastou sozinho — a suíte automatizada e o smoke test não exercitam **todo** combinação de estado possível (ex.: uma rota real selecionada *e* um campo específico do painel principal com texto inválido ao mesmo tempo). Fui atrás disso especificamente por ser justamente o tipo de combinação que os testes end-to-end tendem a não cobrir (cada teste tende a variar uma coisa de cada vez). Revisão dirigida em `calculators.py`/`dashboard.py` por todo ponto que faz `float(algo.get()...)`/`int(algo.get()...)` a partir de um campo de texto livre, checando se cada um está dentro de um `try/except ValueError` (padrão já estabelecido no app: nunca travar por entrada inválida, sempre avisar) ou se depende de um Combobox `readonly` (que não pode ter texto inválido por construção).

**Achado**: `Calculators.use_route()` (botão "Usar rota selecionada" na calculadora de flipping) fazia `float(self.app.transport.get().replace(',','.'))` **sem nenhum try/except**, ao contrário de todo outro ponto do app que faz o mesmo tipo de parsing. Reproduzido antes de corrigir, com um cenário realista (rota fabricada com preços válidos em cidades diferentes + campo "Transporte por un." vazio/texto/múltiplos pontos): `ValueError: could not convert string to float`, não capturado, propagando pra fora do callback do botão. Comparado com `use_reference_margin()` (a função-irmã, usada quando não há rota com volume conhecido): essa por coincidência **não trava** com o mesmo tipo de entrada inválida, mas não porque está corretamente protegida — o mesmo `float()` do transporte já é chamado antes, dentro de um `try/except` que existe para outro propósito (calcular a margem de referência), e a exceção ali capturada já aborta a função antes de chegar na segunda chamada não protegida. Ou seja, o mesmo tipo de bug existe no código dessa função também, só está estruturalmente inalcançável hoje — mantive a observação registrada aqui caso a ordem do código mude no futuro.

Corrigido: `use_route()` agora captura o erro nesse ponto específico, usa `0` como transporte só para essa cópia (nunca deixa o campo travado ou pela metade) e adiciona um aviso explícito no texto da operação pedindo pra corrigir o campo e copiar a rota de novo — mesmo padrão de honestidade do resto do app (nunca falha silenciosamente, nunca inventa um valor sem avisar).

Validação: 198 testes passaram (2 novos em `test_calculators.py`, incluindo a reprodução exata do travamento com uma rota real antes da correção, e a confirmação de que o caminho válido com vírgula decimal continua multiplicando corretamente pela quantidade da rota).

# Revisão do aplicativo — 16/09/2026 (parte 13)

## Flip de upgrade de encantamento

Pedido do usuário após a conversa sobre conceitos de flip: "o flip de upgrade é muito benéfico... implemente no app... confira como é feito na Albion Free Market."

**Fonte de dados**: em vez de confiar num guia de terceiros, extraí o custo de cada nível de upgrade direto de `recipes_source.json` (dados brutos do próprio jogo) — campo `enchantments.enchantment[].upgraderequirements.upgraderesource`, presente para os níveis 1–3 (Rúnica/Alma/Relíquia) e **ausente para o nível 4**, confirmando que @3→@4 não existe como upgrade (só craft direto com material @4). Script `upgrade_costs.py` gerou `upgrade_costs.json` com 4.107 passos; conferido à mão que `T4_MAIN_SWORD@1/@2/@3` batem com o valor esperado (288 de cada recurso) e que `@4` realmente não aparece.

**Módulo de economia** (`upgrade_flip.py`): `evaluate_paths()` testa cada nível inicial possível (0 a alvo) e só inclui um caminho se **todos** os preços necessários (item inicial + cada recurso de upgrade em cada nível intermediário) estiverem disponíveis — mesmo princípio de nunca presumir preço ausente como zero, já usado no resto do app. `best_flip()` escolhe o caminho mais barato e compara contra o preço de venda do item já no nível alvo, aplicando as mesmas taxas (`SALES_TAX`/`SETUP_FEE`) já usadas em todo o app.

**Verificado contra dois padrões independentes**: (1) valores reais vistos na AFM (rúnica 5, alma 71, relíquia 479, 288 de cada, total 159.840 para o caminho completo 0→3) viraram um teste (`test_matches_real_afm_totals_for_full_chain`); (2) consulta ao vivo à API real (T4_MAIN_SWORD, Caerleon) encontrou o caminho mais barato de verdade (começar em .1, custo 158.466) e um lucro líquido coerente com a fórmula (258.994 × 0,895 − 158.466 = 73.333,63) ao comparar contra o preço de venda de .3.

**Bug próprio encontrado e corrigido antes de qualquer teste**: `money(self.result['start_level'] and self.result['buy_price'])` na tela — como `start_level` pode ser `0` (caminho que já começa no próprio recurso base), `0 and x` avalia pra `0` em Python, mostrando preço de compra errado sempre que o caminho mais barato começava em .0. Corrigido removendo o `and` desnecessário.

**Fora do escopo, deliberadamente**: reroll de qualidade (probabilístico — precisaria de taxa de sucesso que não temos como verificar sem dado real) e "Equivalent Tiers" da AFM (comparação entre tiers, funcionalidade separada e maior).

A tela nova filtra preços pela mesma idade máxima configurada na tela principal — como os preços vêm da API em lote (mesma fonte já usada nas rotas de flipping), valem as mesmas ressalvas já documentadas: no padrão de 15 min, praticamente nada passa; é preciso aumentar a janela (testado com 1440 min) pra ver cobertura real, especialmente pros recursos de upgrade, negociados com menos frequência que o próprio equipamento.

Validação: 196 testes passaram (19 novos: 4 de extração do catálogo, 15 do módulo de economia), `pyflakes`/`py_compile` limpos, e um teste funcional de ponta a ponta na janela real (abrir, escolher item, consultar preços reais, conferir resultado) confirmando que o filtro de idade e os modos "Imediata"/"Ordem de compra/venda" funcionam como esperado.

# Revisão do aplicativo — 15/09/2026 (parte 12)

## Rotas de flipping ampliadas pela API

Pergunta direta do usuário depois da comparação com a AFM: "por que o site tem vários itens de flipping e o meu app não tem nenhum?" Investigado com o banco real, não hipótese.

**Diagnóstico**: com ~370 mil ordens no banco, o fluxo AODP local sozinho tinha só 5 rotas calculáveis (0 positivas) em 60 min — 388 de 489 variantes de equipamento (79%) tinham só oferta de venda, sem pedido de compra em cidade nenhuma. A mesma lista de itens via API agregada tinha rota possível em 82% dos casos. Isso confirma: sites estabelecidos (AFM) consultam o banco agregado central do AODP, não dependem de um único fluxo ao vivo local.

**Duas iterações até funcionar de verdade:**
1. `route_enrichment.py` (`RouteEnrichment`, mesmo padrão de `PriceAPI`/`PriceHistory`): consulta em lote via `MarketService.get_many()` (já com throttle/cache/lock) os itens que o fluxo já observou, em segundo plano, a cada 60s. Mesclado no parâmetro `api` de `snapshot()`. **Não bastou** — rotas continuaram em 5, porque `trading.snapshot()` exigia `amount is not None` (quantidade conhecida) pra considerar um preço em qualquer rota, e a API nunca informa quantidade — rejeitando 100% dos dados de API por design.
2. Corrigido `trading.snapshot()`: quantidade vira `None` (não inventada) quando só há dado da API, em vez de rejeitar o preço inteiro. Isso quebrou `use_route()` em `calculators.py` (fazia `float() * None`, travaria) — corrigido com fallback de quantidade=1 e aviso explícito "Volume desconhecido (via API)". Testado de novo com o banco real: **5 rotas → 425 rotas, 0 → 76 positivas**, em 1440 min.

**Achado adicional durante a validação**: a API reflete a última observação por cidade, que pode ter até ~22h para itens pouco negociados (diferente do fluxo, que é contínuo) — então o filtro de idade máxima do próprio usuário precisa ser amplo o bastante pra deixar passar esse dado; com 60 min quase nada da API passa, com 1440 min a cobertura completa aparece.

Rotas com volume desconhecido aparecem marcadas como tal na tabela ("Qtd. limite: desconhecido (API)"), nunca com um número inventado — mesmo princípio já usado no gráfico individual e na simulação de referência.

Atualizado um teste existente (`test_reconciled_routes.py`) que verificava o comportamento antigo (rota some quando só há dado da API) para o novo, correto (rota aparece com o preço reconciliado e volume `None`, nunca com o lucro antigo/otimista nem volume inventado).

Validação: 168 → 177 testes, incluindo o novo módulo testado sem tocar rede real, e dois testes novos em `test_trading.py` (rota via API com volume desconhecido; rota com volume conhecido vencendo empate de lucro contra rota via API).

# Revisão do aplicativo — 15/09/2026 (parte 11)

## QA comparativo com o Albion Free Market

Pedido do usuário: comparar com albionfreemarket.com (site estabelecido, mesma fonte AODP, catálogo de ~11.968 itens pesquisáveis) para checar se a nossa busca está correta.

**Achado concreto, verificado contra a API real (não presumido)**: diários (`journalitem`) e contratos de trabalhador (`labourercontract`) tinham sido excluídos do nosso catálogo por suposição de que não eram negociáveis. A AFM os trata como categoria pesquisável ("Laborers"). Testado contra `/stats/history/` e `/stats/prices/` da API:
- Diários: nenhum preço, nunca (atual ou histórico de 30 dias) — a suposição de "não negociável" era **certa** para esse caso.
- Contratos de trabalhador: sem preço atual, mas **histórico real de negociação** (item vendido em Bridgewatch e Caerleon nos últimos 30 dias) — a suposição estava **errada** aqui.

Adicionadas ao catálogo (`catalog_items.py`): `journalitem`, `labourercontract`, `hideoutitem`, `siegebanner`, `killtrophy`, `rewardtoken`, `trashitem` — todas com nome resolvido corretamente em `items.json` (conferido, não só assumido). Catálogo foi de 9.973 para **10.208** códigos.

**Verificado e confirmado já coberto** (não precisava de mudança): ferramentas de coleta (picaretas etc., já estavam em `weapon` com código `T#_2H_TOOL_*`), artefatos (780 códigos já em `simpleitem`), itens de fazenda (109 já em `farmableitem`) — bati contagens contra as categorias da AFM (Gathering Equipment 32, Artifact 169, Farming 81) e a cobertura já batia.

**Gap conhecido e não perseguido**: a AFM lista "Hardcore Expeditions" (181 itens, recompensas de conteúdo específico tipo masmorra corrompida) que não consegui localizar com confiança nos dados-fonte sem adivinhar convenção de nome — não adicionado para não incluir algo incerto. Também não investigado a fundo: `consumablefrominventoryitem` (categoria grande, 1362 itens, mas contém muita coisa explicitamente marcada `_NONTRADABLE` nos próprios dados — misturada, não óbvia de filtrar corretamente sem mais tempo).

Validação: 168 testes passaram, incluindo os testes atualizados de categorias incluídas/excluídas do catálogo.

# Revisão do aplicativo — 15/09/2026 (parte 10)

## Redimensionamento e paleta de cores do jogo

Pedido do usuário: o app não pode quebrar ao redimensionar, e o visual deveria lembrar o jogo.

**Redimensionamento.** Medido antes de mexer: a barra de filtros principal (nome/código, cidade, idade máxima) já precisa de ~939px de largura sozinha, sem nenhuma forma de rolar — abaixo de ~1130px de largura total de janela, campos ficavam simplesmente inacessíveis, sem aviso. Isso provavelmente motivou o `minsize(1100,740)` original, que por sua vez já deixava pouca margem em telas de notebook comuns (1366×768). Corrigido: a barra de filtros agora vive dentro de um canvas com rolagem horizontal automática — abaixo da largura necessária, aparece uma barra de rolagem; acima, ela fica oculta. `minsize` reduzido para `(1000,650)`. Testado programaticamente em 1920×1080, 1366×768, 1100×740, 1000×650 e 900×600 (abaixo do mínimo, onde o Tk trava no mínimo): em nenhum caso um controle fica inacessível.

**Paleta de cores.** Pesquisei antes de aplicar — não inventei valores. Achado real (não é a convenção "WoW" que eu presumiria por padrão): qualidade no Albion usa cor **metálica** (pedra/ferro/bronze/prata/ouro), encantamento usa **verde/azul/roxo/amarelo** em sistema de losangos, e tier usa **cinza/bronzeado/verde/azul/vermelho/laranja/amarelo/branco** — com hex reais extraídos de screenshots pela comunidade para os tiers 3–7 (ex.: tier 5 vermelho `#6F2019`/`#934038`, tier 7 dourado `#C8A940`/`#E8C95F`). O tema atual (fundo azul-marinho `#101B2B`, destaque verde-menta `#8EDFC3`) não tinha nada a ver com isso.

- Fundo trocado de azul-marinho para carvão/marrom escuro (`#171310`/`#221D17`/`#2C2418`).
- Destaque trocado de verde-menta para dourado/bronze (`#D4AF37` acento principal, `#6B4F23`/`#4A3820` seleção/estado ativo).
- Texto trocado de branco-azulado para branco-pergaminho quente (`#EDE6D6`/`#B3A78C`/`#8F8570`).
- Barra "vender" do gráfico trocada de verde para dourada — **e corrigi o texto da legenda que ainda dizia "Verde: vender"** depois da troca de cor (achado revisando o próprio diff, antes de rodar qualquer teste — o tipo de inconsistência que só aparece olhando o resultado, não testando isoladamente).
- Aplicado de forma sistemática (mapa cor-antiga → cor-nova, script único) em `dashboard.py`, `calculators.py`, `production_ui.py`, `history_ui.py`, `ui_design.py` — 96 substituições ao todo, sem nenhuma cor antiga sobrando (conferido por busca).

**Limite real, não escondido**: não tenho como ver a janela renderizada neste ambiente. Validei o que dá para validar sem olhos — compilação, nenhum erro de cor inválida do Tcl/Tk ao navegar por todas as 8 abas e todos os diálogos (busca, craft, planejador, biblioteca de receitas, histórico, registro em lote), suíte completa passando. Se alguma cor ficar ruim visualmente (contraste, combinação estranha), só o usuário consegue ver e apontar o quê exatamente ajustar.

Validação: 167 testes passaram (nenhum teste verifica cor específica — é comportamento puramente visual).

# Revisão do aplicativo — 15/09/2026 (parte 9)

## Registro em lote no histórico

Pedido do usuário, depois de conversar sobre como alimentar o histórico diariamente: registrar várias operações concluídas de uma vez, sem passar pela calculadora completa uma a uma.

- `history_ui.flip_entry_from_row()`/`craft_entry_from_row()`: funções puras (sem Tk) que calculam previsto e realizado idênticos para uma operação já concluída — reaproveitam `flipping()` pra flip; craft usa o mesmo modelo simples (recebido − gasto) já usado na confirmação individual. Extraídas deliberadamente do diálogo pra serem testáveis sem simular clique em widget, mesmo padrão de `search_catalog()` em `catalog_search.py`.
- Diálogo com duas abas (Flipping/Craft), 5 linhas pré-criadas por aba, botão "+ linha" pra mais, "×" por linha pra remover. "Registrar tudo" processa as duas abas: linha em branco é ignorada, linha com erro fica no formulário com a mensagem de status explicando o quê, linha registrada com sucesso some da lista.
- `self.bulk_flip_rows`/`self.bulk_craft_rows`/`self.bulk_status`/`self.submit_bulk` ficam expostos na instância de `HistoryView` enquanto o diálogo está aberto — não é só estética, é o que permite testar o fluxo completo (preencher campos, registrar, checar o que ficou no histórico) sem depender de navegar a árvore de widgets.

Validação: 167 testes passaram (12 novos), incluindo teste de ponta a ponta com 5 linhas simultâneas (3 flips + 2 crafts) conferindo a tabela principal e os totais do resumo depois do registro.

# Revisão do aplicativo — 15/09/2026 (parte 8)

## Correção: app travava com idade máxima alta

Reportado pelo usuário: usar idade máxima grande (1440 min / 24h) travava o app. Medido com o banco real (não hipótese): com ~369 mil ordens acumuladas no banco, a janela de 24h processava **o banco inteiro a cada atualização**, levando **3,06 segundos por ciclo** — só que o ciclo roda a cada 1,5 segundo. A interface nunca alcançava, ficando permanentemente atrás e parecendo travada.

- `market_view.filtered_orders()` ganhou um parâmetro opcional `limit` (LIMIT na consulta SQL, mantendo as mais recentes). `None` por padrão — comportamento idêntico para testes e para `benchmark_search.py`, que depende do total sem corte.
- `dashboard.py` passa `limit=ORDER_WINDOW_LIMIT` (30.000) na chamada real. O rodapé avisa quando o corte é aplicado, com o mesmo padrão de transparência já usado para truncamento de exibição ("Mais itens disponíveis pelos filtros").
- Medido antes/depois com o banco de produção real: 1440 min caiu de **3,06s para 0,16–0,22s** por ciclo — a mesma verificação que encontrou o problema confirmou a correção, não foi só teoria.

Validação: 155 testes passaram, incluindo o corte em si e o aviso no rodapé do dashboard.

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
