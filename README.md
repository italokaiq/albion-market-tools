# Monitor Albion — Américas

Abra `iniciar.cmd` para iniciar a janela. Requer Python 3.12 com Tkinter (já disponível neste computador). Não precisa informar senha do jogo nem manter o Albion aberto.

## Dashboard sem Office

Ao selecionar um equipamento, o gráfico consulta a API pública das **Américas** em segundo plano, nas oito cidades/mercados. A consulta se repete no máximo uma vez por minuto por item e qualidade enquanto ele permanecer selecionado. Não é necessário instalar nada adicional. Em falhas, o fluxo ao vivo continua funcionando e o painel mostra o erro de consulta.

O gráfico combina a API com o fluxo: para cada lado e cidade, usa a observação com o horário mais recente. A idade da API é a data original informada pelo serviço, nunca o horário de download. Preços fora da idade máxima aparecem em cinza com `*`, somente como referência. Cada valor identifica `API` ou `Fluxo`. Mesmo com a API, alguns mercados podem não ter preços registrados.

A API de preços não fornece a quantidade disponível. Por isso seus valores complementam **o gráfico do equipamento selecionado**, mas não são convertidos em ordens fictícias nem alimentam as quantidades e os lucros de lote das rotas. As listas, a matriz e as oportunidades continuam usando as ordens coletadas pelo fluxo. O craft também consulta a API, sem presumir quantidade disponível. Não há seleção automática de equipamento.

Na página Oportunidades, a lista inicia em **Equipamentos coletados**: equipamentos com dados recentes aparecem mesmo sem rota lucrativa. Selecione um deles para comparar os preços no gráfico. O seletor **Oportunidades de flipping** restringe a lista às rotas e respeita o filtro de margem positiva. Sem resultados, uma mensagem explica se faltam dados ou rotas. A pesquisa aceita palavras separadas, como `espada T4` ou `anciao 8.2`, ignorando acentos. A lista depende dos dados coletados e dos filtros; não representa todo o catálogo do jogo. Preços ausentes continuam identificados, sem valores inventados.

A interface usa navegação lateral em três áreas: **Flipping**, **Craft** e **Mercado**. Flipping reúne oportunidades, rotas e simulação; Craft concentra o planejamento da produção; Mercado contém a matriz e os dados detalhados. Os filtros gerais aparecem apenas nas telas de mercado e rotas. Use **Mais filtros** para qualidade, tier, encantamento, transporte e demais opções. O perfil Premium/sem Premium fica no rodapé do menu lateral.

Nas calculadoras, os rótulos ficam acima dos campos e os resultados com e sem Premium aparecem lado a lado em uma tabela. Custos avançados e explicações são expansíveis. Em Craft, informe o custo da estação e o retorno nos campos principais. Abra a seção de custos adicionais para transporte, diários e Foco. A tela tem rolagem para receitas maiores. Os custos continuam incluídos quando a seção é recolhida.

Abra `iniciar.cmd`. Toda a análise funciona na janela do programa, sem Excel, pacote Office, navegador ou conta adicional. Os dados e gráficos atualizam automaticamente a cada 1,5 segundo enquanto o monitor estiver aberto.

- **Visão geral**: quantidade de variantes, mercados com dados, rotas positivas e melhor margem por unidade. A lista mostra até 100 rotas. Selecione uma para ver o gráfico de preços nas oito cidades/mercados.
- **Preços por cidade**: matriz semelhante à referência, com linhas Comprar por e Vender por. Dê dois cliques em um equipamento para abrir seu gráfico na Visão geral.
- **Onde comprar e vender**: origem, destino, preços, margem após custos, quantidade limite e idade dos dados. Por padrão só aparecem rotas com margem positiva; desmarque a opção para ver também as negativas.
- **Ordens observadas** e **Comparar mercados**: detalhes da coleta e preços por qualidade e cidade.

No gráfico, azul é o preço para comprar de uma oferta de venda e verde é o preço pago por uma ordem de compra. Cada preço mostra sua idade. Sem observação recente, aparece “sem dado”. O tamanho da barra compara preços, não volume de vendas.

Escolha **Premium** ou **Sem Premium** no painel. As rotas imediatas usam respectivamente 4% ou 8% de taxa sobre a venda, além do transporte por unidade que você informar. O padrão é Sem Premium. As configurações são salvas ao fechar a janela. O cálculo é `venda × (1 − taxa) − compra − transporte`. A quantidade limite é o menor volume observado nos dois melhores preços. Não se presume liquidez além desse volume, nem se estima perda de carga durante o transporte.

