# Spec — Per-workspace execution policy: dedicated group, fallback and isolation floor

Status: **implemented** — delivered in PRs (waves 1–4), behind the `EXECUTOR_POLICY_ROUTING` flag; includes the post-implementation repair migration `20260908_0001` (`d9e3f1a5b624`). · Date: 2026-09-06 (rev. 5)
Scope: `app/` (routing, model, API, scheduler, consumer), `web/app/components/workspace/` (config)
Does not touch: `flow/` (engine) or `executor/` (runner) — the change is about _where_ the job goes, not _how_ it runs.

> **Maintenance note.** This spec has already been implemented. The inline `arquivo:linha` (file:line)
> citations were written BEFORE the routing refactor and have **drifted** — for
> example, `_resolve_candidates` is now at `workflow_execution_service.py:319`
> (not `:258`), `_dispatch_job` at `:447` (not `:317`) and `send_job` at
> `executor_connections.py:1417` (not `:1328`). The mechanisms described remain
> valid; treat the numbers below as indicative. The actual location is in the
> delivered modules: `app/services/workspace_executor_service.py` (the policy and
> its rules), `_resolve_candidates_by_policy` + the isolation barrier in
> `workflow_execution_service.py`, `app/models/workspace_executor.py`,
> `WorkflowRun.dispatch_tier`, and the migrations `20260907_0001` / `20260907_0002` /
> `20260908_0001`.

## 1. Problem

A workspace bound to a dedicated executor, when that executor is unavailable,
**silently falls back to the shared pool**. For data under hard isolation
(data residency, on-premise network/credentials, compliance), running on the pool is
_incorrect_ — and today it happens without warning. For other workspaces, falling back to the pool is
exactly what the owner wants — but they **never chose it**, and nothing shows them that
it happened.

There is a single cause, in `_resolve_candidates`
(`app/services/workflow_execution_service.py:258`): the function builds a list of
candidates `[dedicado do workspace, se online] + [pool default inteiro, least-loaded]`
and `_dispatch_job` (`:317`) consumes that list **in order as a failover sequence**.
The dedicated executor is, in practice, just **priority #1** — never a constraint, and never
a choice:

| Dedicated executor's situation | Current behavior | Evidence |
|----------------------|---------------------|-----------|
| Online with spare capacity | runs on the dedicated executor ✅ | `workflow_execution_service.py:284-287` |
| Offline / no `public_key` / `status!=active` | **falls back to the pool** ⚠️ | `:288-307` (pool always appended) |
| Online but with a full queue (same worker) | `send_job=False` → **falls back to the pool** ⚠️ | `executor_connections.py:1310-1317` |
| Online but full (multi-worker, via relay) | `send_job=True` → run **fails** (does not overflow) 🐞 | `executor_connections.py:1328-1352` |
| Only the dedicated executor, and it is down | **falls back to the pool** ⚠️ | `:288-307` |
| Neither dedicated nor pool | 503 without creating a run | `:309-312` |

Two data axes intersect badly:

- `Executor.executor_type` / `Executor.is_default` — _membership in the shared
  pool_ (a property of the executor). `app/models/executor.py:34,37`.
- `Workspace.target_executor_id` — _workspace→executor edge_, today **1:1** and with no
  validation that the target is `dedicated`. `app/models/workspace.py:21`,
  `app/api/routers/workspace_router.py:576`.

And there are two discrepancies that make it worse:

- **The UX lies**: the screen says "Dedicado **fixa** um executor específico" ("Dedicated **pins** a specific executor")
  (`web/app/components/workspace/settings-sheet/executor-section.tsx:96`), but the
  runtime does a best-effort preference with fallback.
- **Nobody sees where it ran**: `WorkflowRun.host` exists and is exposed as `agent_host`
  in observability (`app/services/observability_service.py:198`), but no screen
  renders it; there is no "ran on the pool" toast/badge.

## 2. The owner's decisions

### 2.1 First round (2026-09-06) — the model

1. ~~"Dedicated" = HARD isolation; a workspace with a dedicated executor never touches the pool.~~
   **Superseded by the 4th round (§2.4):** hard isolation becomes **one of the
   policies** the owner chooses (`terminal: falhar`), and the platform admin can
   make it mandatory per workspace (floor).
2. **If the chain is exhausted: fail IMMEDIATELY.** No waiting queue, no automatic
   re-dispatch.
3. **Granularity: per workspace.** Not per workflow, not per trigger.
4. **Group of dedicated executors: YES.** A workspace points to a **set** of 1..N
   dedicated executors; failover happens within the tier.
5. **Capability-based routing: NOT** needed. The group is by executor
   identity, not by label/capability.

### 2.2 Second round (2026-09-06) — the edge cases

6. ~~Q1 — Migration: the `target_executor_id` values become isolated (no pool).~~ **Superseded
   (§2.4):** they become **tier 1 = {executor}, terminal = pool** — exactly what they do
   today, now explicit and visible. **Zero behavior change.**
