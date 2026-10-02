# Histórico (métricas de execução) — redesenho

Data: 2026-09-06. Estado: em implementação.

A rota `/observability` ("Histórico" na sidebar) passa a responder quatro
perguntas, nesta ordem: **está tudo bem agora?** · **como foi o período?** ·
**o que precisa de atenção?** · **qual execução, exatamente?**

Este documento é o contrato entre backend e web. O que está aqui é o que os
dois lados implementam; o que não está, não entra nesta rodada.

## 1. Decisões

| Decisão | Motivo |
|---|---|
| Período (7/30/90 dias) no cabeçalho, uma vez, e todos os blocos obedecem | Hoje o seletor mora no gráfico e governa oito cards sem dizer isso |
| Quatro indicadores do período, cada um comparado ao período anterior de mesmo tamanho | 1.284 execuções é muito ou pouco? Só a comparação responde |
| Taxa de sucesso = concluídas ÷ (concluídas + falhas) | A fórmula atual põe em andamento e canceladas no denominador e cai em pico de carga |
| Duração típica = mediana das concluídas, com p95 ao lado | A média inclui falhas, zeros do agendador e órfãos; uma execução de 40 min entre cem de 30 s vira "54 s" |
| Faixa "Agora": em andamento, na fila, presas, executores online, confirmações atrasadas | Nada na tela diz o que está acontecendo neste instante |
| "Precisa de atenção": falhas repetidas (com último erro), presas, executor no teto | O backend calcula `top_failing_workflows` e a tela descarta |
| Tabela de execuções em português, com erro na linha, nível (reserva/pool), origem e clique que abre a execução num painel | Linhas parecem clicáveis e não abrem nada; status em inglês; `error_message` e `dispatch_tier` chegam e não aparecem |
| Visões da mesma tabela: Execuções · Por workflow · Por executor · Confirmações (admin) | A aba Workflows é uma lista de nomes; a de Executores repete cards |
| Filtros por workspace, workflow, executor, status, origem e busca, todos na URL | A página soma todos os workspaces e ignora o seletor; F5 zera tudo |
| Saem: Total de workflows, Workflows ativos, Execuções (24h), Execuções (7 dias), Duração média, interruptor "Ativo" por linha de execução | Cadastro não é execução; três recortes do mesmo contador; desligar um workflow é ação de workflow, não de execução |
| Migração aditiva: `trigger_source`, `triggered_by`, `error_category` em `workflow_runs`; `schedule_id` gravado no despacho normal | "Agendado às 03:00" e "manual · ana" mudam o diagnóstico; hoje `schedule_id` só é gravado quando o agendamento falha |

## 2. Banco

`workflow_runs` ganha três colunas anuláveis (migração `20260909_0001`, revisão
`e1f4a2b7c935`, down `d9e3f1a5b624`; reversível):

| coluna | tipo | valores |
|---|---|---|
| `trigger_source` | VARCHAR(16) | `manual` · `retry` · `webhook` · `schedule` · `mcp` (agente via servidor MCP, `docs/specs/mcp-server.md`) |
| `triggered_by` | VARCHAR(36) | `id_hash` do usuário (nulo em webhook e agendamento) |
| `error_category` | VARCHAR(16) | taxonomia do flow (`user`, `validation`, `timeout`, `resource`, `transient`, `internal`) mais as do servidor: `no_executor` (despacho sem executor), `executor_lost` (executor desconectou), `isolation` (barreira de isolamento), `dispatch` (exceção no despacho) |

Escrita:

- `WorkflowService.start_analysis(..., triggered_by, trigger_source="manual", schedule_id=None)` repassa a `_dispatch_job`, que grava os três no `INSERT` do run `pending`.
- Chamadores: `POST /workflows/{id}/execute` → `manual`; `POST …/retry` → `retry`; webhook → `webhook`; agendador → `schedule` + `schedule_id`. O caminho de falha do agendador (`_registrar_falha_agendada`) grava `schedule`, `schedule_id` e `error_category="no_executor"` (falta de executor) ou `"internal"` (qualquer outra falha do dispatch agendado — antes engolida no log).
- `error_category`: no `job_result` (consumer) a partir de `payload["error_category"]`; `executor_lost` na desconexão; `no_executor` no despacho esgotado; `isolation` na barreira; `dispatch` na exceção do despacho.

