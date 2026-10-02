# Spec — Contrato de dados da aresta (Edge) do workflow

Status: implementado (mergeado no `main`) · Data: 2026-09-05
Escopo: `flow/` (motor), `app/` (validação/persistência), `web/app/components/workflow/` (canvas)

## 1. Problema

Uma aresta hoje é um `dict` sem tipo que carrega **três preocupações no mesmo objeto**,
lidas por subsistemas diferentes:

1. Topologia — `source`, `target` (sólido; `flow/core/graph.py`).
2. Mapeamento de dado — `from_key`, `to_key` (opcionais).
3. Roteamento de ramo — `condition` (bool) / `source_handle` (`true`/`false`), nós de controle.

O significado do mapeamento de dado é resolvido por uma **cascata implícita de 4 modos**
em `flow/executor/core.py` (montagem do input, ~576-601):

| Campos na aresta        | Comportamento                                             |
|-------------------------|----------------------------------------------------------|
| `from_key` achado       | usa aquele campo (explícito) ✅                            |
| `from_key` não achado   | warn + `next(iter(...))` (1º valor) ⚠️ dependente de ordem |
| só `to_key`             | `next(iter(...))` (1º valor) ⚠️                            |
| nenhum                  | `inputs.update(parent_outputs)` (espalha tudo) ⚠️         |

Três dos quatro modos escolhem "primeiro valor" ou "espalha tudo" — dependentes da
**ordem de inserção do dict**. Consequências verificadas:

- **Vazamento de booleano em bifurcação** (corrigido): a aresta de ramo
  nasce sem `from_key`, cai no "espalha tudo", e quem lê `next(iter(inputs.values()))`
  (ComputeBBox, Geocode, HttpRequest, ResponseNode) pegava a decisão `branch` em vez do
  dado. Hoje o contorno é os nós de controle **ordenarem defensivamente** o
  `static_output` (o dado antes do `branch`) — frágil e documentado em
  `flow/nodes/control/conditional.py`.
- **Dois parsers divergentes**: o run real (`core.py:~576`) e a simulação/preview de
  schema (`core.py:~795`) interpretam a MESMA aresta com regras diferentes. No caso
  "sem chaves": run **espalha tudo**; simulação nomeia por **`parent_id`**
  (`to_key = to_key or from_key or parent_id`). O input-inspector pode anunciar algo
  que o run não produz.
- **Terceira camada de resolução**: `node_manager.auto_map_edges()` (`core.py:157`)
  muta as arestas a cada execução, backfillando `from_key`/`to_key` a partir de params
  legados (`outputKey*`/`inputKey*`) dos nós.
- **Sem modelo tipado**: a aresta é `dict` cru em engine, API e UI
  (`edge['source']`, `edge.get('from_key')`, `data?.from_key as string`).

O que **não** é problema (não mexer): o componente de render `custom-edges/index.tsx`
(grande, porém coeso) e o contrato documentado de sub-fluxo em
`flow/utils/workflow_contract.py` (1 aresta sem chave = espalha o dict, de propósito).

## 2. Objetivo / Não-objetivo

Objetivo:
- **Uma** definição tipada de aresta, compartilhada conceitualmente entre engine e web.
- **Um** resolvedor de input por aresta, usado pelo run real E pela simulação.
- Regras de resolução **explícitas e determinísticas**; o "primeiro valor" cego é
  **removido** — `from_key` sem match no run OMITE a porta (nunca dado alheio, nunca
  crash); o `from_key` não-declarado é acusado como erro na validação estática (`/validate`, §7).
- Roteamento de ramo (`condition`) e mapeamento de dado deixam de colidir — aresta de
  ramo passa a carregar dado explícito, e o roteamento passa a gatear por `Edge.is_branch`.
- Robustez de grafo e de skip: aresta órfã não derruba o run (F1); merge/diamante não
  skipa nó com pai vivo (F2).

Não-objetivo:
- Redesenhar o render da aresta.
- Um NOVO campo de porta na aresta. A multi-porta continua expressa por
  `from_key`/`to_key` — não há `target_handle`/`source_handle` de dado no modelo.

