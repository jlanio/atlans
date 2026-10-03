# app/services/workflow_execution_service.py
# Orchestration and dispatch of workflow runs to executors.

import asyncio
import json
import random
import time
from app.core.utils.logger import get_logger
import uuid
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import func, select as sa_select, update as sa_update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core.authorization.workflow_access import (
    exigir_papel,
    role_in_run_workspace,
)
from app.core.config import policy_routing_enabled
from app.core.rbac import ROLE_OPERATOR
from app.core.executor_connections import _capacity_is_full, executor_registry
from app.core.exceptions import (
    NoExecutorAvailableError,
    WorkflowDecryptionError,
    WorkflowInactiveError,
    WorkflowNotFoundError,
)
from app.core.job_crypto import build_job_message
from app.services.fundos_do_mapa import inject_basemaps
from app.services.fuso_do_agendamento import injetar_fuso_do_agendamento
from app.core.utils.encryption import decrypt_workflow_connections
from app.core.utils.workflow_nodes import node_props
from app.crud.workflow_crud import WorkflowCRUD
from app.models.executor import Executor
from app.models.models import Workflow, WorkflowRun
from app.models.workspace import Workspace
from app.services import workspace_executor_service as politica
from app.services.credential_resolver import inject_credentials
from app.services.fechamento_de_run import OPEN_STATUSES, REPETIVEL, fechar_runs
from app.services.user_executor_service import get_default_agents

_logger = get_logger(__name__)

# Size of the already serialized payload above which the envelope encryption leaves the
# event loop and goes to a thread. Below that the thread hop costs more than
# the encryption itself.
_LIMIAR_CIFRA_EM_THREAD = 256 * 1024


@dataclass
class DispatchResult:
    """Result of dispatching a workflow to an executor."""
    id: str
    has_response_node: bool = False


class CandidateList(list):
    """Ordered list of candidate executors, annotated with the policy.

    It is a `list` on purpose: `_dispatch_job` and the existing tests iterate the
    list and pass MagicMocks; the attributes below are optional and read with
    `getattr`. `tiers` maps executor → tier at which it enters the chain
    ("primary" | "fallback" | "pool"); `allowed` is the set allowed by the
    policy (spec §5.3), `None` on the legacy path; `mode` and
    `exhausted_message`/`exhausted_category` feed the per-policy message.
    """
    tiers: dict[str, str]
    allowed: set[str] | None
    mode: str | None
    exhausted_message: str | None
    exhausted_category: str | None

    def __init__(self, executores=(), *, tiers=None, allowed=None, mode=None,
                 exhausted_message=None, exhausted_category=None):
        super().__init__(executores)
        self.tiers = dict(tiers or {})
        self.allowed = allowed
        self.mode = mode
        self.exhausted_message = exhausted_message
        self.exhausted_category = exhausted_category


def _safe_pinned_outputs(raw: dict | None, pin_metadata: dict | None = None) -> dict:
    """Filters `pinned_outputs` for sending to the executor.

    Only passes the nodes that have matching metadata. `pin_metadata` is written
    exclusively by the explicit pin of whoever is using it, so it is the proof
    that someone ASKED for that freeze; whatever is in `pinned_outputs`
    without a counterpart there is an orphan — a leftover of a deleted node, of a restored
    workflow, of an unpin that did not clean everything up.

    **An orphan does not pass, not even when there is no metadata at all.** The previous version
    short-circuited (`if meta_keys and nid not in meta_keys`), so that the
    empty column let ALL entries through. The effect was not theoretical:

    - an orphan with `__pin_s3_key__` makes the executor download the object and SKIP the node
      (`flow/executor/core.py`), and the validity is read from
      `pin_metadata[node_id]` — with no metadata there is no `expires_at`, so that
      orphan **never expires**. The workflow finishes green, with stale data, and nothing in the
      response says it came from cache;
    - and the path did not depend on legacy data: with `{A, B}` in `pinned_outputs`
      and only `A` in `pin_metadata`, B was discarded; unpinning A writes
      `pin_metadata = None` (`pin_service.py`), the column empties and **B
      came back to life on the next run**. Unpinning one node revived the pin of
      another.

    The accepted cost: a workflow that still depended on a pin without metadata now
    re-executes the node. Slower once, and correct.
    """
    if not raw:
        return {}
    meta_keys = set((pin_metadata or {}).keys())
    safe = {}
    for nid, val in raw.items():
        # Without metadata it is an orphan, and orphans do not go to the executor.
        if nid not in meta_keys:
            continue
        if isinstance(val, dict) and ("__pin_s3_key__" in val or not val):
            safe[nid] = val
        else:
            # Raw data (legacy) — marks as empty for auto-pin on the next run
            safe[nid] = {}
    return safe


def _get_redis():
    """Retorna o pool Redis centralizado."""
    from app.core.redis import get_redis_pool
    return get_redis_pool()


def _validate_no_disabled_nodes(definition: dict, disabled: set[str]) -> None:
    """Blocks the dispatch if the workflow contains nodes disabled by the admin.

    Raised BEFORE the envelope is created and BEFORE the executor is contacted:
    the server does not even reserve resources for a workflow that is going to fail at
    NodeFactory.create() on the executor. The operator sees an explicit message naming
    which nodes need to be re-enabled.
    """
    if not disabled:
        return
    from app.core.exceptions import DisabledNodesInWorkflowError

    offenders = sorted({
        n.get("name") for n in (definition.get("nodes") or [])
        if n.get("name") in disabled
    })
    if offenders:
        raise DisabledNodesInWorkflowError(
            "Workflow contém node(s) desabilitados pelo admin: "
            f"{', '.join(offenders)}. "
            "Reabilite via /admin/settings ou substitua os nodes."
        )


def _validate_trigger_inputs(definition: dict, inputs: dict | None) -> None:
    """Validates the dispatch inputs against the triggers' payload_schema.

    In this first version we cover WebhookTrigger, which is the only trigger with a
    `payload_schema` configured by the user. Aborts the dispatch with
    WorkflowInputValidationError (422) before dispatching to the executor,
    returning a message with the exact path of the field and the reason for the failure.
    """
    from jsonschema import Draft7Validator
    from app.core.exceptions import WorkflowInputValidationError

    inputs = inputs or {}
    for node in definition.get("nodes", []):
        if node.get("name") != "WebhookTrigger":
            continue
        props = node_props(node)
        schema = props.get("payload_schema")
        if not (isinstance(schema, dict) and schema.get("properties")):
            continue

        field = (props.get("payloadField") or "").strip()
        # Same resolution as the trigger:
        #   - field defined → inputs[field]
        #   - field empty   → inputs already is the payload
        raw = inputs.get(field) if field else inputs
        if raw is None:
            payload: dict = {}
        elif isinstance(raw, str):
            try:
                import json as _json
                payload = _json.loads(raw)
            except Exception:
                payload = {field or "payload": raw}
        elif isinstance(raw, dict):
            payload = raw
        else:
            payload = {field or "payload": raw}

        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        if not errors:
            continue
        parts = [f"'{err.json_path or '$'}': {err.message}" for err in errors]
        if len(parts) == 1:
            detail = f"Payload inválido em {parts[0]}"
        else:
            detail = f"Payload inválido — {len(parts)} erros: " + "; ".join(parts)
        raise WorkflowInputValidationError(detail)