Runs anteriores à migração ficam com tudo nulo; a web mostra "—".

## 3. API (`/observability`)

Filtros comuns (opcionais). `workspace_id` vale nos cinco endpoints (`/metrics`, `/runs-by-day`, `/metrics/workflows`, `/metrics/executores` e `/runs`); `workflow_id` só em `/metrics`, `/runs-by-day` e `/runs` (as visões "por workflow" e "por executor" não recebem recorte por workflow); `tz` só em `/runs-by-day`:

- `workspace_id`: para usuário comum precisa estar entre os seus workspaces (senão 403 `workspace_access_denied`); admin filtra qualquer um.
- `workflow_id` (só `/metrics`, `/runs-by-day`, `/runs`): precisa pertencer a um workspace acessível (senão 404).
- `tz` (só `/runs-by-day`): nome IANA (ex. `America/Sao_Paulo`) para cortar o dia; default `UTC`; inválido → 422.

Escopo continua o de hoje (admin vê tudo; usuário vê os workspaces onde é dono ou membro). Cache Redis de 45 s inclui os filtros na chave.

### 3.1 `GET /metrics?days=&workspace_id=&workflow_id=&force=`

Campos existentes continuam (`period_days`, `total_workflows`, `active_workflows`, `total_runs`, `failed_runs`, `avg_duration_seconds`, `runs_last_24h`, `runs_last_7d`, `runs_prev_7d`, `success_rate_prev_7d`, `by_status`, `top_failing_workflows`), com estas mudanças:

- `success_rate` = `success / (success + failed)` na janela; `0.0` quando o denominador é zero. `success_rate_prev_7d` segue a mesma fórmula.
- `by_status` ganha `cancelled` e `pending`; `other` passa a ser só o que não é nenhum dos cinco.
- `top_failing_workflows[]` passa a trazer `workflow_name`, `total_runs`, `failure_rate` (falhas ÷ total do workflow na janela), `last_error` (texto, até 200 caracteres), `last_error_category`, `last_failed_at`. Top 5 por `failure_count`.

Campos novos:

```jsonc
{
  "success_runs": 1235, "cancelled_runs": 3, "running_runs": 3, "pending_runs": 1,
  "prev_period": {            // janela anterior de mesmo tamanho (days..2*days atrás)
    "total_runs": 1147, "success_runs": 1118, "failed_runs": 29, "success_rate": 0.975,
    "p50_seconds": 38.0
  },
  "duration": { "p50_seconds": 42.0, "p95_seconds": 190.0 },   // só status success com duration > 0; null sem dados
  "now": {                    // SEM janela: o instante da consulta
    "running": 3, "pending": 1,
    "stuck_count": 1,
    "stuck": [{ "run_id": "…", "workflow_hash": "…", "workflow_name": "Cadastro rural · lote 7",
                "agent_host": "executor:…", "executor_name": "geo-02", "started_at": "…",
                "elapsed_seconds": 8040, "typical_seconds": 360 }],   // até 5, mais antigas primeiro
    "executors": { "online": 4, "total": 5 },                         // executores ativos no escopo
    "queued_on_executors": 12,                                        // soma de capacity.queued dos online; null se nenhum publica
    "overdue_acks": 2                                                 // admin; null para os demais
  }
}
```

"Presa" = `status IN ('running','pending')` há mais que `max(3 × p50 do workflow nos últimos 90 dias, 900 s)`; sem p50, `3600 s`.

Executores no escopo: admin → todos com `status='active'`; usuário → os acessíveis (`get_user_accessible_agents`). `online` via presença no Redis.

