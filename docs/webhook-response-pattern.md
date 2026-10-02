# Padrão Webhook + ResponseNode

Este documento descreve o protocolo de requisição/resposta entre cliente e servidor para execução de workflows via webhook, incluindo o modo síncrono habilitado pelo `ResponseNode`.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Modos de Execução](#modos-de-execução)
- [Fluxo Assíncrono (padrão)](#fluxo-assíncrono-padrão)
- [Fluxo Síncrono (ResponseNode)](#fluxo-síncrono-responsenode)
- [Parâmetro no_wait](#parâmetro-no_wait)
- [Diagrama de Sequência Completo](#diagrama-de-sequência-completo)
- [Referência da API](#referência-da-api)
- [Autenticação e limites](#autenticação-e-limites)
- [ResponseNode — Propriedades](#responsenode--propriedades)
- [Exemplos](#exemplos)

---

## Visão Geral

O endpoint `POST /webhook/execute/{id_hash}` é o ponto de entrada para disparo externo de workflows. Ele suporta dois modos:

| Modo | Comportamento | Uso |
|---|---|---|
| **Assíncrono** | Retorna `202 Accepted` imediatamente com `task_id` | Callers que só enfileiram; progresso consumido via WebSocket |
| **Síncrono** | Bloqueia até o workflow completar, retorna a resposta HTTP do `ResponseNode` | Integrações externas que precisam da resposta inline |

A chave de controle é o parâmetro `no_wait` no body da requisição e a presença do `ResponseNode` na definição do workflow.

---

## Modos de Execução

```
has_response_node=False  →  sempre retorna 202 imediatamente
has_response_node=True
  ├─ no_wait=True   →  retorna 202 imediatamente (caller pediu retorno assíncrono)
  └─ no_wait=False  →  bloqueia até ResponseNode completar (caller externo)
```

---

## Fluxo Assíncrono (padrão)

Usado quando o workflow **não** contém `ResponseNode`, ou quando `no_wait=true`.

```
Cliente                 Servidor                  Executor
  │                        │                         │
  │── POST /webhook/... ──►│                         │
  │                        │── WebSocket job ───────►│
  │◄─── 202 {task_id} ─────│                         │
  │                        │                         │ executa...
  │── WS /ws/workflow/{id}►│                         │
  │                        │◄── node_event ──────────│
  │◄── node status ────────│                         │
  │                        │◄── job_result ──────────│
  │◄── __workflow_complete__│                         │
  │── WS close ───────────►│                         │
```

**Detalhes:**
1. Cliente recebe `task_id` imediatamente
2. Abre WebSocket `GET /ws/workflow/{task_id}` enviando JWT no primeiro frame
3. Recebe eventos de nós em tempo real (`started`, `completed`, `failed`)
4. Recebe `__workflow_complete__` ao final e fecha o WebSocket

---

## Fluxo Síncrono (ResponseNode)

Usado quando o workflow contém `ResponseNode` **e** o caller **não** envia `no_wait=true`.

```
Cliente                 Servidor                      Executor
  │                        │                             │
  │── POST /webhook/... ──►│                             │
  │   (no_wait ausente)    │── WebSocket job ───────────►│
  │                        │                             │
  │                        │  BRPOP webhook_response:id  │ executa nós...
  │         (bloqueado)    │  (aguardando)               │
  │                        │                             │── publica node events
  │                        │◄── node_event (N vezes) ────│    via Redis pub/sub
  │                        │                             │
  │                        │◄── job_result ──────────────│
  │                        │    (stats.__response__)     │
  │                        │                             │
  │                        │  LPUSH webhook_response:id  │
  │                        │  (BRPOP retorna)            │
  │                        │                             │
  │◄── HTTP Response ───── │                             │
  │    status: 200          │── RPUSH __workflow_complete►│
  │    body: {...}          │   (histórico Redis)         │
  │    headers: {...}       │                             │
```

**Detalhes:**
1. Servidor detecta `ResponseNode` na definição do workflow → `has_response_node=True`
2. Após despachar o job, executa `BRPOP webhook_response:{task_id}` com timeout configurável
3. Executor executa o workflow; `ResponseNode` produz `{"__response__": {...}}` nos outputs
4. `executor_ws_router` recebe `job_result`, extrai `stats.__response__`, faz `LPUSH webhook_response:{task_id}`
5. `webhook_router` acorda do BRPOP e retorna a resposta HTTP construída a partir do `ResponseNode`
6. Se o workflow falhar antes do `ResponseNode`, o servidor retorna `HTTP 500`
7. Se o executor não responder dentro de `WEBHOOK_RESPONSE_TIMEOUT` segundos, retorna `HTTP 504`

---

## Parâmetro no_wait

`no_wait` é uma opção **do servidor** que força o retorno assíncrono (`202`) mesmo
em workflows com `ResponseNode`. Hoje **nenhum cliente do repositório o envia** —
ele existe para callers externos que preferem consumir o resultado via WebSocket
em vez de bloquear na resposta HTTP.

> **O canvas não usa este endpoint.** A execução manual pelo canvas passa por
> `POST /workflows/{id}/execute` (autenticado por JWT), que devolve
> `{"task_id", "workflow"}` e nunca envia `no_wait` — ver `executeWorkflow` em
> `web/service/GisFlowService.ts`. O `/webhook/execute` exige um `WebhookTrigger`
> no fluxo e recusa qualquer outro tipo de trigger, por isso não serve ao canvas.

### Quando usar

| Caller | Valor recomendado | Motivo |
|---|---|---|
| Integração externa | ausente / `false` | Obtém a resposta HTTP do `ResponseNode` de forma síncrona |
| Script / curl | ausente / `false` | Mesmo que integração externa |
| Caller que prefere WebSocket | `true` | Recebe `202 {task_id}` na hora e consome eventos em `/ws/workflow/{task_id}` |

### Como funciona

O parâmetro é lido do body JSON e removido antes de ser passado como `inputs` ao workflow:

```python
# webhook_router.py
no_wait = bool(body.pop("no_wait", False))

if no_wait or not getattr(async_result, "has_response_node", False):
    return JSONResponse({"task_id": task_id}, status_code=202)
```

---

## Diagrama de Sequência Completo

### Infraestrutura envolvida

```
┌─────────┐    ┌──────────┐    ┌───────────┐    ┌───────┐    ┌───────┐
│ Cliente │    │ FastAPI  │    │  Executor   │    │ Redis │    │  DB   │
└────┬────┘    └────┬─────┘    └─────┬─────┘    └───┬───┘    └───┬───┘
     │              │                │               │             │
     │ POST /webhook│                │               │             │
     │─────────────►│                │               │             │
     │              │ build_job_msg  │               │             │
     │              │────────────────►               │             │
     │              │                │               │             │
     │              │ LPUSH run_creates              │             │
     │              │───────────────────────────────►│             │
     │              │                │               │             │
     │              │ (has_response_node=True, no_wait=False)       │
     │              │ BRPOP webhook_response:{id}    │             │
     │              │───────────────────────────────►│             │
     │              │                │               │             │
     │              │                │ executa nós   │             │
     │              │                │───────────────►             │
     │              │                │               │             │
     │              │ PUBLISH node_event             │             │
     │              │◄───────────────────────────────│             │
     │              │                │               │             │
     │              │ LPUSH webhook_response:{id}    │             │
     │              │◄───────────────────────────────│             │
     │              │ (BRPOP retorna)│               │             │
     │              │                │               │             │
     │ HTTP Response│                │               │             │
     │◄─────────────│                │               │             │
     │              │                │               │             │
     │              │ LPUSH run_results              │             │
     │              │───────────────────────────────►│             │
     │              │                │               │             │
     │              │ RPUSH + PUBLISH __workflow_complete           │
     │              │───────────────────────────────►│             │
```

---

## Referência da API

### `POST /webhook/execute/{id_hash}`

**Parâmetros de path:**
- `id_hash` — identificador público do workflow

**Body (JSON):**

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `no_wait` | `boolean` | `false` | Se `true`, retorna 202 imediatamente sem aguardar `ResponseNode` |
| `debug_mode` | `boolean` | `false` | Ativa modo debug (publica eventos com inputs/outputs dos nós) |
| `*` | `any` | — | Demais campos são passados como `inputs` ao workflow |

**Respostas:**

| Status | Condição | Body |
|---|---|---|
| `202 Accepted` | Sem `ResponseNode`, ou `no_wait=true` | `{"task_id": "uuid"}` |
| `200` (ou configurado) | Com `ResponseNode` e `no_wait=false` | Payload definido pelo `ResponseNode` |
| `413 Payload Too Large` | Body acima de 10 MB (via `Content-Length`) | `{"detail": "Payload excede 10MB."}` |
| `429 Too Many Requests` | Rate limit: 20/min por par (IP, `id_hash`) | resposta padrão do rate-limiter |
| `500 Internal Server Error` | Workflow falhou antes do `ResponseNode` | `{"error": "...", "task_id": "uuid"}` |
| `502 Bad Gateway` | `body_ref.s3_key` rejeitado, ou falha ao baixar o body do MinIO | `{"error": "...", "task_id": "uuid"}` |
| `503 Service Unavailable` | Nenhum executor disponível (header `Retry-After: 60`) | `{"detail": "Execução temporariamente indisponível para este workflow."}` |
| `504 Gateway Timeout` | Executor não respondeu em `WEBHOOK_RESPONSE_TIMEOUT`s | `{"error": "timeout", "task_id": "uuid", "message": "..."}` |
| `404 Not Found` | Workflow não existe | `{"detail": "Workflow não encontrado"}` |
| `403 Forbidden` | Workflow desativado | `{"detail": "Workflow está desativado..."}` |
| `403 Forbidden` | Workflow sem node `WebhookTrigger` | `{"detail": "Workflow não possui node WebhookTrigger..."}` |

### `GET /ws/workflow/{task_id}`

WebSocket para receber eventos de execução em tempo real.

**Protocolo:**
1. Conectar
2. Enviar JWT no primeiro frame (texto puro)
3. Receber eventos JSON até `__workflow_complete__`

**Formato de evento de nó:**
```json
{
  "run_id":      "uuid",
  "node":        "node-uuid",
  "status":      "started" | "completed" | "failed" | "debug",
  "timestamp":   1741234567.89,
  "duration_ms": 142.5,
  "error":       null,
  "extra": {
    "node_name": "DatabaseSpatialQuery",
    "node_type": "datasource"
  }
}
```

**Evento de conclusão:**
```json
{
  "run_id":      "uuid",
  "node":        "__workflow_complete__",
  "status":      "completed" | "failed",
  "timestamp":   1741234568.01,
  "duration_ms": 1234.5,
  "error":       null
}
```

**Replay de histórico:** O servidor armazena todos os eventos no Redis (`workflow:{run_id}:history`). Ao conectar, o WebSocket replaya automaticamente o histórico antes de escutar novos eventos. Isso garante que nenhum evento seja perdido mesmo que o cliente conecte após o início da execução.

---

## Autenticação e limites

- **Sem JWT global.** O `/webhook/execute` não passa pela autenticação JWT. O
  controle de acesso é a credencial do node `WebhookTrigger`: sem `credential_id`,
  acesso livre; com `credential_id`, o token é validado em `start_analysis`.
- **Rate limit:** 20 req/min por par (IP, `id_hash`) — saturar *um* workflow
  específico exige rotação de IP a cada janela.
- **Body máximo:** 10 MB (`413` acima disso).
- **TTL da resposta:** a chave Redis `webhook_response:{task_id}` expira em 300 s.

---

## ResponseNode — Propriedades

| Propriedade | Tipo | Padrão | Descrição |
|---|---|---|---|
| `statusCode` | `select` (valores string) | `"200"` | Código HTTP. Lista fechada: 200, 201, 204, 301, 302, 400, 401, 403, 404, 422, 500 |
| `contentType` | `select` | `application/json` | `Content-Type` da resposta. Lista fechada: `application/json`, `text/plain`, `text/html`, `application/xml`, `text/csv` |
| `bodyMode` | `select` | `field` | Origem do body: `empty` (sem body), `literal` (texto/template Jinja em `customBody`), `field` (campo do input) |
| `customBody` | `code` | `""` | Texto literal ou template Jinja (visível quando `bodyMode=literal`). Ex.: `Olá {{ WebhookTrigger.output.nome }}` |
| `bodyField` | `string` | `""` | Campo de entrada a usar como body (visível quando `bodyMode=field`). Vazio = primeiro input |
| `headers` | `object` | `{}` | Headers adicionais (chave → valor) |

**Prioridade do body:** `customBody` > `bodyField` > primeiro input disponível.

**Output interno:** O nó produz `{"__response__": {...}}` nos outputs (chaves `status_code`, `content_type`, `headers` e `body` ou `body_ref`). Esta chave é tratada especialmente pelo servidor e pelo executor — não é passada para nós downstream.

**Conversão automática:** Se o body for um `GeoDataFrame`, é convertido automaticamente para GeoJSON via `__geo_interface__` (e um `DataFrame` puro vira lista de records).

### Saneamento da resposta

`/webhook/execute` não tem JWT, e o `content_type`/`headers` da resposta vêm do
autor do workflow. O servidor os saneia antes de responder (`webhook_router.py`):

- **Allowlist de `content_type`:** tipos fora de `application/json`, `application/xml`,
  `application/geo+json`, `text/plain`, `text/csv`, `text/xml`, `text/html` são
  **rebaixados para `text/plain`** — o conteúdo chega ao caller, só deixa de ser
  interpretado como markup pelo navegador.
- **Blocklist de headers:** o workflow não pode definir headers de segurança/identidade
  (`content-security-policy`, `x-frame-options`, `set-cookie`, `content-type`, …).
- **CSP endurecida para `text/html`:** respostas HTML recebem uma CSP com `sandbox`
  (origem opaca, sem script), contendo XSS refletido na origem da API.

### Body grande (body_ref)

Se o body serializado passa de `WEBHOOK_RESPONSE_INLINE_LIMIT` (padrão **1 MB**), o
`ResponseNode` sobe o conteúdo para o MinIO e retorna `__response__.body_ref`
(`{s3_key, size, content_type}`) em vez do body inline — evitando head-of-line
blocking no WebSocket executor→servidor. O `webhook_router` então baixa o objeto do
MinIO, streama para o caller e agenda a remoção.

> **Limitação conhecida (em correção):** o caminho > 1 MB está sob conserto e não
> se deve assumir que funciona ponta a ponta hoje. Para respostas grandes, prefira
> paginar ou compactar o body por ora.

---

## Exemplos

### Disparo assíncrono (sem ResponseNode)

```bash
curl -X POST https://api.exemplo.com/webhook/execute/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"cidade": "São Paulo", "raio_km": 5}'

# Resposta imediata:
# HTTP 202
# {"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

### Disparo síncrono (com ResponseNode)

```bash
curl -X POST https://api.exemplo.com/webhook/execute/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"cidade": "São Paulo", "raio_km": 5}'

# Resposta após execução completa:
# HTTP 200
# Content-Type: application/json
# {"total_areas": 42, "geometrias": [...]}
```

### Forçar retorno assíncrono mesmo com ResponseNode

```bash
curl -X POST https://api.exemplo.com/webhook/execute/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"cidade": "São Paulo", "no_wait": true}'

# Resposta imediata:
# HTTP 202
# {"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

### Variável de ambiente

```env
# Tempo máximo de espera pela resposta do ResponseNode (segundos)
WEBHOOK_RESPONSE_TIMEOUT=60
```

---

## Considerações de Design

### Por que oferecer retorno assíncrono?

Um caller que queira **eventos de nó em tempo real** precisa abrir o WebSocket
**antes** de a execução terminar. Se a resposta HTTP bloqueasse até o `ResponseNode`,
o caller só receberia o `task_id` no fim e perderia a progressividade (os eventos
existem no histórico Redis, mas chegariam todos de uma vez). Por isso o modo síncrono
é opcional: `no_wait=true` (ou a ausência de `ResponseNode`) devolve o `task_id` na
hora, para o caller escutar `/ws/workflow/{task_id}`.

O canvas obtém esse mesmo feedback ao vivo por outro caminho — dispara em
`POST /workflows/{id}/execute` (autenticado) e consome o WebSocket pelo `task_id`
retornado —, sem tocar no `/webhook/execute`.

### Por que usar Redis BRPOP/LPUSH?

O `webhook_router` (FastAPI) e o `executor_ws_router` são duas corrotinas independentes no mesmo servidor. O Redis atua como canal de comunicação entre elas:
- `executor_ws_router` faz `LPUSH webhook_response:{task_id}` quando o job completa
- `webhook_router` acorda do `BRPOP` e retorna a resposta HTTP

Isso evita qualquer acoplamento direto entre os dois handlers e funciona mesmo com múltiplos workers.

### Compatibilidade com histórico de eventos

O `log_workflows_router` subscreve o canal Redis **antes** de ler o histórico, garantindo que nenhum evento seja perdido independentemente do timing de conexão do cliente.
