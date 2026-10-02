# Dashboard (landing) — redesenho

Data: 2026-09-07. Estado: **parcialmente implementado**. Construído e no código hoje: cabeçalho (escopo +
período), faixa de **Saúde**, **Precisa de atenção | Próximas execuções**, e o
**Resumo do período** (indicadores + gráfico). **NÃO** construído nesta rodada
(ver §4): "Atividade recente", "Atalhos / Seus workspaces / Armazenamento", a
busca de `storage` no hook de dados, e o carimbo de frescor ("atualizado há X")
no cabeçalho. Exemplo aprovado: mockup "Dashboard, nova versão" (desktop 1440,
telefone 390, temas escuro e claro).

A rota `/dashboard` é a visão geral do **administrador do sistema** — restrita ao
admin por enquanto (o middleware barra quem não é admin, o mesmo portão de `/admin/*`;
some da sidebar e da paleta para os demais). A **landing** pós-login passou a ser a
Home `/` (globo 3D + assistente).
Papel próprio do Dashboard: **orientação + triagem + roteamento**, não análise. Abre respondendo
o AGORA e desce por prioridade operacional: **está tudo bem agora? → o que precisa
de mim? → o que vai rodar? → como andou?** (o "por onde entro?" — atalhos/roteamento —
ficou para depois; §4.)

Delimitação — regra de ouro: o Dashboard **resume e roteia**; as irmãs **detalham e
editam**. Nunca tem tabela filtrável, visões ou painel de execução embutido; nunca
lista/edita workflows (isso é Projetos); nunca gere workspaces (isso é Workspaces).
Reusar `indicadores`/`grafico-por-dia`/`atencao-lista` do Histórico é reuso de FAMÍLIA,
sem a superfície interativa (sem filtros, sem tabela, sem visões); a única herdada é o
**seletor de período** (7/30/90 dias), no cabeçalho.

## 1. Decisões

| Decisão | Motivo |
|---|---|
| **Escopo: workspace ATIVO por padrão, com um toggle "Todos os workspaces"** | Pedido do dono. O toggle troca o `workspace_id` de todas as chamadas (default = `WorkspaceContext.current`; "todos" = sem `workspace_id`). |
| Estado do escopo na URL: `?escopo=todos` (default = ativo, omitido) | F5/voltar/link preservam a escolha; espelha o padrão do Histórico |
| No escopo "todos", cada item de lista **diz o workspace** (etiqueta com cor); no escopo de um workspace, a etiqueta some (é redundante) | O que torna a visão global legível sem confundir |
| Faixa de **Saúde colorida** no topo (verde/âmbar/vermelho) com veredito em uma frase + a linha "agora" | Nada na tela dizia o instante; o dado (`now`) já vinha e era descartado |
| **Precisa de atenção** (presas, falhas repetidas, executor no teto) que resume e deep-linka ao Histórico/Executores | O backend calcula `top_failing_workflows` e a tela ignorava |
| **Próximas execuções** agendadas (forward-looking) — EXCLUSIVO do Dashboard | Nenhuma outra tela responde "o que vai rodar" |
| **Resumo do período: 7 / 30 / 90 dias (default 30), com seletor no cabeçalho** — o mesmo grupo do Histórico | Pedido do dono; a janela governa indicadores, gráfico e as falhas da atenção, como no Histórico |
| 4 indicadores comparados ao período anterior + gráfico de 4 séries — reuso de `observability/indicadores` e `grafico-por-dia` | Mesma família; sem a superfície do Histórico |
| Atividade recente enriquecida: status pt-BR, **workspace · origem · quando**, leva ao painel da execução — **não construído nesta rodada (§4)** | A atual tinha data crua e nenhum contexto |
| Atalhos de verdade (lidera **"Abrir «workspace ativo»"** + Novo workflow); lista "Seus workspaces" para rotear; armazenamento com quebra — **não construído nesta rodada (§4)** | "Duração média" sai dos atalhos (vira indicador); storage sem cota/tendência (o endpoint não tem) |
| Saem: `MetricCard`/`AnimatedNumber`, `RunsChart` (2 séries), `framer-motion`, datas cruas, `avg_duration_seconds` | A família abandonou; incoerências e ruído |
| Sem migração de banco; único endpoint tocado: `/workspaces/storage/my` ganhou `workspace_id` opcional (feito no backend, **nunca ligado** na tela e depois removido — §2.1, §4) | Coerência do storage com o escopo |