7. **Q3 — Pool executor in a dedicated tier: NO.** An `is_default=true` executor
   is rejected on inclusion (§4.3) and evicted on promotion to default (§4.4). The pool only
   takes part as the chain's **terminal**, never as a tier member.
8. **Q5 — Synchronous webhook: YES, return 503** to the external caller when the chain is
   exhausted. With a **generic** body (does not leak fleet state to an anonymous caller, §6) and
   `Retry-After`.
9. **Q6 — Scheduler: YES, notify the owner** when an occurrence fails because the chain was
   exhausted. Notification on **state transition**, with a bounded reminder — never one
   email per tick (§7.4).

### 2.3 Third round (2026-09-06) — wrap-up

10. **Q2 — Tier of one: YES.** A single executor in the primary tier is valid and is the
    expected case after the migration. The screen reports the health (§9) but does **not** force a 2nd
    member.
11. **Q4 — All full: fail immediately** (when the chain is exhausted). No waiting for a
    slot; each executor's local queue already absorbs spikes.
12. **Q7 — Label: "Isolado" (Isolated) workspace** for the policy that never touches the pool;
    **Dedicado** (Dedicated) remains the executor type (§9 for the three labels).

### 2.4 Fourth round (2026-09-06) — the policy belongs to the owner

> "Let the workspace administrator/owner decide whether, as a fallback, they want to run on
> another group or on the pool; handing this decision to the user is more sensible."

13. **The fallback policy is chosen by the workspace owner/admin**, per
    workspace, as a **chain of tiers + terminal** (§4, §5): primary tier of
    dedicated executors → optional fallback tier (other dedicated executors of the
    workspace itself) → terminal **fail** or **pool**.
14. **Q8 — Preselection for new groups: Fail.** Safe by default: whoever wants the pool
    as a last resort opts in consciously.
15. **Q9 — Tiers in v1: primary + one fallback.** Two tiers, not N.
16. **Q10 — Platform admin floor: YES, already in v1.** The platform admin can
    set, per workspace, that the terminal **must be fail** (`isolation_floor =
    no_pool`); the workspace owner/admin cannot loosen it. This is what restores a
    *hard* guarantee where it is an external requirement.

**There are no open questions.**

### 2.5 Fifth round (2026-09-07) — post-implementation adjustments

Review of the implementation in use (reported bugs + static review through four
lenses + smoke test against a real database). Rules that now apply:

- **No primary tier ⇒ terminal `fail`.** "Pool as a last resort" is a
  choice made WITH a primary on the table (and asks for confirmation on screen); when
  the primary is emptied — through the editor, by forced revocation or through the legacy
  endpoint — the terminal goes back to the default. Without this, the old choice reappeared
  on the next executor added, without confirmation.
- **Legacy endpoint `PUT /workspaces/{id}/executor`:** a pool executor or
  `null` CLEARS all tiers (it used to leave tier 1 orphaned). A tier 1
  born from empty through this path gets terminal `pool` (outside the floor):
  that is the behavior the legacy path has today, and the policy has to start out the same
  so that flipping the flag changes nothing. Isolating is an explicit decision in the editor.
- **The `no_pool` floor is absolute:** it applies even without a primary tier (§5.3 overrides the
  earlier wording of §4.2). With no primary and under the floor, the workspace is Isolated
  with zero executors — nothing runs until one is added. Before, emptying the primary
  of a workspace with a floor sent runs to the pool.
- **Executor authorization = legacy pointer ∪ tiers.** Drive, artifacts,
  portal, ChangeDetector, Drive events and GeoSync auto-detection now
  recognize tier members (`workspace_ids_for_executor`). Before, a job
  routed to a tier member broke on the first Drive read (403).
- **One run per occurrence:** `NoExecutorAvailableError` carries `run_id` when
  the dispatch has already created the `failed` run; the scheduler only materializes a
  synthetic run when there is none.
- **Backfill repaired** (migration `d9e3f1a5b624`): pool and
  revoked executors leave the tiers; orphaned fallback entries are removed; workspaces in the trash
  get the same backfill so that a restore does not come back without a tier.
- **Single vocabulary on screen:** modes *Compartilhado* (Shared) / *Isolado* (Isolated) /
  *Dedicado + pool* (Dedicated + pool); tiers *executores principais* (primary executors) and *de reserva* (fallback); what
  happens when nobody is available is the *último recurso* (last resort). "Fallback"
  stays in the code. The panel section is called *Execução* (Execution) and the editor, *Política
  de execução* (Execution policy).
- **With the flag off, the screen follows the legacy behavior:** the asset panel and the
  row derive the executor from the legacy pointer (what routes today) and show
  the policy as a *preview* (dashed badge); the group only takes over the selector when
  the policy is in effect. The editor opens with the notice "ainda não está em vigor" (not in effect yet).
- **The floor has a screen:** Configurações (Settings) → Execução (Execution) lists the policy of every
  workspace (`GET /admin/workspaces/policies`) with an "Exigir
  isolamento" (Require isolation) toggle per workspace; requiring it asks for confirmation and points out who would be left
  without an executor. A floor with no primary becomes a pending item in the overview.