async def _validate_trigger_credentials_only(
    definition: dict, request=None, *, pre_resolved: dict | None = None,
    allowed_owner_ids=None, autenticar_entrada: bool = True,
) -> None:
    """
    Validates only trigger nodes with a linked credential (e.g. WebhookTrigger).
    Does not inject connectionString into datasource nodes — that is done by the worker at runtime.

    If pre_resolved is provided, uses that dictionary instead of going to the database again.
    Fail-closed: if a trigger declares credential_id but the credential is not
    present in `resolved` (missing/expired/deleted), raises HTTP 403 — this
    holds on ALL paths, and it is what catches a deleted credential.

    `autenticar_entrada=False` skips only the authentication of the caller (the
    webhook token), which makes no sense in a trigger already authenticated by session.
    """
    from fastapi import HTTPException
    from app.core.authorization.credential_validators import validate_credential_by_type

    trigger_nodes = [
        (n, node_props(n).get("credential_id"))
        for n in definition.get("nodes", [])
        if n.get("type") == "trigger" and node_props(n).get("credential_id")
    ]
    if not trigger_nodes:
        return

    cred_ids = [cid for _, cid in trigger_nodes]
    if pre_resolved is not None:
        resolved = {cid: pre_resolved[cid] for cid in cred_ids if cid in pre_resolved}
    else:
        from app.core.authorization.credential_loader import resolve_credentials_from_ids
        resolved = await resolve_credentials_from_ids(
            cred_ids, allowed_owner_ids=allowed_owner_ids,
        )

    for _, cred_id in trigger_nodes:
        cred = resolved.get(cred_id)
        if not cred:
            # The trigger declares a credential but it could not be resolved — treat it
            # as an authentication failure (never a silent fail-open).
            raise HTTPException(
                status_code=403,
                detail="Credencial do trigger não pôde ser resolvida (ausente, expirada ou removida).",
            )
        await validate_credential_by_type(
            cred, request=request, autenticar_entrada=autenticar_entrada,
        )


def _collect_credential_ids(*definitions: dict) -> list[str]:
    """Extracts unique credential IDs from the nodes of one or more definitions.

    Accepts several because the sub-workflow chain also goes into the envelope: a
    database node INSIDE a sub-workflow needs the credential resolved just like
    one in the root workflow. While this only looked at the root, that node reached the
    executor with `credential_id` and without `connectionString`, and failed with
    "deve ser resolvido antes da execução" (must be resolved before execution) — a message
    that describes a server problem as if it were the node's configuration.

    Uses `node_props` to ensure that collector and validator agree on the
    extraction — see the docstring of `node_props`.
    """
    return list({
        cid
        for definition in definitions
        for node in (definition or {}).get("nodes", [])
        if (cid := node_props(node).get("credential_id"))
    })


async def _load_workflow(
    crud: WorkflowCRUD,
    id_hash: str,
    request: Request | None,
    workflow: Workflow | None = None,
) -> tuple[Workflow, dict]:
    """Loads the workflow, validates its state and decrypts the definition.

    `workflow` is the object the caller already has at hand. The three authenticated
    triggers (execute, retry, webhook) go through the authorization dependency,
    which ALREADY loaded and decrypted the workflow; redoing the
    `SELECT` here transferred and deserialized the whole `definition` column a
    second time (~1.7 MB and ~4.4 ms of `json.loads` on a large workflow) only to
    discard the result — SQLAlchemy's identity map returns the same object.
    The scheduler triggers by hash only and still falls into the SELECT.

    The validations apply equally on both paths: they are applied to the object,
    not to the query result.
    """
    wf = workflow if workflow is not None else await crud.get_by_hash(id_hash)
    if not wf:
        raise WorkflowNotFoundError(f"Workflow {id_hash} não existe")
    if not wf.flag_ative:
        raise WorkflowInactiveError(f"Workflow {id_hash} está desativado.")

    try:
        definition = decrypt_workflow_connections(wf.definition)
    except Exception as e:
        raise WorkflowDecryptionError(
            f"Não foi possível descriptografar a definição do workflow {id_hash}."
        ) from e

    # Trigger credentials validation moved to start_analysis (resolves once)
    return wf, definition


async def _is_available(executor_id: str) -> bool:
    """Candidate to be TRIED: presence True or "don't know" (spec §5.1).

    Only a confirmed absent presence excludes. A Redis blip or a
    reconnection in progress cannot take a live executor off the list — the
    real `send_job` will tell whether it connects, and failover continues if not.
    """
    return (await executor_registry.presence_or_unknown(executor_id)) is not False


# Runs that occupy an executor in the server's eyes: dispatched and still without
# an outcome. `pending` is included because the INSERT already writes the host before sending.
_IN_FLIGHT_STATUSES = ("pending", "running")

# Executor defaults (EXECUTOR_MAX_CONCURRENT / EXECUTOR_MAX_QUEUE_SIZE), for
# those that have not declared their own and have no readable database ceiling.
_DEFAULT_SLOTS = 4
_DEFAULT_QUEUE = 50

# Random draw for the order (uniform in [0, 1)). A module function so the tests
# can fix the order; it is not security, just spreading.
_desempate = random.random