## 2. API

### 2.1 `GET /workspaces/storage/my` — `workspace_id` opcional (feito, depois removido)

> A rota e o `getMyStorageUsage` da web saíram sem nunca terem sido chamados. Ficam aqui
> como registro da regra, para quando o bloco de Armazenamento (§4) for construído.

Query param novo `workspace_id?: str`. Sem ele: soma todos os workspaces do usuário
(comportamento de sempre — escopo "todos"). Com ele: só aquele workspace, **validado
por pertencimento** (`workspace_id not in workspace_ids` → 403). Ao contrário do
`/observability/metrics`, este endpoint não recebe o objeto `user`, então aplica a
regra a todos igualmente, **sem o bypass de admin** que o metrics tem (§2.2) — na
prática as duas só divergem para um admin de plataforma, e o Dashboard nunca manda um
`workspace_id` fora do acesso (o escopo ativo sempre usa `current.id_hash`). Web:
`GisFlowService.getMyStorageUsage(workspaceId?)` (o método existiu; **o Dashboard nunca
o chamou** — §4).

### 2.2 Reaproveitados, sem mudança — todos já aceitam `workspace_id`

- `GET /observability/metrics?days=30[&workspace_id=&force=]` → `IObservabilityMetrics`.
  O `run_f` de `_resolver_escopo` filtra `WorkflowRun`, então no bloco `now` só
  `running`/`pending`/`stuck` respeitam o escopo. `now.executors`, `queued_on_executors`
  e `overdue_acks` refletem a **frota acessível do usuário** (pool default + workspaces
  do usuário + atribuídos), global por design — o despacho tira dessa mesma frota, então
  ela é relevante mesmo escopado; a frota por workspace fica para v2 (§4). `workspace_id`
  fora do acesso → 403 (o admin de plataforma tem bypass: vê qualquer `workspace_id`,
  inclusive inexistente → zeros).
- `GET /observability/runs-by-day?days=30[&workspace_id=&tz=]` → gráfico (4 séries).
- `GET /observability/runs?limit=6[&workspace_id=]` → hoje só alimenta a detecção do
  "vazio de primeiro uso" (§3.10); a lista "Atividade recente" não foi construída (§4).
  `IRunSummary` já traz `workspace_name` e `trigger_source`.
- `GET /observability/metrics/executores?days=30[&workspace_id=&force=]` → item
  "executor no teto" da atenção (opcional; falha → sem esse item).
- `GET /workflows[?workspace_id=]` → "Próximas execuções" (usa `schedule` +
  `has_*_trigger` da listagem, já entregues no PR de Projetos).

**Janela = 7 / 30 / 90 dias (default 30)**, escolhida no cabeçalho (`?periodo=`, reusando
`Periodo`/`PERIODOS` do Histórico), em `metrics`, `runs-by-day` e `metrics/executores`.
Instante (`now`) não é janela: poll de 30 s isolado, sempre na janela corrente.

## 3. Web

### 3.1 Estrutura (de cima para baixo) — o que existe hoje

