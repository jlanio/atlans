# Spec — Política de execução por workspace: grupo dedicado, fallback e piso de isolamento

Status: **implementado** — entregue em PRs (ondas 1–4), atrás da flag `EXECUTOR_POLICY_ROUTING`; inclui a migração de reparo pós-implementação `20260908_0001` (`d9e3f1a5b624`). · Data: 2026-09-06 (rev. 5)
Escopo: `app/` (roteamento, modelo, API, agendador, consumer), `web/app/components/workspace/` (config)
Não toca: `flow/` (motor) nem `executor/` (runner) — a mudança é de _para onde_ o job vai, não de _como_ ele roda.

> **Nota de manutenção.** Esta spec já foi implementada. As citações `arquivo:linha`
> inline foram escritas ANTES do refactor de roteamento e **derivaram** — por
> exemplo, `_resolve_candidates` está hoje em `workflow_execution_service.py:319`
> (não `:258`), `_dispatch_job` em `:447` (não `:317`) e `send_job` em
> `executor_connections.py:1417` (não `:1328`). Os mecanismos descritos continuam
> válidos; trate os números abaixo como indicativos. A localização real está nos
> módulos entregues: `app/services/workspace_executor_service.py` (a política e
> suas regras), `_resolve_candidates_by_policy` + a barreira de isolamento em
> `workflow_execution_service.py`, `app/models/workspace_executor.py`,
> `WorkflowRun.dispatch_tier`, e as migrações `20260907_0001` / `20260907_0002` /
> `20260908_0001`.

## 1. Problema

Um workspace ligado a um executor dedicado, quando esse executor está indisponível,
**cai silenciosamente no pool compartilhado**. Para dados sob isolamento duro
(residência de dados, rede/credenciais on-premise, compliance), rodar no pool é
_incorreto_ — e hoje acontece sem aviso. Para outros workspaces, cair no pool é
exatamente o que o dono quer — mas ele **nunca escolheu isso**, e nada lhe mostra que
aconteceu.

A causa é única e está em `_resolve_candidates`
(`app/services/workflow_execution_service.py:258`): a função monta uma lista de
candidatos `[dedicado do workspace, se online] + [pool default inteiro, least-loaded]`
e `_dispatch_job` (`:317`) consome essa lista **em ordem como sequência de failover**.
O dedicado é, na prática, apenas a **prioridade #1** — nunca uma restrição, e nunca
uma escolha:

| Situação do dedicado | Comportamento atual | Evidência |
|----------------------|---------------------|-----------|
| Online e com folga | roda no dedicado ✅ | `workflow_execution_service.py:284-287` |
| Offline / sem `public_key` / `status!=active` | **cai no pool** ⚠️ | `:288-307` (pool sempre anexado) |
| Online porém com fila cheia (mesmo worker) | `send_job=False` → **cai no pool** ⚠️ | `executor_connections.py:1310-1317` |
| Online porém cheio (multi-worker, via relay) | `send_job=True` → run **falha** (não transborda) 🐞 | `executor_connections.py:1328-1352` |
| Só o dedicado e ele está fora | **cai no pool** ⚠️ | `:288-307` |
| Nem dedicado nem pool | 503 sem criar run | `:309-312` |

Dois eixos de dado se cruzam mal:

- `Executor.executor_type` / `Executor.is_default` — _pertencimento ao pool
  compartilhado_ (propriedade do executor). `app/models/executor.py:34,37`.
- `Workspace.target_executor_id` — _aresta workspace→executor_, hoje **1:1** e sem
  validação de que o alvo seja `dedicated`. `app/models/workspace.py:21`,
  `app/api/routers/workspace_router.py:576`.

E há duas divergências que agravam:

- **UX mente**: a tela diz "Dedicado **fixa** um executor específico"
  (`web/app/components/workspace/settings-sheet/executor-section.tsx:96`), mas o
  runtime faz preferência best-effort com fallback.
- **Ninguém vê onde rodou**: `WorkflowRun.host` existe e é exposto como `agent_host`
  na observabilidade (`app/services/observability_service.py:198`), mas nenhuma tela
  o renderiza; não há toast/badge de "rodou no pool".

## 2. Decisões do dono

### 2.1 Primeira rodada (2026-09-06) — o modelo

1. ~~"Dedicado" = isolamento DURO; um workspace com dedicado nunca toca o pool.~~
   **Superada pela 4ª rodada (§2.4):** o isolamento duro passa a ser **uma das
   políticas** que o dono escolhe (`terminal: falhar`), e o admin da plataforma pode
   torná-la obrigatória por workspace (piso).
2. **Se a cadeia se esgota: falhar NA HORA.** Sem fila de espera, sem re-despacho
   automático.
3. **Granularidade: por workspace.** Não por workflow, não por trigger.
4. **Grupo de dedicados: SIM.** Um workspace aponta para um **conjunto** de 1..N
   executores dedicados; o failover acontece dentro do nível.
5. **Roteamento por capability: NÃO** é necessário. O grupo é por identidade de
   executor, não por rótulo/capacidade.

### 2.2 Segunda rodada (2026-09-06) — as arestas

6. ~~Q1 — Migração: os `target_executor_id` viram isolados (sem pool).~~ **Superada
   (§2.4):** viram **nível 1 = {executor}, terminal = pool** — exatamente o que fazem
   hoje, agora explícito e visível. **Zero mudança de comportamento.**
