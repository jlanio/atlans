# Projetos (listagem de workflows) — redesenho

Data: 2026-09-07. Estado: implementado e integrado à base (exceção: a faixa
"Precisa de atenção" da §3.7 nunca foi construída — ver a nota lá).
Exemplo aprovado: mockup "Projetos, nova versão" (desktop 1440, telefone 390,
temas escuro e claro).

A rota `/projects` ("Projetos" na sidebar) é a estante do workspace ativo. Ela
passa a responder, nesta ordem: **qual workflow eu quero?** (achar e abrir em um
clique) · **o que ele é?** (gatilho, agendamento, portal, sub-fluxo) · **como
ele anda?** (última execução, falha, em execução) · **o que precisa de
atenção?**

Este documento é o contrato entre backend e web. O que está aqui é o que os
dois lados implementam; o que não está, não entra nesta rodada.

## 1. Decisões

| Decisão | Motivo |
|---|---|
| Uma ação primária no cabeçalho: **Criar workflow**. "Novo grupo" vira outline; "Atualizar" vira ghost | Hoje três botões do mesmo peso; criar grupo acontece uma vez por mês |
| ~~Faixa **Precisa de atenção**~~ (NÃO IMPLEMENTADA — ver §3.7): só quando há algo: falharam na última execução · agendamento pausado · ainda não executou | Nada na tela diz que o agendado das 6h falhou |
| Busca + chips com contagem (Ativos, Inativos, Em execução, Com falha, Agendados, Webhook, Sub-fluxos, Com portal, Assistente) + ordenação, tudo na URL | O filtro de status vive num dropdown; F5 zera tudo; a busca não acha grupos |
| Cada linha diz **o que é** (ícone do gatilho, metadados) e **como anda** (última execução com status, quando, erro resumido; em execução há X) | Um ponto de 8px é a única leitura de estado |
| O interruptor Ativado/Inativo sai do card: **Ativar** fica a um clique (ícone só na linha inativa); **Desativar…** vai para o menu, com confirmação que diz o que pausa | Ação arriscada no lugar mais visível, sem confirmação |
| A grade sai; fica uma lista só | Só mudava o número de colunas e cortava o nome |
| Grupos como seções: contagem certa ("3 workflows · 2 ativos"), descrição no cabeçalho, "vazio" em vez de "(0 workflows)", "Recolher todos"; **Sem grupo** vira seção com título | "(0 workflows)"; a API conta só ativos; os soltos aparecem sem título |
| Última execução vem de `GET /observability/metrics/workflows` (janela de 30 dias fixada pela web — o endpoint aceita `days` e assume 90 —, cache de 45 s), em paralelo com a listagem; se falhar, a lista sai sem a coluna e um aviso discreto oferece tentar de novo | Já existe, com escopo, resumo de erro e testes; "última vitalícia" na listagem seria varredura sem janela |
| Gatilho e agendamento entram na **listagem** (`WorkflowListItem`): quatro booleanos pelo mesmo mecanismo do selo Sub-fluxo e um resumo do agendamento por uma query a mais em lote | São a natureza do workflow, não execução; custo ~zero |
| Nome de quem alterou/criou entra na listagem (`updated_by_username`, `created_by_username`) | Workspace compartilhado: "alterado há 2 d por maria" |
| Ficam: prefetch do editor no hover, grupos recolhidos por workspace no `localStorage`, arrastar pela alça (workflow e grupo), confirmações que dizem a consequência, toasts com o nome, listagem magra (schema de parâmetros buscado no clique) | Decisões documentadas no código |
| Sem migração de banco | Tudo sai de expressões e queries sobre o que existe |

## 2. API

### 2.1 `GET /workflows?workspace_id=` — `WorkflowListItem` (aditivo)

Campos novos, todos com default, nenhum consumidor existente quebra
(`ActiveRunsContext`, `command-palette`, `sub-workflow-helper` leem só
`id_hash`/`name`/`description`).