```
Dashboard              [↻ Atualizar]  [«Bacia do Rio Doce» ▾]  [7 · 30 · 90 dias]
«Bacia do Rio Doce» · 8 workflows ativos   (toggle de escopo → "Todos os workspaces"; período → ?periodo=)

┌ SAÚDE — agora ────────────────────────────────────────────────────────────────┐
│ (friso âmbar) Precisa de você: 1 execução presa há 18 min e 2 workflows falhando │
│ ● 3 em andamento · 2 na fila │ ⏱ 1 presa há 18 min │ ● Executores 5 de 6 online  Ver em andamento →
└──────────────────────────────────────────────────────────────────────────────────┘
     (estado calmo → uma LINHA verde fina, não um cartão grande)

┌ Precisa de atenção ─────────────────┐  ┌ Próximas execuções ────────────┐
│ presas → falhas repetidas → teto    │  │ agendadas, por horário          │
└─────────────────────────────────────┘  └─────────────────────────────────┘

┌ RESUMO DO PERÍODO · ÚLTIMOS N DIAS ────────────────────────── Ver no Histórico →┐
│ [Execuções] [Taxa de sucesso] [Duração típica] [Falhas]   (4 indicadores)        │
│ ▂▃▅▇… gráfico por dia (4 séries de status)                                        │
└────────────────────────────────────────────────────────────────────────────────┘
```

A região Atenção|Próximas usa a grade `lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]`;
Saúde e Resumo ocupam a largura toda. Telefone: uma coluna, mesma ordem; cabeçalho
empilha (título; abaixo o toggle, o período e o Atualizar); indicadores 2×2; gráfico
`h-40`; alvos ≥ 40 px. (As regiões "Atividade recente" e "Atalhos" do plano original
não foram construídas — §4.)

### 3.2 Módulos (`web/app/components/dashboard/`)

| Arquivo | Responsabilidade |
|---|---|
| `index.tsx` | Orquestra: escopo, dados, composição, roteamento das ações. |
| `dashboard-url.ts` / `use-dashboard-url.ts` | Estado do escopo e do período na URL (`?escopo=todos`, `?periodo=`; `Periodo`/`PERIODOS` reusados do Histórico). |
| `use-dashboard-dados.ts` | 5 chamadas em paralelo escopadas (§3.3), falha parcial por seção, poll da saúde 30 s, sequência. |
| `saude.ts` / `saude-hero.tsx` | Tom (puro) + faixa colorida com veredito (§3.4). |
| `proximas.ts` / `proximas-lista.tsx` | Deriva e lista as próximas execuções agendadas (§3.6). |
| `estados.tsx` | Skeleton da 1ª carga, erro de espinha, vazio de primeiro uso e o aviso âmbar de falha parcial por seção (§3.10). |
| `cabecalho.tsx` | Título, subtítulo com escopo, toggle de escopo, seletor de período, Atualizar (§3.9). |
| reuso do Histórico | `observability/indicadores.tsx`, `grafico-por-dia.tsx`, `atencao.ts`+`atencao-lista.tsx`; `ItensAgora` extraído de `agora-faixa.tsx` (export nomeado, não-quebra) para a Saúde reusar a mesma linha. |

`page.tsx` é um wrapper fino que renderiza `<DashboardView/>`.

### 3.3 Dados (`use-dashboard-dados.ts`)

```ts
interface DadosDoDashboard {
  metrics: IObservabilityMetrics | null   // saúde + atenção + indicadores
  dias: IRunsByDay[]                       // gráfico
  runs: IRunSummary[]                      // só alimenta o "vazio de primeiro uso" (§3.10)
  executores: IExecutorMetrics[]           // atenção "executor no teto" (opcional)
  workflows: IWorkflow[]                   // próximas execuções (com schedule)
  carregando: boolean                      // 1ª carga do escopo atual (skeleton)
  atualizando: boolean
  falhas: { metrics: boolean; dias: boolean; runs: boolean; workflows: boolean }
  erroEspinha: string | null               // só quando metrics cai na 1ª carga (bloqueia a tela)
  atualizadoEm: number | null              // carimbo da última resposta; HOJE não é exibido (§4)
  recarregar: (opts?: { force?: boolean }) => void
}
// null = "todos" (sem workspace_id); undefined = escopo ativo ainda sem id (workspace
// carregando) → NÃO busca, mantém o skeleton; dias = 7/30/90
useDashboardDados(escopoWorkspaceId: string | null | undefined, dias: number)
```