## Flipping e crafting

Em **Planejar produção**, clique em **Escolher equipamento pelo nome**. Busque, por exemplo, `espada T4.1`, selecione um resultado e confirme em **Usar equipamento e carregar receita** (ou dê dois cliques). O app preenche código final, itens por craft, materiais, quantidades e elegibilidade de retorno. Os ingredientes também mostram seus nomes. Receitas alternativas ficam disponíveis num seletor. Os campos continuam editáveis e os preços são limpos ao trocar de receita.

O catálogo local inclui 7.049 equipamentos/encantamentos extraídos dos tipos `weapon` e `equipmentitem` do arquivo público https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/items.json, baixado em 14/09/2026. As receitas encantadas usam os materiais correspondentes; artefatos sem retorno ficam desmarcados. Não são inferidas receitas ausentes, de consumíveis ou refino. O catálogo funciona sem conexão; mudanças futuras do jogo exigem atualizá-lo. Depois de escolher a receita, use **Buscar preços recentes** e confira o retorno e os custos da estação.

**Calculadora de flipping** compara os perfis Premium (4%) e Sem Premium (8%) lado a lado. Informe preços, quantidade, transporte total e se a compra/venda será imediata ou por ordem. Uma ordem acrescenta 2,5% de criação sobre seu valor. Recriações extras cobram novamente esse percentual, supondo o mesmo preço e quantidade. O resultado discrimina taxas, lucro líquido, lucro por unidade, ROI sobre custo de aquisição mais transporte e preço de equilíbrio. **Usar rota selecionada** copia preços e quantidade da oportunidade marcada; os preços copiados expiram conforme a idade máxima e o lote não pode exceder o volume observado sem informar novos preços. A compra imediata não tem taxa de criação; a venda imediata tem imposto, mas não criação de ordem.

**Calculadora de craft** usa uma receita informada por você: código final, crafts, itens produzidos por craft, materiais por craft e seus preços. Use a busca por nome para preencher equipamentos do catálogo, ou informe uma receita manualmente. Adicione ou remova materiais, e marque **Retorna** apenas nos materiais que admitem retorno. Artefatos não devem ser marcados. Informe o percentual de retorno mostrado na estação no jogo, nas condições de cidade/Foco que pretende usar. Esse percentual já deve incluir o efeito do Foco; o app não o aplica uma segunda vez nem o confunde com o bônus de produção.

Informe o custo total de uso da estação em prata (não a tarifa por 100 de nutrição), transporte total e demais despesas. Crédito de diários é o ganho líquido que você estimar, já descontados os diários vazios e taxas. Foco total e valor por ponto são opcionais para atribuir um custo de oportunidade ao Foco. O perfil Premium muda a tributação da venda, não o retorno configurado.

**Buscar preços recentes** preenche os materiais na cidade de compra e o produto na cidade de venda usando a idade máxima do painel. A qualidade final é respeitada. As demais buscas gerais do painel não limitam essa consulta. Materiais usam o menor preço de oferta (compra imediata) ou maior ordem de compra (referência para criar ordem); a venda final usa maior ordem de compra (imediata) ou menor oferta de venda (referência de anúncio). Preços de ordens são referências concorrentes, não promessa de preenchimento. Os valores copiados são invalidados se a cidade, receita, qualidade ou modo de negociação mudar, ou se ultrapassarem a idade máxima. Dados ausentes limpam o preço e bloqueiam o cálculo; insumos com qualidade variável e quantidades disponíveis devem ser conferidos no jogo.

O custo econômico desconta o valor esperado dos recursos retornados, pelo mesmo preço dos insumos, e pode incluir custo do Foco. O saldo em prata após vender o produto não inclui venda dos recursos devolvidos nem considera Foco como despesa em dinheiro. A diferença é mostrada para distinguir estoque retornado de prata realizada. A quantidade de produção é `crafts × itens/craft`; não se presume recrafting dos recursos retornados nem uma qualidade aleatória melhor que a informada.

**Salvar receita** guarda a receita atual em `receita_craft.json`; **Carregar receita** restaura os campos e limpa preços, retorno e estação, para informar valores atuais. As contas são estimativas percentuais: arredondamentos, tarifas mínimas do jogo, ordens parcialmente preenchidas, custos adicionais de relistagem do craft e mudanças de preço precisam ser conferidos antes de executar.