7. **Q3 — Executor do pool num nível dedicado: NÃO.** Um executor `is_default=true`
   é recusado na inclusão (§4.3) e expulso na promoção a default (§4.4). O pool só
   participa como **terminal** da cadeia, nunca como membro de nível.
8. **Q5 — Webhook síncrono: SIM, devolve 503** ao chamador externo quando a cadeia se
   esgota. Com corpo **genérico** (não vaza estado da frota a um anônimo, §6) e
   `Retry-After`.
9. **Q6 — Agendador: SIM, notifica o dono** quando uma ocorrência falha por cadeia
   esgotada. Notificação por **transição de estado**, com lembrete limitado — nunca um
   e-mail por tick (§7.4).

### 2.3 Terceira rodada (2026-09-06) — fechamento

10. **Q2 — Nível de um: SIM.** Um único executor no nível principal é válido e é o caso
    esperado após a migração. A tela informa a saúde (§9) mas **não** força um 2º
    membro.
11. **Q4 — Todos cheios: falhar na hora** (quando a cadeia se esgota). Sem espera por
    slot; a fila local de cada executor já absorve picos.
12. **Q7 — Rótulo: workspace "Isolado"** para a política que nunca toca o pool;
    **Dedicado** continua sendo o tipo do executor (§9 para os três rótulos).

### 2.4 Quarta rodada (2026-09-06) — a política é do dono

> "Facultar ao administrador/dono do workspace se ele deseja como fallback executar em
> outro grupo ou no pool; jogar esta decisão ao usuário é mais sensato."

13. **A política de fallback é escolhida pelo dono/admin do workspace**, por
    workspace, como uma **cadeia de níveis + terminal** (§4, §5): nível principal de
    executores dedicados → nível de fallback opcional (outros executores dedicados do
    próprio workspace) → terminal **falhar** ou **pool**.
14. **Q8 — Pré-seleção para grupos novos: Falhar.** Seguro por padrão: quem quer o pool
    como último recurso marca conscientemente.
15. **Q9 — Níveis em v1: principal + um fallback.** Dois níveis, não N.
16. **Q10 — Piso do admin da plataforma: SIM, já em v1.** O admin da plataforma pode
    fixar, por workspace, que o terminal **tem de ser falhar** (`isolation_floor =
    no_pool`); o dono/admin do workspace não consegue afrouxar. É o que restaura uma
    garantia *dura* onde ela é exigência externa.

**Não há questões em aberto.**

### 2.5 Quinta rodada (2026-09-07) — ajustes pós-implementação

Revisão da implementação em uso (bugs relatados + revisão estática em quatro
lentes + smoke contra banco real). Regras que passaram a valer:

- **Sem nível principal ⇒ terminal `fail`.** "Pool como último recurso" é uma
  escolha feita COM um principal na mesa (e pede confirmação na tela); ao
  esvaziar o principal — pelo editor, por revogação forçada ou pelo endpoint
  legado — o terminal volta ao padrão. Sem isto, a escolha antiga reaparecia
  no próximo executor incluído, sem confirmação.
- **Endpoint legado `PUT /workspaces/{id}/executor`:** um executor do pool ou
  `null` LIMPA todos os níveis (antes deixava nível 1 órfão). Um nível 1
  nascendo do vazio por esse caminho recebe terminal `pool` (fora do piso):
  é o comportamento que o legado tem hoje, e a política precisa nascer igual
  para a virada da flag não mudar nada. Isolar é decisão explícita no editor.
- **Piso `no_pool` é absoluto:** vale mesmo sem nível principal (§5.3 vence a
  redação anterior de §4.2). Sem principal e sob piso, o workspace é Isolado
  com zero executores — nada roda até incluir um. Antes, esvaziar o principal
  de um workspace com piso mandava as execuções para o pool.
- **Autorização do executor = ponteiro legado ∪ níveis.** Drive, artefatos,
  portal, ChangeDetector, eventos de Drive e a auto-detecção do GeoSync passam
  a reconhecer membros de nível (`workspace_ids_for_executor`). Antes, um job
  roteado para um membro de nível quebrava na primeira leitura do Drive (403).
- **Um run por ocorrência:** `NoExecutorAvailableError` carrega `run_id` quando
  o dispatch já criou o run `failed`; o agendador só materializa um run
  sintético quando não há nenhum.
- **Backfill reparado** (migração `d9e3f1a5b624`): executores do pool e
  revogados saem dos níveis; reservas órfãs saem; workspaces na lixeira
  recebem o mesmo backfill para um restore não voltar sem nível.
- **Vocabulário único na tela:** modos *Compartilhado* / *Isolado* /
  *Dedicado + pool*; níveis *executores principais* e *de reserva*; o que
  acontece quando ninguém está disponível é o *último recurso*. "Fallback"
  fica no código. A seção do painel chama-se *Execução* e o editor, *Política
  de execução*.
- **Com a flag desligada, a tela segue o legado:** o painel do ativo e a
  fileira derivam o executor do ponteiro legado (o que roteia hoje) e mostram
  a política como *prévia* (selo tracejado); o grupo só toma o seletor quando
  a política vale. O editor abre com o aviso "ainda não está em vigor".
- **Piso tem tela:** Configurações → Execução lista a política de todos os
  workspaces (`GET /admin/workspaces/policies`) com um interruptor "Exigir
  isolamento" por workspace; exigir pede confirmação e aponta quem ficaria
  sem executor. Um piso sem principal vira pendência na visão geral.