def _count(valor) -> int:
    """Non-negative integer, or 0 — the capacity comes from outside (executor/Redis)."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return 0
    return max(valor, 0)


def _smallest_positive(*valores: int) -> int:
    """The smallest of the positive values; 0 if none is."""
    return min((v for v in valores if v > 0), default=0)


def _full_by_declared(cap: dict) -> bool:
    """The SAME computation as `send_job`'s `is_full`: if it says full, the send will
    be refused. Unreadable capacity is not "full" — the send is what decides."""
    if not cap:
        return False
    try:
        return _capacity_is_full(cap)
    except TypeError:
        return False


@dataclass(frozen=True)
class _ExecutorState:
    """How an executor is doing, for the dispatch order (`_executor_states`)."""
    carga: int              # jobs it has (running + in the local queue)
    vagas: int              # concurrent runs it can hold
    fila: int               # jobs its local queue can hold beyond the slots
    cheio_declarado: bool   # its last `capacity` already hits the ceiling

    @property
    def livres(self) -> int:
        return self.vagas - self.carga

    @property
    def cheio(self) -> bool:
        """Nothing else fits: according to its own report (send_job refuses) or to the
        server's count (its local queue refuses, and the run FAILS — with no
        failover, because the send had already been accepted)."""
        return self.cheio_declarado or self.carga >= self.vagas + self.fila

    @property
    def occupancy(self) -> float:
        """Occupancy with this one more job: (load + 1) / slots."""
        return (self.carga + 1) / self.vagas


async def _counted_by_server(db: AsyncSession, ids: list[str]) -> dict[str, int] | None:
    """`pending`/`running` runs of each executor, counted in the database; None if the
    count did not come through.

    It is the load that all API workers see the same way and that changes at the
    instant of dispatch: the run's INSERT, with the host, is committed before the
    job goes out. The one declared by the executor only arrives every 10 s — in a burst,
    all the jobs went to whoever was empty in the last report.

    Best-effort, in a SAVEPOINT opened on the session's CONNECTION:
    - on Postgres, an error in this query (lock_timeout, statement_timeout,
      cancellation) would abort the request's transaction, and the run's INSERT right
      after would fail — the ordering bringing down the dispatch. The savepoint
      rolls back only the nested point;
    - on the connection, and not with `Session.begin_nested()`: that one flushes
      whatever the session has pending before the SAVEPOINT, and an error from that flush
      would be swallowed here as "count unavailable", with the transaction already
      lost. Here nothing from the session is flushed or expired;
    - only a driver error (`DBAPIError`) becomes degradation, and a lost connection does not:
      the INSERT ahead would fail anyway, and with a worse error. Bugs propagate.
    """
    hosts = {f"executor:{i}": i for i in ids}
    consulta = (
        sa_select(WorkflowRun.host, func.count())
        .where(
            WorkflowRun.status.in_(_IN_FLIGHT_STATUSES),
            WorkflowRun.host.in_(list(hosts)),
        )
        .group_by(WorkflowRun.host)
    )
    conexao = await db.connection()
    try:
        async with conexao.begin_nested():
            linhas = (await conexao.execute(consulta)).all()
    except DBAPIError as exc:
        if exc.connection_invalidated:
            raise
        _logger.warning(
            "Carga contada pelo servidor indisponível (%s) — ordenando pela declarada.", exc,
        )
        return None
    return {hosts[host]: int(n) for host, n in linhas if host in hosts}


async def _executor_states(db: AsyncSession, executores: list[Executor]) -> dict[str, _ExecutorState]:
    """Load, slots, queue and "full" for each candidate.

    - load = the one counted by the server. It is fresh and the same on all workers;
      the declared one (running + queued from the last `capacity`) is up to 10 s old and, added
      to it or compared with it, made a just-freed executor look busy. The
      declared one only applies when the count did not come through.
    - slots/queue = the smaller of the declared (max_concurrent/max_queue, already
      capped at the database ceiling) and the database ceiling — before the first
      `capacity` the worker holding the WebSocket has only a provisional value, and
      the workers cannot see the same executor with different sizes.
    - cheio_declarado = `send_job`'s `is_full` over the declared one: catches the
      draining executor, which announces itself full to get out of the way.
    """
    ids = [ag.id_hash for ag in executores]
    # `return_exceptions`: an error on one side cannot propagate with the other
    # still in flight — the query would use the session while the caller is already using it
    # again. After both finish, a count error propagates; an error reading the
    # capacity counts as nothing declared.
    counted, declaradas = await asyncio.gather(
        _counted_by_server(db, ids),
        executor_registry.read_capacities(ids),
        return_exceptions=True,
    )
    if isinstance(counted, BaseException):
        raise counted
    if isinstance(declaradas, BaseException) or not isinstance(declaradas, dict):
        declaradas = {}
    executor_states: dict[str, _ExecutorState] = {}
    for ag in executores:
        cap = declaradas.get(ag.id_hash)
        cap = cap if isinstance(cap, dict) else {}
        declarada = _count(cap.get("running")) + _count(cap.get("queued"))
        executor_states[ag.id_hash] = _ExecutorState(
            carga=counted.get(ag.id_hash, 0) if counted is not None else declarada,
            vagas=_smallest_positive(
                _count(cap.get("max_concurrent")),
                _count(getattr(ag, "max_concurrent_jobs", None)),
            ) or _DEFAULT_SLOTS,
            fila=_smallest_positive(
                _count(cap.get("max_queue")),
                _count(getattr(ag, "max_queue_size", None)),
            ) or _DEFAULT_QUEUE,
            cheio_declarado=_full_by_declared(cap),
        )
    return executor_states


def _sort_key(s: _ExecutorState) -> tuple:
    """Three groups, in this order:

    1. With a free slot — the job starts right away. Draw WEIGHTED by the free
       slots (Efraimidis–Spirakis: U^(1/weight), largest first). With the strict
       minimum, simultaneous decisions — the API workers, concurrent
       requests — started from the same snapshot and all chose the same
       executor; the draw spreads them in proportion to the slack. In sequence, the
       database already shows each previous dispatch.
    2. No slot, with room in the local queue — the job will wait in some queue: the
       one with the lowest occupancy relative to its slots, which is where it should start soonest.
    3. Full — according to the report (`send_job` refuses) or to the count (the local
       queue refuses and the run fails). They go last: tried only if there is no
       other. This is where the draining executor lands.
    """
    if s.cheio:
        return (2, s.occupancy, _desempate())
    if s.livres > 0:
        return (0, -(_desempate() ** (1 / s.livres)))
    return (1, s.occupancy, _desempate())


async def _sorted_eligible(
    db: AsyncSession, executores: list[Executor], *, excluir: set[str] = frozenset(),
) -> list[Executor]:
    """Filters by `active` + `public_key` + availability (in parallel) and
    sorts by `_sort_key` over `_executor_states`."""
    base = [
        ag for ag in executores
        if ag.id_hash not in excluir and ag.status == "active" and ag.public_key
    ]
    if not base:
        return []
    flags = await asyncio.gather(*[_is_available(ag.id_hash) for ag in base])
    vivos = [ag for ag, ok in zip(base, flags) if ok]
    if len(vivos) < 2:
        return vivos
    executor_states = await _executor_states(db, vivos)
    vivos.sort(key=lambda ag: _sort_key(executor_states[ag.id_hash]))
    return vivos


async def _resolve_candidates(db: AsyncSession, wf: Workflow) -> CandidateList:
    """Candidate executors, in attempt order.

    With `EXECUTOR_POLICY_ROUTING=on` the list is the CHAIN of the workspace's
    policy (spec §5); with `off`, the legacy path (the workspace's dedicated one and
    then the entire pool). After the backfill of migration 20260907_0002 both
    produce the same chain for every existing workspace — the same
    executors in the same tiers; within a tier the order involves a random draw
    (`_sort_key`), so it is only identical with the draw fixed, as in the
    golden test.
    """
    if policy_routing_enabled() and wf.workspace_id:
        return await _resolve_candidates_by_policy(db, wf)
    return await _resolve_candidates_legacy(db, wf)


async def _resolve_candidates_legacy(db: AsyncSession, wf: Workflow) -> CandidateList:
    """Legacy priority order: 1. the workspace's dedicated executor (if available);
    2. the default executor pool, in `_sort_key` order. Raises 503 if
    the list ends up empty."""
    candidates: list[Executor] = []
    tiers: dict[str, str] = {}

    if wf.workspace_id:
        result = await db.execute(
            sa_select(Executor)
            .join(Workspace, Workspace.target_executor_id == Executor.id_hash)
            .where(
                Workspace.id_hash == wf.workspace_id,
                Workspace.deleted_at.is_(None),
                Executor.deleted_at.is_(None),
            )
        )
        ag = result.scalar_one_or_none()
        if ag and ag.status == "active" and ag.public_key and await _is_available(ag.id_hash):
            candidates.append(ag)
            tiers[ag.id_hash] = politica.DISPATCH_PRIMARY

    defaults = await get_default_agents(db)
    for ag in await _sorted_eligible(db, defaults, excluir={c.id_hash for c in candidates}):
        candidates.append(ag)
        tiers[ag.id_hash] = politica.DISPATCH_POOL

    if not candidates:
        raise NoExecutorAvailableError(
            "Nenhum executor disponível (pool padrão vazio ou todos offline). Contate o administrador.",
            category="no_pool_executor",
        )
    return CandidateList(candidates, tiers=tiers, mode=None)


def _policy_messages(p: "politica.WorkspacePolicy") -> tuple[str, str]:
    """(detailed message for the owner, error_category) when the chain is exhausted."""
    n = len(p.primary) + len(p.fallback)
    if p.mode == politica.MODE_ISOLATED:
        return (
            f"Workspace isolado: nenhum dos {n} executores dedicados está disponível. "
            "O job NÃO foi enviado ao pool compartilhado.",
            "no_dedicated_executor",
        )
    if p.mode == politica.MODE_DEDICATED_POOL:
        return (
            f"Nenhum executor disponível: {n} dedicados e o pool compartilhado estão fora.",
            "no_executor_chain",
        )
    return ("Nenhum executor do pool compartilhado disponível.", "no_pool_executor")


async def _resolve_candidates_by_policy(db: AsyncSession, wf: Workflow) -> CandidateList:
    """Policy chain: tier 1 → tier 2 → terminal (spec §5).

    Within a tier, the `_sort_key` order; between tiers, strict
    order. The pool only comes in if the EFFECTIVE terminal is `pool` (the admin's floor
    wins). Pool mode (no tier 1) is the usual one."""
    p = await politica.load_policy_by_id(db, wf.workspace_id)
    if p is None:
        # Deleted/nonexistent workspace: the legacy path returns the pool — keep it.
        return await _resolve_candidates_legacy(db, wf)

    cadeia: list[Executor] = []
    tiers: dict[str, str] = {}

    if p.has_primary:
        for ag in await _sorted_eligible(db, p.primary):
            cadeia.append(ag); tiers[ag.id_hash] = politica.DISPATCH_PRIMARY
        for ag in await _sorted_eligible(db, p.fallback, excluir=set(tiers)):
            cadeia.append(ag); tiers[ag.id_hash] = politica.DISPATCH_FALLBACK

    if p.allows_pool:
        defaults = await get_default_agents(db)
        for ag in await _sorted_eligible(db, defaults, excluir=set(tiers)):
            cadeia.append(ag); tiers[ag.id_hash] = politica.DISPATCH_POOL

    mensagem, categoria = _policy_messages(p)
    if not cadeia:
        _log_dispatch_event(
            wf=wf, mode=p.mode, candidates_total=0, chosen=None, tier=None,
            failovers=0, decision_ms=0.0, outcome="no_candidates", category=categoria,
        )
        raise NoExecutorAvailableError(mensagem, category=categoria)

    allowed = await politica.allowed_executor_ids(db, p)
    return CandidateList(
        cadeia, tiers=tiers, allowed=allowed, mode=p.mode,
        exhausted_message=mensagem, exhausted_category=categoria,
    )


def _log_dispatch_event(*, wf, mode, candidates_total, chosen, tier, failovers,
                        decision_ms, outcome, category=None, run_id=None) -> None:
    """One JSON line per dispatch decision — replaces the loose `info` from before
    and is the source of the per-tier metrics (spec §11)."""
    evento = {
        "event": "dispatch",
        "run_id": run_id,
        "workflow_hash": getattr(wf, "id_hash", None),
        "workspace_id": getattr(wf, "workspace_id", None),
        "mode": mode or "legacy",
        "candidates_total": candidates_total,
        "chosen_executor": chosen,
        "dispatch_tier": tier,
        "failovers": failovers,
        "decision_ms": round(decision_ms, 1),
        "outcome": outcome,
    }
    if category:
        evento["error_category"] = category
    nivel = _logger.info if outcome == "dispatched" else _logger.warning
    nivel("dispatch_event %s", json.dumps(evento, ensure_ascii=False, default=str))


@dataclass
class _Dispatch:
    """What the phases of `_dispatch_job` share: the already written run, the
    chain with the policy annotations and the decision clock (spec §11).
    `ultimo_erro` accumulates the reason for the last refusal, which goes into the
    run's message when no candidate accepts."""
    db: AsyncSession
    wf: Workflow
    run: WorkflowRun
    # The run id as a string, and not `run.task_id`: a rollback midway (the
    # closing bookkeeping does one) expires the object, and reading an expired
    # attribute in an async session is implicit I/O.
    job_id: str
    candidatos: list[Executor]
    tiers: dict
    allowed: set[str] | None
    mode: str | None
    inicio: float
    has_response_node: bool
    ultimo_erro: str = ""

    def resultado(self) -> DispatchResult:
        return DispatchResult(id=self.job_id, has_response_node=self.has_response_node)