> **Atualização (sub-fluxo multi-porta).** O que antes era não-objetivo — "multi-porta
> de entrada" — passou a ser suportado para os três nós de sub-fluxo SEM tocar no modelo
> da aresta: as portas são DECLARADAS no nó e cada aresta cai na sua chave.
> - `SubWorkflowOutput` (`dynamic_inputs`) e `SubWorkflow` (portas do contrato do filho):
>   entradas nomeadas → cada aresta grava um `to_key` distinto.
> - `SubWorkflowInput` (`outputs_from_ports`): saídas nomeadas → cada aresta que sai leva
>   um `from_key` distinto, escolhendo o que passar adiante.
> - `≤1` porta declarada mantém o handle anônimo e o **espalhamento** (aresta sem chave),
>   preservando os sub-fluxos existentes.
> - O `handle` do React Flow de um nó SubWorkflow (invoke) vem de um contrato ASSÍNCRONO;
>   as arestas são re-ancoradas (`reancorarArestasDoNo`) quando o contrato chega, senão
>   colapsam na primeira porta ao recarregar (a `data` da aresta preserva `to_key`/`from_key`).

**Decisão do dono (2026-09-05): strict por padrão, SEM migração.** Os workflows salvos
não precisam de compatibilidade — são poucos e são corrigidos à mão. Consequências, todas
validadas contra o código real (workflow de raio de impacto, 12 agentes, C1/C3 confirmados
seguros, C2 refutado):
- **Sem `schema_version` e sem gate de versão** — o campo não existe em lugar nenhum
  (engine/app/web/DB) e o engine já é "uma versão só". Não introduzi-lo é custo zero.
- **Sem camada de migração de dados** — o antigo PR 3 (migração + strict gated) some.
  `auto_map_edges` é **aposentado** do runtime (é no-op salvo para params legados
  `outputKey*/inputKey*`, que nenhum nó/front atual emite).
- **Corrigir à mão** = redesenhar a aresta no canvas (o front grava `from_key`) ou editar
  o JSON. Reabrir+salvar sozinho NÃO faz backfill.

## 3. Modelo canônico da Edge

Engine (`flow/executor/edge_resolver.py`) — dataclass frozen `Edge`, com `from_dict`
tolerante ao formato atual. NÃO foi criado um `flow/core/edge.py` separado (como
esboçado numa versão anterior deste spec): o modelo vive junto do resolvedor. Só existe
`from_dict`; não há `to_dict` — o executor segue guardando e lendo o dict original da
aresta, e o modelo só carrega o que a semântica usa. O `source_handle` gravado pela UI
fica no dict e não entra no modelo.

```python
@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    # mapeamento de dado (ambos None => modo "spread", ver §4)
    from_key: str | None = None
    to_key: str | None = None
    # roteamento de ramo (nós de controle); None = aresta de dado comum
    condition: bool | None = None

    @property
    def is_branch(self) -> bool:
        return self.condition is not None
```

Web (`web/app/components/workflow/canvas-types.tsx`) — type espelhado. **PLANEJADO —
ainda NÃO existe no código:** `AtlansEdgeData` não está definido em lugar nenhum de
`web/`; a `data` da aresta hoje é lida sem type dedicado (`data?.from_key as string`).
Tipar continua sendo o item de front pendente (§6).

```ts
// PLANEJADO (ainda não implementado)
export interface AtlansEdgeData {
  from_key?: string
  to_key?: string
  condition?: boolean
  // source_handle vive no campo nativo do React Flow (sourceHandle)
}
```

`kind` é derivado (`is_branch`), não persistido — evita um quarto campo para manter em
sincronia.

## 4. Resolvedor único

`flow/executor/edge_resolver.py` (novo), sem dependência de `core`/asyncio — puro e
testável:

```python
# Retorna as entradas que ESTA aresta injeta no nó destino.
#   - modo mapeado:  {to_key or from_key: value}
#   - modo spread:   dict inteiro do pai (cópia rasa)
def resolve_edge_inputs(edge, parent_outputs, *, logger=None) -> dict:
    # NÃO levanta: from_key sem match OMITE a porta (não injeta valor alheio nem
    # None). O erro de from_key não-declarado é da validação estática (/validate,
    # §7), não do run — que precisa tolerar saída opcional/dinâmica.
    if edge.from_key:
        if edge.from_key in parent_outputs:
            return {edge.to_key or edge.from_key: parent_outputs[edge.from_key]}
        log_from_key_ausente(edge)          # linha de log acionável; não contribui
        return {}

    if edge.to_key:                          # rename do 1º output; pai vazio → nada
        return {edge.to_key: _first(parent_outputs)} if parent_outputs else {}

    # spread: sanционado APENAS quando o pai declara 1 saída, ou a aresta é sub-fluxo
    return dict(parent_outputs)
```