- **Carga por executor:** o editor mostra o que cada executor publica
  ("1 de 4 em execução · 2 na fila") e marca quem está cheio — é o que dá
  sentido a "online".
- **Ações destrutivas pedem confirmação:** voltar ao pool pelo seletor rápido
  com um dedicado na mesa (apaga a política inteira) e remover o último
  principal (leva a reserva junto). O 409 de revogar/remover executor lista os
  workspaces afetados e a tela oferece "mesmo assim" (`force`), em vez de um
  toast genérico.

## 3. Objetivo / Não-objetivo

Objetivo:
- O comportamento de fallback vira uma **escolha declarada** do dono do workspace, e
  a tela mostra exatamente o que acontece quando o executor cai — porque foi ele quem
  definiu.
- Três resultados possíveis, todos explícitos:
  - **Pool** (default, inalterado): workspace sem grupo usa o pool compartilhado.
  - **Isolado**: nível(is) de executores dedicados, terminal **falhar**; **nunca** pool.
  - **Dedicado com fallback**: nível(is) dedicados e, esgotados, o **pool**.
- **Piso do admin da plataforma** que torna "Isolado" obrigatório onde for exigência.
- Falha **legível e atribuível** para o dono, **opaca** para chamadores anônimos.
- O conjunto permitido de executores como **invariante verificável** (§5.3), por
  política — não só como caminho feliz do roteamento.
- Corrigir a assimetria relay/direto do `is_full` (🐞 acima) para que "cheio" faça
  failover _dentro do nível_, em vez de matar o run em um caminho e transbordar no outro.
- **Migração sem mudança de comportamento** (§8).

Não-objetivo:
- Fila de espera / re-despacho automático (o dono escolheu falhar na hora).
- Roteamento por capability/label.
- Política por-workflow ou por-trigger.
- Mais de dois níveis (Q9).
- Redesenhar o enrollment/mTLS ou o protocolo de job.

### 3.1 E quem não tem executor dedicado? (modo pool)

É a maioria dos workspaces, e a resposta curta é: **nada muda por padrão**. Workspace
sem nível principal = modo pool = exatamente o de hoje — least-loaded entre os
executores `is_default`, failover dentro do pool, 503 só se o pool inteiro estiver
fora. A migração, a flag de roteamento (§8) e o piso **não tocam** esses workspaces.
Ter política é opt-in: basta ter acesso a um executor dedicado e criar o nível
principal.

O que o modo pool **ganha** com esta spec, sem pedir:

- **Capacidade mais previsível.** Hoje todo dedicado que cai transborda para o pool.
  Com a política, só transborda quem **escolheu** o pool como terminal — e isso fica
  visível (§8, onda 1), o que tende a reduzir o transbordo inconsciente.
- **Correção do relay `is_full`** (§5.2). O bug é do `send_job`, não do modo.
- **Sinal de presença endurecido** (§5.1). O 503 espúrio por blip de Redis atinge o
  pool inteiro hoje; a mitigação vale para todos.
- **Agendador que não engole falha** (§7.4). Um cron cujo pool está fora recebe o mesmo
  tratamento de um cron cuja cadeia se esgotou.
- **Observabilidade** (§8, onda 1): `agent_host` na tela. **Saúde do pool** e
  pre-flight (§9).

## 4. Modelo de dados

### 4.1 Níveis de executores do workspace

Hoje o vínculo é 1:1 (`Workspace.target_executor_id`). A política pede N executores em
até dois níveis. Proposta: uma tabela de junção **`workspace_executors`** com o nível.

```
workspace_executors
  workspace_id  FK workspaces.id_hash   NOT NULL
  executor_id   FK executors.id_hash    NOT NULL
  tier          smallint                NOT NULL  CHECK (tier IN (1, 2))
                                        -- 1 = principal, 2 = fallback
  added_by      String(36)              -- User.id_hash de quem incluiu (auditoria)
  created_at    timestamptz             default now()
  UNIQUE (workspace_id, executor_id)    -- um executor não está em dois níveis
  INDEX (workspace_id, tier)            -- leitura quente no dispatch
  INDEX (executor_id)                   -- "quais workspaces dependem deste executor?" (§4.4)
```

### 4.2 Política e piso, no workspace

```
workspaces (colunas novas)
  fallback_terminal  String(8)  NOT NULL default 'fail'    -- 'fail' | 'pool'  (Q8: default falhar)
  isolation_floor    String(8)  NOT NULL default 'none'    -- 'none' | 'no_pool' (Q10; só admin da plataforma)
```

Regras derivadas, sem flag de "modo":

> **Modo pool ⇔ zero linhas com `tier = 1`.** A política só é lida quando há nível
> principal.
> **Isolado ⇔ há nível principal e o terminal efetivo é `fail`.**
> **Terminal efetivo = `fail` se `isolation_floor = no_pool`, senão `fallback_terminal`.**

O terminal efetivo é calculado **no dispatch**, não só na escrita: mesmo que o banco
tenha `fallback_terminal = pool` num workspace com piso (estado que a API recusa,
§4.5), o roteamento trata como `fail`. Defesa em profundidade contra escrita direta ou
ordem de migração.

`Workspace.target_executor_id` é absorvido e **aposentado**: a migração copia cada
`target_executor_id IS NOT NULL` para uma linha `tier = 1` e grava
`fallback_terminal = 'pool'` (§8); a coluna fica em desuso por um release e depois é
removida. Nível de fallback (`tier = 2`) só existe quando o dono o criar (Q9).