```python
# Gatilhos — mesmo mecanismo de has_publish_map/is_subworkflow (`_tem_node`,
# LIKE sobre definition->>'nodes', que a query já parseia). Colisões de
# substring conhecidas e aceitas (documentadas no CRUD).
has_webhook_trigger:  bool = False   # _tem_node("WebhookTrigger",  "has_webhook_trigger")
has_schedule_trigger: bool = False   # _tem_node("ScheduleTrigger", "has_schedule_trigger")
has_file_trigger:     bool = False   # _tem_node("FileTrigger",     "has_file_trigger")
has_geofence_trigger: bool = False   # _tem_node("GeofenceTrigger", "has_geofence_trigger")
# "Só manual" = nenhum dos quatro e não é sub-fluxo — derivado na web.

# Agendamento — uma query a mais, em lote, mesclada em Python:
#   SELECT workflow_hash, active, next_run_at, last_run_at, strategy,
#          cron_expression, interval, unit, rrule_expression, timezone
#     FROM schedules WHERE workflow_hash IN (<hashes da página>)
# Se houver mais de uma linha por workflow: a ativa com menor next_run_at;
# sem ativa, qualquer uma. `next_run_at`/`last_run_at` são gravados UTC naive
# (ver `_to_utc_naive` no agendador): normalizar com tzinfo=UTC ANTES de
# devolver, senão o Pydantic serializa sem offset e a web lê como hora local.
schedule: Optional[WorkflowScheduleSummary] = None

class WorkflowScheduleSummary(BaseModel):
    active: bool
    next_run_at: Optional[datetime]      # None = pausado, ou recém-criado (o agendador preenche em ≤30 s)
    last_run_at: Optional[datetime]
    strategy: str                        # "cron" | "interval" | "rrule"
    cron_expression: Optional[str] = None
    interval: Optional[int] = None
    unit: Optional[str] = None
    rrule_expression: Optional[str] = None
    timezone: Optional[str] = None

# Autoria — uma query `users WHERE id_hash IN (...)` (mesmo padrão de
# `_nomes_de_usuarios` em observability/frota.py). Id sem linha em `users`
# (não há FK) → None; usuário excluído pelo admin (soft delete) mantém o nome.
created_by_username: Optional[str] = None
updated_by_username: Optional[str] = None
```

Onde: as quatro expressões entram em `_METADATA_COLUMNS` (`app/crud/workflow_crud.py`);
a mescla de agendamento e nomes fica em `WorkflowService.list_workflows_metadata`
e `list_workflows_metadata_by_ids` (`app/services/workflow_service.py`), que
passam a devolver dicts (os `RowMapping` do CRUD são imutáveis). A listagem
passa de 1 para 3 queries, todas por índice e em lote — nenhuma por linha.
`deleted_at` (sempre nulo) sai do schema.

### 2.2 `GET /workflow-groups` — `WorkflowGroupRead`

`workflow_count` passa a contar **todos** os workflows não excluídos do grupo
(`deleted_at IS NULL`); campo novo `active_count` conta os com `flag_ative`.
Uma agregação só (`count(*)` + `count(*) FILTER (WHERE flag_ative)`, ou
`sum(case …)` para valer em SQLite). Corrigir nos quatro pontos do router
(`create_group`, `list_groups`, `get_group`, `update_group`).

### 2.3 Reaproveitados, sem mudança

- `GET /observability/metrics/workflows?workspace_id=X&days=30[&force=1]` →
  `IWorkflowMetricsRow` por workflow: `last_run_at`, `last_status`, `last_error`,
  `last_error_category`, `total_runs`, `success_runs`, `failed_runs`,
  `running_runs`, `success_rate`, `p50_seconds`. Sempre com `workspace_id`. Os
  30 dias (`days=30`) são escolha da web (`JANELA_EM_DIAS` em `como-anda.ts`); o
  endpoint em si aceita qualquer `days` e assume 90 por padrão.
- `GET /observability/runs?status=running&limit=200` (já consumido pelo
  `ActiveRunsContext`): o contexto passa a guardar também `started_at`,
  `trigger_source` e `executor_name` de cada run vivo.
- `POST /workflows/{id}/execute`, `PUT /workflows/{id}/status`, grupos, mover,
  duplicar, excluir, portal: como hoje.

## 3. Web

### 3.1 Estrutura da página (de cima para baixo)