Regras (o "padrão" strict — validadas contra o código real):
- **Modo mapeado** (`from_key` presente): único caminho para grafos novos. `to_key`
  default = `from_key`.
- **Run leniente; erro estrito no `/validate`** (decisão de implementação). O
  `resolve_edge_inputs` só enxerga `parent_outputs` (o que o pai emitiu no run) e **NÃO
  levanta**: um `from_key` sem correspondência **omite** a porta — não injeta valor alheio
  nem `None`, não estoura. É o fim do "primeiro valor" cego (raiz do F5/F14) sem trocar um
  cross-feed silencioso por um crash em produção: uma saída opcional/dinâmica ausente num
  lote não pode derrubar um fluxo legítimo. A checagem de `from_key` **não-declarado**
  (typo/defasado = erro) mora na validação ESTÁTICA (`/validate`, §7), que tem as chaves
  declaradas do pai à mão e acusa antes de rodar, sem falso-positivo de runtime.
  - `from_key` presente mas não emitido neste run (balde vazio do Switch — F5; saída
    opcional) → contribui **nada**. Correção na FONTE: o Switch passa a emitir TODOS os
    baldes declarados (vazios inclusive), então um `from_key` de balde vazio resolve para
    um container vazio em vez de sumir e cruzar outro balde.
  - pai **skipado** → a aresta **some** do merge (não injeta `None`, F14). Como pai
    skipado e pai que retornou `{}` são indistinguíveis no resolvedor, o run detecta o
    skip por `node_stats[...]['status'] == 'skipped'` e pula a aresta antes de resolver.
- **Modo só-`to_key`** (sem `from_key`): rename do 1º output do pai — permanece (contrato
  real, ex.: `SubWorkflowInput`→nó multi-porta, `static_output=[]`). Pai vazio → não
  contribui. A ambiguidade (origem multi-saída sem `from_key`) é sinalizada no `/validate`
  como **aviso**, não bloqueia o run.
- **Modo spread** (nenhuma chave): **permanece legal** — é o fan-out do `SubWorkflowInput`
  e a base dos nós sem schema que leem `next(iter(inputs.values()))`. NÃO vira erro. A
  validação (§7) emite aviso quando o pai tem >1 saída (heurística de aresta não mapeada).
- **Aresta de ramo** (`is_branch`): o roteamento passa a gatear por `Edge.is_branch`
  (`condition` bool), **não** pelo output cru `"branch"` (mata F7/F8). O dado é mapeado
  como qualquer outra aresta — a UI já grava `from_key` (o dado, ex.: `result`) na aresta
  de ramo; `__branch__` namespaced é desnecessário (a UI só persiste `condition` bool ou
  ausente).

Substituições:
- `core.py:576-601` passa a montar `inputs` chamando `resolve_edge_inputs` por aresta
  (spread = `inputs.update`, mapeado = `inputs[k] = v`).
- `core.py:795-807` (simulação) usa o MESMO resolvedor sobre o schema simulado — mata a
  divergência run × preview. Fim do `to_key or from_key or parent_id`.

**Paridade run × preview.** As duas funções — `resolve_edge_inputs` (valores, no run) e
`resolve_edge_schema_inputs` (tipos, no preview) — nomeiam EXATAMENTE as mesmas portas
para o mesmo grafo. Sob strict (implementado):
- **`from_key` sem match** (não emitido no run / não presente nos campos do preview) →
  ambos **omitem** a porta (`{}`). Fim do "primeiro valor" e do sentinela `<unknown>`:
  run e preview omitem igualmente, então a paridade vale inclusive com o pai vazio
  (`{}` == `{}`).
- O **erro** de `from_key` defasado NÃO vive no resolvedor (que apenas omite) e sim no
  `/validate` (§7), que compara contra o schema declarado da origem. Mudar um lado sem o
  outro reabriria a divergência run × preview — por isso `resolve_edge_inputs` e
  `resolve_edge_schema_inputs` andam sempre juntos.

## 5. Sem migração — strict por padrão (decisão do dono)

Não há migração de dados nem `schema_version`. O engine já é "uma versão só"; strict passa
a ser o comportamento único. `auto_map_edges` (`node_manager.py`, chamado em `core.py:158`)
é **removido do runtime** — validado como no-op salvo para params legados
`outputKey*/inputKey*`, que nenhum nó nem o front atual emitem.