async def _dispatch_job(
    wf: Workflow,
    definition: dict,
    candidates: list[Executor],
    inputs: dict | None,
    debug_mode: bool,
    *,
    db: AsyncSession,
    pre_resolved: dict | None = None,
    disabled_nodes: list[str] | None = None,
    subworkflow_definitions: dict | None = None,
    trigger_source: str | None = None,
    triggered_by: str | None = None,
    schedule_id: int | None = None,
) -> DispatchResult:
    """Persists the WorkflowRun in the DB and tries to dispatch to each candidate.

    Sequence (anti-race):
      1. INSERT WorkflowRun(status='pending', host=<first candidate>) —
         ensures the run exists in the DB before any network call. WS
         /ws/workflow/<task_id> finds the run immediately after the POST
         /execute returns.
      2. Loop over the candidates: encrypt job + send_job to the executor.
      3. Success: UPDATE status='running'. Returns DispatchResult.
      4. No candidate accepts: UPDATE status='failed' + error_message.
         Re-raise NoExecutorAvailableError to the caller (POST returns 5xx).

    Each step is a function: `_create_run` (1), `_serializar_payload` (the
    envelope, once), `_try_candidates` (2 and 3, with the isolation
    barrier and `_confirm_delivery`) and `_close_without_executor` (4). This
    function only chains them and holds the safety net.

    Before, this creation was asynchronous via the Redis queue 'run_creates' (a consumer
    did the INSERT). It caused 4404 under load (consumer lagging), and could
    leave orphan runs if the API crashed between send_job and lpush.

    The whole body after the INSERT runs inside a try/except: any unexpected
    exception (TypeError in build_job_message due to an invalid public key,
    credential resolver failure, send_job blowing up) left the run in
    'pending' forever — the watchdog only reconciles 'running' and the cancel
    answered "Execucao sem executor associado" (run with no associated executor). Now the run is marked as
    'failed' with the error message before the re-raise.

    `trigger_source`, `triggered_by` and `schedule_id` go into the INSERT along
    with the host (docs/specs/metrics-history.md §2): they are labels of the run, not
    of the dispatch — a separate UPDATE afterwards would cost one more commit on the
    critical path. Whoever closes the run here also writes `error_category`
    ("isolation", "no_executor", "dispatch"), so that History can group "why it
    failed" without a LIKE on `error_message`.
    """
    has_response_node = any(n.get("name") == "Response" for n in definition.get("nodes", []))
    job_id = str(uuid.uuid4())
    inicio = time.monotonic()
    tiers: dict = getattr(candidates, "tiers", None) or {}
    allowed = getattr(candidates, "allowed", None)
    mode = getattr(candidates, "mode", None)

    run = await _create_run(
        db, wf, candidates, tiers, job_id,
        trigger_source=trigger_source, triggered_by=triggered_by, schedule_id=schedule_id,
    )
    despacho = _Dispatch(
        db=db, wf=wf, run=run, job_id=job_id, candidatos=candidates, tiers=tiers,
        allowed=allowed, mode=mode, inicio=inicio, has_response_node=has_response_node,
    )

    try:
        plaintext = await _serializar_payload(
            wf, definition, job_id, inputs, debug_mode,
            pre_resolved=pre_resolved, disabled_nodes=disabled_nodes,
            subworkflow_definitions=subworkflow_definitions,
        )
        entregue = await _try_candidates(despacho, plaintext)
        if entregue is not None:
            return entregue
        raise await _close_without_executor(despacho)

    except Exception as exc:
        # Safety net: closes the run before propagating. Idempotent — path
        # (4) already wrote 'failed' and it is not rewritten here.
        await _close_orphan_dispatch(db, run, exc)
        raise