### 3.2 `GET /runs-by-day?days=&workspace_id=&workflow_id=&tz=`

`{ "days": [ { "day": "2026-09-06", "total", "success", "failed", "running", "cancelled", "other" } ] }`

- Todos os dias da janela, em ordem, com zeros onde não houve execução.
- Dia calculado em `tz` (`start_time AT TIME ZONE tz` no PostgreSQL; em SQLite, cálculo em Python).
- `running` = só `running` + `pending`; `cancelled` à parte; `other` = o resto.

### 3.3 `GET /metrics/workflows?days=&workspace_id=&force=` (novo)

```jsonc
{ "period_days": 30, "workflows": [ {
  "workflow_hash": "…", "workflow_name": "Integração SICAR", "workspace_id": "…", "workspace_name": "Cadastro",
  "active": true, "total_runs": 61, "success_runs": 33, "failed_runs": 28, "running_runs": 0,
  "success_rate": 0.54, "p50_seconds": 170.0, "last_run_at": "…", "last_status": "failed",
  "last_error": "Timeout ao consultar o WFS do SICAR (30 s)", "last_error_category": "timeout",
  "origem": "usuario"
} ] }
```

Todos os workflows acessíveis (inclusive sem execução na janela, com zeros); ordem: `total_runs` desc, nome asc. Cache de 45 s.

`origem` é a do FLUXO (`workflows.origem`: `usuario` | `assistente` — quem o criou), e não a do disparo. A visão "Por workflow" usa esse campo para o selo do assistente e para o chip de filtro, sem uma segunda chamada: o inventário vem inteiro e o recorte é local.

### 3.4 `GET /metrics/executores?days=&workspace_id=&force=`

Cada item continua com `agent_host`, `display_name`, `total_runs`, `success_runs`, `failed_runs`, `success_rate`, `avg_duration_seconds`, `last_run_at` e ganha:

`executor_id`, `executor_type` (`default`|`dedicated`), `is_default`, `status`, `online` (bool), `capacity` (`{running, queued, max_concurrent, max_queue}` ou `null` quando o executor não publica), `p50_seconds`.

A linha de runs sem host deixa de se chamar "desconhecido": `agent_host: null`, `display_name: "Sem executor"`, `unassigned: true` (são falhas de despacho). Executores online sem execução na janela também entram (com zeros), para a visão mostrar a frota inteira.

### 3.5 `GET /runs`

Filtros novos: `workspace_id`, `trigger_source`, `tier` (`primary`|`fallback`|`pool`), `q` (busca `ILIKE` em `error_message`, no nome do workflow e no id da execução). `date_from` já existe e a web passa a enviar o início da janela.

`workflow_origem` (`usuario`|`assistente`) recorta pela origem do FLUXO — o chip "Assistente" da barra. É outro eixo que `trigger_source` (o disparo) e combina com ele: um fluxo do assistente executado à mão casa `workflow_origem=assistente` e `trigger_source=manual`. Como `q`, exige o join com `workflows`, então runs de fluxos apagados de vez ficam fora do recorte (o recorte é sobre fluxos vivos); sem o parâmetro, a listagem segue sem join nenhum.

Cada run ganha, para qualquer usuário no escopo: `workflow_name`, `workspace_id`, `workspace_name`, `executor_id`, `executor_name` (nome amigável; `null` sem host), `trigger_source`, `triggered_by`, `triggered_by_username`, `error_category`, `schedule_id`, `workflow_origem` (`null` quando o fluxo foi apagado de vez). `workflow_active` e `owner_username` continuam admin-only.

### 3.6 `GET /runs/{run_id}`

Mesmos campos novos do 3.5, mais `typical_seconds` (p50 do workflow nos últimos 90 dias, `null` sem dados).

## 4. Web

Tudo novo em `web/app/components/observability/`; a página `page.tsx` só compõe.

### 4.1 Estado na URL (`historico-url.ts`, puro)