Ponto adversário a ter em mente (validado): remover `auto_map_edges` **não** faz o legado
"estourar" — uma aresta legada sem `from_key` cai em **spread silencioso** (dict inteiro do
pai no filho), que pode entregar dado errado sem erro. Como são poucos workflows e o dono os
corrige à mão, isso é aceito; opcionalmente, `core.py` loga um `warning` quando uma aresta
cai em spread tendo o pai >1 saída (transforma a regressão silenciosa em linha acionável).

Limpeza coordenada ao aposentar o backfill: remover `_PREFIXOS_LEGADOS`
(`parameter_validation.py`), ajustar `test_parametro_descartado.py`, e atualizar
`docs/creating-nodes.md` (§97-170), que ainda ensina o padrão `inputKey/outputKey` — nenhum
nó do repo o segue, mas um nó novo escrito a partir do doc defasado misrotearia sem o
backfill.

## 6. Web

Estado validado: o front **já** nasce quase-strict — `handleConnectNodes` (`index.tsx:
504-527`) e o botão "+" do drawer (`nodes-drawer.tsx:107`) gravam `from_key = 1º candidato`
sempre que a origem declara saídas, **inclusive** nas arestas de ramo (`from_key` do dado
de passagem). Os comentários em `conditional.py`/`jinja_branch.py`/`change_detector.py`
("ramo nasce sem from_key") estão defasados (ainda NÃO corrigidos no código — ver PR-C).
Estado dos buracos:
- **F9 — RESOLVIDO.** `escolherChave` (`custom-edges/index.tsx:101`) agora sincroniza o
  `sourceHandle` ao trocar `from_key` via `sourceHandleDaChave` (`:117,127`), mantendo a
  invariante `sourceHandle == from_key` para nó multi-saída.
- **Picker desabilitado no ramo (PENDENTE)** (`custom-edges/index.tsx:99`): `podeTrocar`
  ainda exclui handles `true/false` (`!HANDLE_DE_RAMO.has(handleKey)`), então um `from_key`
  errado numa bifurcação continua sem UI de correção. Habilitar `podeTrocar` mesmo com
  handle `true/false` (a cor/rota segue vindo do handle; só o DADO passa a ser escolhível).
- **F10 — RESOLVIDO.** `useCanvasHistory` captura um baseline logo após a hidratação
  (função de reset do histórico), então a 1ª edição de aresta passou a ser desfazível.
- Validação no canvas (PENDENTE): marcar visualmente aresta **ambígua** (origem multi-saída
  sem `from_key`) antes do run — reaproveita `losingEdgeIds`/estilo de aresta.
- `AtlansEdgeData` tipado (PENDENTE — ainda não existe); remover os `as string` soltos.

## 7. Validação & contrato

- `app/services/validate_service.py::validar_definicao` (a validação estática; hoje quem a
  consome é a tool `validate_workflow` do MCP — a casca REST `POST /workflows/validate` saiu
  por não ter chamador) devolve, além do schema por nó,
  diagnósticos de aresta sob a chave reservada `__edge_diagnostics__`
  (`WorkflowExecutor.validate_edges()`): `from_key` que **não é** saída declarada da
  origem → **erro** (fiação defasada); aresta de dado sem `from_key`/`to_key` de origem
  multi-saída → **aviso** de ambiguidade. Origem sem schema conhecido não gera
  diagnóstico. Usa o schema simulado (`resolve_edge_schema_inputs`) como fonte das portas.
- **Corpo aceito** (PR 3 da Fase 0 do MCP): `nodes[]` = `{id, name, type, parameters?,
  properties?, alias?}` — `properties` é sinônimo de `parameters` (em conflito, `parameters`
  vence), `alias` é opcional e chega ao executor, `position` é ignorado; `workspace_id`
  opcional no topo; `edges[]` inalterado (`source`, `target`, `from_key?`, `to_key?`,
  `condition?`).
