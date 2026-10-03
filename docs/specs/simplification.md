# Spec — Platform simplification (F0)

> Approved by the owner on 2026-09-24 ("approved as recommended"). Source
> report, with evidence and measurements: the "Simplificação do Atlans" (Atlans simplification) artifact.
> Given premise: **nothing is really in production** — there are no users and no
> legacy to preserve. Each phase is a PR with the complete gate; no phase
> starts before the previous one is green.

## The north star (the three decisions that hold everything up)

- **N1 — The Home is the product; `(dashboard)` is the admin console.** The middleware
  already sends anyone who is not an admin back to `/`. Taken as given: each feature has ONE home
  per audience; page × modal stops being an ambiguity.
- **N2 — One vocabulary: "assistente" (assistant).** `copiloto`/`agente`/`assistente` are the
  same concept. A single public name: **assistente**, routes included.
- **N3 — Zero base: the database is born ready.** The chain of 53 migrations collapses
  into a single initial revision; `init_schema.sql` (already tested by convergence)
  is its body.

## Frozen decisions (by the owner, 2026-09-24)

| Item | Decision |
|---|---|
| A2 | **Remove** the global signature mechanism (`verify_signature` + `ENABLE_SIGNATURE_VERIFICATION` + validation by `NODE_ENV`). The edge keeps JWT, PAT, mTLS and per-webhook HMAC. |
| A3 | The `/drive` page **stays as an admin console, with its own UploadZone**. The cut is declarative (N1), not in code. |
| A5 | The rename to **assistente** includes **the routes** (`/assistente/*` in the Home; `/assistente/editor/*` in the drawer). |
| A6 | The editor drawer **stays**; the dependency is inverted — the drawer imports from the Home, never the other way around. |
| A15 | Criterion for a helper in the front end: **only when there is behavior** (probing, webhook test, sub-workflow ports). Layout and simple validation become schema. |

## Orphan protocol

No endpoint, symbol or file is deleted without the search being recorded in the PR across
**six territories**: `web/` (service + components), `app/mcp/tools/`,
`executor/` + `flow/`, scheduled tasks/internal consumers (`run_result_consumer`,
workers), `tests/`, `docs/`. The search and its result go into the PR description.
A symbol with a consumer in ANY territory is not an orphan — only the
shell with no consumer is cut.

**Result already run for A1 (2026-09-24):** the user ROUTES
`POST /drive/upload-url` and `POST /drive/confirm-upload/{id}` have no
consumer at all (web: 0; MCP: 0; executor: uses its own `executor-*` routes). But
the METHODS `DriveService.create_upload_url` and `confirm_upload` have live
consumers — the MCP Drive write tools (`app/mcp/tools/drive_escrita.py`) and the
executor's confirm. **Cut: the two routes + `UploadUrlRequest` + the route
tests. Kept: the service methods.**

## Findings (what and where — evidence in the report)

**Group I — dead code and double paths**
- A1 Orphan user presign routes (see the protocol above). *(F1)*
- A2 Global signature that never turns on; `NODE_ENV` unused outside the config. *(F1)*
- A3 `/drive` = admin console with its own upload (declared; no code).
- A4 Do not touch: the `(auth)` pages are adapters (email/next-auth); `workflow-groups` has a consumer; `executor_ws` is WS.

**Group II — vocabulary and boundaries**
- A5 copiloto/agente → assistente, end to end. *(F4)*
- A6 The drawer imports from the Home. *(F5)*
- A7 Web types in a single home (`web/interface/` goes away). *(F2)*
- A8 A single `lib/formatos.ts` (today 3 copies; 37 files importing from observability). *(F2)*

**Group III — foundation**
- A9 Squash 53→1 migration; `ATLANS_DROP_*` out; CD = `upgrade head`. *(F3)*
- A10 Slice monoliths: `drive_router` (3 routers in one file), `executor_ws_router` (2,420 lines), `observability_service` (1,822 lines). *(F5)*

**Group IV — front end**
- A11 `admin/settings/page.tsx` (1,707 lines, 16 components) sliced within its folder. *(F2)*
- A12 `GisFlowService` by domain + pending lint. *(F1 lint, F5 slicing)*

