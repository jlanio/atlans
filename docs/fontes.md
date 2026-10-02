# Catálogo de fontes de dados (WFS)

O assistente da Home e o assistente do editor passavam a maior parte do tempo de
uma resposta **prospectando dado externo**: adivinhando `url` e `typeName` de um
WFS, descobrindo pelo erro que a camada não existia, esperando 3 × 60 s de
timeout numa URL inventada. Nenhuma das ferramentas listava camadas, sondava um
endereço ou buscava por tema; `validate_workflow` não toca a rede, então uma
URL errada passava com `ok: true` e só estourava em `run_workflow`; e o nó WFS
refazia o GetCapabilities em toda execução e em todo retry.

Este documento descreve o **catálogo interno de fontes** que resolve isso na
fase 1: a tabela `fontes_de_dados`, a semente versionada em `catalogo/`, as
quatro ferramentas MCP, a regra "catálogo primeiro" nos roteiros, o aviso da
validação, o aprendizado das execuções, a verificação por endpoint e o cache do
executor. **Nada muda na interface** nesta fase — o que muda é o comportamento
do assistente: antes de qualquer prospecção, ele consulta o catálogo.

## O que é uma fonte

Uma linha de `fontes_de_dados` é **uma camada de um serviço**: hoje, sempre um
WFS (`tipo="wfs"`, nó `WFS`). Os campos que importam:

| Campo | Significado |
|---|---|
| `workspace_id` | `NULL` = fonte da **plataforma** (visível para todo mundo); preenchido = fonte do workspace. A busca junta as duas |
| `url`, `type_name` | O endpoint já normalizado (sem query/fragment) e a camada (`ns:camada`) |
| `chave` | `sha256(workspace\|tipo\|url\|type_name)`, UNIQUE — é o que torna o upsert idempotente |
| `propriedades` | O que se cola no nó: `url`, `typeName`, `sortBy` quando há coluna de id, e `version` (guardado; ver fase 2) |
| `instituicao`, `grupo`, `titulo`, `descricao`, `temas`, `dicas` | Os metadados do Vault (ou do GetCapabilities, ou de quem registrou) |
| `esquema` | `crs`, `bbox`, `geometry_type`, `geometry_column`, `columns[{name,type,xsd,nullable}]`, `feature_count`, `columns_source` |
| `busca` | Texto normalizado (sem acento, minúsculas) com instituição, grupo, título, camada, host, descrição, temas e colunas — é sobre ele que a busca faz `LIKE` |
| `prioridade` | 1 preferida · 2 normal · 3 secundária (do Vault: `#preferida`, `#secundaria`, frontmatter `prioridade`) |
| `origem` | `vault` (a semente), `aprendida` (de uma execução), `manual` (`register_source`). Uma origem nunca é rebaixada: `aprendida` não sobrescreve `vault`/`manual` |
| `estado` | `ok`, `falhando`, `nao_verificada` — o resultado da última verificação, com `verificada_em` e `ultimo_erro` |
| `usos`, `usada_em` | Quantas execuções bem-sucedidas usaram a fonte |
| `vault_hash` | Hash do registro parseado; a reimportação pula o que não mudou |

A tabela nasce na base zero: o CREATE mora em `scripts/init_schema.sql` (o
corpo da única revisão alembic — F3 da simplificação) ao lado do modelo
`app/models/fonte_de_dados.py`, e `tests/unit/test_init_schema_bootstrap.py`
prende script e models um ao outro, coluna a coluna. `chave` é UNIQUE simples
(e não UNIQUE composto com `workspace_id` nulo) para ser portável entre
Postgres e o SQLite dos testes. `JSON`, não JSONB, pelo mesmo motivo.

## De onde vem: a semente em `catalogo/`

`catalogo/geoservicos/` é a semente que acompanha o repositório, mantida como
um vault de notas Markdown: uma pasta por instituição, com a nota da instituição
(`Endpoint WFS`, finalidade, versão do WFS), `Camadas.md` e `Atributos.md`. Os
nomes, títulos e esquemas das camadas são os que cada serviço publica (ver a
nota de origem em [`catalogo/README.md`](../catalogo/README.md)). O
formato, as extensões opcionais (frontmatter, tags inline, `_sinonimos.md`) e o
passo a passo para atualizar estão em [`catalogo/README.md`](../catalogo/README.md).