### 4.3 Validação de membro (na inclusão em qualquer nível)

- deve existir, `status='active'`, não `deleted_at`, e ter `public_key` (senão nunca
  seria despachável);
- **`is_default=true` é recusado** (Q3) — executor do pool não entra em nível; o pool
  participa só como terminal. Erro 422 com mensagem explícita;
- **não pode estar no outro nível** (UNIQUE) — um executor é principal *ou* fallback;
- quem adiciona precisa ter acesso ao executor (mesma checagem de
  `set_workspace_agent`, `workspace_router.py:594-598`) e ser owner/admin do workspace;
- **nível 2 exige nível 1** não vazio; esvaziar o nível 1 apaga o nível 2 (não existe
  "só fallback");
- inclusão/remoção geram **evento de auditoria** (quem, qual executor, qual nível, qual
  workspace, quando).

### 4.4 Consistência ao longo do tempo (o que hoje ninguém trata)

Hoje apagar/revogar um executor **não** toca `Workspace.target_executor_id` (nenhuma
escrita em `user_executor_service.py` / `executor_service.py`; só leituras). O ponteiro
fica pendurado e a UI mostra "sumido". Com níveis isso vira bomba-relógio: um nível
principal que esvazia em silêncio faz **toda execução futura falhar** (terminal `fail`)
ou **transbordar para o pool sem ninguém saber** (terminal `pool`). Regras:

- **Revogar/apagar/desativar um executor**: listar os workspaces que o têm em algum
  nível (índice `executor_id`). Se a remoção **esvaziaria o nível principal** de um
  workspace, a operação é **bloqueada** com a lista, salvo `force=true` explícito — e,
  forçada, notifica os donos. Se sobra ≥1 membro no nível, remove a linha e avisa.
- **Promover um executor a `is_default`** (`set_default_agent`,
  `user_executor_service.py:108-137`): é a operação inversa do Q3 — o executor é
  **retirado de todos os níveis** em que estiver, com o mesmo bloqueio se esvaziar um
  nível principal.
- **Executor `inactive`/`pending`** continua no nível (é reversível), mas não é elegível
  no dispatch (§5) e conta como "indisponível" na saúde (§9).

### 4.5 Quem escreve o quê

| Campo | Escreve | Regra |
|-------|---------|-------|
| níveis (`workspace_executors`) | owner/admin do workspace | §4.3 |
| `fallback_terminal` | owner/admin do workspace | `pool` é **recusado (403)** se `isolation_floor = no_pool`; a troca gera auditoria |
| `isolation_floor` | **só admin da plataforma** | ao fixar `no_pool`, a API também força `fallback_terminal = fail` e notifica o dono; auditoria |

## 5. Roteamento (o coração da mudança)

Reescrever `_resolve_candidates` (`workflow_execution_service.py:258-314`) para montar
a **cadeia** a partir da política:

```
candidatos(ws):
  n1 = elegiveis(tier 1)              # active + public_key + disponivel, least-loaded
  se n1 é vazio E ws não tem tier 1:  # MODO POOL (inalterado)
      retorna pool least-loaded
  n2 = elegiveis(tier 2)              # least-loaded (pode ser vazio)
  cadeia = n1 + n2                    # ordem estrita entre níveis
  se terminal_efetivo(ws) == 'pool':
      cadeia += pool least-loaded     # o pool é o último recurso, escolhido pelo dono
  retorna cadeia                      # vazia ⇒ NoExecutorAvailableError (falha na hora)
```

- **Dentro de um nível**, least-loaded (running+queued); **entre níveis**, ordem
  estrita. `_dispatch_job` consome a cadeia como hoje — o mecanismo de failover não
  muda, só o _conteúdo_ da lista. _(2026-09-26: a carga passou a ser a contada no banco — runs em voo por
  host — e a ordem dentro do nível passou a ser: com vaga livre por sorteio
  ponderado pelas vagas, sem vaga pela ocupação relativa, cheios (pelo
  relatório ou pela contagem) por último; ver "Escolha do executor" em
  `docs/architecture.md`.)_
- **Cadeia vazia ⇒ falha imediata**, reusando os caminhos existentes: nada online →
  `NoExecutorAvailableError` **antes de criar o run** (`:309-312`); online mas todos
  recusam → run `failed` + `account_terminal_run` (`:506-517`). Mensagem por política
  (§6).
- **Nível em que rodou fica registrado**: `WorkflowRun.dispatch_tier`
  (`'primary' | 'fallback' | 'pool'`), gravado no mesmo ponto em que `host` é gravado
  (`:369` no INSERT, `:443` no failover). É o que torna "rodou no fallback/pool"
  observável por run sem depender da configuração atual (que pode mudar depois).

### 5.1 Confiabilidade do sinal (obrigatório sob falha-na-hora; vale para todos)

Com fallback para o pool, um sinal frouxo custava "foi pro pool". Com terminal
**falhar**, o mesmo sinal frouxo passa a custar "o run **falhou**". E o sinal é o mesmo
para o pool: um blip que marca todos os `is_default` offline devolve **503 espúrio** a
quem só usa o pool, hoje. O endurecimento de `disponivel(e)` é melhoria **geral** e
entra antes de ligar o roteamento novo:

- **Blip de Redis**: `is_online` é fail-closed (`executor_connections.py:541-547`); um
  blip no instante do dispatch marcaria um nível (ou o pool) inteiro offline. Mitigar:
  tratar "presença = não sei" (tri-estado `None`) de forma conservadora — tentar o
  envio mesmo assim (o `send_job` real dirá se conecta), em vez de excluir o candidato
  só pela leitura de presença.
- **Reconexão**: a presença é apagada na hora na desconexão limpa
  (`executor_connections.py:1033-1034`), sem carência de dispatch, enquanto os órfãos
  têm grace de ~20s (`executor_ws_router.py:196`). Espelhar uma **carência curta** no
  dispatch antes de considerar um executor indisponível.
- **Cheio momentâneo**: `capacity` é defasado ~10s. Dentro de um nível é benigno (só
  reordena). Se um nível inteiro parece cheio, a cadeia avança para o próximo nível ou
  terminal — que é a política escolhida; e se a cadeia se esgota, vale Q4: falha na hora.

### 5.2 Correção da assimetria relay (🐞, obrigatória)

`send_job` no caminho relay não checa `is_full` (`executor_connections.py:1328-1352`):
um membro cheio alcançado por relay "aceita" o job e o run **falha** por fila cheia em
vez de a cadeia avançar. Corrigir para que o relay também sinalize capacidade (checar
`is_full` via presença de capacity no Redis, ou request/response), de modo que "cheio"
⇒ `send_job=False` ⇒ próximo candidato. Sem isso, a cadeia é não-determinística
(depende de o WS estar no mesmo worker uvicorn).

### 5.3 O conjunto permitido como invariante (defesa em profundidade)

O roteamento é _uma_ decisão; a política tem de sobreviver a regressões nela.

- **Conjunto permitido** de um workspace = `nível 1 ∪ nível 2 ∪ (pool se terminal
  efetivo = pool)`. Para modo pool, = pool.
- **Segunda barreira em `_dispatch_job`** (`:410`): antes de `build_job_message`,
  **assertar** `ag.id_hash ∈ permitido(ws)`. Violação ⇒ não envia, run `failed`,
  log `ERROR` e `dispatch_event` com `outcome=isolation_violation` (deve ser
  **sempre 0**; alerta em `>0`, sobre o log — o servidor não tem exporter de
  métricas). Como implementado: a **coluna** `WorkflowRun.error_category` recebe o
  valor grosso `isolation` (taxonomia curta da coluna), enquanto a categoria
  granular `isolation_violation` é a do `NoExecutorAvailableError.category` e do
  `dispatch_event`. O piso é lido
  aqui também: com `isolation_floor = no_pool`, executor do pool nunca é permitido,
  diga o que disser `fallback_terminal`.
- **Ancoragem criptográfica, já existente**: o envelope é cifrado para a chave X25519
  **do executor escolhido** (`build_job_message(agent_x25519_pub_pem=…)`, `:413-431`).
  Um job cifrado para `geo-01` é ilegível para `pool-a`. A asserção acima garante que
  um job só é cifrado para chaves do conjunto permitido.
- **Credenciais só viajam para o conjunto permitido**: `inject_credentials`
  (`:378-382`) roda antes do laço de candidatos; a lista é a cadeia, então credenciais
  de um workspace isolado nunca entram num envelope para o pool.
- **Sub-workflows**: o coletor já descarta sub-fluxos de outros workspaces
  (`workflow_service.py:538`) e a duplicação é restrita ao mesmo workspace (`:306-314`).
  Invariante a **preservar com teste**: a cadeia inteira do envelope herda a política do
  workspace do disparo.
- **Mover workflow entre workspaces** (`moveTargets`, `WorkspaceContext.tsx:44`): mover
  entre workspaces de **políticas diferentes** muda a fronteira de execução dos dados.
  O diálogo avisa ("passa a poder rodar no pool compartilhado" / "passa a ser isolado")
  e exige confirmação. Runs já feitos mantêm `run.workspace_id` de origem
  (`workflows_router.py:435-443`).

## 6. Falha legível — e quem pode ler

Dois públicos, duas mensagens:

- **Dono/operador (run, histórico, log, e-mail)** — detalhada, por política:
  - Isolado: **"Workspace isolado: nenhum dos N executores dedicados está disponível.
    O job NÃO foi enviado ao pool compartilhado."** + nome e motivo por membro/nível.
  - Dedicado com fallback: **"Nenhum executor disponível: N dedicados e o pool
    compartilhado estão fora."**
  - Modo pool: **"Nenhum executor do pool compartilhado disponível."**
  `error_category` do `NoExecutorAvailableError` (propagado ao `detail` do 503 e às
  métricas): `no_dedicated_executor` (isolado) | `no_executor_chain` (fallback
  esgotado) | `no_pool_executor` (pool). Separam "meu grupo caiu" de "a plataforma
  caiu". Como implementado, a **coluna** `WorkflowRun.error_category` guarda o valor
  grosso `no_executor`; a granularidade acima vive na exceção, não na coluna.
- **Chamador anônimo do webhook** — genérica: corpo `503 {"detail": "Execução
  temporariamente indisponível para este workflow."}` + header `Retry-After: 60`.
  **Sem** nomes, contagens ou política: o código já cuida de não vazar o estado da
  frota a um anônimo (`workflow_service.py:520-573`) e esta spec mantém a regra.

## 7. Efeitos por caminho de disparo