**Group V — workflow engine (nodes and edges)**
- A13 Port declared 2× per node (`outputs` × `static_output`) → one form, with a type. *(F6)*
- A14 `'type'` with 3 roles and 19 values; the base class docstring lies; `register_node` starts validating the description at import time. *(F6)*
- A15 Poor schema → 14 helpers; enrich it (`required`/`placeholder`/`help`/`visible_when`) and apply the helper criterion. *(F6, last)*
- A16 `isValidConnection` at gesture time, derived from the `GET /nodes` catalog; validate remains the final judge. *(F6)*

**What is good and is not touched:** IResponse/dedup of GETs; documented stores;
the source catalog with a convergence test; specific security guards;
in the engine: single-source registry, `execute_sync` in a thread, pre-executor lint,
validate with a single body for the route and MCP.

## Plan

| Phase | Content | Gate |
|---|---|---|
| F0 | This spec | — |
| F1 | A1 (routes), A2, `NODE_ENV`, service lint | complete |
| F2 | A8, A7, A11 | complete |
| F3 | A9 | complete + clean stack from scratch |
| F4 | A5 | complete + adversarial review |
| F5 | A10, A12, A6 | complete + adversarial review |
| F6 | A13 → A14 → A16 → A15 | complete + adversarial review + manual canvas |
| F7 | `architecture.md`, follow-ups, before×after | final report |

**Complete gate** = full backend `pytest` · web `lint + typecheck +
testes + build` · `detect-secrets` with nothing new. Structural phases close with
their own adversarial review.

## Result (F7 — closing, 2026-09-24)

Measured between the commit before F0 and the end of F6. Outside docs:
**391 files, +8,665 −12,393 = −3,728 net lines** — with LARGER test suites
at the end (backend 4,516 tests, web 1,972) than at the start.

| Target | Before | After |
|---|---|---|
| `executor_ws_router.py` | 2,420 lines in one file | 452-line facade + `executor_ws/` package (4 modules, acyclic graph) |
| `observability_service.py` | 1,822 lines | 950-line facade + `observability/` package (5 modules, one owner per constant) |
| `GisFlowService.ts` | 1,076 lines of static class | 42-line facade + 11 domains in `service/dominios/` |
| `admin/settings/page.tsx` | 1,707 lines | 341 lines + 9 components in the folder |
| `drive_router.py` | 669 lines, 3 audiences in one file | 173 lines (user) + executor + admin, permission at the edge |
| Alembic migrations | 54 revisions | 1 (zero base with an anti-purge guard); CD = `upgrade head` |
| Vocabulary | 28 `copiloto`/`agente` files | 0 — one name (`assistente`), routes included |
| Web types | `interface/` (5 files) + `types.ts` | one home (`service/types.ts`) |
| Number/date formats | 3 copies | `lib/formatos.ts` |
| Node output | declared 2× ×64 nodes, untyped | a single `outputs`, typed, order preserved |
| `description()` | never validated; the base class docstring lied | 3 closed vocabularies, validated at import time |
| Canvas connection | any port to any port | refused at gesture time, derived from the catalog; validate remains the judge |
| Node forms | 14 helpers; layout in the front end | `required` (26) + `placeholder` in the schema; criterion written down; FileTriggerHelper (112 lines of layout) dead |
| `app/core/security.py` + user presign | 66 lines + routes | dead (upload only through the Drive filter) |

**Follow-ups swept**: `ExecuteParamsDialog` already lives in the execution domain
(`workflow/`) — closed with no action. Deploy actions for the owner, outside the repo:
`alembic stamp --purge 9ed006ca1660` on the existing database and, if they are set,
renaming the `COPILOTO_*` → `ASSISTENTE_*` envs on the server. Product backlog
(clip button, placeholder with a step, attachments as chips, `payment` event in the
provider panel) is not simplification and stays as backlog.

**F6 pending item**: interactive manual canvas in the first window with the authenticated
stack (script in the F6 closing); covered until then by 4,516+1,972 tests and by the
previewer.