- `escopoWorkspaceId` (resolvido no `index`): `escopo === "todos" ? null`; no escopo
  ativo, `undefined` enquanto a lista de workspaces carrega (não busca), depois
  `current?.id_hash`. As **cinco** chamadas partem juntas (`Promise.allSettled`) —
  `metrics`, `runs-by-day`, `runs`, `executores` e a listagem de `workflows`; só
  `metrics` é espinha (alimenta saúde + atenção + indicadores) — se ela cair na 1ª carga,
  `erroEspinha` bloqueia; as demais degradam por seção (aviso âmbar de 1 linha,
  `falhas.*`). Nunca zerar a tela. **Não há chamada de `storage`.**
- `executores` é a única opcional que **não** vira aviso: falha → `[]` (a atenção só
  perde o item "executor no teto").
- Recarrega ao trocar o escopo E ao trocar `current` quando o escopo é o ativo. Não
  recarrega ao trocar `current` quando o escopo é "todos". Recarrega também ao trocar
  o período — mas isso é uma RECARGA (o botão gira, a tela fica), não skeleton: o
  skeleton fica reservado à 1ª carga de um escopo, como o seletor do Histórico.
- "Atualizar" → `force:true` (fura o cache das métricas). Poll de 30 s só de `metrics`
  (aba visível), sem ligar `carregando`/`atualizando`, com carimbo de sequência (resposta
  velha nunca sobrescreve a nova; força não é sobrescrita por tick — mesmo padrão de
  `use-projetos-dados`). `atualizadoEm` guarda a última resposta aceita (mas não é
  exibido hoje — §4).
- SEM `ActiveRunsContext` para o "agora": ele é do workspace ativo e não serve ao escopo
  "todos"; o instante vem de `metrics.now`.

### 3.4 Saúde (`saude.ts` puro + `saude-hero.tsx`)

```ts
type TomDeSaude = "calmo" | "atencao" | "critico"
function tomDeSaude(now: INowBlock | null | undefined, temAtencao: boolean): TomDeSaude
// crítico: now.stuck_count > 0  OU  (executors.total > 0 && executors.online === 0)
// atenção: executors.online < executors.total  OU  overdue_acks > 0  OU há itens de atenção*
// calmo: nenhum dos acima
// (* "há itens de atenção" é decidido no index via montarAtencao; a saúde recebe, além
//    de `now`, a contagem por tipo da lista (ResumoDaAtencao: falhas, saturado) para
//    dizer "2 workflows falhando" sem reimplementar top_failing. As presas NÃO entram
//    no resumo: já têm motivo próprio, e recontá-las duplicaria o veredito.)
// A frota (executors) que pesa no tom é a acessível do usuário, não recortada por
// workspace (§2.2) — o despacho tira dela, então conta mesmo no escopo de um workspace.
function veredito(now, tom, resumo, semExecucoes?): string
// calmo: "Tudo tranquilo — nada pedindo atenção agora." (ou "…— nada rodando ainda."
//        quando semExecucoes, §3.10);  senão: "Precisa de você: {1–2 motivos}."
```

- `saude-hero.tsx`: no **calmo**, uma linha verde fina (friso 4px + ícone check + frase
  + `ItensAgora`), como a `agora-faixa` neutra do Histórico — NÃO um cartão verde grande.
  No **atenção/crítico**, o envelope `rounded-xl` ganha friso grosso (padrão
  `workspace-hero`, sem brilho difuso) + veredito de duas partes. Reusa `ItensAgora` (extraído de
  `agora-faixa.tsx`). "Ver em andamento →" → `/observability?status=running` (com
  `&workspace=` quando escopado). Presa clicável → `/observability/run/{runId}`.
- Textos dos motivos: "1 execução presa há 18 min", "2 workflows falhando", "1 executor
  no teto", "frota parcialmente offline: 5 de 6". Junta os 1–2 mais graves.

### 3.5 Precisa de atenção — reuso de `observability/atencao.ts` + `atencao-lista.tsx`