- **Load per executor:** the editor shows what each executor publishes
  ("1 de 4 em execução · 2 na fila" — 1 of 4 running · 2 queued) and marks the ones that are full — that is what gives
  meaning to "online".
- **Destructive actions ask for confirmation:** going back to the pool through the quick selector
  with a dedicated executor on the table (deletes the whole policy) and removing the last
  primary (takes the fallback tier with it). The 409 from revoking/removing an executor lists the
  affected workspaces and the screen offers "mesmo assim" (anyway; `force`), instead of a
  generic toast.

## 3. Goal / Non-goal

Goal:
- The fallback behavior becomes a **declared choice** of the workspace owner, and
  the screen shows exactly what happens when the executor goes down — because they are the one who
  defined it.
- Three possible outcomes, all explicit:
  - **Pool** (default, unchanged): a workspace without a group uses the shared pool.
  - **Isolated**: tier(s) of dedicated executors, terminal **fail**; **never** pool.
  - **Dedicated with fallback**: dedicated tier(s) and, once exhausted, the **pool**.
- **Platform admin floor** that makes "Isolated" mandatory where it is a requirement.
- Failure that is **readable and attributable** for the owner, **opaque** for anonymous callers.
- The allowed set of executors as a **verifiable invariant** (§5.3), per
  policy — not just as the routing's happy path.
- Fix the relay/direct asymmetry of `is_full` (🐞 above) so that "full" fails over
  _within the tier_, instead of killing the run on one path and overflowing on the other.
- **Migration with no behavior change** (§8).

Non-goal:
- Waiting queue / automatic re-dispatch (the owner chose to fail immediately).
- Capability/label-based routing.
- Per-workflow or per-trigger policy.
- More than two tiers (Q9).
- Redesigning enrollment/mTLS or the job protocol.

### 3.1 What about those without a dedicated executor? (pool mode)

This is most workspaces, and the short answer is: **nothing changes by default**. A workspace
with no primary tier = pool mode = exactly today's behavior — least-loaded among the
`is_default` executors, failover within the pool, 503 only if the whole pool is
down. The migration, the routing flag (§8) and the floor **do not touch** these workspaces.
Having a policy is opt-in: all it takes is having access to a dedicated executor and creating the primary
tier.

What pool mode **gains** from this spec, without asking:

- **More predictable capacity.** Today every dedicated executor that goes down overflows to the pool.
  With the policy, only those who **chose** the pool as terminal overflow — and that becomes
  visible (§8, wave 1), which tends to reduce unwitting overflow.
- **Fix for the relay `is_full`** (§5.2). The bug is in `send_job`, not in the mode.
- **Hardened presence signal** (§5.1). The spurious 503 from a Redis blip hits the
  whole pool today; the mitigation applies to everyone.
- **A scheduler that does not swallow failures** (§7.4). A cron whose pool is down gets the same
  treatment as a cron whose chain was exhausted.
- **Observability** (§8, wave 1): `agent_host` on screen. **Pool health** and
  pre-flight (§9).

## 4. Data model

### 4.1 Workspace executor tiers

Today the link is 1:1 (`Workspace.target_executor_id`). The policy calls for N executors in
up to two tiers. Proposal: a **`workspace_executors`** join table with the tier.

```
workspace_executors
  workspace_id  FK workspaces.id_hash   NOT NULL
  executor_id   FK executors.id_hash    NOT NULL
  tier          smallint                NOT NULL  CHECK (tier IN (1, 2))
                                        -- 1 = primary, 2 = fallback
  added_by      String(36)              -- User.id_hash of who added it (audit)
  created_at    timestamptz             default now()
  UNIQUE (workspace_id, executor_id)    -- an executor is not in two tiers
  INDEX (workspace_id, tier)            -- hot read at dispatch
  INDEX (executor_id)                   -- "which workspaces depend on this executor?" (§4.4)
```

### 4.2 Policy and floor, on the workspace

```
workspaces (new columns)
  fallback_terminal  String(8)  NOT NULL default 'fail'    -- 'fail' | 'pool'  (Q8: default fail)
  isolation_floor    String(8)  NOT NULL default 'none'    -- 'none' | 'no_pool' (Q10; platform admin only)
```

Derived rules, with no "mode" flag:

> **Pool mode ⇔ zero rows with `tier = 1`.** The policy is only read when there is a primary
> tier.
> **Isolated ⇔ there is a primary tier and the effective terminal is `fail`.**
> **Effective terminal = `fail` if `isolation_floor = no_pool`, otherwise `fallback_terminal`.**

The effective terminal is computed **at dispatch**, not only on write: even if the database
has `fallback_terminal = pool` on a workspace with a floor (a state the API rejects,
§4.5), routing treats it as `fail`. Defense in depth against direct writes or
migration ordering.

`Workspace.target_executor_id` is absorbed and **retired**: the migration copies each
`target_executor_id IS NOT NULL` into a `tier = 1` row and writes
`fallback_terminal = 'pool'` (§8); the column falls out of use for one release and is then
removed. A fallback tier (`tier = 2`) only exists when the owner creates it (Q9).