`?periodo=7|30|90&visao=execucoes|workflows|executores|confirmacoes&status=&workspace=&workflow=&executor=&origem=&assistente=1&q=&execucao=`

- `lerEstado(searchParams)` valida e devolve `EstadoDoHistorico` com defaults (`periodo=30`, `visao=execucoes`); valores inválidos caem no default.
- `assistente=1` é o chip "Assistente" (booleano; só "1" liga). O nome é próprio porque `origem` já é o DISPARO (`trigger_source`) e este recorta por quem CRIOU o fluxo — os dois convivem na URL e se combinam.
- `escreverEstado(estado)` devolve a query string sem os defaults (URL limpa).
- O hook `useHistoricoUrl()` lê com `useSearchParams` e grava com `router.replace` (sem scroll).

### 4.2 Textos (`formatos.ts` e `shared/status-rotulos.ts`, puros)

- `rotuloDoStatus`: `success`→"Concluída", `failed`/`error`→"Falhou", `running`→"Em andamento", `pending`→"Na fila", `cancelled`→"Cancelada", `cached`→"Cache", outro→o próprio texto. O `StatusBadge` passa a usar isto (vale para todas as telas).
- `formatarDuracao(segundos)`: `< 60` → "31 s"; `< 3600` → "4 min 02 s"; senão "2 h 14 min"; `null` → "—".
- `formatarInicio(iso, agora)`: `< 60 min` → "há 12 min"; hoje → "hoje, 03:00"; ontem → "ontem, 17:22"; mesmo ano → "4 set, 03:00"; senão "4 set 2025, 03:00".
- `rotuloDaOrigem`: `manual`→"manual", `retry`→"reexecução", `webhook`→"webhook", `schedule`→"agendado", nulo→null.
- `rotuloDaCategoria`: `timeout`→"tempo esgotado", `no_executor`→"sem executor", `executor_lost`→"executor caiu", `isolation`→"isolamento", `user`→"erro do fluxo", `validation`→"validação", `resource`→"recursos", `transient`→"transitório", `internal`→"interno", `dispatch`→"despacho".
- `rotuloDoNivel`: `primary`→null (não se marca o normal), `fallback`→"reserva", `pool`→"pool".
- `variacao(atual, anterior)` → `{ pct, delta, direcao: 'sobe'|'desce'|'igual' } | null`.

### 4.3 Blocos