O roteamento é compartilhado (`start_analysis`), então a política atinge os quatro
caminhos — sempre **quando a cadeia se esgota**.

### 7.1 Manual (`workflows_router.py:353`)
503 imediato com a mensagem detalhada. A UI faz **pre-flight** (§9).

### 7.2 Retry (`workflows_router.py:502`)
Refaz `_resolve_candidates` com a política atual. Mesmo pre-flight.

### 7.3 Webhook (`webhook_router.py:184`) — Q5
- Cadeia esgotada → **503 genérico + `Retry-After`** (§6). Documentado no OpenAPI.
- **Idempotência preservada** (verificado): a chave `idempotency:wf_execute:{key}` é
  gravada **só depois** do dispatch bem-sucedido (`workflow_service.py:586-591`); um 503
  não a consome. Trancar com teste (§11).
- **Sem run por chamada**: no caminho "nada online" o 503 continua **stateless**
  (`:309-312`), sem criar `WorkflowRun` — sem amplificação de escrita.

### 7.4 Agendador (`async_scheduler.py:74`) — Q6
Hoje engole a exceção e só avança `next_run_at` (`:155-167`): a ocorrência some. Sob
esta spec, **para qualquer política, inclusive modo pool**:

- **Registrar um `WorkflowRun` `failed`** com a mensagem da política e fechar via
  `account_terminal_run` — a ocorrência agendada precisa ter rastro.
- **Notificar o dono** do workspace (`Workspace.owner_id`) e os admins, por e-mail
  (`email_service.send_email_background`, template novo). O `Schedule` não tem dono
  próprio (`app/models/schedule.py`), então o destinatário vem do workspace.
- **Por transição, não por tick.** Estado por `(schedule_id)` em Redis: notifica na
  **primeira** falha da janela, no máximo **um lembrete** a cada 6 h, e um aviso de
  **recuperação** na próxima ocorrência que roda. Como o pool é compartilhado, um
  incidente atinge muitos workspaces: cada dono recebe **um** aviso do seu cron; o
  admin da plataforma vê o agregado no `/health` (§11).
- O webhook de notificação por workspace (`_fire_notification_if_configured`,
  `run_result_consumer.py:562`) **não** dispara aqui (fechamento fora da fila
  `run_results`); o e-mail é o canal desta falha. Ver §11 sobre unificar.

## 8. Migração e rollout — sem mudança de comportamento

A 4ª rodada removeu o risco que exigia modo sombra: os workspaces com
`target_executor_id` viram **nível 1 = {executor}, `fallback_terminal = pool`** — que é
exatamente o que já fazem. Ninguém passa a falhar onde antes rodava. O que muda é que
a política **aparece** na tela, e quem precisa de isolamento aperta conscientemente.

Ondas, cada uma reversível e entregável em PR próprio:

1. **Observabilidade primeiro.** Renderizar `agent_host` e o badge do nível em que
   rodou (`dispatch_tier`, §5): "rodou no fallback" / "rodou no pool". Evento
   estruturado por dispatch (§11).
2. **Modelo + backfill.** Criar `workspace_executors` (com `tier`), as colunas
   `fallback_terminal` e `isolation_floor`; migração Alembic **idempotente**
   (`INSERT … ON CONFLICT DO NOTHING`) copiando `target_executor_id` como `tier = 1` e
   gravando `fallback_terminal = 'pool'` nesses workspaces. Coluna antiga preservada em
   **dual-write** por um release (rollback = desligar a flag).
3. **Roteamento novo atrás de flag** (`EXECUTOR_POLICY_ROUTING = off | on`), com a
   correção do relay (§5.2) e o endurecimento do sinal (§5.1) **antes**. Em `on` com o
   backfill acima, o resultado é idêntico ao de hoje — a flag existe para rollback, não
   para sombra.
4. **UI da política** (§9) + endpoint do piso para o admin da plataforma (§4.5).
5. **Comunicação** aos donos de workspaces com executor dedicado: "sua política está
   visível; hoje é *fallback: pool*; para isolar, mude o terminal para *falhar*". E
   ao admin da plataforma: onde fixar o piso.
6. Remoção da coluna antiga no release seguinte.

Defaults seguros em todas as ondas: workspace sem nível = modo pool = intacto;
grupos **novos** nascem com terminal `fail` (Q8). Execuções **em voo** não são
re-alocadas.

## 9. Superfície de configuração (web)

`web/app/components/workspace/settings-sheet/executor-section.tsx` deixa de ser um
`<Select>` de um executor e vira o **editor da política**, em três blocos:

1. **Executores dedicados** (nível principal): lista com adicionar/remover; avatar,
   nome, online/offline, carga. Executores `is_default` não aparecem como opção (Q3).
2. **Fallback** (opcional, Q9): "Se nenhum estiver disponível, tentar estes outros
   executores dedicados" — lista do nível 2, mesmas regras.
3. **Quando tudo acima falhar** (terminal, obrigatório, pré-selecionado em **Falhar**):
   - ( • ) **Falhar na hora** — "a execução falha e você é avisado; nada vai ao pool".
   - (   ) **Usar o pool compartilhado** — "os dados poderão rodar em executores
     compartilhados da plataforma". **Desabilitado** com o motivo quando
     `isolation_floor = no_pool`: "definido pelo administrador da plataforma".

Rótulos (Q7):
- **Isolado** — nível(is) dedicados + terminal falhar. Badge roxo (o mesmo de
  "Dedicado" em `ExecutorTypeStyles.ts`), com cadeado quando há piso.