Referências de regras consultadas em 14/09/2026:

- Taxas Premium/sem Premium: https://www.albionledger.net/guides/market-tax
- Criação de ordens: https://forum.albiononline.com/index.php/Thread/201146-Setup-fee-not-included-in-Total-price-during-Sell-Order/
- Retorno de recursos: https://wiki.albiononline.com/wiki/Resource_return_rate
- Craft e Foco: https://albiononline.com/news/guide-crafting

Os filtros de item, cidade, tier, encantamento, qualidade e idade limitam a análise. Deixe cidade vazia para comparar todas. O filtro Venda/Compra afeta apenas a aba de ordens. Não encontrar uma rota positiva significa que ela não foi encontrada nos dados e filtros atuais, não que ela não exista no jogo.

Caerleon (3005) e Mercado Negro (3003) ficam separados. Portais são normalizados para o mercado da cidade conforme o mapeamento do AODP. Uma mesma ordem recebida pelo portal e pela cidade é contada uma única vez na matriz e nas rotas.

A geração automática de Excel foi desativada. A planilha anteriormente criada permanece na pasta `outputs/albion-americas`, como fotografia do momento daquela exportação. Ela não é necessária para usar o painel.

## Uso

- Deixe a janela aberta e o computador conectado. Fechar a janela encerra a coleta.
- Pesquise pelo nome em português ou código de item, por exemplo `bolsa`, `T4_BAG`, `T5_` ou `@1`. A busca ignora acentos.
- Filtre pelo nome da cidade ou identificador do mercado, tier, encantamento e qualidade.
- Escolha compras, vendas e a idade máxima. A janela atualiza a cada 1,5 segundo.
- A lista mostra até 500 ordens recentes; as demais continuam no banco local `mercado.sqlite3` por até 24 horas, com limpeza durante a coleta.
- Em caso de falha, a conexão é refeita automaticamente. Mensagens perdidas durante desconexões não são recuperadas.

## Comparação e idade

A aba **Comparar mercados** agrupa todas as ordens do período filtrado por item, qualidade, encantamento e mercado. Mostra a menor venda e a maior compra observadas, com quantidade disponível naquele preço e idade de cada lado. Qualidades e encantamentos diferentes não são misturados. O filtro Venda/Compra se aplica apenas à aba de ordens; a comparação sempre considera os dois lados. São exibidos até 1.000 grupos, em ordem de código do item e mercado.

Verde indica recebimento há até 5 minutos; amarelo, de 5 a 15 minutos; vermelho, mais de 15 minutos. A idade máxima exclui registros antigos de ambas as abas. Quando várias ordens têm o mesmo melhor preço, a quantidade é somada e a idade mostrada é a mais antiga delas. “—” indica ausência de observação, nunca preço zero. A cor da linha de comparação corresponde ao lado mais antigo. Um aviso aparece após 60 segundos sem mensagens; isso também pode ocorrer por falta de atividade, não necessariamente por falha de rede.

As atualizações preservam a seleção e a linha no topo da tabela quando ela continua presente. Nomes vêm dos catálogos públicos `items.json` e `world.json` do ao-data/ao-bin-dumps, baixados em 14/09/2026. Os arquivos ficam junto ao programa e funcionam sem download na inicialização. Nomes desconhecidos mantêm o código. Os mercados mantêm os nomes do catálogo sem juntar identificadores diferentes.

## Limites

Este é um monitor de observações, não uma cópia completa do livro de ofertas. Preços chegam apenas quando colaboradores consultam o mercado. A idade exibida é desde o recebimento local, não uma garantia de quando o jogo foi consultado. Ofertas podem ser vendidas ou canceladas sem aviso no fluxo; o filtro de idade reduz, mas não elimina esse problema. Registros com quantidade zero são removidos. Os preços usam o campo `UnitPriceSilver` do fluxo, em prata por unidade. Não há alertas nesta versão.

## Fontes

- https://www.albion-online-data.com/developer
- https://github.com/ao-data/albiondata-client/blob/master/lib/market.go
- https://docs.nats.io/reference/protocols/client

## Verificação

Execute `python -m unittest -v` para testar atualização de ordens, remoção e tratamento do preço.


## Integridade dos dados e uso simples