```
Projetos                                                  [Atualizar]  [Novo grupo] [+ Criar workflow]
10 workflows em 3 grupos · 8 ativos · 4 agendados · 2 com portal

[🔍 Buscar workflow ou grupo…]  [Ordenar: Nome ▾]  [Recolher todos]
(Todos 10) (Ativos 8) (Inativos 2) | (Em execução 1) (Com falha 2) (Agendados 4) (Webhook 1) (Sub-fluxos 1) (Com portal 2)

┌ ⋮⋮ ▾ Hidrologia  3 workflows · 3 ativos  Rotinas diárias da bacia                                  ⋯ ┐
│  ⋮⋮ [⏱]  Consolidação de outorgas                         ● Concluída há 3 h              [▶] [⋯]   │
│          Une as outorgas da ANA e do IGAM…                61 execuções em 30 d · 3 falhas · mediana 3 min │
│          Agendado todo dia às 06:00 · próxima amanhã, 06:00 · alterado há 2 d por maria                    │
│  …                                                                                                        │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ ⋮⋮ ▸ Entregas de campo  2 workflows · 1 ativo  (recolhido)                                            ⋯ ┐
┌ ⋮⋮ ▾ Rascunhos  vazio                                                                                ⋯ ┐
│     Nenhum workflow aqui. Arraste um para cá ou use "Mover para grupo" no menu do workflow.              │
SEM GRUPO  4 workflows · 3 ativos
   [Ta] Recorte por município  (Sub-fluxo)                    ● Concluída há 15 min          [▶ apagado] [⋯]
   …
```

Telefone (390px): cabeçalho empilhado (botão primário ocupa a linha, menu "⋯"
com Novo grupo e Atualizar); busca com a largura
inteira; chips rolam na horizontal; grupos e linhas em uma coluna; a linha
mostra ícone, nome + selos, metadados (gatilho/agendamento), como anda, e os
dois botões (40px) à direita; a descrição some; a alça de arrastar some
(mover pelo menu).

### 3.2 Módulos (`web/app/components/projects/`)

| Arquivo | Responsabilidade |
|---|---|
| `index.tsx` | Orquestra: dados, URL, DnD, diálogos, composição das seções. Sem lógica pura. |
| `projetos-url.ts` / `use-projetos-url.ts` | Estado na URL (§3.6). Mesmo padrão de `observability/historico-url.ts` + `use-historico-url.ts`. |
| `use-projetos-dados.ts` | Três chamadas em paralelo (§3.3), falha parcial, `atualizadoEm`, atualização periódica das métricas. |
| `gatilho.ts` | Deriva o gatilho e o resumo do agendamento (§3.4). Puro. |
| `como-anda.ts` / `como-anda-celula.tsx` | Deriva e renderiza a coluna "como anda" (§3.5). O componente tem nome próprio porque o webpack do Next resolve `.tsx` antes de `.ts` e o tsc faz o inverso. |
| `filtros.ts` / `filtros-barra.tsx` | Predicados e contagens dos chips; busca; ordenação; barra (§3.6). |
| `cabecalho.tsx` | Título, subtítulo com contagens, Atualizar, Novo grupo, Criar workflow. (Não há frescor "atualizado há X" no cabeçalho de Projetos — só no Histórico.) |
| `grupo-secao.tsx` | Cabeçalho do grupo, corpo, vazio, alvos de arrasto (§3.8). |
| `linha-workflow.tsx` | A linha (§3.9). Substitui `workflow-card.tsx` (que é removido). |
| `confirmar-desativar.tsx` | Diálogo de confirmação de desativar (§3.9). |
| `estados.tsx` | Skeleton, vazio de primeiro uso, sem resultado, aviso de métricas indisponíveis (§3.10). |
| mantidos | `dialog-content/*`, `grupos-colapsados.ts`, `ordem-dos-grupos.ts`, `selo-subfluxo.tsx` |

Formatadores reaproveitados de `web/lib/formatos.ts`: `formatarInicio`
("há 3 h" / "hoje, 18:00" / "ontem" / "4 set, 03:00"), `formatarDuracao`,
`rotuloDaOrigem`, `formatarInteiro`, `plural`. Rótulo de
status por `shared/status-rotulos.ts` (`rotuloDoStatus`).

### 3.3 Dados (`use-projetos-dados.ts`)

```ts
interface DadosDeProjetos {
  workflows: IWorkflow[]            // GET /workflows?workspace_id
  grupos: IWorkflowGroup[]          // GET /workflow-groups?workspace_id
  metricas: Map<string, IWorkflowMetricsRow> | null   // por workflow_hash; null = indisponível
  carregando: boolean               // primeira carga (skeleton)
  atualizando: boolean              // recargas seguintes (botão gira, lista fica)
  erro: string | null               // listagem ou grupos falharam (estado de erro com "Tentar de novo")
  metricasIndisponiveis: boolean    // só as métricas falharam (aviso discreto)
  atualizadoEm: number | null       // carimbo da última resposta aceita
  recarregar: (opcoes?: { force?: boolean }) => void
  // mutações locais (otimistas), usadas pelo index: setWorkflows/setGrupos ou equivalentes
}
```