async def _create_run(
    db: AsyncSession,
    wf: Workflow,
    candidates: list[Executor],
    tiers: dict,
    job_id: str,
    *,
    trigger_source: str | None,
    triggered_by: str | None,
    schedule_id: int | None,
) -> WorkflowRun:
    """1) Creates the run in the DB BEFORE touching the network (solves the WS↔consumer race).

    SEC: the host of the FIRST candidate already goes into the INSERT. The guarantee that
    matters is "host written before sending" — it is what makes
    `_run_belongs_to_agent` refuse an executor that claims someone else's run —
    and the first candidate is already known here. Writing the host only in the loop
    cost a second commit (one more WAL fsync) between the decision and the
    frame going out over the WebSocket. Now only the failover pays for that UPDATE.

    It stays OUTSIDE the safety net of `_dispatch_job`: if this commit fails,
    there is no run to close.
    """
    run = WorkflowRun(
        task_id=job_id,
        workflow_hash=wf.id_hash,
        workspace_id=wf.workspace_id,
        status="pending",
        node_stats={},
        host=f"executor:{candidates[0].id_hash}" if candidates else None,
        dispatch_tier=tiers.get(candidates[0].id_hash) if candidates else None,
        trigger_source=trigger_source,
        triggered_by=triggered_by,
        schedule_id=schedule_id,
    )
    db.add(run)
    await db.commit()
    return run


async def _serializar_payload(
    wf: Workflow,
    definition: dict,
    job_id: str,
    inputs: dict | None,
    debug_mode: bool,
    *,
    pre_resolved: dict | None,
    disabled_nodes: list[str] | None,
    subworkflow_definitions: dict | None,
) -> bytes:
    """The job envelope, with the credentials injected, already serialized."""
    # Injects credentials into the payload (without saving to the database). The
    # sub-workflow chain goes through the SAME treatment: it travels in the envelope and the
    # executor has no DB to resolve anything on its own.
    enriched = await inject_credentials(definition, pre_resolved=pre_resolved)
    enriched_subs = {
        hash_: await inject_credentials(sub_def, pre_resolved=pre_resolved)
        for hash_, sub_def in (subworkflow_definitions or {}).items()
    }
    # And the installation's base map in the Carta nodes, for the same reason: the
    # executor does not have the configuration (see app/services/fundos_do_mapa.py).
    enriched = inject_basemaps(enriched)
    enriched_subs = {hash_: inject_basemaps(sub) for hash_, sub in enriched_subs.items()}
    # And the default schedule timezone in a ScheduleTrigger without a timezone: the node's
    # default is that of the environment of whoever imports it, and the executor does not have the
    # installation's (see app/services/fuso_do_agendamento.py).
    enriched = injetar_fuso_do_agendamento(enriched)
    enriched_subs = {hash_: injetar_fuso_do_agendamento(sub) for hash_, sub in enriched_subs.items()}

    agent_payload = {
        "workflow_definition": enriched,
        "workflow_hash":       wf.id_hash,
        "run_id":              job_id,
        "params":              inputs or {},
        "workspace_id":        wf.workspace_id,
        "debug_mode":          debug_mode,
        "pinned_outputs":      _safe_pinned_outputs(wf.pinned_outputs, wf.pin_metadata),
        "pin_metadata":        wf.pin_metadata or {},
        # Snapshot of the nodes disabled at dispatch time. SubWorkflowNode
        # uses it to validate sub-workflows without needing to query the server's DB.
        "disabled_nodes":      disabled_nodes or [],
        # Pre-resolved definitions of the entire sub-workflow chain. The executor
        # has no access to the DB (only flow/ and executor/ in Docker), so it needs to
        # receive everything here. Map {hash: definition}.
        "subworkflow_definitions": enriched_subs,
    }

    # Serializes the payload ONCE, outside the candidate loop: for a
    # large workflow that is a few MB of json.dumps, and before it was redone
    # per candidate on every failover. It goes to a thread: there is no way to know the
    # size before serializing (the encryption's `_LIMIAR` gate depends on this
    # result), and an inline json.dumps of megabytes froze the worker that
    # serves the WebSockets of ALL executors. It is once per dispatch
    # (not per candidate), so the thread hop is cheap — unlike the
    # encryption, which can repeat on failover and whose size is already known.
    return await asyncio.to_thread(
        lambda: json.dumps(agent_payload, ensure_ascii=False).encode()
    )