### 4.3 Member validation (on inclusion in any tier)

- must exist, have `status='active'`, no `deleted_at`, and have a `public_key` (otherwise it would never
  be dispatchable);
- **`is_default=true` is rejected** (Q3) — a pool executor does not join a tier; the pool
  takes part only as terminal. Error 422 with an explicit message;
- **cannot be in the other tier** (UNIQUE) — an executor is primary *or* fallback;
- whoever adds it must have access to the executor (same check as
  `set_workspace_agent`, `workspace_router.py:594-598`) and be owner/admin of the workspace;
- **tier 2 requires a non-empty tier 1**; emptying tier 1 deletes tier 2 (there is no
  "fallback only");
- inclusion/removal generate an **audit event** (who, which executor, which tier, which
  workspace, when).

### 4.4 Consistency over time (what nobody handles today)

Today deleting/revoking an executor does **not** touch `Workspace.target_executor_id` (no
write in `user_executor_service.py` / `executor_service.py`; only reads). The pointer
is left dangling and the UI shows "sumido" (gone). With tiers this becomes a time bomb: a primary
tier that empties silently makes **every future run fail** (terminal `fail`)
or **overflow to the pool without anyone knowing** (terminal `pool`). Rules:

- **Revoking/deleting/deactivating an executor**: list the workspaces that have it in some
  tier (`executor_id` index). If the removal **would empty the primary tier** of a
  workspace, the operation is **blocked** with the list, unless `force=true` is explicit — and,
  when forced, it notifies the owners. If ≥1 member remains in the tier, it removes the row and warns.
- **Promoting an executor to `is_default`** (`set_default_agent`,
  `user_executor_service.py:108-137`): this is the inverse operation of Q3 — the executor is
  **removed from every tier** it is in, with the same block if it would empty a
  primary tier.
- **An `inactive`/`pending` executor** stays in the tier (it is reversible), but is not eligible
  at dispatch (§5) and counts as "unavailable" in the health view (§9).

### 4.5 Who writes what

| Field | Written by | Rule |
|-------|---------|-------|
| tiers (`workspace_executors`) | workspace owner/admin | §4.3 |
| `fallback_terminal` | workspace owner/admin | `pool` is **rejected (403)** if `isolation_floor = no_pool`; the change is audited |
| `isolation_floor` | **platform admin only** | when setting `no_pool`, the API also forces `fallback_terminal = fail` and notifies the owner; audited |

## 5. Routing (the heart of the change)

Rewrite `_resolve_candidates` (`workflow_execution_service.py:258-314`) to build
the **chain** from the policy:

```
candidates(ws):
  n1 = elegiveis(tier 1)              # active + public_key + disponivel, least-loaded
  if n1 is empty AND ws has no tier 1: # POOL MODE (unchanged)
      return pool least-loaded
  n2 = elegiveis(tier 2)              # least-loaded (may be empty)
  chain = n1 + n2                     # strict order between tiers
  if terminal_efetivo(ws) == 'pool':
      chain += pool least-loaded      # the pool is the last resort, chosen by the owner
  return chain                        # empty ⇒ NoExecutorAvailableError (fails immediately)
```

- **Within a tier**, least-loaded (running+queued); **between tiers**, strict
  order. `_dispatch_job` consumes the chain as it does today — the failover mechanism does not
  change, only the _content_ of the list. _(2026-09-26: the load is now the one counted in the database — in-flight runs per
  host — and the order within the tier is now: those with a free slot by a draw
  weighted by free slots, those without a slot by relative occupancy, full ones (by the
  report or by the count) last; see "Choosing the executor" in
  `docs/architecture.md`.)_
- **Empty chain ⇒ immediate failure**, reusing the existing paths: nothing online →
  `NoExecutorAvailableError` **before creating the run** (`:309-312`); online but all
  refuse → run `failed` + `account_terminal_run` (`:506-517`). Message per policy
  (§6).
- **The tier it ran on is recorded**: `WorkflowRun.dispatch_tier`
  (`'primary' | 'fallback' | 'pool'`), written at the same point where `host` is written
  (`:369` in the INSERT, `:443` on failover). This is what makes "ran on the fallback/pool"
  observable per run without depending on the current configuration (which may change later).

### 5.1 Signal reliability (mandatory under fail-immediately; applies to everyone)

With fallback to the pool, a loose signal cost "it went to the pool". With terminal
**fail**, the same loose signal now costs "the run **failed**". And the signal is the same
for the pool: a blip that marks all the `is_default` executors offline returns a **spurious 503** to
those who only use the pool, today. Hardening `disponivel(e)` is a **general** improvement and
lands before the new routing is switched on:

- **Redis blip**: `is_online` is fail-closed (`executor_connections.py:541-547`); a
  blip at the moment of dispatch would mark a whole tier (or the pool) offline. Mitigation:
  treat "presence = don't know" (tri-state `None`) conservatively — try the
  send anyway (the real `send_job` will tell whether it connects), instead of excluding the candidate
  just on the presence read.