Na semente atual: 114 pastas; **76 instituições com WFS → 25.492 camadas, todas
com atributos** (o IBGE sozinho tem 9.759, em WFS 1.0.0). As outras pastas são
ArcGIS REST ou placeholders "(Metadados em validação)" e ficam de fora com o
motivo `sem_endpoint_wfs` — prontas para uma fase futura.

O parser é `app/services/fontes_vault.py` (puro, sem banco): `ler_pasta()`
devolve um `RegistroDoVault` por camada ou uma `Ignorada(pasta, motivo)` por
pasta que não entra. As fixtures de `tests/fixtures/vault/` são recortes reais.

### Importação no arranque

`app/core/fontes_catalogo.py` roda como tarefa de fundo do lifespan da API
(`app/main.py`):

1. `importar_catalogo_no_arranque()` lê `FONTES_CATALOGO_DIR` (fora do `.env`,
   `catalogo/geoservicos`; vazio ou inexistente = não importa). Todo worker
   carrega os sinônimos de `_sinonimos.md` (eles vivem na memória do processo).
   A API sobe antes do `alembic upgrade head`: a importação **espera a tabela
   existir** (até 10 min) e só então o worker que pegar o lock Redis
   `fontes_catalogo:lock` (TTL 600 s) importa; se a importação falhar, ele
   devolve o lock, para a próxima subida não esperar o TTL.
2. `fontes_service.importar_pasta()` compara `{chave: vault_hash}` das linhas
   `origem='vault'` com a pasta: insere as novas em lotes de 500, atualiza as de
   hash diferente, pula as iguais e marca `deleted_at` nas que sumiram da pasta
   (soft delete — a linha e o histórico ficam). **Subir de novo com a mesma pasta
   é uma consulta e zero escritas.**
3. Em seguida, uma verificação inicial **só do que está pendente** (nunca
   verificado ou vencido) — ver "Verificação por endpoint".

`Dockerfile.api` copia `catalogo/` para a imagem; sem isso a importação não
roda em produção. A pasta está fora do `detect-secrets` (o baseline exclui
`^catalogo/`) e do limite de tamanho do pre-commit.

### Um registro grande demais não pode levar o lote junto

Numa instalação real a importação já morreu no registro 6.779: 48 dos 25.492
registros tinham `titulo` acima de 255 caracteres (indicadores do IBGE chegam a 276) e a
coluna era `VARCHAR(255)`. Como o commit é **por lote de 500**, o
`StringDataRightTruncationError` abortava tudo dali em diante — ficavam 6.500 registros
no banco, **19 mil se perdiam** e o único sinal era um ERROR no log. O assistente ficava
sem três quartos das camadas.

Três mudanças, e a terceira é a que impede a repetição:

1. **`titulo` virou `TEXT`** (hoje direto no `scripts/init_schema.sql`; a migração histórica `a3c81d7e2f46` fez a troca). Título é escrito por gente; qualquer
   limite fixo volta a estourar no próximo catálogo, e `descricao`/`dicas` já eram `TEXT`.
2. **Guarda de borda por tipo de campo.** Os de EXIBIÇÃO (`instituicao`, `grupo`) são
   cortados no limite da coluna — um rótulo sem a cauda ainda serve. Os FUNCIONAIS
   (`type_name`, `url`) **não podem** ser cortados: o `type_name` vai literalmente na
   consulta WFS e a `chave` deriva dele, então um corte criaria uma fonte que aponta para
   uma camada inexistente. Esses fazem o registro ser **pulado**, com o motivo no resumo.
   O limite vem da COLUNA (`fontes_service._limite`), não de uma constante copiada.
3. **`tests/unit/test_catalogo_cabe_nas_colunas.py`**, e este é o teste que faltava: o
   SQLite dos outros testes **ignora o tamanho de `VARCHAR`**, então o estouro era
   invisível para a suíte inteira — passava em CI e falhava no PostgreSQL. O teste novo lê
   o catálogo REAL do repositório e compara cada campo com o limite da coluna, sem banco
   nenhum. Ele falha no dia em que alguém acrescentar um registro que produção recusaria.

## A regra "catálogo primeiro"