1. Escolha Premium ou Sem Premium conforme sua conta.
2. Para flipping, selecione uma rota observada e use **Usar rota selecionada** na calculadora. O transporte por unidade é convertido para o total do lote. Valores manuais são informados pelo usuário, não validados pela coleta.
3. Para craft, escolha o equipamento pelo nome, informe retorno e estação reais do jogo e clique em **Buscar preços recentes**. A consulta combina fluxo e API, escolhendo o preço mais recente dentro da idade máxima. Materiais usam qualidade Normal; o produto final respeita a qualidade escolhida. A origem, idade e volume conhecido de cada preço aparecem abaixo dos controles.
4. A API não fornece volume. Isso aparece como **volume desconhecido**. O resultado do craft é uma previsão com preços observados, não uma comprovação de que todo o lote pode ser negociado naquele preço.
5. Retorno e estação começam vazios e precisam ser preenchidos. Zero deve ser informado explicitamente quando for o valor correto. Mudar o número de crafts limpa o custo total da estação. Os custos opcionais iniciam em zero como valores não incluídos; preencha os que se aplicarem. Diários e Foco não são consultados automaticamente.
6. Campos sem preço não são substituídos por exemplos, médias inventadas ou zero. Uma resposta atrasada da API não sobrescreve preços que você editou nem aplica valores à receita/cidade anterior.

A confirmação de compras, vendas, tarifas mínimas e arredondamentos exatos por transação não está integrada. Lucro exibido é calculado, e retorno de materiais é um valor esperado. Nenhuma ordem de jogo é criada automaticamente.

## Busca completa e resumo da operação

Na tela Oportunidades, use **Buscar no catálogo** para pesquisar equipamentos por nome, código, tier ou encantamento e escolher a qualidade. O catálogo pesquisa todos os equipamentos presentes no arquivo local, independentemente das ordens recebidas. A lista mostra 100 resultados por vez e permite **Carregar mais**, sem truncar a pesquisa. Ao selecionar, o gráfico consulta a API das Américas; a consulta em segundo plano respeita os intervalos existentes. Ausência de cobertura na API permanece identificada como sem dado.

**Simular rota selecionada** abre a calculadora com uma rota coletada que tenha preços e quantidades conhecidos. O resumo apresenta investimento inicial, receita bruta, transporte, taxas, lucro estimado e volume observado. Itens consultados apenas pela API não ganham quantidade fictícia nem uma rota executável presumida. Sem rota, o app limpa os preços da simulação anterior e explica o motivo.

Essa integração resolve a lacuna de pesquisa geral sem coleta local indicada na revisão anterior, dentro do catálogo de equipamentos instalado. Atualização automática do catálogo, favoritos, histórico e múltiplas receitas salvas continuam pendentes.

Validação desta integração: 39 testes passaram, incluindo abertura da pesquisa, seleção sem ordens, permanência da seleção e remoção de resultado anterior quando não há rota.

## Busca e comparação de todo o mercado — 15/09/2026

**Buscar no catálogo** deixou de listar só equipamentos: agora pesquisa qualquer item negociável do jogo — armas, armaduras, recursos brutos e refinados, consumíveis, monturas, mobília e sementes de fazenda — num catálogo local de 9.973 códigos (base e variantes de encantamento), extraído de todas as categorias relevantes do `ao-bin-dumps` e gerado por `python catalog_items.py`. A tela ganhou filtros dedicados de **Tier** e **Encantamento**, além da busca textual e da qualidade já existentes.

Ao selecionar qualquer item — não apenas equipamentos —, a Visão geral consulta as oito cidades/mercados (fluxo AODP e API das Américas combinados) e agora mostra, além do gráfico, uma **tabela de comparação por cidade** com preço, idade e origem (fluxo/API) de cada lado. Essa comparação deixou de depender do filtro "Somente equipamentos": antes, um recurso ou consumível selecionado na busca ficava sem preço do fluxo local nessa tela, mesmo com ordens recentes no banco, porque esse filtro (pensado para a lista de rotas de flipping) também esvaziava indevidamente a consulta do item selecionado individualmente. Isso foi corrigido; o filtro agora afeta somente a lista de oportunidades, como pretendido.

Validação: 81 testes passaram, incluindo a extração do catálogo por categoria (equipamentos, recursos com variantes `_LEVEL1-4` convertidas para `@1-@4`, exclusão de itens não negociáveis como diários e contratos), os filtros de tier/encantamento na busca e a regressão do preço de itens não-equipamento.