`montarAtencao({ metrics, executores })` já existe. O `index` mapeia `AcaoDeAtencao`:
`abrir-execucao` → `/observability/run/{runId}`; `filtrar-workflow` →
`/observability?workflow={id}&status=failed` (a visão padrão — execuções — aplica os
dois filtros; a visão "workflows" ignoraria ambos e cairia numa lista sem recorte);
`abrir-executor` → `/executores`. Os deep-links levam `&workspace={id}` quando o painel
está escopado a um workspace. No escopo "todos", cada item ganha a etiqueta do workspace via o join
`workflow_hash → Workflow.id_hash → workspace_id → WorkspaceContext` (usando o índice de
`workflows` já buscado para as Próximas); não resolveu → etiqueta some, nunca inventa.
Vazio → verde "Nada pendente. Última falha há X." (`textoDeVazio` do Histórico).

### 3.6 Próximas execuções (`proximas.ts` puro + `proximas-lista.tsx`)

- `proximas(workflows, agora)`: filtra `schedule?.active && flag_ative && next_run_at`
  no futuro; ordena por `next_run_at` asc; corta em 5. Cada item: ícone do gatilho +
  nome + workspace (escopo "todos") + `resumirAgendamento`/`formatarProxima`
  (de `projects/gatilho.ts`). Clique → editor `/workflow/{id}` com prefetch.
- Vazio → "Nenhuma execução agendada." Pausados/nunca-executados NÃO entram.
- Contraste com a Home: o painel "Meu → Agendamentos" (`GET /me/schedules`) lista os
  agendamentos da pessoa entre TODOS os workspaces, ativos E pausados — os pausados
  aparecem com o `motivoPausa` de `resumirAgendamento` (ex.: "workflow inativo") — e
  oferece pausar/ativar e rodar agora (com clique, por papel operator). Aqui, no
  Dashboard, "Próximas" é só uma prévia dos ativos.

### 3.7 Cabeçalho + toggle de escopo (`cabecalho.tsx`)

- `h1` "Dashboard"; subtítulo = escopo + contagem: escopo ativo → "«{nome}» · {N}
  workflows ativos"; "todos" → "Todos os workspaces · {W} workspaces · {N} workflows
  ativos" (`N = metrics.active_workflows`). Skeleton enquanto carrega.
- **Toggle de escopo** (segmentado, só com > 1 workspace): "«{workspace ativo}»" ↔
  "Todos os workspaces". Muda `?escopo=`. `aria-label="Escopo do painel"`.
- **Seletor de período** (segmentado, 7/30/90 dias, default 30): reusa `PERIODOS` do
  Histórico e o mesmo desenho. Muda `?periodo=`. `aria-label="Período"`, cada botão
  `aria-label="Últimos N dias"`. Governa a janela dos indicadores, do gráfico e das
  falhas em "Precisa de atenção" (a "Saúde · agora" e as "Próximas" não mudam).
- Atualizar (`ghost`, `TbRefresh` sob `motion-safe:`). O carimbo de frescor
  "atualizado há X" **NÃO** é exibido aqui: `atualizadoEm` existe no hook mas o cabeçalho
  não o renderiza; `textoDeFrescor` só é usado no Histórico (§4).

### 3.8 Estados

- Carregando (1ª vez do escopo): skeletons com altura real por bloco. Recargas não
  mostram skeleton.
- Erro de espinha (`metrics` caiu na 1ª carga): bloco "Não foi possível carregar o
  painel" + "Tentar de novo". Numa recarga com dados na tela, mantém + aviso.
- Falha parcial: cada seção (gráfico/atenção/próximas) com aviso âmbar de 1 linha; o
  resto continua.
- Vazio de primeiro uso (0 workflows E 0 execuções recentes E 0 no período): bloco
  centralizado "Nada rodou ainda" + "Criar workflow"; os demais blocos não aparecem.
- Sem execuções mas com workflows: saúde "Tudo tranquilo — nada rodando ainda";
  indicadores "—"; gráfico "Sem execuções no período."; atenção verde; próximas mostra
  os agendados.
- Trocar escopo/`current` reinicia a 1ª carga daquele escopo (skeleton).

### 3.9 Acessibilidade

Saúde e cada seção como `<section aria-labelledby>`; toggle com `aria-label`; itens de
atenção/próximas são botões/links com nome; ícones `aria-hidden`; alvos ≥ 40 px
no telefone; movimento sob `motion-safe:`; foco `ring-[3px]`.