- **Dedicado · fallback: pool** — nível(is) dedicados + terminal pool. Badge roxo com
  sufixo teal (o teal do pool).
- **Compartilhado** — modo pool, como hoje quando `target=null`.

Mais:
- **Saúde por nível** como conceito de primeira classe: `GET
  /workspaces/{id}/executors` devolve os membros por `tier` com `online`, `capacity` e
  os agregados `available_primary`, `available_fallback`. A UI mostra "**N de M
  disponíveis**" por nível; com 0 no principal e terminal falhar, alerta que _novas
  execuções vão falhar_; com terminal pool, avisa que _vão para o pool_.
- **Saúde do pool** para workspaces em modo pool ("N de M online" entre os
  `is_default`) e o **mesmo pre-flight** — um 503 por pool fora tem de ser tão
  descobrível quanto um por cadeia esgotada.
- **Pre-flight no disparo**: se a cadeia efetiva tem 0 disponíveis, aviso inline antes
  do clique; o botão continua habilitado (falhar de propósito é escolha válida).
- **Painel do workspace** (`workspace-hero.tsx`): a linha de status reflete a política
  ("Isolado · 2 de 2 online" / "Dedicado · fallback: pool · 1 de 2 online").
- **Trocar o terminal** para `pool` pede confirmação com a frase dos dados
  compartilhados; a troca fica na auditoria.

Backend (nomes provisórios):
`GET/PUT /workspaces/{id}/executors` (níveis), `POST/DELETE
/workspaces/{id}/executors/{executor_id}?tier=1|2`, `PUT /workspaces/{id}/fallback`
(terminal; owner/admin), `PUT /admin/workspaces/{id}/isolation-floor` (só admin da
plataforma).

## 10. Exemplo trabalhado

Três workspaces, três políticas. Pool compartilhado = { pool-a, pool-b }.

- **"Bacia do Paranapanema"** — dados com residência obrigatória on-premise. Nível 1 =
  { geo-01, geo-02 }; terminal **falhar**; **piso `no_pool`** fixado pelo admin da
  plataforma. Política: **Isolado** 🔒.
- **"Licenciamento Ambiental"** — prefere disponibilidade. Nível 1 = { lic-01 }; nível
  2 = { lic-02 }; terminal **pool**. Política: **Dedicado · fallback: pool**.
- **"Cadastro Urbano"** — sem executor dedicado. Política: **Compartilhado** (pool).

| # | Workspace | Estado | Hoje | Sob esta spec |
|---|-----------|--------|------|---------------|
| A | Bacia | geo-01 online e livre | roda em geo-01 | roda em geo-01 (`dispatch_tier=primary`) |
| B | Bacia | geo-01 **cheio**, geo-02 livre | **cai no pool-a** ⚠️ | roda em **geo-02** ✅ |
| C | Bacia | geo-01 e geo-02 **offline** | **roda no pool** ⚠️ (dado vaza) | **falha na hora**; pool intacto ✅ |
| D | Bacia | cron com os dois offline | roda no pool, silencioso | run **`failed`** + e-mail ao dono (uma vez por janela) ✅ |
| E | Bacia | admin do workspace tenta terminal = pool | (n/a) | **403**: piso `no_pool` fixado pelo admin da plataforma ✅ |
| F | Licenciamento | lic-01 offline, lic-02 livre | cai no pool ⚠️ | roda em **lic-02** (`fallback`) — badge "rodou no fallback" ✅ |
| G | Licenciamento | lic-01 e lic-02 offline, pool-a livre | roda no pool (invisível) | roda em **pool-a** (`pool`) — badge "rodou no pool"; foi escolha do dono ✅ |
| H | Licenciamento | tudo offline (dedicados e pool) | 503 | 503 / `failed` com `no_executor_chain` ✅ |
| I | Cadastro | cron com pool-a e pool-b offline | ocorrência **silenciosamente perdida** | run **`failed`** + e-mail ao dono ✅ |
| J | qualquer | webhook externo com cadeia esgotada | resposta do pool ou 503 cru | **503 genérico + `Retry-After`**; reenvio com a mesma `idempotency_key` é atendido quando voltar ✅ |
| K | Bacia | admin tenta revogar geo-02 com geo-01 já apagado | ponteiro pendurado | **bloqueado**: "esvaziaria o nível principal" (ou `force` + aviso) ✅ |

O contraste que importa continua sendo **C**: o caso que motivou a spec. E **G** é a
novidade da 4ª rodada: o mesmo transbordo de hoje, agora **escolhido** pelo dono e
**visível** no run.

## 11. Sugestões para uma spec segura e moderna

Recomendações minhas, além do que as decisões exigem. **[v1]** = levar já;
**[depois]** = pode esperar. **Pós-implementação:** os itens **[v1]** foram
entregues — teste de contrato por política, sinal `isolation_violation` no log,
trilha de auditoria, aviso ao cruzar política, 503 stateless no webhook,
notificação por transição no agendador, evento estruturado de dispatch, badge por
run, saúde por nível + pre-flight, e a flag de roteamento. Os **[depois]** seguem
como backlog.

Fronteira de verdade
- **[v1] Teste de contrato por política**: (a) Isolado + tudo offline ⇒ 503, **zero**
  `send_job` ao pool, zero envelope cifrado fora do conjunto permitido; (b) fallback:
  pool ⇒ pool só **depois** de esgotar os níveis; (c) piso `no_pool` ⇒ terminal `pool`
  no banco é ignorado no dispatch. A asserção de §5.3 é a versão em runtime.