Ela mora em cinco lugares, para que nenhuma superfície a esqueça:

- **Guia de autoria**, tópico `sources` (`app/mcp/guia/sources.md`,
  `get_authoring_guide(topic="sources")`, resource
  `atlans://guide/authoring/sources`): a ordem obrigatória — `search_sources`
  com o tema em duas ou três grafias → `describe_source` e colar
  `node_snippet.properties` → só sem resultado, pedir a URL à pessoa ou
  `probe_source` → `register_source` para não sondar duas vezes.
- **Instruções do servidor MCP** (`app/mcp/instrucoes.py`): "fonte externa
  (WFS) nunca é inventada nem sondada de primeira".
- **Roteiros** da Home (`assistente_superficie.py`), do assistente do editor
  (`assistente_service.py`) e do prompt `criar_fluxo` (`app/mcp/prompts.py`):
  passo 2, antes de `search_nodes`/`describe_node`.
- **`describe_node("WFS")`**: o nó declara `source_kind: "wfs"` na descrição
  (`flow/nodes/datasource/wfs.py`, campo `source_kind` em `NodeDefinition`) e o
  catálogo de nós acrescenta a dica "não invente `url`/`typeName`: consulte
  `search_sources`". Nenhum `if name == "WFS"` — qualquer nó que declare
  `source_kind` ganha a dica. O campo não é propriedade do nó, então o
  formulário do editor não muda.
- **Receita 5** do guia (`recipes.md`): WFS catalogado
  (`Funai:tis_poligonais`) → `AttributeFilter` → `PublishMap`, com `sortBy`.

## As quatro ferramentas MCP

`app/mcp/tools/fontes.py`; guardas em `app/mcp/guardas.py`.

| Ferramenta | Escopo | Papel | Cota | O que faz |
|---|---|---|---|---|
| `search_sources(query, workspace_id?, kind?, institution?, limit=20)` | `workflows:read` | viewer | geral | Busca SEM rede. Itens leves (`id, kind, node, scope, state, verified_at, uses, priority, type_name, host, institution, group`) com título e temas em `untrusted_data`; `total`; `hint` quando não há resultado |
| `describe_source(source_id)` | `workflows:read` | viewer | geral | A ficha: `node_snippet` (`{name: "WFS", type: "datasource", properties: {url, typeName, sortBy?, maxFeatures}}` — só propriedades que o nó declara hoje), esquema resumido (até 50 colunas), `state/origin/verified_at/uses/institution`; título, descrição, dicas e temas em `untrusted_data` |
| `probe_source(url, type_name?, version="2.0.0")` | `workflows:write` | editor | `probe` (10/min) | Sonda um WFS: sem `type_name`, lista as camadas (`layers_listed`, até 50); com `type_name`, o esquema do DescribeFeatureType mais CRS/bbox (`layer_described`). Não cria fonte, mas **atualiza** uma já catalogada no escopo. Traz `catalog_hint` quando o mesmo host já está catalogado |
| `register_source(url, type_name, workspace_id?, version, title?, description?, tags?, hints?)` | `workflows:write` | editor | `probe` | Valida a camada contra a lista, DescribeFeatureType, upsert `manual/ok` no catálogo do workspace; devolve a ficha + `outcome: created\|updated` |

- `probe_source` e `register_source` são as únicas ferramentas com
  `openWorldHint: true` (campo `open_world` em `Guarda`): fazem o servidor
  falar com uma URL pública. IP privado, loopback e link-local continuam
  bloqueados pela validação SSRF; o balde `probe` limita a 10/min por token.
- Nas duas superfícies do assistente elas passam **sem clique**
  (`ESCRITAS_SEM_CLIQUE` na Home, `ESCREVEM_MAS_PASSAM` no editor): sondar e
  registrar uma fonte é a via normal de trabalho, não uma ação destrutiva.
- Erros de sondagem viram `erro("source_unreachable", …, reason=<código>)` com
  `codigo ∈ {timeout, http_status, ssrf, tamanho, tls, sem_camadas,
  camada_inexistente, xml, rede}` — e `candidates` quando a camada não existe
  mas há parecidas.

### Como a busca funciona

