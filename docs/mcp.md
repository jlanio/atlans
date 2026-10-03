# Atlans MCP server

Atlans exposes an **MCP** (Model Context Protocol) server at the `/mcp` path
of the site itself: on an installation at `atlans.example.org`,
**`https://atlans.example.org/mcp`**. The examples below use that domain; the
tokens screen shows the commands already filled in with your installation's address. Any
client that speaks MCP over HTTP
(*streamable HTTP*) connects with a URL and a personal access token, and from then on sees
the workspaces, workflows, node catalog, credentials and Drive of the account
that owns the token — **nothing beyond what that account could already reach through the UI**.

This document is the single source for anyone connecting a client: URL, token,
tools, limits, errors and what to do when it does not work.

## Contents

- [What it is and what you can do with it](#what-it-is-and-what-you-can-do-with-it)
- [Connecting](#connecting)
- [Authentication](#authentication)
- [Snippets per client](#snippets-per-client)
- [Scopes and tools](#scopes-and-tools)
- [Running a workflow](#running-a-workflow)
- [Resources](#resources)
- [Prompts](#prompts)
- [Limits](#limits)
- [Errors](#errors)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Changelog and versioning](#changelog-and-versioning)

---

## What it is and what you can do with it

MCP is an open protocol for giving a client program access to *tools*
(function calls), *resources* (documents addressable by URI) and *prompts*
(ready-made scripts) of an external system. The Atlans server publishes all three.

With a read token, the connected client can:

- list the workspaces and workflows the account can reach, with triggers,
  schedule, portal status and date of last change;
- open a workflow — summary of its nodes and edges, `params_schema`, pins,
  number of versions — and, on request, the whole **redacted** definition;
- read a workflow's input and output contract (`inputs`/`outputs`);
- search the 63 built-in nodes and read each one's properties schema;
- list credentials (metadata only — never the secret) and Drive files,
  and generate a temporary download URL;
- read the authoring guide, topic by topic.

With `workflows:write`, in addition:

- validate a definition without saving anything and get the report per node and per
  edge (errors, warnings, output schema, suggested `params_schema`);
- create and update workflows — always validating first, by default;
- activate and deactivate a workflow, and publish it to (or unpublish it from) the portal.

With `runs:execute`, trigger a run and, if you want, **wait for the outcome**
in the same call, with node-by-node progress (see
[Running a workflow](#running-a-workflow)).

Reading runs — history, the detail of one of them and the artifacts it produced —
requires only `workflows:read`, as in the UI.

What is **not** included, by decision: deleting a workflow, credential CRUD (nor
reading the secret), managing members, executors and workspace
policy, moving a workflow between workspaces and any `/admin` route.

---

## Connecting

| Item | Value |
|---|---|
| Canonical URL | `https://<site>/mcp` (e.g. `https://atlans.example.org/mcp`) |
| Transport | streamable HTTP (`POST` with an SSE response) |
| Authentication | `Authorization: Bearer atl_pat_…` |
| Session | *stateless* — there is no back-channel from the server to the client |

`https://atlans.example.org/mcp/`, with a trailing slash, works the same: both spellings are
exact routes to the same server and **neither of them redirects**. This is
deliberate — a `307` would make the client repeat the request, and with it the
`Authorization` header, to the `Location` address. Prefer the form without the slash, which is
the one clients ship with.

The server rejects any request that carries the `Origin` header, with `403`:
in this phase only clients that are not browsers connect (see
[403 mentioning `Origin`](#403-mentioning-origin)).

In development, with the local API, the URL is `http://localhost:8000/mcp`.

---

## Authentication

Access is through a **personal access token** (PAT): each account creates, lists and revokes only its
own tokens, at **`/settings/tokens`** (through the Ctrl+K palette, "Tokens de
acesso" (Access tokens), or through the URL), and the token acts on behalf of whoever created it — never use
someone else's, because everything it does is recorded in their name. For
now only the system administrator can reach pages outside the Home (the
`web/proxy.ts` sends everyone else back to `/`, and the item was removed from the account menu), so
today only administrators can create tokens; the MCP rejection messages
say so. When creating one you choose:

- **name** — to recognize the token in the list and revoke it later;
- **scopes** — `workflows:read`, `workflows:write`, `runs:execute`,
  `triggers:manage`, `drive:read`, `drive:write`. Grant only what you will use;
- **workspaces** — the explicit list of current ones, or "todos, inclusive os que
  eu entrar depois" (all, including the ones I join later);
- **expiration** — 30, 90, 180 or 365 days.

The secret (`atl_pat_` + 43 characters) appears **only once**, at the moment of
creation. Keep it in a secrets manager or in an environment variable.

Rules for sending it:

- the token **always** goes in the `Authorization: Bearer atl_pat_…` header;
- **never** in a query string (`?token=`/`?access_token=`) — the request is
  rejected with 401 on purpose: query strings leak into proxy logs and browser
  history;
- the server does **not** accept the UI's session JWT;
- every authentication failure responds `401` with the header
  `WWW-Authenticate: Bearer realm="atlans-mcp"` (and `error="invalid_token"`
  when the secret's format is right but the token does not resolve — revoked,
  expired, or belonging to a suspended user).

The token is revoked automatically when the owner's password changes, when the account
is suspended and when the account is deleted. Revoking it in the token list cuts off
access immediately.

---

## Snippets per client

All the examples read the secret from `ATLANS_TOKEN`, never from the command line:
a command with the literal secret stays in `~/.bash_history` and shows up in `ps`.

```bash
export ATLANS_TOKEN='atl_pat_…'   # do gerenciador de segredos, não do histórico
```

### Claude Code

```bash
claude mcp add --transport http atlans https://atlans.example.org/mcp --header "Authorization: Bearer ${ATLANS_TOKEN}"
```

### Cursor, VS Code and Windsurf

In the client's `mcp.json`:

```json
{
  "mcpServers": {
    "atlans": {
      "url": "https://atlans.example.org/mcp",
      "headers": {
        "Authorization": "Bearer ${ATLANS_TOKEN}"
      }
    }
  }
}
```

Some clients do not interpolate environment variables inside `mcp.json`;
in those, replace `${ATLANS_TOKEN}` with the secret and treat the file as a
secret (out of version control, permission `600`).

### mcp-remote

For clients that only speak MCP over stdio:

```bash
npx mcp-remote https://atlans.example.org/mcp --header "Authorization:${AUTH_HEADER}"
```

Set `AUTH_HEADER="Bearer atl_pat_…"` in the environment. The split into two variables
comes from `mcp-remote` itself: it cuts the argument at the first space.

### Anthropic API MCP connector

The `mcp_servers` block does not work on its own — you also have to declare the
corresponding `mcp_toolset`, with the same `name`:

```python
import os
from anthropic import Anthropic

client = Anthropic()
resposta = client.beta.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[
        {
            "type": "url",
            "url": "https://atlans.example.org/mcp",
            "name": "atlans",
            "authorization_token": os.environ["ATLANS_TOKEN"],
        }
    ],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "atlans"}],
    messages=[{"role": "user", "content": "Liste meus fluxos ativos."}],
)
```

### OpenAI Agents SDK

```python
import os
from agents import Agent
from agents.mcp import MCPServerStreamableHttp

servidor = MCPServerStreamableHttp(
    params={
        "url": "https://atlans.example.org/mcp",
        "headers": {"Authorization": f"Bearer {os.environ['ATLANS_TOKEN']}"},
    }
)
agente = Agent(name="Atlans", mcp_servers=[servidor])
```

---

## Scopes and tools

Authorization has two layers, and both have to pass:

1. **token scope** — what the token requests at creation;
2. **workspace role** — what the account has inside it
   (`viewer` < `editor` < `operator` < `admin` < `owner`).

A tool outside the token's scope does not even show up in `tools/list`, and when called
directly it responds `forbidden_scope`, naming the missing scope. An insufficient role
responds `forbidden`. There is no administrator scope: a PAT
never goes beyond member scope, even if the account is a platform admin.

| Tool | Scope | Minimum role | What it does |
|---|---|---|---|
| `list_workspaces` | `workflows:read` | member | Workspaces reached by the token, with the role in each one |
| `list_workflows` | `workflows:read` | member | Workflows of the workspace (or of all of them), as lightweight items |
| `get_workflow` | `workflows:read` | member | Workflow summary; `include_definition=true` brings the redacted definition |
| `get_workflow_contract` | `workflows:read` | member | The workflow's declared `inputs`/`outputs` |
| `search_nodes` | `workflows:read` | — | Compact index of the node catalog |
| `describe_node` | `workflows:read` | — | Properties, inputs and outputs of a node |
| `list_credentials` | `workflows:read` | member | Credential metadata — never the secret |
| `list_drive_files` | `drive:read` | member | Files in the workspace's Drive |
| `get_drive_download_url` | `drive:read` | member | Presigned download URL (5 min) |
| `get_portal_info` | `workflows:read` | member | The workflow's portal status and the sharing URL |
| `get_authoring_guide` | `workflows:read` | — | One topic of the authoring guide |
| `validate_workflow` | `workflows:write` | editor | Validates a definition without saving anything: report per node and per edge, disabled nodes, sub-workflows and suggested `params_schema`. Rejects up front a definition with a plaintext secret |
| `create_workflow` | `workflows:write` | editor | Creates a workflow in the workspace; validates first by default and stamps authorship with the token's owner |
| `update_workflow` | `workflows:write` | editor | Updates definition, name, description or `params_schema` — only the fields sent change |
| `set_workflow_active` | `workflows:write` | editor | Activates or deactivates the workflow, syncing its schedules. The only path to `is_active` |
| `set_portal_access` | `workflows:write` | editor | Publishes or unpublishes on the portal (`disabled`/`public`/`private`) and returns the absolute URL |
| `run_workflow` | `runs:execute` | operator | Triggers a run and, by default, waits for the outcome while reporting progress |
| `get_run` | `workflows:read` | member | Detail of a run: status, time, error and the snapshot of each node |
| `list_runs` | `workflows:read` | member | Run history, with filters for workflow, workspace, status, origin, date and text |
| `get_run_artifacts` | `workflows:read` | member | Artifacts of a run, with a temporary download URL (5 min) |
| `get_run_events` | `workflows:read` | member | Raw log of a run — **lasts 1 hour**; `availability` says why it came back empty |
| `cancel_run` | `runs:execute` | operator | Stops a run in progress; `outcome` distinguishes request sent, closed and already finished |
| `retry_run` | `runs:execute` | operator | Triggers a NEW run of the same workflow — **it does not repeat the previous one**: current definition and `params_schema` defaults, never the original inputs |
| `list_workflow_versions` | `workflows:read` | viewer | Snapshots of a workflow: number, note and date — without each one's definition |
| `get_workflow_version` | `workflows:read` | viewer | One version from the history, with the **redacted** definition |
| `restore_workflow_version` | `workflows:write` | editor | Rolls the workflow back to an earlier version. **Reversible**: the current state becomes a snapshot before the switch |
| `duplicate_workflow` | `workflows:write` | editor | Copy in the same workspace. Pins, portal and history do not come along; the schedule comes along switched off |
| `list_artifacts` | `workflows:read` | viewer | The files that runs produced, in the given workspace (or in all of the token's), with filters and pagination |
| `list_pins` | `workflows:read` | viewer | Which node outputs are frozen. `cached` says whether the cache already exists; `expired` is a report, not an action |
| `pin_node_output` | `workflows:write` | editor | Freezes a node's output starting with the next run. `ttl_hours` from 1 to 8760. A node that writes a file is rejected |
| `unpin_node_output` | `workflows:write` | editor | Unfreezes and deletes the cache. `outcome=not_pinned`, without an error, when there was no pin |
| `list_schedules` | `workflows:read` | viewer | When the workflow triggers on its own. Includes `workflow_active`, because the scheduler ignores schedules of an inactive workflow |
| `create_schedule` | `triggers:manage` | **operator** | Cron (5 fields), interval or RRULE. Scheduling is executing — hence the role |
| `update_schedule` | `triggers:manage` | **operator** | Only the fields sent. `active=false` pauses without losing the configuration |
| `delete_schedule` | `triggers:manage` | **operator** | Requires `confirm=true`; without it, describes what would be deleted and does not delete it |
| `create_drive_upload_url` | `drive:write` | editor | Step 1 of 3: returns a URL that accepts PUT. **It does not send the file** — whoever has the bytes does the PUT |
| `confirm_drive_upload` | `drive:write` | editor | Step 3: measures the actual object and publishes it to the Drive. Above the ceiling, rejects it and deletes the bytes |
| `delete_drive_file` | `drive:write` | editor | Requires `confirm=true`. No trash bin. It is also how you replace a file |
| `search_sources` | `workflows:read` | viewer | Searches the catalog of pre-mapped sources (known WFS layers) by theme, WITHOUT network. Call it before filling in `url`/`typeName` |
| `describe_source` | `workflows:read` | viewer | A source's record: ready-to-paste `node_snippet`, schema (CRS, extent, columns) and status of the last check |
| `probe_source` | `workflows:write` | editor | Probes a WFS outside the catalog: layers (GetCapabilities) and, with `type_name`, the schema. Metadata only; it does not create a source, but it updates the status of an already cataloged one and talks to the internet (`probe` bucket, `openWorldHint`) |
| `register_source` | `workflows:write` | editor | Probes and stores a layer in the workspace's catalog, with title, themes and hints. Idempotent: the same URL+layer updates the row |

The four source tools revolve around the **internal catalog** of pre-mapped WFS
layers (`docs/sources.md`): the guide's rule is to consult `search_sources`
before filling in any `url`/`typeName`, and to probe (`probe_source`) and
register (`register_source`) only what the catalog does not have. Those two are the only
tools annotated with `openWorldHint: true` — they make the server talk to a
public URL (private IPs, loopback and link-local are still blocked) — and they spend
the `probe` bucket.

Reading runs requires `workflows:read`, not `runs:execute`: it is the same requirement
as in the UI, where following the history only depends on being a member of the run's
workspace. A read token follows what others triggered; it is triggering that
requires the execution scope and the `operator` role.

Two things about runs that the tool says, and that are worth stating here too because
whoever reads the doc is usually whoever writes the agent:

**The log lasts one hour.** `get_run_events` reads the history from Redis, with a TTL of
3600 s. After that the events do not exist anywhere — what remains of the
run is the `node_stats` of `get_run`, which is in the database and does not expire. When the
list comes back empty, `availability` gives the reason (`em_andamento`, `expirada`,
`sem_eventos`, `indeterminada`) instead of letting the agent conclude on its own that
"there was no output".

**`retry_run` does not repeat the run.** Atlans does not store a run's `inputs`,
so re-running exactly that one is not possible: the tool triggers the workflow with
the **current definition** and with the defaults that the `params_schema` declares — never the
original inputs. The response includes `reused_inputs: false` and
`inputs_sent` with what was actually sent, so that this does not go
unnoticed. A workflow with a required parameter without a default is rejected with
`validation`, instead of spending an executor on a doomed run. Whoever needs
a true repeat uses `run_workflow(workflow_id, inputs=…)`. The new run is
marked with origin `mcp`, not `retry`: it is indistinguishable from an ordinary
trigger, and labeling it otherwise would record in the "Histórico" (History) a re-run that did not
happen.

**`cancel_run` responds `already_finished` in two different cases**, because the
core uses a single label: the run had already finished, or there is no executor
associated with it — and in the second case it may stay in `running`. That is why the
response includes `status_before`, the state at the instant before the request, and a
`hint` warning when the two disagree. And calling it twice is safe, but it does not
necessarily return the same thing: what closes a run that was already delivered is the
executor, on its way back, so both calls usually respond `requested`.

Three things about the collection, for the same reason:

**`restore_workflow_version` is reversible, and the response says how.** Before
switching the definition, the current state becomes a new snapshot in the history — its
number comes back in `snapshot_version`, and restoring that number
undoes the operation. What is **not** guaranteed is the resynchronization of the
schedule: it is best-effort in the core, and if it fails the restore still
holds, with no warning in the response. For a workflow that depends on a schedule, confirm with
`get_workflow`.

**A version's definition always comes out redacted.** The history stores the
connection string encrypted; `get_workflow_version` decrypts it to check that the
token is not corrupted and then **erases the value** before returning it. There is no
parameter to ask for the secret — restoring does not need it, because the restore
copies the encrypted blob without opening it.

**`list_artifacts` distinguishes the two dates that its sibling tool conflates.** An item
includes `content_expires_at` (when the FILE leaves retention — days) and
`url_expires_at` (when the signed LINK expires — 5 minutes). In
`get_run_artifacts`, `expires_at` means the second one; reusing the name here
for the first would make the reader conclude that the download is valid for a week.

**`duplicate_workflow` leaves things behind, on purpose.** Pins (they point
to artifacts of runs the copy never had), portal status (a copy
is not born published because the original was) and version history (it describes
edits that did not happen there). The schedule comes along, but **switched off**:
duplicating usually precedes an edit, and being born triggering on its own would double the
load silently.

Input conventions, applying to all of them:

- `workflow_id` and `workspace_id` accept **id or name**; a name that matches more
  than one resource returns `ambiguous` with the list of candidates;
- `workspace_id` is **optional** when the token reaches exactly one workspace;
- text written by people (name, description, alias, error message, file
  name) always comes out inside `untrusted_data`; ids, enums, numbers and dates
  stay at the top of the response;
- a definition sent to `validate_workflow`, `create_workflow` or
  `update_workflow` **cannot carry a secret in plaintext**: the call is
  rejected with `secret_in_definition`, which lists the field paths (never
  the values). This also applies to the one that only validates — rejecting up front is what
  keeps the password from reaching the validation path. A credential is referenced
  by `credential_id` (`list_credentials`);
- `validate_first=true` is the default for `create_workflow` and `update_workflow`:
  with errors in the report, nothing is saved. `force=true` saves despite ordinary
  errors, but **never** despite fatal ones (nonexistent node, duplicate id, cycle,
  `credential_id` that is not a UUID) — those are always rejected, because they produce a workflow
  that the executor cannot even assemble.

---

## Running a workflow

```text
run_workflow(workflow_id, inputs?, debug_mode=false, wait=true,
             timeout_seconds=120, idempotency_key?)
```

### `inputs` checked before dispatch

`inputs` is checked against the workflow's `params_schema` **before** the run
is dispatched — a swapped parameter discovered in the middle of the run has already cost an
executor, a database write and a wrong artifact. The rules:

- **coercion only from text.** `"5"` becomes `5` (integer if it is pure digits,
  otherwise decimal), `"true"`/`"1"`/`"sim"` become `true`, `"false"`/`"0"`/`"não"`
  become `false`, and an `object` accepts an object, a list or the corresponding JSON as a
  string. Whoever sends `1` where `boolean` was declared gets an error: in JSON,
  a number is a number;
- **an empty string never becomes a value.** `""` in a `number` field is an error, not zero;
- **required with no value and no `default` is an error**; with a `default`, the default is
  filled in (and coerced by the same rules);
- **an undeclared key passes through untouched** and is listed in `hints` — the webhook
  trigger has its own `payload_schema`, validated at dispatch;
- **a missing or malformed `params_schema` is not an error**: the `inputs` go through without
  checking and a warning in `hints` says nobody checked them.

The problems come back aggregated in a single `validation` error, with
`errors: [{path, message}]` — fix everything at once. The message names the
field and the expected type and **never echoes the value received**.

### `wait`, timeouts and status

With `wait=true` (the default) the call holds the response until the run finishes,
reporting node-by-node progress, and returns the complete outcome: status,
duration, the snapshot of each node, the error and the list of artifacts (without links — to
download, call `get_run_artifacts`). The timeout is `timeout_seconds`, between **5 and
300 seconds**, with **120 s** by default; a value outside the range is clamped to the
nearest limit.

The possible statuses — and the difference between the last two matters:

| `status` | Meaning | What to do |
|---|---|---|
| `success` / `failed` / `cancelled` | Outcome recorded | Read the result |
| `running` | Still executing, or the timeout ran out before the end | Query `get_run(run_id)`; the run **continues** on the server |
| `unknown` | The workflow **finished**, but the outcome has not been recorded yet | Query `get_run(run_id)` again shortly — **do not run it again** |

`unknown` is the case where the completion event arrived before the history
row was written. Calling it `running` would make the client wait for an end
that has already happened, and could convince it to trigger the same run again.

With `wait=false` the response comes back immediately, with the `run_id` and `status: "running"`.

In a response with an outcome, `events_dropped` says how many events the buffer
discarded during the wait: the progress may have skipped nodes. The outcome itself
comes from the database and is complete.

### Idempotency and rejections

`idempotency_key` protects against repeated triggering of the same workflow by the same
user for 24 hours: the second call with the same key returns the
original run, **even if it failed**. The key is per user — two
people with the same key make two runs.

Rejections that happen before any cost: a deactivated workflow responds
`workflow_inactive` (activate it with `set_workflow_active`), invalid `inputs`
respond `validation`, and the ceiling of concurrent waits responds `wait_limit`
without dispatching anything. If there is no executor online, the response is `no_executor`.

---

## Resources

Resources are reads addressable by URI — useful when the client prefers
attaching a document to making a tool call. All of them require
`workflows:read` and respect the same workspace scope.

| URI | Type | Content |
|---|---|---|
| `atlans://guide/authoring/{topic}` | `text/markdown` | One topic of the guide: `overview`, `edges`, `credentials`, `expressions`, `inputs`, `sources`, `sql`, `pitfalls`, `recipes` |
| `atlans://catalog/nodes{?type}` | `application/json` | Catalog index; without `type`, the list of types with the count of each |
| `atlans://catalog/nodes/{name}` | `application/json` | Complete definition of a node |
| `atlans://workspaces/{id}/workflows` | `application/json` | The workflows of a workspace |
| `atlans://workflows/{id}` | `application/json` | Workflow summary, with the redacted definition |
| `atlans://workflows/{id}/contract` | `application/json` | The workflow's input and output contract |
| `atlans://runs/{id}` | `application/json` | A run with the **complete** snapshot of each node — the same as `get_run(node_stats="full")` |

The catalog never comes out as a single blob: `atlans://catalog/nodes` without `type`
returns the index of types and the hint to filter, because the complete JSON of the 63
nodes exceeds 78 KB.

`atlans://runs/{id}` includes the complete `node_stats` (with `output_keys` and
`output_columns`) because whoever attaches a run to the context is investigating
a failure; the `get_run` tool still offers the summary to those who only want the
status. The run's error message and each node's come out sanitized, inside
`untrusted_data`.

Every resource respects the same guard as the tool it is an alias of: reading
workspace data checks the scope, requires the role and leaves an audit row.
`resources/read` does not consume the tool-call quota (see
[Limits](#limits)).

---

## Prompts

Prompts are ready-made scripts: the client requests one by name (`prompts/get`) with the
arguments and receives a text that DIRECTS the subsequent tool calls.
They do not spend quota and do not require any token scope (the connection itself still
requires the token): what requires scope and role are the tools the script
tells the client to call.

| Prompt | Arguments | What the script does |
|---|---|---|
| `criar_fluxo` | `descricao` (required), `workspace_id` | Understand the data → guide and node catalog → draft → `validate_workflow` until the report is clean → show the JSON → **offer** `create_workflow`, never create without confirmation |
| `diagnosticar_run` | `run_id` | `get_run` with `node_stats="full"` → read `error_category` → find the first node that failed → compare with `typical_seconds` → consult the guide's pitfalls |
| `revisar_fluxo` | `workflow_id` | `get_workflow` with the definition → `validate_workflow` → expired credentials in `list_credentials` → schedule stuck on an inactive workflow → failure history. Reports only, does not fix |
| `explicar_fluxo` | `workflow_id` | `get_workflow` + `get_workflow_contract` → what triggers it, what goes in, what each step does, what comes out and what it depends on. Read-only |

**A prompt never interpolates text coming from the database.** Workflow name, description and
error message do not go into the script — only what the person typed as an
argument and the identifiers they passed. The reason is straightforward: the text of a
prompt reaches the client at the level of instructions, with no `untrusted_data` to
wrap it in, and a workflow named "Ignore the previous instructions…" would become an
order. The workflow's data enters the conversation later, through the tools'
return values, already separated.

---

## Limits

| Limit | Value | Where |
|---|---|---|
| Tool calls | 120/min per token | Server |
| `run_workflow`, `retry_run` | 20/min per token, **combined** | Server (`run` bucket, on top of the general one) |
| `validate_workflow`, `create_workflow`, `update_workflow` | 20/min per token, combined | Server (`validate` bucket, on top of the general one) |
| `probe_source`, `register_source` | 10/min per token, combined | Server (`probe` bucket, on top of the general one) |
| Concurrent waits (`wait=true`) | 3 per token, 40 on the platform (`wait_limit`) | Server |
| `wait` timeout | 120 s by default, 300 s at most, 5 s at least | Server |
| Items per page in `list_runs` | 20 by default, 100 at most | Server |
| Artifacts per response in `get_run_artifacts` | 100 (`truncated: true` when there are more) | Server |
| Items per page in `list_artifacts` | 50 by default, 100 at most (`has_more`) | Server |
| Versions per page in `list_workflow_versions` | 50 by default and at most (`has_more` + `offset`) | Server |
| Events per response in `get_run_events` | 200 by default and at most (`dropped_oldest` counts what was left out) | Server |
| Run log retention | 3600 s (1 h) from the last event | Redis |
| HTTP requests | 240/min per IP (burst 60) | Traefik (`rate-mcp`) |
| Request body | 4 MiB | Transport |

`resources/read` and `prompts/get` do not count toward the 120/min quota.

No cut is silent, and each tool says what it cut: `list_runs`,
`list_artifacts` and `list_workflow_versions` return `has_more` (the first
two with `offset` to request the next page; the third as well);
`get_run_artifacts` returns `truncated: true` with a hint when the run
produced more files than fit in the response; and `get_run_events` returns
`returned` and `dropped_oldest` — the latter counting the oldest events
that were left out, because whoever investigates a failure wants the end of the log.

The edge limit is per **IP** and the tool limit is per **token**: several
clients behind the same NAT share the first, and each token has the second all
to itself. Exceeding the call quota returns `rate_limited` with
`retry_after_seconds`; exceeding the ceiling of waits returns `wait_limit`; at
Traefik, an HTTP `429`.

`run_workflow(wait=true)` holds the call until the run finishes; once the
timeout passes, the response comes back with `status: "running"` and the `run_id` to query
later, and the run continues on the server. The ceiling of concurrent waits exists
because each wait holds an event subscription and an open response: at the
ceiling, run with `wait=false` and follow it through `get_run(run_id)`. Artifacts
never travel through MCP — what comes back is a presigned URL.

With Redis down, the quotas **fail open** (with a warning in the server log) and
the ceiling of waits falls back to a per-process counter: a transient infrastructure
incident does not turn into a rejection of every call.

---

## Errors

Every tool failure comes back as an MCP tool error, with the message in JSON:

```json
{
  "code": "forbidden_scope",
  "message": "Este token não tem o escopo necessário: workflows:write.",
  "hint": "crie um token com esse escopo em /settings/tokens (hoje, página só de administradores do sistema)",
  "missing_scope": "workflows:write"
}
```

`code` and `message` are always present; `hint` appears when there is an
obvious action; the other fields depend on the code.

| `code` | When | Extra fields |
|---|---|---|
| `unauthorized` | Token missing, invalid, expired or revoked (arrives as HTTP 401, before any tool) | — |
| `forbidden` | Insufficient role in the workspace, or resource outside the token's scope | — |
| `forbidden_scope` | The token does not request the scope the tool requires | `missing_scope` |
| `not_found` | Workflow, file, node or run that does not exist — or that the account cannot reach | — |
| `ambiguous` | The name given matches more than one resource | `candidates[]` |
| `validation` | Invalid input | `report` when the rejection comes from the lint of a definition; `errors[{path, message}]` when it comes from the `inputs` or the shape of the body |
| `conflict` | Workflow name already used in the workspace | `suggestion`, an alternative name derived from the one sent (absent when it cannot be derived) |
| `workflow_inactive` | The workflow is deactivated and cannot be run | — |
| `no_executor` | No executor online to handle the run | — |
| `unavailable_local` | The content only exists on the executor; there is no remote download | — |
| `secret_in_definition` | The definition sent carries a plaintext secret | `paths[]` — the path of each field, never the value |
| `rate_limited` | The token's call quota was exceeded | `retry_after_seconds` |
| `wait_limit` | Concurrent waits (`wait=true`) at the token's or the platform's ceiling | — |
| `unavailable` | Dependency down (503) | — |
| `internal_error` | Unforeseen failure; the message is generic on purpose | — |

Treat the list of extra fields as a floor, not as a closed contract: a
new field may appear in a minor version, and the client should ignore what it does not
know. What does not change is the `code` + `message` pair.

`not_found` comes before `forbidden` on purpose, and it goes further than that: a workflow
that exists in another account's workspace responds exactly the same `not_found`
as an identifier that never existed — same sentence, same `hint`. The difference
would be a way to discover, one id at a time, what lies on the other side of the wall.
When the resource belongs to your own account and it is the *token* that cannot reach it (a token
issued for a single workspace), the response is `forbidden`: there is then no existence to
hide from someone who already sees it in the UI, but rather a reach to explain.

---

## Security

- **The token reaches no more than the account already reached.** Effective scope =
  token scopes ∩ token workspaces ∩ actual role in each workspace. There is no
  administrator path: a platform admin's PAT sees as a member.
- **Content in `untrusted_data` is data, not instructions.** Workflow name,
  description, alias, file name and error message are text written by
  people and may contain anything. The server separates them from the rest of the
  response precisely so that the client treats them as content.
- **Definitions come out redacted.** `connectionString`, `Authorization` and other
  sensitive keys become `<REDACTED>`, including when nested and inside lists,
  and every leaf string goes through the secret redactor. A credential is referenced
  by `credential_id` — never by pasting the secret into the definition: a definition
  with a plaintext secret is **rejected up front** with `secret_in_definition`,
  before any validation or saving, in the three tools that receive a
  definition (`validate_workflow` included). The rejection cites the field's path
  and never the value.
- **A run's error message is data.** `error_message` and each
  node's `error` come out redacted (a connection string becomes `<REDACTED>`) and always inside
  `untrusted_data` — it is the field most likely to carry a secret or a
  command phrase aimed at whoever reads the response. In the run listing it
  comes summarized; the full text is in `get_run`. The progress notifications
  of `run_workflow` carry the node name and the status, **never** the error.
- **A presigned URL lasts 5 minutes** and is a bearer capability: whoever has the
  link downloads the file, without a token. Do not log it or pass it on.
- **A secret is never echoed.** Not in an error message, not in the audit log — what
  is recorded about the call is the token prefix, the user, the tool, the
  duration and the result.

---

## Troubleshooting

### 401 with `WWW-Authenticate: Bearer`

The `Authorization` header did not arrive, is not `Bearer`, or the token does not resolve.
Check, in this order: the environment variable is exported in the session that runs
the client; the value starts with `atl_pat_`; the token is not revoked or
expired (the list at `/settings/tokens` shows both); the account has not been
suspended. An `error="invalid_token"` in the header means the format is
right and it is the token that is no longer valid — you have to create another one.

If the token is in the URL as `?token=`, move it to the header: a query string is
rejected even with the correct secret.

### 421 Misdirected Request

The request's `Host` is not on the list accepted by the transport. It happens when
pointing the client at a domain or port different from the configured ones. The default
list accepts the host of `FRONTEND_URL` and, locally, `localhost` or `127.0.0.1`.
For another domain, set `MCP_ALLOWED_HOSTS`.

### 403 mentioning `Origin`

The client sent an `Origin` header. The server rejects any `Origin` on
purpose: in this version only clients that are not browsers connect. If your
client sends `Origin`, it is running inside a browser — that path
depends on OAuth and does not exist yet.

### 429

Two possible sources. An **HTTP** `429` comes from Traefik: it is 240 requests
per minute per IP, and the relief is to wait or spread the calls out. A tool
error with `code: "rate_limited"` comes from the server: it is the token's quota, and
`retry_after_seconds` says how long until the window rolls over.

### The tool does not show up in the list

`tools/list` is filtered by the token's scope. If `create_workflow` does not show up,
the token does not request `workflows:write`. Scopes cannot be edited: create another token with the
right scopes and revoke the old one.

### The download URL does not open

In production, `MINIO_EXTERNAL_ENDPOINT` has to be the public address of the S3 (e.g.
`https://s3.atlans.example.org`) — the
signature pins the host, and with `localhost` the URL only resolves from inside
Docker. The API logs a warning at boot when the value points to a
local address. Remember also that the URL is valid for 5 minutes.

---

## Changelog and versioning

The server declares its own version in `initialize` (the `version` field), separate
from the MCP protocol version. It is how you check which contract is live
after a deploy — a new tool bumps the minor version.

### 1.5.0

- Drive write tools: `create_drive_upload_url`,
  `confirm_drive_upload` and `delete_drive_file`. With them **all six token
  scopes now unlock something** — `drive:write` was the last one the screen
  offered with an affirmative description and nothing behind it.
- The upload is **three calls**, and the middle step does not go through MCP: the tool
  returns a presigned URL and whoever has the bytes does the PUT directly to storage.
  Sending a file over JSON-RPC would mean base64 inside the message — a
  40 MB shapefile would become 54 MB of text in the caller's context. The
  consequence is stated in the description: **an agent without the file on disk cannot
  send it**, only pass the URL along.
- `confirm_drive_upload` measures the ACTUAL object, not the size declared in step 1.
  Above the workspace's ceiling, it rejects **and deletes the bytes**.
- `delete_drive_file` requires `confirm=true` and has no trash bin. It is also how you
  replace a file, because **overwriting is not a Drive operation**.
- Documented what the Drive does **not** have, so the agent does not find out by trying:
  it is flat — no renaming, no moving, no folders.

### 1.4.0

- Trigger tools: `list_schedules`, `create_schedule`, `update_schedule`
  and `delete_schedule`. This is the **`triggers:manage`** scope ceasing to be a chip
  on the token card with nothing behind it.
- The three write ones require **`operator`**, not `editor`: scheduling is executing —
  a one-minute schedule triggers the workflow with the owner's credentials,
  indefinitely. Same yardstick as `run_workflow` and the REST route.
- `delete_schedule` requires `confirm=true`. Without it, it describes what would be deleted
  and does not delete it: removal has no undo and fails silently — nothing breaks, the
  routine just stops happening.
- `list_schedules` returns **`workflow_active`** at the top. The scheduler ignores
  schedules of an inactive workflow, and nothing in the schedule itself gives this away: it was
  the most common cause of "the cron stopped" without any signal.
- **Unified default time zone.** There were three answers to "which time zone applies when the
  schedule does not state its own?": the node sent a fixed time zone, the schema used
  another and a null column fell back to **UTC** inside the scheduler —
  four hours of difference, silently, between the screen and the trigger. Now it is a
  single constant. No migration and no recreating schedules: the value is what the node already
  sent, so `_mesma_configuracao` keeps agreeing.

### 1.3.0

- Pin tools: `list_pins`, `pin_node_output` and `unpin_node_output`. The
  two write ones are **idempotent** — unique among the server's writes:
  pinning an already pinned node rewrites the same entry, and unpinning twice does not
  change anything.
- `pin_node_output` **rejects a node that writes a file** (output, map publishing,
  email, webhook response). Freezing their output made the executor skip the
  write: the workflow finished green without producing the file. The REST route
  started rejecting it in the same diff, so the phantom pin gets in through no
  path.
- Along with it came five fixes to the pins REST API, which had no tests at all: the
  `GET /pins` stopped blowing up with a 500 on a malformed date, `ttl_hours` got a
  range (`0` was accepted and became "no expiration"), the unpin started committing
  BEFORE deleting from storage, reading the cache artifact stopped raising
  on a duplicate row, and the body's `node_id` — required and ignored — became
  optional with `extra="forbid"`.

### 1.2.0

- Collection tools: `list_workflow_versions`, `get_workflow_version`
  (redacted definition), `restore_workflow_version` (with the number of the previous
  snapshot in the response), `duplicate_workflow` (which rejects a broken sub-workflow
  before copying and stamps the caller's authorship) and `list_artifacts`.

### 1.1.0

- Run tools: `get_run_events` (raw log, with `availability`
  explaining why the list came back empty), `cancel_run` (with `outcome` and
  `status_before` distinguishing request sent, closed here and already finished) and
  `retry_run` (triggers a new run of the same workflow, without reusing
  inputs).

### 1.0.0

- Server at `https://<site>/mcp`, stateless streamable HTTP transport.
- Authentication by personal access token in the `Authorization` header.
- Discovery and read tools: `list_workspaces`, `list_workflows`,
  `get_workflow`, `get_workflow_contract`, `search_nodes`, `describe_node`,
  `list_credentials`, `list_drive_files`, `get_drive_download_url`,
  `get_portal_info`, `get_authoring_guide`.
- Building tools: `validate_workflow`, `create_workflow`,
  `update_workflow`, `set_workflow_active`, `set_portal_access` — with rejection of
  plaintext secrets in the definition (`secret_in_definition`) and validation
  before saving by default.
- Run tools: `run_workflow` (with `wait`, node-by-node progress and
  checking of the `inputs` against the `params_schema`), `get_run`, `list_runs` and
  `get_run_artifacts`.
- Resources for the authoring guide, the node catalog, the workspaces, the workflows
  and the runs (`atlans://runs/{id}`).
- Prompts `criar_fluxo`, `diagnosticar_run`, `revisar_fluxo` and `explicar_fluxo`.
- Per-token quotas (general, `validate`, `run` and `probe`), ceiling of concurrent waits and
  per-IP rate limit at the edge.

### Versioning policy

The version follows *semver* over the **tool contract**:

- **major** — removal or incompatible change in the output format;
- **minor** — new tool, resource, prompt or field;
- **patch** — an adjustment that does not change the contract.

A tool that is going away stays marked as `deprecated` in its description for **at least one minor
version**, saying what to use instead, before it disappears. A new field
may appear at any time: treat the output as an open object and
ignore what you do not know.