- **Sessão de banco só quando precisa**: abre apenas se há `credential_id` (UUID válido) ou
  `workspace_id`; o caso comum (definição solta) não paga conexão. Com `workspace_id`: **403**
  se o usuário não é membro (`get_workspace_member_role`, checada ANTES das credenciais — não
  revela a existência de credencial a quem não é do workspace); as credenciais compartilhadas
  com o workspace só entram no escopo para papel **`operator` ou superior** — o mesmo exigido
  para executar, porque a simulação do `DatabaseSpatialQuery` conecta ao banco da credencial;
  abaixo disso vale só o escopo do próprio usuário e `hints` avisa. Nunca as privadas de
  outros membros — `assert_credentials_accessible(…, shared_workspace_id)` na guarda e
  `credential_scope({user}, shared_workspace_id=…)` na simulação. Nós desabilitados
  (`disabled_names`) são checados sempre que há sessão; referências de sub-fluxo
  (`validate_subworkflow_references_against_db`) **só com `workspace_id`** — sem filiação
  provada, a consulta por hash seria um oráculo de existência, estado e portas de workflows
  de outros workspaces; e, com `workspace_id`, a consulta filtra pelo workspace, então alvo
  de outro workspace lê como `nao existe` (ativo ou não — o mesmo vale para o create/update
  de workflow, que usam a mesma função). Credencial fora do escopo → **403** antes de
  simular (sem `workspace_id`, a mensagem sugere informá-lo); `credential_id` que não é
  UUID → **422** `invalid_definition` (`invalid_credential_id`), sem ir ao banco. Sem `workspace_id`,
  `subworkflow_errors` vem `null` (e `disabled_nodes` também, quando nenhuma sessão abriu) e
  `hints` pede `workspace_id` — inclusive no `report` do 422.
- **Lint ANTES de construir o executor** (`flow/utils/definition_lint.py`, puro — sem banco
  nem executor). Códigos fatais → **422**
  `{"error": "invalid_definition", "message": "Definição inválida: …", "report": {…}}`
  (`DefinicaoInvalidaError`, `app/core/exceptions.py`; `report` tem a mesma forma do
  `__report__` abaixo, com `ok: false`):
  `unknown_node` (mensagem começa com `Node '<name>' não encontrado para instância
  (id=<id>).`; só é fatal para nó que entraria na ordem de execução — isolado ou fora do cone
  do trigger fica como erro no relatório, porque o construtor nem o instancia),
  `duplicate_node_id`, `cycle`, `construction_error` e `invalid_credential_id` (fatal por
  contrato, não por construção: o id nunca chega ao banco, e quem só olha o status HTTP —
  o `validar.py` da skill — reprovava com o 403 de antes e continua reprovando). Nó
  inexistente e ciclo estouravam em 500 antes; id duplicado passava em silêncio (o último
  vencia) e agora é recusado de propósito. Códigos **não fatais** (resposta 201, dentro de
  `__report__`) — erros: `invalid_alias`, `reserved_alias` (`RESERVED_ALIASES`,
  `flow/core/aliases.py` — saiu de `flow/executor/core.py`), `duplicate_alias` (quando há
  `alias` explícito), `secret_in_definition` (expressões `{{ }}`/`$Alias` e esquemas como
  `Bearer` não contam), `invalid_json_property` (propriedade `object` com JSON ilegível — o
  run falha no `validate()` do nó), `empty_fallback_output` (Switch com `fallback_output: ""`
  — o run emite a porta `''`, que nenhuma aresta nomeia: fiação morta que o diagnóstico de
  aresta não enxerga), `disabled_node`, `subworkflow_reference`, `edge_from_key_unknown`,
  `simulate_error`; avisos: `orphan_edge`, `unreachable_node`, `undeclared_property`,
  `missing_required_parameter`, `duplicate_alias` (derivado do `name` e referenciado),
  `edge_spread_ambiguous`. O lint é linear no tamanho da definição (tokenizador de blocos
  Jinja com `str.find`, teto por string e um índice único de nomes referenciados para a
  checagem de alias duplicado). Os diagnósticos de aresta
  seguem em `__edge_diagnostics__` (formato de hoje, só quando há) e aparecem também no
  `__report__` como `edge_from_key_unknown` (erro) / `edge_spread_ambiguous` (aviso).
- **`__report__` (sempre presente na 201)**: `{"ok": bool, "errors": [...], "warnings": [...],
  "disabled_nodes": list|null, "subworkflow_errors": list|null, "suggested_params_schema":
  {nome: {"type": "string", "required": true}}, "hints": [str]}`. Cada item de
  `errors`/`warnings` tem exatamente `{code, severity, node_id, edge, message}` — `node_id` e
  `edge` podem ser `null`; `edge` = `{"source", "target"}` ou `{"source", "target",
  "from_key"}`. `ok` é `false` quando há qualquer erro (avisos não derrubam);
  `simulate_error` espelha o nó que saiu da simulação com `status: "error"`.
  `suggested_params_schema` é **heurístico**: referências `inputs.<nome>` só em nós
  `type == "trigger"` (nos demais, `inputs` é a entrada das arestas) e `ports` de
  `SubWorkflowInput` — quando vem não-vazio, `hints` diz para revisar antes de gravar em
  `params_schema`.
