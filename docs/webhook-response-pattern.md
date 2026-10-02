# Webhook + ResponseNode pattern

This document describes the request/response protocol between client and server for running workflows via webhook, including the synchronous mode enabled by the `ResponseNode`.

---

## Contents

- [Overview](#overview)
- [Execution Modes](#execution-modes)
- [Asynchronous Flow (default)](#asynchronous-flow-default)
- [Synchronous Flow (ResponseNode)](#synchronous-flow-responsenode)
- [The no_wait parameter](#the-no_wait-parameter)
- [Complete Sequence Diagram](#complete-sequence-diagram)
- [API Reference](#api-reference)
- [Authentication and limits](#authentication-and-limits)
- [ResponseNode — Properties](#responsenode--properties)
- [Examples](#examples)

---

## Overview

The `POST /webhook/execute/{id_hash}` endpoint is the entry point for triggering workflows externally. It supports two modes:

| Mode | Behavior | Use |
|---|---|---|
| **Asynchronous** | Returns `202 Accepted` immediately with `task_id` | Callers that only enqueue; progress consumed via WebSocket |
| **Synchronous** | Blocks until the workflow completes, returns the `ResponseNode`'s HTTP response | External integrations that need the response inline |

What controls it is the `no_wait` parameter in the request body and the presence of the `ResponseNode` in the workflow definition.

---

## Execution Modes

```
has_response_node=False  →  always returns 202 immediately
has_response_node=True
  ├─ no_wait=True   →  returns 202 immediately (caller asked for an asynchronous return)
  └─ no_wait=False  →  blocks until ResponseNode completes (external caller)
```

---

## Asynchronous Flow (default)

Used when the workflow does **not** contain a `ResponseNode`, or when `no_wait=true`.

```
Client                  Server                    Executor
  │                        │                         │
  │── POST /webhook/... ──►│                         │
  │                        │── WebSocket job ───────►│
  │◄─── 202 {task_id} ─────│                         │
  │                        │                         │ executes...
  │── WS /ws/workflow/{id}►│                         │
  │                        │◄── node_event ──────────│
  │◄── node status ────────│                         │
  │                        │◄── job_result ──────────│
  │◄── __workflow_complete__│                         │
  │── WS close ───────────►│                         │
```

**Details:**
1. The client receives `task_id` immediately
2. Opens the WebSocket `GET /ws/workflow/{task_id}`, sending the JWT in the first frame
3. Receives node events in real time (`started`, `completed`, `failed`)
4. Receives `__workflow_complete__` at the end and closes the WebSocket

---

## Synchronous Flow (ResponseNode)

Used when the workflow contains a `ResponseNode` **and** the caller does **not** send `no_wait=true`.

```
Client                  Server                        Executor
  │                        │                             │
  │── POST /webhook/... ──►│                             │
  │   (no_wait absent)     │── WebSocket job ───────────►│
  │                        │                             │
  │                        │  BRPOP webhook_response:id  │ executes nodes...
  │         (blocked)      │  (waiting)                  │
  │                        │                             │── publishes node events
  │                        │◄── node_event (N times) ────│    via Redis pub/sub
  │                        │                             │
  │                        │◄── job_result ──────────────│
  │                        │    (stats.__response__)     │
  │                        │                             │
  │                        │  LPUSH webhook_response:id  │
  │                        │  (BRPOP returns)            │
  │                        │                             │
  │◄── HTTP Response ───── │                             │
  │    status: 200          │── RPUSH __workflow_complete►│
  │    body: {...}          │   (Redis history)           │
  │    headers: {...}       │                             │
```

**Details:**
1. The server detects a `ResponseNode` in the workflow definition → `has_response_node=True`
2. After dispatching the job, it runs `BRPOP webhook_response:{task_id}` with a configurable timeout
3. The executor runs the workflow; the `ResponseNode` produces `{"__response__": {...}}` in the outputs
4. `executor_ws_router` receives `job_result`, extracts `stats.__response__`, does `LPUSH webhook_response:{task_id}`
5. `webhook_router` wakes up from the BRPOP and returns the HTTP response built from the `ResponseNode`
6. If the workflow fails before the `ResponseNode`, the server returns `HTTP 500`
7. If the executor does not respond within `WEBHOOK_RESPONSE_TIMEOUT` seconds, it returns `HTTP 504`

---

## The no_wait parameter

`no_wait` is a **server-side** option that forces the asynchronous return (`202`) even
in workflows with a `ResponseNode`. Today **no client in the repository sends it** —
it exists for external callers that prefer to consume the result via WebSocket
instead of blocking on the HTTP response.

> **The canvas does not use this endpoint.** Manual execution from the canvas goes through
> `POST /workflows/{id}/execute` (authenticated by JWT), which returns
> `{"task_id", "workflow"}` and never sends `no_wait` — see `executeWorkflow` in
> `web/service/GisFlowService.ts`. `/webhook/execute` requires a `WebhookTrigger`
> in the workflow and rejects any other type of trigger, which is why it does not suit the canvas.

### When to use it

| Caller | Recommended value | Reason |
|---|---|---|
| External integration | absent / `false` | Gets the `ResponseNode`'s HTTP response synchronously |
| Script / curl | absent / `false` | Same as external integration |
| Caller that prefers WebSocket | `true` | Receives `202 {task_id}` right away and consumes events at `/ws/workflow/{task_id}` |

### How it works

The parameter is read from the JSON body and removed before being passed as `inputs` to the workflow:

```python
# webhook_router.py
no_wait = bool(body.pop("no_wait", False))

if no_wait or not getattr(async_result, "has_response_node", False):
    return JSONResponse({"task_id": task_id}, status_code=202)
```

---

## Complete Sequence Diagram

### Infrastructure involved

```
┌─────────┐    ┌──────────┐    ┌───────────┐    ┌───────┐    ┌───────┐
│ Client  │    │ FastAPI  │    │  Executor   │    │ Redis │    │  DB   │
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
     │              │                │ executes nodes│             │
     │              │                │───────────────►             │
     │              │                │               │             │
     │              │ PUBLISH node_event             │             │
     │              │◄───────────────────────────────│             │
     │              │                │               │             │
     │              │ LPUSH webhook_response:{id}    │             │
     │              │◄───────────────────────────────│             │
     │              │ (BRPOP returns)│               │             │
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

## API Reference

### `POST /webhook/execute/{id_hash}`

**Path parameters:**
- `id_hash` — public identifier of the workflow

**Body (JSON):**

| Field | Type | Default | Description |
|---|---|---|---|
| `no_wait` | `boolean` | `false` | If `true`, returns 202 immediately without waiting for the `ResponseNode` |
| `debug_mode` | `boolean` | `false` | Enables debug mode (publishes events with the nodes' inputs/outputs) |
| `*` | `any` | — | All other fields are passed as `inputs` to the workflow |

**Responses:**

| Status | Condition | Body |
|---|---|---|
| `202 Accepted` | No `ResponseNode`, or `no_wait=true` | `{"task_id": "uuid"}` |
| `200` (or configured) | With `ResponseNode` and `no_wait=false` | Payload defined by the `ResponseNode` |
| `413 Payload Too Large` | Body above 10 MB (via `Content-Length`) | `{"detail": "Payload excede 10MB."}` |
| `429 Too Many Requests` | Rate limit: 20/min per (IP, `id_hash`) pair | the rate limiter's default response |
| `500 Internal Server Error` | Workflow failed before the `ResponseNode` | `{"error": "...", "task_id": "uuid"}` |
| `502 Bad Gateway` | `body_ref.s3_key` rejected, or failure downloading the body from MinIO | `{"error": "...", "task_id": "uuid"}` |
| `503 Service Unavailable` | No executor available (header `Retry-After: 60`) | `{"detail": "Execução temporariamente indisponível para este workflow."}` |
| `504 Gateway Timeout` | Executor did not respond within `WEBHOOK_RESPONSE_TIMEOUT`s | `{"error": "timeout", "task_id": "uuid", "message": "..."}` |
| `404 Not Found` | Workflow does not exist | `{"detail": "Workflow não encontrado"}` |
| `403 Forbidden` | Workflow deactivated | `{"detail": "Workflow está desativado..."}` |
| `403 Forbidden` | Workflow without a `WebhookTrigger` node | `{"detail": "Workflow não possui node WebhookTrigger..."}` |

### `GET /ws/workflow/{task_id}`

WebSocket for receiving run events in real time.

**Protocol:**
1. Connect
2. Send the JWT in the first frame (plain text)
3. Receive JSON events until `__workflow_complete__`

**Node event format:**
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

**Completion event:**
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

**History replay:** The server stores all events in Redis (`workflow:{run_id}:history`). On connecting, the WebSocket automatically replays the history before listening for new events. This guarantees that no event is lost even if the client connects after the run has started.

---

## Authentication and limits

- **No global JWT.** `/webhook/execute` does not go through JWT authentication. The
  access control is the credential of the `WebhookTrigger` node: without `credential_id`,
  open access; with `credential_id`, the token is validated in `start_analysis`.
- **Rate limit:** 20 req/min per (IP, `id_hash`) pair — saturating *one* specific
  workflow requires rotating IPs every window.
- **Maximum body:** 10 MB (`413` above that).
- **Response TTL:** the Redis key `webhook_response:{task_id}` expires in 300 s.

---

## ResponseNode — Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `statusCode` | `select` (string values) | `"200"` | HTTP code. Closed list: 200, 201, 204, 301, 302, 400, 401, 403, 404, 422, 500 |
| `contentType` | `select` | `application/json` | The response's `Content-Type`. Closed list: `application/json`, `text/plain`, `text/html`, `application/xml`, `text/csv` |
| `bodyMode` | `select` | `field` | Source of the body: `empty` (no body), `literal` (text/Jinja template in `customBody`), `field` (input field) |
| `customBody` | `code` | `""` | Literal text or Jinja template (visible when `bodyMode=literal`). E.g.: `Olá {{ WebhookTrigger.output.nome }}` |
| `bodyField` | `string` | `""` | Input field to use as the body (visible when `bodyMode=field`). Empty = first input |
| `headers` | `object` | `{}` | Additional headers (key → value) |

**Body priority:** `customBody` > `bodyField` > first available input.

**Internal output:** The node produces `{"__response__": {...}}` in the outputs (keys `status_code`, `content_type`, `headers` and `body` or `body_ref`). This key is handled specially by the server and by the executor — it is not passed on to downstream nodes.

**Automatic conversion:** If the body is a `GeoDataFrame`, it is automatically converted to GeoJSON via `__geo_interface__` (and a plain `DataFrame` becomes a list of records).

### Response sanitization

`/webhook/execute` has no JWT, and the response's `content_type`/`headers` come from the
workflow's author. The server sanitizes them before responding (`webhook_router.py`):

- **`content_type` allowlist:** types other than `application/json`, `application/xml`,
  `application/geo+json`, `text/plain`, `text/csv`, `text/xml`, `text/html` are
  **downgraded to `text/plain`** — the content reaches the caller, it just stops being
  interpreted as markup by the browser.
- **Header blocklist:** the workflow cannot set security/identity headers
  (`content-security-policy`, `x-frame-options`, `set-cookie`, `content-type`, …).
- **Hardened CSP for `text/html`:** HTML responses get a CSP with `sandbox`
  (opaque origin, no scripts), containing reflected XSS at the API's origin.

### Large body (body_ref)

If the serialized body exceeds `WEBHOOK_RESPONSE_INLINE_LIMIT` (default **1 MB**), the
`ResponseNode` uploads the content to MinIO and returns `__response__.body_ref`
(`{s3_key, size, content_type}`) instead of the inline body — avoiding head-of-line
blocking on the executor→server WebSocket. The `webhook_router` then downloads the object from
MinIO, streams it to the caller and schedules its removal.

> **Known limitation (being fixed):** the > 1 MB path is under repair and you
> should not assume it works end to end today. For large responses, prefer to
> paginate or compress the body for now.

---

## Examples

### Asynchronous trigger (without ResponseNode)

```bash
curl -X POST https://api.exemplo.com/webhook/execute/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"cidade": "São Paulo", "raio_km": 5}'

# Immediate response:
# HTTP 202
# {"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

### Synchronous trigger (with ResponseNode)

```bash
curl -X POST https://api.exemplo.com/webhook/execute/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"cidade": "São Paulo", "raio_km": 5}'

# Response after the run completes:
# HTTP 200
# Content-Type: application/json
# {"total_areas": 42, "geometrias": [...]}
```

### Forcing an asynchronous return even with ResponseNode

```bash
curl -X POST https://api.exemplo.com/webhook/execute/wf_abc123 \
  -H "Content-Type: application/json" \
  -d '{"cidade": "São Paulo", "no_wait": true}'

# Immediate response:
# HTTP 202
# {"task_id": "550e8400-e29b-41d4-a716-446655440000"}
```

### Environment variable

```env
# Maximum time to wait for the ResponseNode's response (seconds)
WEBHOOK_RESPONSE_TIMEOUT=60
```

---

## Design Considerations

### Why offer an asynchronous return?

A caller that wants **real-time node events** has to open the WebSocket
**before** the run finishes. If the HTTP response blocked until the `ResponseNode`,
the caller would only receive the `task_id` at the end and would lose the progressive updates (the events
exist in the Redis history, but they would all arrive at once). That is why the synchronous mode
is optional: `no_wait=true` (or the absence of a `ResponseNode`) returns the `task_id` right
away, so the caller can listen on `/ws/workflow/{task_id}`.

The canvas gets this same live feedback by another path — it triggers via
`POST /workflows/{id}/execute` (authenticated) and consumes the WebSocket using the returned
`task_id` —, without touching `/webhook/execute`.

### Why use Redis BRPOP/LPUSH?

The `webhook_router` (FastAPI) and the `executor_ws_router` are two independent coroutines in the same server. Redis acts as the communication channel between them:
- `executor_ws_router` does `LPUSH webhook_response:{task_id}` when the job completes
- `webhook_router` wakes up from the `BRPOP` and returns the HTTP response

This avoids any direct coupling between the two handlers and works even with multiple workers.

### Compatibility with the event history

The `log_workflows_router` subscribes to the Redis channel **before** reading the history, guaranteeing that no event is lost regardless of the timing of the client's connection.