async def _try_candidates(d: _Dispatch, plaintext: bytes) -> DispatchResult | None:
    """2) Tries to dispatch to each candidate in priority order.

    Returns the result of the first one that accepts (3), or None if none accepted
    — with the reason for the last refusal in `d.ultimo_erro`. A candidate outside the
    policy raises, with the run already closed (`_block_outside_policy`).
    """
    encrypt_in_thread = len(plaintext) >= _LIMIAR_CIFRA_EM_THREAD
    for indice, ag in enumerate(d.candidatos):
        label = f"{ag.name}@{ag.id_hash[-5:]}" if ag.name else ag.id_hash

        # Isolation barrier (spec §5.3): before ENCRYPTING for this executor's
        # key, it has to be in the set the policy
        # allows. A refactor that reintroduces the pool into the chain is caught
        # here, not in production by the customer — and the job never goes out.
        if d.allowed is not None and ag.id_hash not in d.allowed:
            raise await _block_outside_policy(d, ag, indice, label)

        try:
            job_msg = await _encrypt_for(d, ag, plaintext, encrypt_in_thread)
        except RuntimeError as exc:
            _logger.warning("Falha ao cifrar job para executor '%s': %s", label, exc)
            d.ultimo_erro = f"Falha ao cifrar job para '{label}': {exc}"
            continue

        # SEC: the host has to be written BEFORE sending — it is what
        # `_run_belongs_to_agent` uses in the WS router to authorize
        # job_result/node_event, and without it any executor could
        # claim the run (cross-tenant fail-open). The first candidate
        # was already written in the INSERT; only the failover needs to rewrite it.
        if indice:
            d.run.host = f"executor:{ag.id_hash}"
            d.run.dispatch_tier = d.tiers.get(ag.id_hash)
            await d.db.commit()

        try:
            sent = await executor_registry.send_job(ag.id_hash, job_msg)
        except Exception as exc:
            # send_job touches the connection's in-memory state (e.g. is_full() with
            # a malformed capacity raises TypeError). That brought down the whole
            # dispatch and left the run in 'pending'; here it becomes a refusal by this
            # candidate so that the failover continues.
            _logger.warning("Erro ao enviar job ao executor '%s': %s", label, exc)
            d.ultimo_erro = f"Erro ao enviar job para '{label}': {exc}"
            continue

        if not sent:
            _logger.warning("Executor '%s' recusou job (fila cheia ou desconectado). Tentando próximo.", label)
            d.ultimo_erro = f"Executor '{label}' não aceitou o job (fila cheia ou desconectado)."
            continue

        return await _confirm_delivery(d, ag, indice, label)
    return None


async def _block_outside_policy(
    d: _Dispatch, ag: Executor, indice: int, label: str,
) -> NoExecutorAvailableError:
    """Closes the run and records the isolation violation; returns the exception that
    the caller raises. The job does NOT go out: nothing was encrypted for this executor."""
    _logger.error(
        "VIOLAÇÃO DE ISOLAMENTO: executor '%s' fora do conjunto permitido do "
        "workspace '%s' (run %s). Job NÃO enviado.", label, d.wf.workspace_id, d.job_id,
    )
    mensagem = (
        "Barreira de isolamento: o roteamento escolheu um executor fora da "
        "política do workspace. O job não foi enviado."
    )
    # Conditional, like every server-side close: a
    # cancellation that arrived in this window wins.
    await fechar_runs(d.db, [d.run], de=OPEN_STATUSES, para="failed", mensagem=mensagem, categoria="isolation")
    _log_dispatch_event(
        wf=d.wf, mode=d.mode, candidates_total=len(d.candidatos), chosen=ag.id_hash,
        tier=d.tiers.get(ag.id_hash), failovers=indice,
        decision_ms=(time.monotonic() - d.inicio) * 1000,
        outcome="isolation_violation", category="isolation_violation", run_id=d.job_id,
    )
    return NoExecutorAvailableError(
        mensagem, category="isolation_violation", run_id=d.job_id,
    )


async def _encrypt_for(d: _Dispatch, ag: Executor, plaintext: bytes, encrypt_in_thread: bool) -> dict:
    """The envelope encrypted for this executor's key. RuntimeError means an invalid
    key, and the candidate is skipped."""
    argumentos = dict(
        executor_id=ag.id_hash,
        workspace_id=d.wf.workspace_id or "",
        agent_x25519_pub_pem=ag.public_key,
        job_type="run_workflow",
        payload=plaintext,
        job_id=d.job_id,
    )
    # Above the threshold, AES-GCM + base64 + signature go to a
    # thread: `cryptography` releases the GIL in the primitives, and this
    # worker also serves the WebSockets of ALL executors —
    # encrypting a megabyte envelope inline froze the whole process
    # for tens of milliseconds on every trigger. Below the
    # threshold the thread hop would cost more than it saves.
    if encrypt_in_thread:
        return await asyncio.to_thread(build_job_message, **argumentos)
    return build_job_message(**argumentos)