- **Schema por nó e `schema_source`**: cada nó sai como `{"status": "ok", "schema":
  [{"fields": [{"name", "type"}]}], "schema_source": "static" | "simulated" | "declared" |
  "unknown"}` ou `{"status": "error", "error": "…"}` (`unknown` = nó `dynamic_output` sem
  `simulate()` e sem nada declarável — schema vazio, mas o nó não some; `output_vars` que o
  run rejeitaria vira `status: "error"` com a mensagem do runtime). Nó `dynamic_output`
  **sem** `simulate()` deixa de sumir
  da resposta: as saídas vêm da definição, nesta ordem — `output_vars` (PythonScript) →
  `rules[].output` + `fallback_output` (Switch) → `ports` (`outputs_from_ports`,
  `SubWorkflowInput`) → `static_output` (normalizado; a forma plana `[{name, type}]` vira
  `[{"fields": […]}]`) — com `schema_source: "declared"`. `validate_edges` passa a enxergar
  esses nós, então o "origem sem schema conhecido" acima ficou restrito a quem não declara
  saída de forma nenhuma.
- **Chaves reservadas**: consumidores devem pular toda chave que começa com `__`
  (`__edge_diagnostics__`, `__report__` e o que vier) ao iterar os schemas por `node_id`.
- **Onde mora o enforcement strict: na validação ESTÁTICA (`/validate`), não no run.** O
  run é resiliente de propósito — um `from_key` sem correspondência **omite** a porta (não
  levanta), para que uma saída opcional/dinâmica ou um pai skipado não derrube um fluxo
  legítimo em produção (ver §4). A checagem estática tem o schema declarado à mão e pode
  acusar o `from_key` defasado ANTES de rodar, sem risco de falso-positivo.
- **Enforcement na ESCRITA** (create/update) **não** é feito — bloquearia salvar
  rascunhos quebrados; `/validate` reporta e o run tolera.

## 8. Fases / PRs (reordenado após a validação de raio de impacto)

> **Estado atual (verificado contra o código):** PR 1, PR-A, PR-B, PR-C e PR-D estão
> IMPLEMENTADOS e mergeados. O backend do PR-E (`/workflows/validate` + `validate_edges`)
> também está. Restam apenas itens de front do PR-E (ver marcações abaixo e §6). A ordem
> abaixo descreve o sequenciamento histórico; não é mais um backlog aberto. A validação
> robusta do `/validate` (lint + 422 estruturado + saídas declaradas, §7) entrou depois, no
> PR 3 da Fase 0 do MCP (`docs/specs/mcp-server.md` §6.3).

Sem a camada de migração, a ordem foi do mais isolado ao mais acoplado. O acoplamento real
é SEMÂNTICO — strict × pai skipado vazio —, então o strict entrou por ÚLTIMO, depois que
skip (PR-B) e roteamento (PR-C) já estavam corretos.

- **PR 1 — Resolvedor único (FEITO).** `Edge` + `edge_resolver`
  (`flow/executor/edge_resolver.py`), os dois sites do `core.py`, paridade run × preview
  (inclui pai vazio, F3/F12). Risco: baixo.
- **PR-A — Robustez de grafo (F1) — FEITO.** Aresta órfã (`source`/`target` ∉ `node_defs`)
  é descartada e logada em `graph.py` (`_index_edges:44-58`; a mesma guarda em
  `compute_order:70-79`). Não derruba mais o run. Risco: baixo.
- **PR-B — Correção de skip (F2) — FEITO.** `skipped` só é marcado quando NÃO há pai vivo
  com output: o run rastreia `has_live_input` (`core.py:558`, marcado em `:662`, honrado em
  `_propagate_skip:711`), independente da ordem do batch. Risco: médio.
- **PR-C — Roteamento por `Edge.is_branch` (F7/F8) — FEITO** (código); higiene pendente.
  `core.py:637-646` roteia só quando existem arestas de ramo
  (`Edge.from_dict(e).is_branch`, `condition` bool) E `outputs["branch"]` é bool (mata F7); mantém
  ativas TODAS as arestas de dado e desativa só arestas de ramo com `condition != branch`
  (mata F8). **Pendente (higiene):** os comentários defasados em
  `conditional.py`/`jinja_branch.py`/`change_detector.py` ("ramo nasce sem from_key" — hoje
  nasce COM) ainda NÃO foram corrigidos (verificado: o comentário segue em
  `conditional.py:252-258`). Risco: médio.