## Planejar a cadeia de craft, refino e venda

Ao escolher um equipamento na tela de craft, abre-se **Planejar compra, refino, craft e venda**. Também é possível reabrir pelo botão **Comparar compra, refino e cidades**. O lote, qualidade, modos de compra/venda e perfil Premium vêm da calculadora. A API das Américas é consultada automaticamente para o produto, materiais refinados e dependências de refino até os tiers inferiores. O Mercado Negro é avaliado para venda, não como estação de produção.

1. Na aba **Custos e retornos**, selecione a etapa (craft ou material refinado). Preencha, nas cidades que deseja avaliar, o retorno real mostrado no jogo e o custo da estação em prata por operação. Para refino, uma operação é uma execução da receita indicada pelo catálogo; para craft, é um craft do equipamento. Tarifas por nutrição não são valores totais por operação.
2. Informe o transporte em prata por unidade por trecho entre cidades. É uma hipótese uniforme fornecida por você; o programa não calcula distância, peso, risco ou preço de viagem. Digite zero somente se quiser explicitamente excluir esse custo.
3. Clique **Aplicar custos e comparar**. As abas mostram rotas de craft/venda, compra versus refino por material e destino, e os preços observados. Selecione uma rota para ver compras e refinos intermediários em cada cidade.

O motor compara compra de refinados contra refino recursivo: matéria-prima e material refinado do tier inferior, que também pode ser comprado ou produzido. Usa receitas convencionais do catálogo local; substituições com tokens de facção não são avaliadas. O retorno não é presumido a partir do nome da cidade: informe o percentual real já considerando bônus, Foco e condições atuais. Consulte os guias oficiais de [refino](https://albiononline.com/news/guide-refining) e [craft](https://albiononline.com/news/guide-crafting).

Taxas de ordem: compra 2,5%; venda 2,5% mais imposto de 4% Premium ou 8% sem Premium. Transporte e estação são custos; recursos retornados representam estoque esperado e reduzem o custo econômico, sem virar prata recebida. Desembolso bruto mostra compras antes de reutilizar retornos. O comparador não monetiza Foco, diários ou probabilidades de qualidade: a qualidade escolhida é um cenário de venda, não garantia de produção nessa qualidade.

Cidades e etapas sem custos completos são excluídas, não consideradas piores. A melhor alternativa é somente entre as opções avaliáveis com os dados presentes. Os preços mantêm limite de idade; volumes ausentes da API permanecem desconhecidos. O planejamento não reserva ordens nem garante quantidade ou execução. Campos da calculadora alterados enquanto o comparador está aberto invalidam a comparação e exigem reabertura.

Validação: consulta real da cadeia T4_MAIN_AXE com 13 códigos retornou 168 preços (não necessariamente todos dentro do limite de idade). Testes cobrem taxas dos dois perfis, compra versus refino, custo bruto versus retorno esperado, tier inferior ausente, receitas encantadas, transporte, validade de preços e invalidação da interface.

## Perfis, recuperação e diagnóstico

O planejador oferece **Salvar perfil** e **Carregar perfil**, com nome escolhido por você. São armazenados o contexto da receita/lote/qualidade/modos e os custos informados. Preços não são salvos no perfil. Um perfil de outro contexto é recusado; após carregar, confira a data e os custos e use **Confirmar custos e comparar**. Os perfis ficam em `perfis_producao.json`, com versão de formato para permitir futuras migrações. Formatos não suportados são rejeitados sem sobrescrever o arquivo.

Preferências, receita atual e perfis são gravados por substituição atômica; a versão anterior é copiada para o respectivo `.json.bak`. Este é um backup local de uma versão, não proteção contra perda do computador e não inclui o banco de mercado. Para restaurar, feche o app, preserve o arquivo atual com outro nome e copie o `.bak` para o nome original `.json`.

Use `iniciar.cmd` para iniciar com registro de erros em `logs/erros.log`. Os logs têm rotação limitada e não são enviados a serviços externos. `diagnosticar.cmd` informa versão de Python/SQLite e integridade básica dos catálogos, sem listar preços. O diagnóstico não testa rede nem valida cada receita semanticamente. A inicialização ainda requer Python 3.12+ com Tkinter; não foi criado instalador independente ou atualização automática.