async def _confirm_delivery(d: _Dispatch, ag: Executor, indice: int, label: str) -> DispatchResult:
    """3) Success — transitions pending → running, but ONLY if the run has not
    yet reached a terminal state. Between the INSERT of step (1) and this
    point seconds go by (inject_credentials resolves/decrypts
    credentials, envelope encryption, send_job) and the run already shows up on the
    runs screen: the user may cancel it in that window. With an
    unconditional `run.status = "running"` the UPDATE by PK erased the
    'cancelled', the API had already answered 200/cancelled and the job ran
    to the end.

    'running' is part of the condition because the executor's ACK also
    promotes the run (see `_record_job_ack`) and usually arrives BEFORE this
    commit: the executor confirms within milliseconds. With only 'pending', a
    rowcount of 0 would be read as a cancellation and the dispatch would send
    'cancel' to a healthy job.
    """
    transition = await d.db.execute(
        sa_update(WorkflowRun)
        .where(
            WorkflowRun.task_id == d.job_id,
            WorkflowRun.status.in_(("pending", "running")),
        )
        .values(status="running")
        .execution_options(synchronize_session=False)
    )
    await d.db.commit()

    if not transition.rowcount:
        # We lost to the cancellation. The executor HAS ALREADY accepted the job, so
        # the only way to honor the 'cancelled' is to notify it.
        _logger.warning(
            "Run '%s' saiu de 'pending' durante o despacho — pedindo ao "
            "executor '%s' que interrompa o job recem-enviado.", d.job_id, label,
        )
        try:
            await executor_registry.send_json(
                ag.id_hash, {"type": "cancel", "job_id": d.job_id}
            )
        except Exception as exc:
            _logger.error(
                "Falha ao pedir interrupcao do job '%s' ao executor '%s': %s",
                d.job_id, label, exc,
            )
        return d.resultado()

    # Syncs the object WITHOUT dirtying it: a normal assignment would make the
    # next flush re-emit `SET status=...` by PK, reintroducing the
    # unconditional writer that the UPDATE above has just eliminated.
    set_committed_value(d.run, "status", "running")

    _log_dispatch_event(
        wf=d.wf, mode=d.mode, candidates_total=len(d.candidatos), chosen=ag.id_hash,
        tier=d.tiers.get(ag.id_hash), failovers=indice,
        decision_ms=(time.monotonic() - d.inicio) * 1000, outcome="dispatched", run_id=d.job_id,
    )
    return d.resultado()


async def _close_without_executor(d: _Dispatch) -> NoExecutorAvailableError:
    """4) No candidate accepted — marks as failed to avoid a zombie run
    in 'pending' forever. Conditional (see `fechar_runs`): the
    user may have cancelled the run while the candidates were answering, and
    the 'cancelled' the API confirmed cannot turn into 'failed'.

    Returns the exception that the caller raises.
    """
    exhausted = getattr(d.candidatos, "exhausted_message", None)
    categoria = getattr(d.candidatos, "exhausted_category", None) or "no_executor"
    last_error = d.ultimo_erro
    mensagem = (
        f"{exhausted} Último motivo: {last_error}" if exhausted and last_error
        else exhausted or last_error or "Nenhum executor aceitou o job."
    )
    # FIXED category, and not `categoria`: the exception's one is the granularity of the
    # alert to the owner ("no_dedicated_executor", "no_executor_chain"...) and does not
    # fit the column's taxonomy, which sums all of that up as "no executor".
    # Retrying is safe: nothing ran, and the executor may come back.
    await fechar_runs(
        d.db, [d.run], de=OPEN_STATUSES, para="failed", mensagem=mensagem,
        categoria="no_executor", extra=REPETIVEL,
    )
    _log_dispatch_event(
        wf=d.wf, mode=d.mode, candidates_total=len(d.candidatos), chosen=None, tier=None,
        failovers=len(d.candidatos), decision_ms=(time.monotonic() - d.inicio) * 1000,
        outcome="all_refused", category=categoria, run_id=d.job_id,
    )

    return NoExecutorAvailableError(mensagem, category=categoria, run_id=d.job_id)


async def _close_orphan_dispatch(db: AsyncSession, run: WorkflowRun, exc: Exception) -> None:
    """Marks as 'failed' a run that blew up during the dispatch.

    Without this the run stayed in 'pending' indefinitely: the executor watchdog
    only reconciles runs in 'running' and `cancel_run` had no host to contact.
    Idempotent: the run that the dispatch itself already closed (step 4, barrier) or
    that the user cancelled midway is not rewritten — `fechar_runs` only closes what
    is still open.
    """
    try:
        await fechar_runs(
            db, [run], de=OPEN_STATUSES, para="failed",
            mensagem=f"Falha no despacho: {exc}"[:1000], categoria="dispatch",
        )
    except Exception as commit_exc:
        _logger.error(
            "Nao foi possivel fechar o run '%s' apos falha de despacho (%s): %s",
            run.task_id, exc, commit_exc,
        )
        try:
            await db.rollback()
        except Exception:
            pass


async def _close_unassigned_run(db: AsyncSession, run: WorkflowRun) -> bool:
    """Closes as 'cancelled' a run that no executor accepted. Returns whether it won.

    A **conditional** UPDATE on purpose, and the condition is `status='pending'` —
    exactly the mirror image of the dispatch's UPDATE (`pending → running`), so
    that exactly one of the two wins. A read-decide-write in separate steps
    would lose the race: the dispatch's `SET status='running'`, being by PK,
    erased the 'cancelled' the API had already confirmed to the user.

    Before, the condition also required `host IS NULL`. The host now goes in already at the
    run's INSERT (that is what avoids an extra commit before sending), so that
    column no longer distinguishes anything: what separates "the executor already has the job" from "the
    job has not left the server yet" is the STATUS — the dispatch only promotes to
    'running' after `send_job` has accepted.

    Careful: 'pending' separates the two cases only while the process that dispatched
    is alive. That is why whoever closes here must notify the host anyway — see
    `_notify_host_of_cancellation`.
    """
    return bool(await fechar_runs(
        db, [run], de=("pending",), para="cancelled",
        mensagem="Cancelado antes de ser atribuído a um executor.", categoria=None,
    ))


async def _notify_host_of_cancellation(run: WorkflowRun) -> None:
    """Asks the executor recorded in `run.host` to interrupt the job. Best-effort.

    Called ALSO when the run was closed locally while still 'pending'.
    Reason: 'pending' does not prove the job did not go out. The host goes in already at the INSERT and
    `send_job` happens BEFORE the pending→running commit; if the worker that
    dispatched dies in that window (rolling restart, `docker compose restart api`,
    OOM killer, SIGKILL), the run stays 'pending' forever with the executor
    actually running the workflow — sending emails, doing INSERTs. The dispatch's
    safety net (rowcount 0 → sends the 'cancel') only exists while
    THAT process is alive, which is exactly what does not hold in this scenario, and
    the user would get "cancelled" with the workflow running to the end.

    Sending the 'cancel' is idempotent: for a job_id the executor never
    received, `JobQueue.cancel` answers "unknown" and marks nothing.

    Does not raise: the local cancellation has already been confirmed in the database and talking to the
    executor is an extra effort, not a condition for answering the user.
    """
    host = run.host or ""
    if not host.startswith("executor:"):
        return
    executor_id = host[len("executor:"):]
    try:
        await executor_registry.send_json(
            executor_id, {"type": "cancel", "job_id": run.task_id},
        )
    except Exception as exc:
        _logger.warning(
            "Falha ao avisar o executor '%s' do cancelamento do run '%s': %s",
            executor_id, run.task_id, exc,
        )