- **PR-D — Strict + aposenta `auto_map_edges` (F5/F14 + §4/§5) — FEITO.** O run não chuta
  mais: `from_key` sem match **omite** a porta (`edge_resolver.py:78-92`, fim do
  `_first_value` cego); pai skipado dropa a aresta (`core.py:593`, via `node_stats` status);
  Switch emite todos os baldes, vazios inclusive (`switch.py:145-172`). `auto_map_edges`
  removido — `node_manager.py` só tem `instantiate_nodes`; ver o comentário em
  `core.py:158-162`. `resolve_edge_schema_inputs` alinhado no mesmo eixo (`core.py:852`).
  Risco: médio-alto.
- **PR-E — Validação + web (F9/F10/F11 + tipos).** **Backend FEITO:**
  `/workflows/validate` devolve `__edge_diagnostics__` via `validate_edges()`
  (`validate_service.py::validar_definicao`, `core.py:861-918`); F11 (`schema == []`) guardado em
  `core.py:850-851`. **Front — parcial:** F9 (sincronizar `sourceHandle` ao trocar
  `from_key`) FEITO em `custom-edges/index.tsx:117,127`; F10 (baseline de histórico no load)
  FEITO em `useCanvasHistory.ts`. **Ainda pendentes:** habilitar o picker em arestas de ramo
  (`podeTrocar` ainda exclui handles `true/false`, `custom-edges/index.tsx:99`) e tipar
  `AtlansEdgeData` (§6). Risco: baixo.
- **Validação no `/validate`: lint + 422 estruturado + saídas declaradas — FEITO (PR 3 da
  Fase 0 do MCP, `docs/specs/mcp-server.md` §6.3).** Pré-checagens antes de construir o
  executor (`unknown_node`/`duplicate_node_id`/`cycle`/`construction_error` → 422
  `invalid_definition`), `__report__` sempre presente com códigos de erro/aviso,
  `schema_source: "declared"` para nó `dynamic_output` sem `simulate()`, `workspace_id`
  opcional com o escopo de credenciais do dispatch e sessão de banco só quando há o que
  checar (§7). Não substitui a validação no canvas (§6, ainda PENDENTE): a marcação visual da
  aresta ambígua continua item de front.

Cada PR foi mergeável isolado e reversível.

## 9. Plano de testes

- Unit do `edge_resolver`: os modos (from_key achado / só to_key / spread) + ramo; sob
  strict `from_key` sem match → omite a porta (nada), pai skipado → aresta ausente. O
  `from_key` não-declarado como erro é testado no `/validate` (`validate_edges`).
- Regressão do Switch: balde vazio em run legítimo NÃO estoura (Switch emite todos os
  baldes) e NÃO entrega dado de outro balde (F5).
- Regressão da bifurcação: reproduzir o caso `dca88dc` (dado × booleano) e travar; nó comum
  que emite `branch` cru NÃO sequestra roteamento (F7); aresta de dado saindo de nó de ramo
  não é desativada (F8).
- Regressão do diamante/merge: nó com pai vivo + pai skipado NÃO é skipado (F2, determinismo
  independente da ordem do batch).
- Aresta órfã: run não estoura com `KeyError`; aresta ignorada e logada (F1).
- Paridade run × simulação: para o mesmo grafo, chaves do run == chaves do preview —
  **incluindo pai vazio e `from_key` sem match** (ambos OMITEM a porta, `{}` == `{}`).
- E2E web: conectar origem multi-saída → `from_key` gravado; trocar `from_key` pelo picker
  mantém `sourceHandle == from_key` (F9); 1ª edição de aresta é desfazível (F10).

## 10. Riscos & rollback

- **Sem migração**: aresta legada sem `from_key` vira spread silencioso ao remover
  `auto_map_edges` — pode entregar dado errado sem erro. Mitigação: `warning` de spread com
  pai multi-saída (§5); os poucos workflows afetados são corrigidos à mão.
- **strict × pai skipado**: `core.py:575-585` monta inputs sobre TODAS as arestas de
  entrada, inclusive de pais skipados (`output = {}`). O strict tem de tratar o pai
  vazio/skipado como "não contribui", nunca "chave faltando" — senão todo diamante com
  `from_key` na aresta de merge do ramo perdedor falha. Por isso o PR-D vem depois do PR-B.
- **Divergência run × preview**: mudar o run strict sem alinhar `resolve_edge_schema_inputs`
  reabre o bug que o PR 1 fechou — os dois andam no mesmo PR (PR-D).