`fontes_service.buscar()`: a consulta é normalizada (sem acento, minúsculas),
os conectivos caem ("de", "em", "do"…), cada termo é expandido pelos sinônimos
(o mapa padrão `SINONIMOS_PADRAO` + o `_sinonimos.md` do Vault) e vira
`(busca LIKE '%t%' OR busca LIKE '%sin1%' …)`; entre termos, AND. O escopo é
`workspace_id IN (…) OR workspace_id IS NULL`, sem as apagadas. A ordem:
`estado='ok'` primeiro, depois `prioridade`, `usos` decrescente e título.
`institution` casa exato ou por texto normalizado; `limit` vai até 100.
São 25 mil linhas × ~300 bytes: a varredura custa milissegundos; um índice
trigram fica como evolução se o catálogo crescer.

## A validação avisa, sem rede

`validate_workflow` (e a rota REST de validação) agora consulta o catálogo
para os nós com `source_kind == "wfs"` quando há `workspace_id`
(`fontes_service.conferir_fontes_da_definicao`):

- `unknown_source` — a `url`+`typeName` não estão no catálogo do workspace nem
  da plataforma; a mensagem manda usar `search_sources`, ou
  `probe_source`/`register_source` antes de executar.
- `failing_source` — a fonte existe, mas falhou na última verificação (com
  `verificada_em` e os primeiros 160 caracteres de `ultimo_erro`).

São **avisos** (`ok` continua "sem erros") e a validação **falha aberta**: banco
indisponível não derruba o relatório. O painel de validação do editor mostra o
aviso como mostra qualquer outro — nenhum componente muda.

## O catálogo aprende das execuções

Fase `fontes` do consumer de resultados (`app/core/run_result_consumer.py`,
entre `pins` e `notificacao`, isolada por `_run_phase`): para um run
`success` com algum nó `WFS`, `fontes_service.aprender_de_execucao()` faz o
upsert `aprendida/ok` no workspace do run, com `esquema = {crs, bbox,
feature_count}` das métricas espaciais e `columns` de `output_columns`
(`columns_source: "run"`). `usos` só conta no primeiro fechamento
(`first_close`) — reentrega da fila não duplica nem infla. Um esquema só é
trocado por um mais completo (`describe_feature_type` > `vault` > `run`), e a
fusão preserva o que só o outro tinha. `FONTES_APRENDER_DAS_EXECUCOES=false`
desliga.

## Verificação por endpoint