async def cancel_run(
    db: AsyncSession,
    run_id: str,
    *,
    user_id: str,
    como_admin: bool = False,
) -> str:
    """Asks the executor to interrupt a run in progress.

    `user_id` is required and keyword-only because this function had NO
    authorization at all: the role was checked only in the route, and any other
    caller — an MCP server tool, a script, a job — cancelled runs
    of any workspace of any account. Now the rule lives here, next to the
    SELECT that loads the run, and whoever forgets the parameter breaks at the call instead
    of silently crossing tenants.

    Authorization is by the RUN's workspace, not by the workflow's current workspace:
    a workflow may have been moved from A to B after it was triggered, and whoever
    controls B must not be able to cancel a run that ran (and consumed
    resources) in A. `como_admin` reproduces the global administrator shortcut that the
    route already had — a personal token never gets it, because `as_user()`
    always returns `role="user"`.

    Returns the "outcome": "requested" when the message reached the executor,
    "already_finished" when the run has already finished (idempotent no-op) and
    "cancelled" when the run was closed here — it never reached an executor, or
    the executor holding it is down.

    For an already delivered run it does NOT write the status to the database: what closes it is the
    `job_result` coming back from the executor (status=cancelled), the usual
    path. Having two writers of the status would open a race between this commit and the
    result that arrives right after — and the run could end up "cancelled"
    even though it completed in the interval between the request and the interruption.

    The only local write is `_close_unassigned_run`'s, restricted by a conditional
    UPDATE to the run that is still 'pending' — the case in which, under normal
    conditions, there is no executor to ask anything of. Losing that condition
    means the dispatch won; so we re-read the run and continue down the normal
    path.

    The decision between "close here" and "wait for the job_result" is by STATUS, not
    by host: the host is filled in since the run's INSERT, but 'pending'
    means `send_job` has not yet confirmed delivery, and without the local
    close the user would have no way at all to clean up the run (the watchdog only
    reconciles 'running'). The local close does NOT waive notifying the host: a
    'pending' may be an already delivered job whose dispatcher died before the
    commit — see `_notify_host_of_cancellation`.

    With the executor holding it down, the run is also closed here
    ("cancelled"): without this there was no way to clean up a lost run from the screen.

    Raises WorkflowNotFoundError if the run does not exist.
    """
    result = await db.execute(
        sa_select(WorkflowRun).where(WorkflowRun.task_id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise WorkflowNotFoundError(f"Execução '{run_id}' não encontrada.")

    if not como_admin:
        papel = await role_in_run_workspace(db, run, user_id)
        exigir_papel(
            papel,
            ROLE_OPERATOR,
            "Requer role 'operator' ou superior para cancelar execuções.",
        )

    if run.status not in ("pending", "running"):
        return "already_finished"

    if run.status == "pending":
        # Nobody has confirmed receipt yet. The watchdog only reconciles
        # 'running', so without this local close the user was left with no
        # way at all to clean up the run. If the dispatch delivers right after,
        # it detects the rowcount 0 of its own UPDATE and sends the 'cancel'.
        if await _close_unassigned_run(db, run):
            _logger.info("Run '%s' cancelado localmente (ainda em 'pending').", run_id)
            # And notifies the host anyway: 'pending' may be a job that HAS ALREADY gone out
            # and whose dispatcher died before the commit — see
            # `_notify_host_of_cancellation`.
            await _notify_host_of_cancellation(run)
            return "cancelled"

        # The dispatch got there first: re-reads the real state before deciding.
        await db.refresh(run)
        if run.status not in ("pending", "running"):
            _logger.info(
                "Run '%s': cancelamento local perdeu a corrida com o dispatch (status=%s).",
                run_id, run.status,
            )
            return "already_finished"

    # The run's host records who is executing it: "executor:{id_hash}".
    host = run.host or ""
    if not host.startswith("executor:"):
        _logger.info(
            "Run '%s' em '%s' não tem executor associado — nada a interromper.",
            run_id, run.status,
        )
        return "already_finished"

    executor_id = host[len("executor:"):]

    # The server dispatches with job_id == task_id (see dispatch above), so the
    # executor locates the job by the same identifier.
    sent = await executor_registry.send_json(executor_id, {
        "type":   "cancel",
        "job_id": run_id,
    })
    if not sent:
        # `send_json` also returns False with the executor ALIVE: missing signing
        # key, relay with no listener during a restart, Redis with an
        # error. Closing in those cases would yield "cancelled" with the job running — and an
        # old executor, without inventory, would carry it to the end. Only a PROVEN
        # absence of presence closes here; the rest stays a 503.
        if await executor_registry.presence_or_unknown(executor_id) is not False:
            raise NoExecutorAvailableError(
                "Não foi possível pedir o cancelamento ao executor agora — tente de novo."
            )
        # Executor down: before, it was a 503 ("não foi possível cancelar", could not cancel) and the
        # run stayed "Em andamento" (in progress) with no way at all to be cleaned up from the screen —
        # precisely the lost run the user was trying to get out of the way. Closes
        # here, conditionally (a job_result that arrives midway wins). If the
        # executor comes back still running the job, its inventory tells it to stop
        # (see `_stop_zombies`) and the late result is refused by idempotency.
        if await _close_offline_run(db, run):
            _logger.info(
                "Run '%s' cancelado no servidor: executor '%s' fora do ar.", run_id, executor_id,
            )
            return "cancelled"
        await db.refresh(run)
        return "already_finished"

    _logger.info("Cancelamento do run '%s' solicitado ao executor '%s'.", run_id, executor_id)
    return "requested"


async def _close_offline_run(db: AsyncSession, run: WorkflowRun) -> bool:
    """Closes as 'cancelled' a run whose executor is down. Returns whether it
    won.

    Conditional on 'pending'/'running', for the same reason as
    `_close_unassigned_run`: a job_result that arrives between the read and this
    UPDATE has already closed the run with the real outcome, and it cannot be overwritten.
    """
    return bool(await fechar_runs(
        db, [run], de=OPEN_STATUSES, para="cancelled",
        mensagem="Cancelada com o executor fora do ar — a execução foi encerrada no servidor.",
        categoria=None,
    ))