- **Reconnection**: presence is deleted immediately on a clean disconnect
  (`executor_connections.py:1033-1034`), with no dispatch grace period, while orphans
  get a grace of ~20s (`executor_ws_router.py:196`). Mirror a **short grace period** at
  dispatch before considering an executor unavailable.
- **Momentarily full**: `capacity` lags by ~10s. Within a tier it is benign (it only
  reorders). If a whole tier looks full, the chain moves on to the next tier or
  terminal — which is the chosen policy; and if the chain is exhausted, Q4 applies: fail immediately.

### 5.2 Fixing the relay asymmetry (🐞, mandatory)

`send_job` on the relay path does not check `is_full` (`executor_connections.py:1328-1352`):
a full member reached through the relay "accepts" the job and the run **fails** because of a full queue
instead of the chain moving on. Fix it so that the relay also signals capacity (check
`is_full` via capacity presence in Redis, or request/response), so that "full"
⇒ `send_job=False` ⇒ next candidate. Without this, the chain is non-deterministic
(it depends on whether the WS is on the same uvicorn worker).

### 5.3 The allowed set as an invariant (defense in depth)

Routing is _one_ decision; the policy has to survive regressions in it.

- **Allowed set** of a workspace = `nível 1 ∪ nível 2 ∪ (pool se terminal
  efetivo = pool)` (tier 1 ∪ tier 2 ∪ (pool if effective terminal = pool)). For pool mode, = pool.
- **Second barrier in `_dispatch_job`** (`:410`): before `build_job_message`,
  **assert** `ag.id_hash ∈ permitido(ws)`. Violation ⇒ does not send, run `failed`,
  `ERROR` log and `dispatch_event` with `outcome=isolation_violation` (must be
  **always 0**; alert on `>0`, based on the log — the server has no metrics
  exporter). As implemented: the `WorkflowRun.error_category` **column** gets the
  coarse value `isolation` (the column's short taxonomy), while the
  granular category `isolation_violation` is the one in `NoExecutorAvailableError.category` and in
  `dispatch_event`. The floor is read
  here too: with `isolation_floor = no_pool`, a pool executor is never allowed,
  whatever `fallback_terminal` says.
- **Cryptographic anchoring, already in place**: the envelope is encrypted to the X25519 key
  **of the chosen executor** (`build_job_message(agent_x25519_pub_pem=…)`, `:413-431`).
  A job encrypted for `geo-01` is unreadable to `pool-a`. The assertion above guarantees that
  a job is only encrypted for keys in the allowed set.
- **Credentials only travel to the allowed set**: `inject_credentials`
  (`:378-382`) runs before the candidate loop; the list is the chain, so credentials
  of an isolated workspace never go into an envelope for the pool.
- **Sub-workflows**: the collector already discards sub-workflows from other workspaces
  (`workflow_service.py:538`) and duplication is restricted to the same workspace (`:306-314`).
  An invariant to **preserve with a test**: the envelope's whole chain inherits the policy of the
  triggering workspace.
- **Moving a workflow between workspaces** (`moveTargets`, `WorkspaceContext.tsx:44`): moving
  between workspaces with **different policies** changes the data's execution boundary.
  The dialog warns ("passa a poder rodar no pool compartilhado" — can now run on the shared pool / "passa a ser isolado" — becomes isolated)
  and requires confirmation. Runs already completed keep their original `run.workspace_id`
  (`workflows_router.py:435-443`).

## 6. Readable failure — and who gets to read it

Two audiences, two messages:

- **Owner/operator (run, history, log, email)** — detailed, per policy:
  - Isolated: **"Workspace isolado: nenhum dos N executores dedicados está disponível.
    O job NÃO foi enviado ao pool compartilhado."** (Isolated workspace: none of the N dedicated executors is available.
    The job was NOT sent to the shared pool.) + name and reason per member/tier.
  - Dedicated with fallback: **"Nenhum executor disponível: N dedicados e o pool
    compartilhado estão fora."** (No executor available: N dedicated executors and the shared pool are down.)
  - Pool mode: **"Nenhum executor do pool compartilhado disponível."** (No shared pool executor available.)
  `error_category` of `NoExecutorAvailableError` (propagated to the 503's `detail` and to the
  metrics): `no_dedicated_executor` (isolated) | `no_executor_chain` (fallback
  exhausted) | `no_pool_executor` (pool). They separate "my group went down" from "the platform
  went down". As implemented, the `WorkflowRun.error_category` **column** stores the coarse value
  `no_executor`; the granularity above lives in the exception, not in the column.
- **Anonymous webhook caller** — generic: body `503 {"detail": "Execução
  temporariamente indisponível para este workflow."}` + header `Retry-After: 60`.
  **No** names, counts or policy: the code already takes care not to leak fleet
  state to an anonymous caller (`workflow_service.py:520-573`) and this spec keeps the rule.

## 7. Effects per trigger path

Routing is shared (`start_analysis`), so the policy reaches all four
paths — always **when the chain is exhausted**.

### 7.1 Manual (`workflows_router.py:353`)
Immediate 503 with the detailed message. The UI does a **pre-flight** (§9).