- As três chamadas partem juntas (`Promise.allSettled`); listagem e grupos são
  obrigatórias, métricas não. `days=30`, sempre com `workspace_id`.
- Recarrega ao trocar de workspace (esperando `workspaceLoading`). "Atualizar"
  chama com `force: true` (fura o cache das métricas).
- Métricas atualizadas sozinhas a cada 60 s com a aba visível (só a chamada de
  métricas; a listagem não muda sozinha). Carimbo de sequência para descartar
  resposta atrasada, como em `use-historico-dados.ts`.
- `ActiveRunsContext` (`runningRuns`) tem precedência sobre `metricas` para
  "em execução" — é mais fresco (10 s).

### 3.4 Gatilho (`gatilho.ts`)

```ts
type TipoDeGatilho = "agendado" | "webhook" | "arquivo" | "geofence" | "manual" | "subfluxo"
interface Gatilho {
  tipo: TipoDeGatilho              // o principal, nesta precedência: subfluxo > agendado > webhook > arquivo > geofence > manual
  rotulo: string                   // "Agendado" | "Webhook" | "Por arquivo" | "Por geofence" | "Só manual" | "Chamado por outros workflows"
  extras: TipoDeGatilho[]          // demais gatilhos presentes (ex.: agendado + webhook) — o rótulo vira "Agendado + webhook"
}
function derivarGatilho(wf: Pick<IWorkflow, "is_subworkflow" | "has_schedule_trigger" | "has_webhook_trigger" | "has_file_trigger" | "has_geofence_trigger">): Gatilho

interface ResumoDoAgendamento {
  estado: "ativo" | "pausado" | "calculando"   // pausado = schedule.active false; calculando = ativo sem next_run_at
  descricao: string                            // "todo dia às 06:00" · "a cada 6 h" · "a cada 15 min" · "dia 1 às 08:00" · "seg–sex às 07:30" · "aos domingos às 02:00" · cron cru quando não reconhecido · "recorrência (RRULE)"
  descricaoCrua: boolean                       // descricao é a expressão cron sem tradução — o componente a mostra em `code`
  proxima: string | null                       // formatarInicio(next_run_at) → "hoje, 18:00" / "amanhã, 06:00" / "1 out, 08:00"; null quando pausado/calculando
  motivoPausa: "workflow inativo" | null       // quando pausado e o workflow está inativo
}
function resumirAgendamento(schedule: IWorkflowSchedule | null | undefined, flagAtive: boolean, agora?: Date): ResumoDoAgendamento | null
```