### 3.10 Textos (pt-BR) — só os que existem hoje

"Dashboard" · "«{nome}» · {N} workflows ativos" · "Todos os workspaces · {W} workspaces
· {N} workflows ativos" · "Escopo do painel" · "Todos os workspaces" · "Atualizar" ·
"Saúde · agora" · "Precisa de você: …" · "Tudo tranquilo — nada pedindo atenção agora." ·
"Tudo tranquilo — nada rodando ainda." · "N workflows falhando" · "N executores no
teto" · "em andamento" · "na fila" · "presa há X" · "Executores N de M online" · "Ver em
andamento" · "Precisa de atenção" · "Próximas execuções" · "Nenhuma execução agendada." ·
"Período" · "Últimos N dias" · "Resumo do período · últimos N dias" · "Ver no Histórico" ·
"Nada rodou ainda" · "Criar workflow".

## 4. Não implementado nesta rodada / futuro

Descrito no plano original mas **não construído** — não presente no código hoje:

- **Atividade recente** (era um bloco próprio): lista das 6 execuções mais recentes
  (`getObservabilityRuns({limit:6})`) com `StatusBadge` pt-BR, `workspace · origem ·
  quando` e duração, levando a `/observability/run/{id}`. Não existe `atividade-lista.tsx`;
  o `runs` buscado hoje só alimenta a detecção do "vazio de primeiro uso" (§3.8). Textos
  que ficariam para este bloco: "Atividade recente", "Nenhuma execução recente.".
- **Atalhos + Seus workspaces + Armazenamento** (era um bloco próprio): "Abrir
  «{workspace}»", "Novo workflow", atalhos para Projetos/Histórico/Executores/Workspaces;
  a lista "Seus workspaces" (rotear com `setCurrent`); e o resumo de armazenamento
  (`formatBytes` + Drive/Artefatos). Não existe `atalhos.tsx`. Textos que ficariam:
  "Atalhos", "Abrir «{nome}»", "Novo workflow", "Seus workspaces", "Armazenamento".
- **Storage no hook de dados**: o campo `storage: IStorageUsage | null` e
  `falhas.storage`, e a chamada `getMyStorageUsage(escopoWorkspaceId)`. O endpoint e o
  método de service chegaram a existir (§2.1), mas nunca foram ligados e saíram: construir
  este bloco inclui recriá-los.
- **Carimbo de frescor no cabeçalho**: "atualizado há X". `atualizadoEm` é rastreado no
  hook mas não é exibido; `textoDeFrescor` só é renderizado no Histórico.

Fora de escopo (v2): mapa de cartões de saúde por workspace; métricas por workspace
(exigiria endpoint agregado `GET /observability/metrics/by-workspace?days=N`); dividir
"em andamento" por workspace; cota/tendência de armazenamento.

## 5. Testes

- API: `tests/unit/test_storage_meu_por_workspace.py` (sem/ com `workspace_id`, 403 fora
  do escopo, zeros sem workspaces) saiu junto com a rota (§2.1).
- Web (`web/__tests__/components/dashboard/`): `saude` (tom calmo/atenção/crítico,
  veredito, motivos); `proximas` (filtra futuro/ativo, ordena, corta em 5, ignora
  pausado); `dashboard-url` (ler/escrever `escopo`, default omitido); `use-dashboard-dados`
  (escopo troca workspace_id, falha parcial por seção, espinha bloqueia só na 1ª carga,
  força não sobrescrita por tick); `cabecalho` (subtítulo por escopo, toggle só com >1);
  `proximas-lista`/`saude-hero` (render, textos, aria); `index` (composição, toggle troca
  escopo e vai à URL, saúde reflete tom, atenção roteia, vazio de primeiro uso).
- E2E (Playwright, API real): escopo default (workspace ativo) e toggle "todos"; saúde
  colorida; atenção com deep-link; próximas; indicadores 30 d; console limpo; escuro e
  claro; 1440 e 390.