### 7.2 Retry (`workflows_router.py:502`)
Redoes `_resolve_candidates` with the current policy. Same pre-flight.

### 7.3 Webhook (`webhook_router.py:184`) — Q5
- Chain exhausted → **generic 503 + `Retry-After`** (§6). Documented in the OpenAPI.
- **Idempotency preserved** (verified): the `idempotency:wf_execute:{key}` key is
  written **only after** a successful dispatch (`workflow_service.py:586-591`); a 503
  does not consume it. Lock this in with a test (§11).
- **No run per call**: on the "nothing online" path the 503 remains **stateless**
  (`:309-312`), without creating a `WorkflowRun` — no write amplification.

### 7.4 Scheduler (`async_scheduler.py:74`) — Q6
Today it swallows the exception and only advances `next_run_at` (`:155-167`): the occurrence disappears. Under
this spec, **for any policy, including pool mode**:

- **Record a `failed` `WorkflowRun`** with the policy's message and close it via
  `account_terminal_run` — the scheduled occurrence needs to leave a trace.
- **Notify the workspace owner** (`Workspace.owner_id`) and the admins, by email
  (`email_service.send_email_background`, new template). The `Schedule` has no owner
  of its own (`app/models/schedule.py`), so the recipient comes from the workspace.
- **Per transition, not per tick.** State per `(schedule_id)` in Redis: notifies on the
  **first** failure of the window, at most **one reminder** every 6 h, and a
  **recovery** notice on the next occurrence that runs. Since the pool is shared, an
  incident hits many workspaces: each owner gets **one** notice for their cron; the
  platform admin sees the aggregate in `/health` (§11).
- The per-workspace notification webhook (`_fire_notification_if_configured`,
  `run_result_consumer.py:562`) does **not** fire here (closing happens outside the
  `run_results` queue); email is the channel for this failure. See §11 on unifying them.

## 8. Migration and rollout — no behavior change

The 4th round removed the risk that called for a shadow mode: workspaces with
`target_executor_id` become **tier 1 = {executor}, `fallback_terminal = pool`** — which is
exactly what they already do. Nobody starts failing where they used to run. What changes is that
the policy **appears** on screen, and whoever needs isolation tightens it consciously.

Waves, each one reversible and deliverable in its own PR:

1. **Observability first.** Render `agent_host` and the badge of the tier it
   ran on (`dispatch_tier`, §5): "rodou no fallback" (ran on the fallback) / "rodou no pool" (ran on the pool). A structured
   event per dispatch (§11).
2. **Model + backfill.** Create `workspace_executors` (with `tier`), the
   `fallback_terminal` and `isolation_floor` columns; an **idempotent** Alembic migration
   (`INSERT … ON CONFLICT DO NOTHING`) copying `target_executor_id` as `tier = 1` and
   writing `fallback_terminal = 'pool'` on those workspaces. Old column preserved under
   **dual-write** for one release (rollback = turn off the flag).
3. **New routing behind a flag** (`EXECUTOR_POLICY_ROUTING = off | on`), with the
   relay fix (§5.2) and the signal hardening (§5.1) **first**. In `on` with the
   backfill above, the result is identical to today's — the flag exists for rollback, not
   for shadowing.
4. **Policy UI** (§9) + floor endpoint for the platform admin (§4.5).
5. **Communication** to owners of workspaces with a dedicated executor: "your policy is
   visible; today it is *fallback: pool*; to isolate, change the terminal to *fail*". And
   to the platform admin: where to set the floor.
6. Removal of the old column in the following release.

Safe defaults in every wave: a workspace with no tier = pool mode = untouched;
**new** groups are born with terminal `fail` (Q8). Runs **in flight** are not
reallocated.

## 9. Configuration surface (web)

`web/app/components/workspace/settings-sheet/executor-section.tsx` stops being a
single-executor `<Select>` and becomes the **policy editor**, in three blocks:

1. **Dedicated executors** (primary tier): a list with add/remove; avatar,
   name, online/offline, load. `is_default` executors do not appear as an option (Q3).
2. **Fallback** (optional, Q9): "Se nenhum estiver disponível, tentar estes outros
   executores dedicados" (If none is available, try these other dedicated executors) — the tier 2 list, same rules.
3. **When everything above fails** (terminal, mandatory, preselected on **Falhar** (Fail)):
   - ( • ) **Falhar na hora** (Fail immediately) — "a execução falha e você é avisado; nada vai ao pool" (the run fails and you are notified; nothing goes to the pool).
   - (   ) **Usar o pool compartilhado** (Use the shared pool) — "os dados poderão rodar em executores
     compartilhados da plataforma" (the data may run on the platform's shared executors). **Disabled** with the reason when
     `isolation_floor = no_pool`: "definido pelo administrador da plataforma" (set by the platform administrator).

Labels (Q7):
- **Isolado** (Isolated) — dedicated tier(s) + terminal fail. Purple badge (the same as
  "Dedicado" in `ExecutorTypeStyles.ts`), with a padlock when there is a floor.