- **Cabeçalho**: "Histórico" + subtítulo "Execuções dos seus workflows · comparado com os N dias anteriores"; à direita, segmentado 7/30/90 e "Atualizar" (`<Button variant="ghost" size="sm" disabled={carregando}>`). NOTA: o carimbo de frescor "atualizado há X s" **não é renderizado** hoje — `textoDeFrescor` existe em `cabecalho.tsx` mas nunca é chamado, e `atualizadoEm` é rastreado no hook (`use-historico-dados.ts`) sem ser exibido.
- **Faixa Agora** (`agora-faixa.tsx`): "Agora · N em andamento · N na fila · N presa(s) há X · Executores a de b online · N confirmações atrasadas (admin)" + link "Ver em andamento →" (aplica `status=running`). Some o que é zero, exceto "em andamento". Atualiza a cada 30 s enquanto a aba está visível (o poll de ACK de 10 s continua só para admin).
- **Indicadores** (`indicadores.tsx`): Execuções (tendência vs anterior, sparkline do total por dia), Taxa de sucesso (tendência em pontos, sparkline da taxa por dia), Duração típica ("42 s" + "5% mais lentas acima de 3 min 10 s"; mediana anterior na descrição), Falhas (delta absoluto, "28 delas em «X»" a partir de `top_failing_workflows[0]`). Menos falhas é verde. Cada card tem `aria-label` com o texto completo.
- **Gráfico por dia** (`grafico-por-dia.tsx`): Recharts sob `dynamic()`, barras empilhadas Concluídas / Falhas / Em andamento / Canceladas nas cores dos status; eixo X "8 ago"; tooltip em português; sem reanimar ao trocar de período (`isAnimationActive={false}` após a primeira pintura).
- **Precisa de atenção** (`atencao.ts` puro + `atencao-lista.tsx`): até 5 itens, nesta ordem: presas (`now.stuck`), falhas repetidas (`top_failing_workflows` com `failure_count ≥ 3` ou `failure_rate ≥ 0.2`), executores no teto (`capacity.running ≥ max_concurrent` e `queued > 0`). Cada item leva a uma ação: abrir a execução, filtrar a tabela pelo workflow com `status=failed`, abrir o executor. Itens que têm fluxo levam o selo do assistente quando a origem é resolvível (as métricas não a trazem: quem compõe a tela passa `origemDoWorkflow`, do inventário por workflow — no Dashboard, da listagem de fluxos). Vazio: "Nada pendente. Última falha há X." (ou "Nenhuma falha no período.").
- **Filtros** (`filtros.tsx`): chips de status (Todas / Falhas / Em andamento / Concluídas / Canceladas) com contagens de `by_status`; depois de um separador, o chip "Assistente" — alternador independente (combina com o status), SEM número, porque a contagem disponível é de fluxos e os outros chips contam execuções; selects Workspace (se o usuário tem mais de um, ou admin), Workflow (com a faísca nos do assistente), Executor, Origem; busca com debounce de 300 ms. O chip vira `workflow_origem=assistente` em `/runs` e, na visão "Por workflow", um recorte local do inventário.
- **Visões**: `tabela-execucoes.tsx` (Status · Workflow (workspace · origem · quem) · Início · Duração · Executor (+nível) · Erro · ›; ficha empilhada no telefone com `CELULA_COM_ROTULO`), `visao-workflows.tsx` (Workflow · Execuções · Sucesso · Duração típica · Última · Falhas/último erro · Ativo (admin, com confirmação ao desligar)), `visao-executores.tsx` (Executor · online · Em execução/fila · Execuções · Sucesso · Duração típica · Última), `visao-confirmacoes.tsx` (o card de ACK de hoje, com textos em português).
- **Painel da execução** (`painel-execucao.tsx`): `Sheet` à direita (largura padrão 520, redimensionável como o de executor); cabeçalho (workflow, status, nível, origem, quem disparou); fatos (início, duração + típica, executor, workspace); erro inteiro com categoria; nós com duração e o que falhou; ações: "Executar de novo" (`POST /workflows/{id}/runs/{run}/retry`, com confirmação), "Abrir workflow" (`/workflow/{id}`), "Ver log" (`/runs/{id}/events`, reaproveitando o painel de log existente quando houver), "Abrir em página" (`/observability/run/{id}`), "Copiar ID". Abre por `?execucao=` na URL.
- **Dados** (`use-historico-dados.ts`): quatro chamadas em paralelo por (período, filtros) com cache de 60 s por chave e carimbo de sequência (a resposta velha nunca sobrescreve a nova); falha parcial vira aviso na seção afetada, não silêncio.

Taxas coloridas por faixa usam `successRateColor(taxa, "amber")`: o amarelo padrão não tem contraste no tema claro.

### 4.4 Colaterais tratados

- `StatusBadge` em português (todas as telas).
- Visão geral (`/dashboard`): usa a `success_rate` corrigida automaticamente; o card "Workflows" deixa de mostrar sparkline de execuções.
- Detalhe do workflow (`/observability/{id}`): linhas levam à execução; link para o editor.
- Links "Ver todas no Observability"/"Abrir na observabilidade" passam a dizer "Histórico".
- `page.tsx.bak` removido.

## 5. Fora desta rodada

Histórico de capacidade dos executores, rollup de `workflow_runs`, tempo real na fila (`acked_at`), métricas por usuário com RBAC próprio, saúde do agendamento ("não rodou às 03:00" exige comparar `next_run_at` com o último run agendado; entra quando `schedule_id` tiver histórico).