- **[v1] Métrica `isolation_violation_total` com alerta em `>0`.** Entregue como o
  `dispatch_event` com `outcome=isolation_violation` (§5.3): sem exporter de métricas
  no servidor, o alerta sai do log.
- **[v1] Trilha de auditoria** para níveis, terminal, piso e `force` (§4.3–4.5).
- **[v1] Aviso ao cruzar política** no diálogo de mover workflow (§5.3).
- **[depois] Atestado no executor.** O envelope carrega `workspace_id`; um executor
  dedicado poderia recusar jobs de workspaces que não o listam em algum nível (lista no
  handshake, `executor_ws_router.py`). Protege contra servidor comprometido ou com bug.

Falha segura
- **[v1] 503 stateless e genérico no webhook** (§6, §7.3).
- **[v1] Teste da idempotência após 503** (`workflow_service.py:586-591` já garante;
  trancar).
- **[v1] Bloqueio de esvaziamento do nível principal** (§4.4).
- **[v1] Notificação por transição** no agendador (§7.4), para todas as políticas.
- **[v1] Confirmação explícita** ao trocar o terminal para `pool` (§9).
- **[depois] `Retry-After` dinâmico**, derivado da próxima renovação de presença.

Operação moderna
- **[v1] Evento estruturado por decisão de dispatch**: `{run_id, workspace_id,
  policy: pool|isolated|dedicated_pool, tiers_available: {primary, fallback},
  chosen_executor, dispatch_tier, decision_ms, outcome}` em log JSON, substituindo o
  `_logger.info` de `:500-503`; métricas `dispatch_total{policy,tier,outcome}` e
  `fallback_used_total{workspace,tier}`.
- **[v1] Badge "rodou no fallback/pool"** por run (`dispatch_tier`), no histórico e
  no painel. O dono escolheu o fallback; tem de ver quando ele foi usado.
- **[v1] Saúde por nível e pre-flight** (§9).
- **[v1] Flag de roteamento** (`off|on`) e rollback = desligar.
- **[depois] E-mail por transição quando um workspace passa a rodar no fallback/pool**
  ("desde HH:MM as execuções de X estão no pool"). O mecanismo é o mesmo do cron (§7.4).
- **[depois] Simulador de política**: "se eu mudar para *falhar*, quantas execuções dos
  últimos 30 dias teriam falhado?" — calculável de `dispatch_tier`. É o que o modo
  sombra faria, agora como ferramenta do dono, não como pré-requisito de rollout.
- **[depois] Unificar canais de notificação** (e-mail e webhook por workspace num
  notificador único, chamado também pelos fechamentos fora da fila).
- **[depois] Prontidão no `/health`** (`health_router.py`): "workspaces isolados com 0
  membros online no principal" e "pool com 0 online".

## 12. Questões em aberto

Nenhuma. As 16 decisões (§2.1–2.4) fecharam o modelo; a implementação por onda
(§8) foi entregue.

## 13. Onde isto vive no código (implementado)

> Os `arquivo:linha` abaixo são **pré-refactor e indicativos** (ver a Nota de
> manutenção no topo). A lista mapeia cada decisão ao seu ponto no código.

- `app/services/workflow_execution_service.py:258-314` — `_resolve_candidates`: a
  cadeia por política (§5).
- `app/services/workflow_execution_service.py:288-307` — onde o pool é anexado hoje;
  passa a ser condicional ao terminal efetivo.
- `app/services/workflow_execution_service.py:363-372, 442-444` — gravação de `host`:
  gravar `dispatch_tier` junto (§5).
- `app/services/workflow_execution_service.py:410-431` — laço de candidatos: asserção
  do conjunto permitido (§5.3) antes de `build_job_message`.
- `app/core/executor_connections.py:1328-1352` — `send_job` relay: correção do `is_full`
  (§5.2).
- `app/core/executor_connections.py:1116-1135` / `:541-547` — `is_online`/presença:
  endurecimento do sinal (§5.1).
- `app/models/workspace.py` — `fallback_terminal`, `isolation_floor`; `app/models/`
  nova `workspace_executors` (com `tier`); `app/models/workflow_run.py` —
  `dispatch_tier`; migração Alembic (§4, §8).
- `app/services/user_executor_service.py:108-137` (`set_default_agent`) e o caminho de
  delete/revoke em `executores_router.py` — consistência dos níveis (§4.4).
- `app/api/routers/workspace_router.py:558-626` — endpoints de níveis e terminal (§9);
  endpoint do piso, só admin da plataforma (§4.5).
- `app/api/routers/webhook_router.py:184-229` — 503 genérico + `Retry-After` (§7.3).
- `app/core/async_scheduler.py:155-167` — registrar `failed` + notificação por
  transição (§7.4); `app/services/email_service.py:52` — envio.
- `app/services/observability_service.py:198-206` — surfacing de `agent_host` e
  `dispatch_tier` (§8, onda 1).
- `web/app/components/workspace/settings-sheet/executor-section.tsx` — editor da
  política, saúde por nível e pre-flight (§9); `web/app/components/workspace/workspace-hero.tsx`
  — status.
- `web/context/WorkspaceContext.tsx:44` (`moveTargets`) e o diálogo de mover — aviso de
  política (§5.3).