25 mil camadas não são 25 mil sondagens: **um GetCapabilities por URL
distinta** marca todas as camadas daquela URL (`fontes_service.verificar_endpoint`).
Presente no capabilities → `ok`, com CRS e bbox no esquema (e título, abstract e
keywords quando faltavam); ausente → `falhando` ("camada não consta no
GetCapabilities"); endpoint fora → todas `falhando` com o erro. Na semente são
76 pedidos por rodada.

`run_verificacao_loop()` repete a rodada a cada `FONTES_VERIFICACAO_INTERVAL`
segundos (padrão 1 dia; 0 desliga — e desliga também a verificação inicial),
só no worker que pegar o lock Redis do intervalo, com no máximo dois endpoints
em paralelo e uma pausa dispersa entre eles. Cada endpoint tem a própria sessão
de banco: falha de um não para a rodada.

`probe_source` com camada e `register_source` verificam UMA fonte ao vivo
(`fontes_service.sondar_wfs`: GetCapabilities + DescribeFeatureType).

Limites da sondagem: GetCapabilities 30 s e 32 MB (o do IBGE lista 9.759
FeatureTypes); DescribeFeatureType 15 s e 2 MB. O XML é parseado com a biblioteca
padrão depois de recusar `<!DOCTYPE`/`<!ENTITY`. Toda ida à rede passa por
`validate_url_ssrf` + `safe_httpx_request` (`flow/utils/geo_helpers.py`); o
`owslib` não é usado no servidor. A rota `GET /nodes/wfs/layers` do editor
virou um wrapper fino de `fontes_service.listar_camadas_wfs`, com o mesmo corpo
e os mesmos status. Com `credential_id` (e o `workflow_id` do fluxo em edição),
ela lista com a credencial do nó — as camadas que um GeoServer esconde do
anônimo —, no mesmo escopo da validação (`validate_service`): as credenciais de quem
pede e, para operator ou acima no workspace do fluxo, as compartilhadas com ele.
É o fluxo que diz o workspace, não o cliente (fluxo inexistente é 404). As
regras da credencial (authkey na URL ou no cabeçalho, Basic; segredo com ao
menos 6 caracteres, para poder ser redigido nas mensagens e nos logs) são as do
nó, em `flow/utils/credencial_wfs.py` — e a tela de Credenciais as aplica ao
gravar e ao Testar.

## O executor não repete o GetCapabilities

`flow/nodes/datasource/wfs.py` guarda o `WebFeatureService` por `(url, version)`
num cache do processo: TTL `WFS_CAPABILITIES_TTL_S` (padrão 3600 s; 0 desliga),
teto de 64 entradas, `threading.Lock` (o nó roda em `asyncio.to_thread`). A
construção acontece fora do lock — segurar o lock por até 60 s travaria todo nó
WFS do processo por causa de um servidor lento. Quando a camada pedida não está
no objeto em cache, o nó refaz o GetCapabilities **uma vez** antes de acusar
"não encontrada" (uma camada publicada há minutos não pode virar falso
negativo). Falha de `getfeature` não invalida o cache. O log diz
"WFS capabilities: cache" ou "rede em N ms".

## Configuração

| Variável | Padrão | Onde | Efeito |
|---|---|---|---|
| `FONTES_CATALOGO_DIR` | `catalogo/geoservicos` | API | Pasta importada na subida; vazia (`FONTES_CATALOGO_DIR=`) ou inexistente = não importa |
| `FONTES_APRENDER_DAS_EXECUCOES` | `true` | API | Fase `fontes` do consumer |
| `FONTES_VERIFICACAO_INTERVAL` | `86400` | API | Intervalo da verificação por endpoint, em segundos; 0 desliga toda sondagem iniciada pelo servidor |
| `WFS_CAPABILITIES_TTL_S` | `3600` | Executor | Cache do GetCapabilities do nó WFS; 0 desliga |

## Testes

- `tests/unit/test_fontes_vault.py` — parser, com fixtures reais (FUNAI, IBGE em
  1.0.0, ArcGIS e placeholder ignorados, formato novo com frontmatter/tags/sinônimos).
- `tests/unit/test_fontes_service.py` — URL/chave/busca, parsers de
  capabilities (1.0/1.1/2.0) e XSD, tradução de erros de rede, upsert, escopo e
  ordem da busca, conferência, aprendizado, verificação, importação idempotente.
- `tests/unit/test_mcp_fontes.py` — as quatro tools, paridade com `GUARDAS`,
  balde `probe`, `open_world`.
- `tests/unit/test_fontes_catalogo.py` — importação no arranque (flag, lock,
  sinônimos, zero escritas na segunda subida), verificação por endpoint (só o
  pendente, falha isolada, paralelismo 2) e o loop; o lock Redis e o laço
  comum a todas as tarefas de fundo, em `tests/unit/test_tarefas_de_fundo.py`.
- `tests/unit/test_validate_service.py`, `test_consumer_aprende_fontes.py`,
  `test_wfs_node.py`, `test_nodes_router_wfs_layers.py`, `test_mcp_catalogo.py`,
  `test_mcp_guia.py`, `test_mcp_prompts.py`, `test_mcp_servidor.py`,
  `test_docs_mcp.py`, `test_assistente_superficie.py`, `test_assistente_service.py`.

## O que fica para a fase 2

- **A interface.** O catálogo não aparece na UI nesta fase. O previewer da
  proposta (aba "Fontes" no editor, ficha da fonte, badge de estado no nó WFS)
  fica como referência: https://claude.ai/artifact/ENuwsPVJCGWVRTpZ8rnm14.
- **`version` no nó WFS.** O catálogo guarda `propriedades.version` (IBGE =
  1.0.0), mas `describe_source` não a põe no `node_snippet` enquanto o nó não a
  declarar — o GeoServer do IBGE responde às duas versões, e a verificação por
  endpoint confirma com o próprio GetCapabilities 2.0.0.
- **ArcGIS REST** (~34,5 mil camadas nas pastas hoje ignoradas): `tipo="arcgis_rest"`,
  nó `HttpRequest`.
- Índice trigram em `busca` se o catálogo crescer muito além da semente.