Cron reconhecido (5 campos): `M H * * *` → "todo dia às HH:MM"; `M H * * 1-5` →
"seg–sex às HH:MM"; `M H * * D` (um dia) → "às segundas às HH:MM" etc.;
`M H D * *` → "dia D às HH:MM"; `0 */N * * *` → "a cada N h" (`0 * * * *` → "a
cada 1 h"); `*/N * * * *` → "a cada N min" (`* * * * *` → "a cada 1 min").
Qualquer outro: o cron cru em `code`. Intervalo:
`interval`+`unit` → "a cada 15 min" / "a cada 6 h" / "a cada 2 dias".
A hora é a do cron no fuso do agendamento (`timezone`), sem converter — é o que
o usuário escreveu. `proxima` usa o relógio local do navegador (é um instante).
Selo/tile do gatilho na linha: agendado = relógio, webhook = raio, arquivo =
arquivo, geofence = pino, manual = play, sub-fluxo = ícone `TbSubtask` em
índigo (mesma cor do `SeloSubFluxo`).

### 3.5 Como anda (`como-anda.ts`)

```ts
type ComoAnda =
  | { tipo: "executando"; desde: string; instante: number; origem: string | null; executor: string | null; tipica: number | null }
  | { tipo: "concluida" | "falhou" | "cancelada"; quando: string; instante: number; erro: string | null; total: number; falhas: number; mediana: number | null }
  // `instante` (ms) é o carimbo usado para ordenar por "última execução" (§3.6).
  | { tipo: "sem-execucoes" }        // sem linha de métricas na janela, ou last_run_at null, e o workflow tem mais de 30 dias
  | { tipo: "nunca" }                // total_runs 0 e criado há menos de 30 dias → "Ainda não executou · execute uma vez para validar"
  | { tipo: "indisponivel" }         // métricas falharam
function derivarComoAnda(wf: IWorkflow, metrica: IWorkflowMetricsRow | undefined, emExecucao: RunningRun | undefined, metricasIndisponiveis: boolean, agora?: Date): ComoAnda
```

Renderização (`como-anda-celula.tsx`), duas linhas:
- executando: `● Em execução há 4 min` (azul, ponto com `motion-safe:animate-ping`) · `agendada · em geo-01 · costuma levar 7 min`
- concluida: `● Concluída há 3 h` (verde) · `61 execuções em 30 d · 3 falhas · mediana 3 min` (omite "· 0 falhas" → "nenhuma falha"; omite mediana nula)
- falhou: `● Falhou há 40 min` (vermelho) · erro resumido em vermelho, truncado, `title` com o texto inteiro
- cancelada: `● Cancelada há X` (cinza) · mesma segunda linha de concluída
- sem-execucoes: `○ Sem execuções em 30 dias` (cinza)
- nunca: `○ Ainda não executou` · `execute uma vez para validar`
- indisponivel: `— Sem dados de execução` (cinza), sem segunda linha

Sub-fluxo executado por outro: a origem vem em `trigger_source` só para o run
vivo; para a última execução não há "via X" barato — a segunda linha é a
contagem normal. (O mockup mostrava "via «Mapa de risco»"; fica fora.)

### 3.6 Busca, filtros, ordenação, URL (`projetos-url.ts`, `filtros.ts`)

```ts
type Filtro = "todos" | "ativos" | "inativos" | "executando" | "falha" | "agendados" | "webhook" | "subfluxos" | "portal" | "pausado" | "nunca"
type Ordem = "nome" | "execucao" | "alterado"
interface EstadoDeProjetos { q: string; filtro: Filtro; ordem: Ordem }
const ESTADO_PADRAO = { q: "", filtro: "todos", ordem: "nome" }
// URL: ?q=&filtro=&ordem=  (omitidos quando iguais ao padrão) — replace, não push, como no Histórico
```

- Chips (com contagem sobre a lista inteira, não a filtrada): Todos · Ativos ·
  Inativos | Em execução · Com falha · Agendados · Webhook · Sub-fluxos · Com
  portal | Assistente. O último fica depois do segundo separador e leva a
  faísca do selo: é o único que recorta por QUEM CRIOU o fluxo, não por uma
  propriedade dele. `pausado` e `nunca` existem só na URL (chegariam pela faixa de atenção
  da §3.7, não implementada; hoje só alcançáveis via query string); quando
  ativos, o chip "Todos" fica desmarcado e "Limpar filtros" aparece.
- Predicados: ativos = `flag_ative`; executando = em `runningHashes`; falha =
  `comoAnda.tipo === "falhou"`; agendados = `has_schedule_trigger`; webhook =
  `has_webhook_trigger`; subfluxos = `is_subworkflow`; portal =
  `has_publish_map && portal_access !== "disabled"`; assistente =
  `origem === "assistente"`; pausado =
  `schedule && !schedule.active`; nunca = `comoAnda.tipo === "nunca"`.
- Busca (`q`, sem acento e sem caixa — normalizar com `normalize("NFD")`):
  nome, descrição e **nome do grupo** (um grupo cujo nome bate mostra todos os
  seus workflows). `useDeferredValue` como hoje.
- Ordenação: nome (`localeCompare` pt-BR) · execução (última execução mais
  recente primeiro; sem execução por último) · alterado (`updated_at` desc).
  A ordem vale dentro de cada grupo e na seção Sem grupo; a ordem dos grupos é
  a `position` (arrasto), como hoje.
- Com busca ou filtro ativo, grupos sem nenhuma linha correspondente não
  aparecem; sem busca nem filtro, todos aparecem (inclusive vazios).
- Contagem no subtítulo do cabeçalho: sempre da lista inteira.

### 3.7 Precisa de atenção — NÃO IMPLEMENTADO (futuro)

> **Estado:** esta faixa NÃO foi construída na tela de Projetos. Não existem os
> módulos `atencao.ts` / `atencao-faixa.tsx` sob `web/app/components/projects/`,
> e o `index` não renderiza faixa alguma entre o cabeçalho e a barra de filtros.
> Os filtros `pausado` e `nunca` existem na URL (`projetos-url.ts`) e a barra
> mostra um chip provisório para eles (`filtros-barra.tsx`), mas **nada na UI os
> aciona** — só são alcançáveis digitando a query string à mão. O conceito hoje
> vive só na tela de Histórico (`observability/atencao.ts` + `atencao-lista.tsx`,
> `montarAtencao`). O desenho abaixo é o alvo, caso a faixa venha a ser portada.

```ts
interface ItemDeAtencao { chave: "falha" | "pausado" | "nunca"; n: number; texto: string; filtro: Filtro }
function montarAtencao(workflows, comoAndaPorHash, resumoPorHash): ItemDeAtencao[]  // só itens com n > 0; ordem: falha, pausado, nunca
```

Textos: "2 falharam na última execução" · "1 agendamento pausado" · "1 ainda
não executou". A faixa seria `<section aria-labelledby>`; cada item um botão
que aplica o filtro (`aria-pressed` quando é o filtro ativo); à direita, link
"Ver no Histórico" → `/observability?visao=workflows&workspace=<id>`. Sem
itens, a faixa não é renderizada. Pausado por workflow inativo conta como
pausado (é o que a pessoa vê: não vai rodar).

### 3.8 Grupos (`grupo-secao.tsx`)

- Cabeçalho: alça (só `canEdit` e mais de um grupo; `title="Arraste para
  reordenar os grupos"`), botão de recolher (`aria-expanded`, chevron), nome,
  contagem "3 workflows · 2 ativos" (ou "vazio"; singular "1 workflow · 1
  ativo"), descrição (truncada, some no telefone), menu ⋯ (`canEdit`): Renomear
  grupo · Excluir grupo (mesma confirmação de hoje, com a contagem).
- Contagem do cabeçalho: da lista inteira do grupo (não da filtrada); com
  filtro ativo, acrescenta "· N com este filtro" quando N < total.
- Corpo: linhas com `gap` de 6px; vazio: "Nenhum workflow aqui. Arraste um para
  cá ou use «Mover para grupo» no menu do workflow." (`canEdit`) / "Nenhum
  workflow neste grupo." (demais).
- Arrasto: mesmos alvos e estados de hoje (receber workflow: borda primária e
  "Solte para mover «X» para <grupo>"; reordenar grupo: tracejado e "Soltar
  aqui move o grupo para esta posição"; o arrastado a 40%). A zona "Solte aqui
  para remover do grupo" aparece ao arrastar um workflow agrupado, como hoje.
- "Recolher todos" / "Expandir todos" na barra de filtros (aparece só com
  grupos); persiste por workspace pelo mecanismo de `grupos-colapsados.ts`.
- Seção **Sem grupo**: título em caixa alta (eyebrow) + "4 workflows · 3
  ativos"; só existe quando há ao menos um grupo. Sem grupos, a lista sai sem
  título, e o convite "Agrupar workflows" (tracejado) continua aparecendo com
  mais de dois workflows, como hoje; a dica da alça no primeiro grupo também.

### 3.9 Linha do workflow (`linha-workflow.tsx`)

Grid desktop: `[alça 14px] [tile 34px] [principal 1fr] [como anda 260px] [ações]`;
altura mínima 56px; `border bg-card rounded-lg shadow-xs`; hover `bg-accent/40`.

- **Alça**: só com grupos (`hasDnd`), `cursor-grab`, some no telefone.
- **Tile** (34px, `rounded-lg bg-muted text-muted-foreground`; índigo para
  sub-fluxo): ícone do gatilho; ponto de 10px no canto inferior direito com
  borda da cor do card: verde ativo · cinza inativo · azul com `animate-ping`
  em execução. `title` com o rótulo do gatilho.
- **Principal**: linha 1 = nome (`<button>` `text-sm font-medium truncate`,
  abre o editor, `aria-label="Abrir <nome> no editor"`) + selos (`Sub-fluxo`
  índigo; `Portal público` / `Portal privado` teal com ícone mundo/cadeado
  quando `has_publish_map && portal_access !== "disabled"`; `Inativo` cinza;
  `Novo` primário quando criado há menos de 24 h); linha 2 = descrição
  (`text-xs text-muted-foreground truncate`, só quando existe; some no
  telefone); linha 3 = metadados (`text-xs text-muted-foreground`, separados
  por "·"): rótulo do gatilho em `font-medium text-foreground`, descrição do
  agendamento e "próxima <quando>" (ou "Agendamento pausado (workflow inativo)"
  em âmbar, ou "próxima: calculando…"), "alterado há X por <username>" (ou
  "criado há X por Y" quando `created_at === updated_at`; sem nome → só "alterado há X").
- **Como anda**: §3.5. No telefone vai para baixo do principal.
- **Ações** (`onClick` com `stopPropagation`): botão **Executar** (`aria-label="Executar <nome> agora"`,
  ícone play, borda; `canExecute`; desabilitado enquanto prepara/dispara; em
  sub-fluxo fica a 45% com `title` "Sub-fluxo: executar sozinho normalmente não
  faz o esperado", mas continua clicável); na linha **em execução** o botão
  vira "Ver execução" (ícone histórico → `/observability?execucao=<run_id>`);
  na linha **inativa** (`canEdit`) o lugar do Executar é **Ativar** (ícone
  interruptor, `aria-label="Ativar <nome>"`, sem confirmação, toast "«X» ativado");
  menu ⋯ (`aria-label="Mais ações de <nome>"`).
- **Clique na linha** abre o editor (como o card de hoje); o botão do nome é o
  alvo de teclado; a linha não tem `role`.
- **Prefetch** do editor no `onPointerEnter` (como hoje).
- **Menu** (ordem fixa; itens gateados como hoje): Abrir no editor · Ver
  execuções (→ `/observability?workflow=<id>`) · Duplicar (`canEdit`) ·
  Configurar (`canEdit`) · Configurar portal (`canEdit && has_publish_map`) ·
  — · Mover para grupo ▸ (`canEdit`, grupos ≠ o atual) · Remover do grupo
  (`canEdit && group_id`) · Mover para workspace (`canManage && podeMover &&
  workspace_id`) · — · Desativar… / Ativar (`canEdit`) · Excluir… (`canEdit`,
  vermelho).
- **Desativar…** abre `confirmar-desativar.tsx`: título "Desativar «X»?";
  texto "O agendamento e o webhook deixam de disparar até você ativar de novo.
  Execuções em andamento continuam." (quando não tem agendamento nem webhook:
  "Ele some dos gatilhos e não pode ser executado até você ativar de novo.");
  botões Cancelar / Desativar. Sucesso: toast "«X» desativado". Atualização
  otimista com reversão, como o `handleChangeActive` de hoje.
- `React.memo` com callbacks estáveis, como o card de hoje (o motivo está
  documentado lá; preservar).

### 3.10 Estados (`estados.tsx`)

- **Carregando** (primeira carga): skeleton com o cabeçalho real e três blocos
  de linha de 56px dentro de um contorno de grupo + duas linhas soltas.
  Recargas seguintes não mostram skeleton (a lista fica, o botão gira).
- **Vazio de primeiro uso** (`workflows.length === 0 && grupos.length === 0`):
  ícone, "Comece pelo primeiro workflow", parágrafo "Um workflow encadeia nós de
  leitura, processamento e saída. Ele roda quando você manda, num horário, ou
  quando um webhook ou um arquivo chega.", três passos (Desenhe · Execute uma
  vez · Agende ou exponha), botão "Criar o primeiro workflow" (`canEdit`; sem
  permissão: "Peça a um editor do workspace para criar o primeiro workflow.").
- **Sem resultado** (busca/filtro sem linhas): "Nenhum workflow com «q»" /
  "Nenhum workflow com este filtro" / "Nenhum workflow com «q» e este filtro";
  quando há resultado sem o filtro: "Há N com «q» sem o filtro."; botão
  "Limpar filtros".
- **Erro de carga** (listagem/grupos): bloco com "Não foi possível carregar os
  projetos", a mensagem, botão "Tentar de novo". Toast também, como hoje.
- **Métricas indisponíveis**: aviso de uma linha acima da lista, âmbar
  discreto: "Sem dados de execução agora — a lista continua completa. [Tentar
  de novo]"; as linhas mostram "— Sem dados de execução".
- **Sem permissão**: viewer vê tudo sem alça, sem Executar/Ativar, sem menu de
  grupo e com o menu do workflow reduzido a "Abrir no editor" e "Ver execuções".

### 3.11 Acessibilidade e movimento

- Chips: `<button aria-pressed>` dentro de `role="group" aria-label="Filtros"`.
- Faixa de atenção (§3.7, não implementada): seria `<section aria-labelledby>` com itens-botões.
- Grupo: botão de recolher com `aria-expanded` e `aria-controls` apontando para
  o corpo (`id` estável por `id_hash`).
- Linha: sem `role`; botão no nome; botões de ação com `aria-label` que inclui
  o nome; ícones `aria-hidden`.
- Alvos de 40px no telefone (`max-md:h-10 max-md:w-10`, `max-md:h-10` em
  chips e campos).
- Animações sob `motion-safe:`; o ping do "em execução" idem.
- Foco visível: `focus-visible:ring-[3px] focus-visible:ring-ring/50`.

### 3.12 Textos (pt-BR)

Cabeçalho: "Projetos" · "{N} workflows em {G} grupos · {A} ativos · {S} agendados · {P} com portal" (omitir partes com zero; sem grupos: "{N} workflows · …"; singular: "1 workflow") · "Atualizar" · "Novo grupo" · "Criar workflow". (Sem frescor "atualizado há X" — ver §3.1.)
Faixa (NÃO IMPLEMENTADA — ver §3.7): "Precisa de atenção" · "{n} falharam na última execução" / "1 falhou na última execução" · "{n} agendamentos pausados" / "1 agendamento pausado" · "{n} ainda não executaram" / "1 ainda não executou" · "Ver no Histórico".
Barra: placeholder "Buscar workflow ou grupo…" · "Ordenar:" Nome / Última execução / Alterado · "Recolher todos" / "Expandir todos" · "Limpar filtros".
Chips: Todos · Ativos · Inativos · Em execução · Com falha · Agendados · Webhook · Sub-fluxos · Com portal.
Gatilho: "Agendado" · "Webhook" · "Por arquivo" · "Por geofence" · "Só manual" · "Chamado por outros workflows" · "próxima {quando}" · "próxima: calculando…" · "Agendamento pausado" · "(workflow inativo)".
Como anda: "Concluída" · "Falhou" · "Cancelada" · "Em execução" · "Sem execuções em 30 dias" · "Ainda não executou" · "execute uma vez para validar" · "Sem dados de execução" · "{n} execuções em 30 d" · "nenhuma falha" / "{n} falhas" · "mediana {duração}" · "costuma levar {duração}" · "em {executor}".
Ações: "Executar agora" · "Ver execução" · "Ativar" · "Mais ações" · menu conforme §3.9 · toasts: `Workflow "X" iniciado!` (como hoje) · "«X» ativado" · "«X» desativado" · "Cópia criada: «Y»" (como hoje) · "Grupo excluído." (como hoje).
Grupos: "{n} workflows · {a} ativos" · "vazio" · "Nenhum workflow aqui. Arraste um para cá ou use «Mover para grupo» no menu do workflow." · "Sem grupo" · "Solte para mover «X» para {grupo}" · "Soltar aqui move o grupo para esta posição" · "Solte aqui para remover do grupo".
Estados: §3.10.

## 4. Fora de escopo

Número de nós; versão; "chamado por N sub-fluxos" (custo N²); período
configurável em Projetos; endpoint de agendamentos por workspace; painel
lateral de resumo antes do editor; mudar a cadência do `ActiveRunsContext`;
colunas novas em `workflows`; paginação da listagem.

## 5. Testes

- API (`tests/integration/`, SQLite, no molde de `test_listagem_marca_subfluxo.py`):
  os quatro booleanos de gatilho; `schedule` mesclado (ativo, pausado, sem
  `next_run_at`, mais de um schedule, `tzinfo` UTC no retorno); nomes de
  usuário (existente, apagado); `deleted_at` fora do payload; grupos:
  `workflow_count` conta inativos e ignora excluídos, `active_count`, nos
  quatro pontos.
- Web (`web/__tests__/components/projects/`): `gatilho` (precedência, cron
  reconhecidos e cru, intervalo, pausado, calculando); `como-anda` (cada
  tipo, precedência do run vivo, `nunca` × `sem-execucoes`); `filtros`
  (predicados, contagens, busca sem acento e por grupo, ordenações);
  `projetos-url` (ler/escrever, padrão omitido); `use-projetos-dados`
  (paralelo, falha parcial, sequência); `linha-workflow` (botão no nome, Ativar
  na inativa, Ver execução na em execução, menu por permissão, sub-fluxo
  apagado); `grupo-secao` (contagem, vazio, aria-expanded); `estados`;
  `index` (composição: seções, Sem grupo, chip filtra, busca por grupo,
  desativar pede confirmação e reverte em erro).
- E2E (Playwright, API real semeada): dobra 1440 e 390 nos dois temas; chips
  filtram e vão para a URL; busca por grupo; abrir editor pelo nome; Executar;
  Desativar com confirmação; Ativar; recolher e persistir; arrastar para grupo;
  sem console.