- **Ordem de `static_output`**: a defesa nos nós de controle só sai depois que o roteamento
  passa a gatear por `Edge.is_branch` (PR-C).

## 11. Sucesso

- Um resolvedor; zero divergência run × preview.
- 0 usos de `next(iter(...))` cego no eixo de aresta; o run omite em vez de chutar, e o
  `from_key` não-declarado vira erro no `/validate` (não crash no run).
- Roteamento gateado por `Edge.is_branch`; nós de controle sem comentário de "ordene o
  static_output ou vaza booleano".
- Aresta órfã não derruba o run; merge não skipa nó com pai vivo.
- Aresta com modelo tipado em engine e web.

## 12. Achados da validação do ciclo de vida (histórico — RESOLVIDOS)

Revisão adversária de todo o fluxo de vida da aresta (front → grafo → resolvedor → ramo/
skip → consumo → sub-fluxo). Os dois achados **dentro do PR 1** (F3 paridade com pai vazio;
F12 política de `from_key` ausente) foram corrigidos/documentados acima. Os pré-existentes
abaixo eram o backlog priorizado; **todos já foram implementados** — a tabela é histórica.
O `Sintoma` descreve o bug ORIGINAL (pré-correção); a coluna `Corrigido em` aponta o código
ATUAL (os números de linha antigos do backlog já não valem).

| # | Sev | Sintoma (original) | Corrigido em | Status |
|---|-----|--------------------|--------------|--------|
| F1 | **alta** | Aresta órfã (source/target inexistente) → `KeyError` em `compute_order`/instanciação derrubava o run. Caso real: front deleta nó e deixa a aresta; expansão de sub-fluxo. | `flow/core/graph.py:44-58` (descarta+loga) e `:70-79` | ✅ resolvido (PR-A) |
| F2 | **alta** | Diamante/merge: `_propagate_skip` zerava `pending` e skipava o nó mesmo com um pai VIVO tendo entregue dados — dependente da ordem do batch. | `flow/executor/core.py:558,662,711` (`has_live_input`) | ✅ resolvido (PR-B) |
| F7 | média | Qualquer nó que emitisse chave booleana `branch` sequestrava o roteamento; arestas sem `condition` viravam inativas → downstream skipado. | `flow/executor/core.py:639-646` (gate por arestas de ramo) | ✅ resolvido (PR-C) |
| F8 | média | Aresta sem `condition` bool saindo de nó de bifurcação era sempre desativada (`None != branch`). Mesmo bloco de F7. | `flow/executor/core.py:643-646` | ✅ resolvido (PR-C) |
| F5 | média | `from_key` inexistente caía no 1º valor: Switch (`dynamic_output`) com bucket vazio cruzava dados do bucket errado, silenciosamente. | `flow/executor/edge_resolver.py:78-92` (omite; retorna `{}`) + `switch.py:145-172` (emite baldes vazios) | ✅ resolvido (PR-D) |
| F14 | baixa | Pai skipado + aresta com `from_key` injetava `None` nomeado no merge. Mesma cascata de F5. | `flow/executor/core.py:593` (dropa a aresta) + `edge_resolver.py:78-92` | ✅ resolvido (PR-D) |
| F11 | média | `schema == []` (ex.: `SubWorkflowInput/Output`, `static_output:[]`) → `IndexError` na simulação marcava o filho como `error` e cascateava. | `flow/executor/core.py:850-851` (normaliza lista vazia) | ✅ resolvido (PR-E backend) |
| F9 | média | Trocar `from_key` pelo badge não atualizava `sourceHandle`: após reload a aresta multi-saída redesenhava da porta errada. | `web/.../custom-edges/index.tsx:117,127` (`sourceHandleDaChave`) | ✅ resolvido (PR-E) |
| F10 | média | Sem snapshot de baseline no load: a PRIMEIRA edição de aresta não era desfazível. | `web/app/hooks/workflow/useCanvasHistory.ts` (baseline pós-hidratação) | ✅ resolvido (PR-E) |

Itens de front que PERMANECEM abertos (ver §6): habilitar o picker de `from_key` em arestas
de ramo (`custom-edges/index.tsx:99`); marcação visual de aresta ambígua no canvas; tipar
`AtlansEdgeData`; e a higiene dos comentários "ramo nasce sem from_key" em
`conditional.py`/`jinja_branch.py`/`change_detector.py` (PR-C).