- **Dedicado · fallback: pool** (Dedicated · fallback: pool) — dedicated tier(s) + terminal pool. Purple badge with
  a teal suffix (the pool's teal).
- **Compartilhado** (Shared) — pool mode, as today when `target=null`.

Also:
- **Health per tier** as a first-class concept: `GET
  /workspaces/{id}/executors` returns the members by `tier` with `online`, `capacity` and
  the aggregates `available_primary`, `available_fallback`. The UI shows "**N de M
  disponíveis**" (N of M available) per tier; with 0 in the primary and terminal fail, it alerts that _new
  runs will fail_; with terminal pool, it warns that _they will go to the pool_.
- **Pool health** for workspaces in pool mode ("N de M online" — N of M online — among the
  `is_default` executors) and the **same pre-flight** — a 503 from a pool being down has to be as
  discoverable as one from an exhausted chain.
- **Pre-flight on trigger**: if the effective chain has 0 available, an inline warning before
  the click; the button stays enabled (failing on purpose is a valid choice).
- **Workspace panel** (`workspace-hero.tsx`): the status line reflects the policy
  ("Isolado · 2 de 2 online" / "Dedicado · fallback: pool · 1 de 2 online").
- **Switching the terminal** to `pool` asks for confirmation with the shared-data
  sentence; the switch is recorded in the audit log.

Backend (provisional names):
`GET/PUT /workspaces/{id}/executors` (tiers), `POST/DELETE
/workspaces/{id}/executors/{executor_id}?tier=1|2`, `PUT /workspaces/{id}/fallback`
(terminal; owner/admin), `PUT /admin/workspaces/{id}/isolation-floor` (platform
admin only).

## 10. Worked example

Three workspaces, three policies. Shared pool = { pool-a, pool-b }.

- **"Bacia do Paranapanema"** — data with mandatory on-premise residency. Tier 1 =
  { geo-01, geo-02 }; terminal **fail**; **`no_pool` floor** set by the platform
  admin. Policy: **Isolado** 🔒.
- **"Licenciamento Ambiental"** — prefers availability. Tier 1 = { lic-01 }; tier
  2 = { lic-02 }; terminal **pool**. Policy: **Dedicado · fallback: pool**.
- **"Cadastro Urbano"** — no dedicated executor. Policy: **Compartilhado** (pool).

| # | Workspace | State | Today | Under this spec |
|---|-----------|--------|------|---------------|
| A | Bacia | geo-01 online and free | runs on geo-01 | runs on geo-01 (`dispatch_tier=primary`) |
| B | Bacia | geo-01 **full**, geo-02 free | **falls back to pool-a** ⚠️ | runs on **geo-02** ✅ |
| C | Bacia | geo-01 and geo-02 **offline** | **runs on the pool** ⚠️ (data leaks) | **fails immediately**; pool untouched ✅ |
| D | Bacia | cron with both offline | runs on the pool, silently | run **`failed`** + email to the owner (once per window) ✅ |
| E | Bacia | workspace admin tries terminal = pool | (n/a) | **403**: `no_pool` floor set by the platform admin ✅ |
| F | Licenciamento | lic-01 offline, lic-02 free | falls back to the pool ⚠️ | runs on **lic-02** (`fallback`) — "rodou no fallback" badge ✅ |
| G | Licenciamento | lic-01 and lic-02 offline, pool-a free | runs on the pool (invisible) | runs on **pool-a** (`pool`) — "rodou no pool" badge; it was the owner's choice ✅ |
| H | Licenciamento | everything offline (dedicated and pool) | 503 | 503 / `failed` with `no_executor_chain` ✅ |
| I | Cadastro | cron with pool-a and pool-b offline | occurrence **silently lost** | run **`failed`** + email to the owner ✅ |
| J | any | external webhook with exhausted chain | pool response or raw 503 | **generic 503 + `Retry-After`**; a resend with the same `idempotency_key` is served when it comes back ✅ |
| K | Bacia | admin tries to revoke geo-02 with geo-01 already deleted | dangling pointer | **blocked**: "esvaziaria o nível principal" (would empty the primary tier) (or `force` + warning) ✅ |

The contrast that matters is still **C**: the case that motivated the spec. And **G** is the
novelty of the 4th round: the same overflow as today, now **chosen** by the owner and
**visible** on the run.

## 11. Suggestions for a safe and modern spec

My own recommendations, beyond what the decisions require. **[v1]** = take it now;
**[later]** = can wait. **Post-implementation:** the **[v1]** items were
delivered — per-policy contract test, `isolation_violation` signal in the log,
audit trail, warning when crossing policies, stateless 503 on the webhook,
per-transition notification in the scheduler, structured dispatch event, per-run
badge, per-tier health + pre-flight, and the routing flag. The **[later]** items remain
in the backlog.

A real boundary
- **[v1] Per-policy contract test**: (a) Isolated + everything offline ⇒ 503, **zero**
  `send_job` to the pool, zero envelopes encrypted outside the allowed set; (b) fallback:
  pool ⇒ pool only **after** the tiers are exhausted; (c) `no_pool` floor ⇒ terminal `pool`
  in the database is ignored at dispatch. The assertion in §5.3 is the runtime version.
- **[v1] `isolation_violation_total` metric with an alert on `>0`.** Delivered as the
  `dispatch_event` with `outcome=isolation_violation` (§5.3): with no metrics exporter
  on the server, the alert comes from the log.
- **[v1] Audit trail** for tiers, terminal, floor and `force` (§4.3–4.5).
- **[v1] Warning when crossing policies** in the move-workflow dialog (§5.3).
- **[later] Attestation on the executor.** The envelope carries `workspace_id`; a dedicated
  executor could refuse jobs from workspaces that do not list it in any tier (list in the
  handshake, `executor_ws_router.py`). Protects against a compromised or buggy server.

Fail safe
- **[v1] Stateless, generic 503 on the webhook** (§6, §7.3).
- **[v1] Idempotency test after a 503** (`workflow_service.py:586-591` already guarantees it;
  lock it in).
- **[v1] Block on emptying the primary tier** (§4.4).
- **[v1] Per-transition notification** in the scheduler (§7.4), for all policies.
- **[v1] Explicit confirmation** when switching the terminal to `pool` (§9).
- **[later] Dynamic `Retry-After`**, derived from the next presence renewal.

Modern operations
- **[v1] Structured event per dispatch decision**: `{run_id, workspace_id,
  policy: pool|isolated|dedicated_pool, tiers_available: {primary, fallback},
  chosen_executor, dispatch_tier, decision_ms, outcome}` as JSON log, replacing the
  `_logger.info` at `:500-503`; metrics `dispatch_total{policy,tier,outcome}` and
  `fallback_used_total{workspace,tier}`.
- **[v1] "rodou no fallback/pool" (ran on the fallback/pool) badge** per run (`dispatch_tier`), in the history and
  in the panel. The owner chose the fallback; they have to see when it was used.
- **[v1] Per-tier health and pre-flight** (§9).
- **[v1] Routing flag** (`off|on`) and rollback = turn it off.
- **[later] Per-transition email when a workspace starts running on the fallback/pool**
  ("since HH:MM the runs of X are on the pool"). The mechanism is the same as the cron one (§7.4).
- **[later] Policy simulator**: "if I switch to *fail*, how many runs in the
  last 30 days would have failed?" — computable from `dispatch_tier`. It is what the shadow
  mode would have done, now as a tool for the owner, not as a rollout prerequisite.
- **[later] Unify notification channels** (email and per-workspace webhook in a
  single notifier, also called by the closings that happen outside the queue).
- **[later] Readiness in `/health`** (`health_router.py`): "isolated workspaces with 0
  members online in the primary" and "pool with 0 online".

## 12. Open questions

None. The 16 decisions (§2.1–2.4) closed the model; the wave-by-wave implementation
(§8) has been delivered.

## 13. Where this lives in the code (implemented)

> The `arquivo:linha` (file:line) references below are **pre-refactor and indicative** (see the Maintenance
> note at the top). The list maps each decision to its point in the code.

- `app/services/workflow_execution_service.py:258-314` — `_resolve_candidates`: the
  per-policy chain (§5).
- `app/services/workflow_execution_service.py:288-307` — where the pool is appended today;
  becomes conditional on the effective terminal.
- `app/services/workflow_execution_service.py:363-372, 442-444` — writing `host`:
  write `dispatch_tier` along with it (§5).
- `app/services/workflow_execution_service.py:410-431` — candidate loop: assertion
  of the allowed set (§5.3) before `build_job_message`.
- `app/core/executor_connections.py:1328-1352` — relay `send_job`: `is_full` fix
  (§5.2).
- `app/core/executor_connections.py:1116-1135` / `:541-547` — `is_online`/presence:
  signal hardening (§5.1).
- `app/models/workspace.py` — `fallback_terminal`, `isolation_floor`; `app/models/`
  new `workspace_executors` (with `tier`); `app/models/workflow_run.py` —
  `dispatch_tier`; Alembic migration (§4, §8).
- `app/services/user_executor_service.py:108-137` (`set_default_agent`) and the
  delete/revoke path in `executores_router.py` — tier consistency (§4.4).
- `app/api/routers/workspace_router.py:558-626` — tier and terminal endpoints (§9);
  floor endpoint, platform admin only (§4.5).
- `app/api/routers/webhook_router.py:184-229` — generic 503 + `Retry-After` (§7.3).
- `app/core/async_scheduler.py:155-167` — record `failed` + per-transition
  notification (§7.4); `app/services/email_service.py:52` — sending.
- `app/services/observability_service.py:198-206` — surfacing `agent_host` and
  `dispatch_tier` (§8, wave 1).
- `web/app/components/workspace/settings-sheet/executor-section.tsx` — policy
  editor, per-tier health and pre-flight (§9); `web/app/components/workspace/workspace-hero.tsx`
  — status.
- `web/context/WorkspaceContext.tsx:44` (`moveTargets`) and the move dialog — policy
  warning (§5.3).
