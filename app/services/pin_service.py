# app/services/pin_service.py
"""
Pins — freezing a node's output so the next run reuses it.

All of the logic was born inside three routes of `workflows_router.py` and stayed
there, with no service and no test at all. Now there are two callers: the screen and
the MCP server, which goes through no request at all. Copying the rules into the second
transport would duplicate the unpin order, the expiration parsing, the output-node
gate and the read that crosses `pinned_outputs` with `pin_metadata` — and the
first time one of them changed, the two would answer different things.

The caller has already resolved WHO is asking (role and workspace); here we resolve WHAT
to do. It is the same boundary as `app/services/artifact_service.py`.

## The two columns, which do not say the same thing

`pin_metadata[nid]` is the INTENT: someone asked for the pin, when, and until when.
`pinned_outputs[nid]` is the MATERIALIZATION: `{}` while the cache does not exist, and
`{"__pin_s3_key__": …}` after a run has written the object.

Each one has a different writer, and that is what makes the distinction hold:
the intent is only born here, by explicit request; the materialization is written by the
run-result consumer (`run_result_consumer._persist_pinned_outputs_if_present`).
A node with intent and no cache is a pin that is still going to happen — and that is
exactly the question "why does my workflow keep recomputing".

## Who honors the TTL

The executor, and it **deliberately does not clear the reference** when the pin expires
(contract pinned in `tests/unit/test_pin_ciclo_de_vida.py`). That is why `expired`
here is informational: this module reports, it does not act. An automatic cleanup of
expired pins would break that contract.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact

logger = get_logger(__name__)

# TTL ceiling: one year. The value itself is arbitrary; what is not arbitrary is
# that a ceiling exists — without it, `timedelta(hours=…)` with a large integer raises
# `OverflowError` and the route returns 500 for an input the schema accepted.
TTL_MAXIMO_HORAS = 8760

# Node types whose output cannot be pinned. See `e_no_de_saida`.
TIPO_DE_SAIDA = "output"


# ── Leitura ──────────────────────────────────────────────────────────────────


def _instante(valor: Any) -> Optional[datetime]:
    """Reads an instant stored in `pin_metadata`, tolerating whatever shows up.

    Today's writer stores `utc_now_naive().isoformat()` — naive, with no
    suffix. But this field is JSON in a database that has seen other versions of
    the code, and a bare `fromisoformat` breaks in four distinct ways, all
    turning into a **500** on a read route:

    - `Z` suffix → `ValueError` in the 3.10 `fromisoformat` (the runtime before
      3.12);
    - offset (`+00:00`) → the value comes back aware, and comparing it with the
      naive one from `utc_now_naive()` raises `TypeError`;
    - non-string value (a number, a `null` that became `0`) → `TypeError`;
    - the entry itself not being a dict → `AttributeError` on `.get`.

    The recipe is the one from `artifacts_router._recusar_se_token_expirado`, which
    does this same computation correctly: it accepts `Z`, normalizes the timezone and,
    here, returns `None` for whatever does not parse — because in a LISTING "I cannot
    read this date" is no reason to bring down the whole response.
    """
    if not isinstance(valor, str) or not valor:
        return None
    try:
        lido = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normalizes to naive UTC, which is the contract of the project's columns and
    # what `utc_now_naive()` returns.
    if lido.tzinfo is not None:
        lido = lido.astimezone(timezone.utc).replace(tzinfo=None)
    return lido


def listar_pins(
    pin_metadata: Any,
    pinned_outputs: Any,
    *,
    node_ids_existentes: Optional[set[str]] = None,
) -> list[dict]:
    """A workflow's pins, with intent and materialization side by side.

    Pure function: it does not touch the database. The caller passes the two columns
    and, optionally, the set of nodes the definition still has.

    `node_ids_existentes=None` means "do not filter" — that is what REST does today.
    Passing the set, pins of deleted nodes disappear, which is the criterion the
    MCP's `get_workflow` already uses (`app/mcp/saida.py`).

    Walks the UNION of the two columns, not one of them. The two previous
    readers disagreed — the route iterated `pinned_outputs`, the MCP iterated
    `pin_metadata` — and each lost what only existed on the other side: a
    `pinned_outputs` entry without metadata (an auto-pin leftover, which the
    dispatch may still send to the executor) vanished from the MCP's view, and a
    recorded intent whose cache never materialized vanished from the screen's view.
    The union loses neither, and `cached` tells the cases apart.

    `expired` has THREE values, not two: `True`, `False` and `None`. `None` is
    "there is a stored date and I cannot read it" — which is not the same as
    "does not expire" (that is `expires_at: None`), and flattening both into `False`
    would hide corrupted data behind a reassuring answer.
    """
    metadata = pin_metadata if isinstance(pin_metadata, dict) else {}
    saidas = pinned_outputs if isinstance(pinned_outputs, dict) else {}
    agora = utc_now_naive()

    # `dict.fromkeys` to preserve insertion order and remove repetition —
    # the final ordering is by `node_id`, but the deterministic origin helps
    # when two keys collide after `str()`.
    todos = dict.fromkeys([*metadata.keys(), *saidas.keys()])

    pins: list[dict] = []
    for node_id in todos:
        nid = str(node_id)
        if node_ids_existentes is not None and nid not in node_ids_existentes:
            continue

        # The entry may not be a dict: `.get` on a loose value is AttributeError.
        bruto = metadata.get(node_id)
        meta = bruto if isinstance(bruto, dict) else {}
        expires_at = meta.get("expires_at")
        instante = _instante(expires_at)

        if not expires_at:
            expirado: Optional[bool] = False
        elif instante is None:
            expirado = None
        else:
            expirado = agora > instante

        ref = saidas.get(node_id)
        pins.append({
            "node_id": nid,
            "pinned_at": meta.get("pinned_at"),
            "expires_at": expires_at if isinstance(expires_at, str) else None,
            "ttl_hours": meta.get("ttl_hours") if isinstance(meta.get("ttl_hours"), int) else None,
            "expired": expirado,
            # "the cache already exists" — the answer to "why does it still recompute".
            "cached": isinstance(ref, dict) and bool(ref.get("__pin_s3_key__")),
        })

    pins.sort(key=lambda p: p["node_id"])
    return pins


# ── The output-node gate ─────────────────────────────────────────────────────


def e_no_de_saida(nome_do_no: Any) -> bool:
    """The node writes a file, and therefore cannot have its output pinned.

    Pinning the output of an output node creates a phantom artifact: the executor
    reuses the frozen value and **suppresses the write**, so the workflow
    "runs successfully" and the file it existed to produce does not appear.
    The pin stays there, looking like it is helping.

    Reads `NODE_REGISTRY` directly, and **not** `NodeService.list_nodes`, which filters
    out nodes disabled by the admin: a disabled output node is still an output
    node, and this gate cannot open because of a catalog decision.

    Unknown name → `False`. Refusing what is not recognized would turn
    every new node, or one from an earlier version of the registry, into a non-pinnable node.
    """
    if not isinstance(nome_do_no, str) or not nome_do_no:
        return False
    from flow.registry import NODE_REGISTRY

    classe = NODE_REGISTRY.get(nome_do_no)
    if classe is None:
        return False
    try:
        descricao = classe.description() or {}
    except Exception:  # noqa: BLE001 — a broken descriptor does not close the gate
        logger.warning("description() do nó '%s' levantou; portão de pin aberto.", nome_do_no)
        return False
    return descricao.get("type") == TIPO_DE_SAIDA


def nome_do_no_na_definition(definition: Any, node_id: str) -> Optional[str]:
    """The node's `name` (the registry key), read from the definition. `None` if absent."""
    if not isinstance(definition, dict):
        return None
    nos = definition.get("nodes")
    if not isinstance(nos, list):
        return None
    for no in nos:
        if isinstance(no, dict) and str(no.get("id")) == str(node_id):
            nome = no.get("name")
            return nome if isinstance(nome, str) else None
    return None


# ── Escrita ──────────────────────────────────────────────────────────────────


class PinEmNoDeSaidaError(ValueError):
    """Pin request on a node whose output is a written file."""


class NoInexistenteError(ValueError):
    """Pin request on a `node_id` the definition does not have."""


def _validar_ttl(ttl_hours: Optional[int]) -> Optional[int]:
    """`None` = no expiration. Otherwise, an integer within the range.

    `0` is refused on purpose rather than accepted: in the previous code it fell
    into the falsy branch and became "no expiration" — the opposite of what whoever
    types `0` is asking for, and silently. Whoever wants "no expiration" sends `null`.
    """
    if ttl_hours is None:
        return None
    if not isinstance(ttl_hours, int) or isinstance(ttl_hours, bool):
        raise ValueError("ttl_hours deve ser um número inteiro de horas ou nulo.")
    if ttl_hours < 1 or ttl_hours > TTL_MAXIMO_HORAS:
        raise ValueError(
            f"ttl_hours deve estar entre 1 e {TTL_MAXIMO_HORAS} horas "
            f"(um ano), ou nulo para não expirar."
        )
    return ttl_hours


async def fixar_saida(
    db: AsyncSession,
    wf,
    node_id: str,
    *,
    outputs: Optional[dict] = None,
    ttl_hours: Optional[int] = None,
    user_id: Optional[str] = None,
    exigir_no_existente: bool = True,
) -> dict:
    """Marks the node to have its output frozen starting with the next run.

    `outputs={}` (the default) is the normal case and the only one the MCP uses: it means
    "pin on the next run" — the node runs once and the auto-pin writes the cache. A
    dict with content is stored as it came, for parity with today's route,
    and the dispatch coerces it to `{}` anyway
    (`workflow_execution_service._safe_pinned_outputs`).

    `exigir_no_existente=False` exists so REST does not start refusing what it
    used to accept: pinning a `node_id` that is not in the definition is useless, but
    turning that into an error is a contract change on a route the screen uses.
    The MCP asks for the check; the route does not.
    """
    ttl = _validar_ttl(ttl_hours)

    nome = nome_do_no_na_definition(getattr(wf, "definition", None), node_id)
    if nome is None and exigir_no_existente:
        raise NoInexistenteError(f"O fluxo não tem nó com id '{node_id}'.")
    if e_no_de_saida(nome):
        raise PinEmNoDeSaidaError(
            f"O nó '{node_id}' ({nome}) grava um arquivo. Fixar a saída dele faria o "
            f"executor reaproveitar o valor congelado e PULAR a gravação — o fluxo "
            f"terminaria com sucesso e sem produzir o arquivo."
        )

    # Audit (SEG-10): NEVER store the client's `outputs`. Before, an `outputs`
    # with a forged `__pin_s3_key__` was persisted here and, on unpin, became a
    # delete of an object from ANOTHER workspace. The dispatch already coerces everything
    # to `{}` (`_safe_pinned_outputs`) and the real pin reference is only written by the
    # consumer (server-side, with prefix pin-cache/{workspace}/…). Storing `{}`
    # means "pin on the next run" with no forgery path at all.
    if outputs and any(isinstance(k, str) and k.startswith("__pin") for k in outputs):
        raise ValueError("outputs de pin nao pode conter chaves internas (__pin*).")
    pinned = dict(wf.pinned_outputs or {})
    pinned[node_id] = {}
    wf.pinned_outputs = pinned
    flag_modified(wf, "pinned_outputs")

    agora = utc_now_naive()
    meta = dict(wf.pin_metadata or {})
    entrada = {
        "pinned_at": agora.isoformat(),
        "ttl_hours": ttl,
        "expires_at": (agora + timedelta(hours=ttl)).isoformat() if ttl else None,
        "pinned_by": user_id,
    }
    meta[node_id] = entrada
    wf.pin_metadata = meta
    flag_modified(wf, "pin_metadata")

    await db.commit()
    return {
        "pinned": node_id,
        "total_pinned": len(pinned),
        "pinned_at": entrada["pinned_at"],
        "expires_at": entrada["expires_at"],
        "ttl_hours": ttl,
    }


async def _artefato_de_pin(db: AsyncSession, workflow_hash: str, node_id: str):
    """The node's pin-cache row, or `None`. The NEWEST, if there is more than one.

    It used to be `scalar_one_or_none()`, which raises `MultipleResultsFound` with two
    rows — and two rows are reachable: `artifacts` has no unique constraint
    on `(workflow_hash, node_id, is_pinned)` (`models/artifact.py`), and the
    consumer's `_upsert_pin_artifact` inserts when it finds nothing. Two runs of the
    same workflow finishing together find nothing, each inserts its own, and
    from then on every read raised.

    `ORDER BY id DESC LIMIT 1` instead of a unique index because the deploy does not run
    migrations and a `CREATE UNIQUE INDEX` would fail if the duplicate already exists in
    production. The index stays on record for after the data is clean.
    """
    resultado = await db.execute(
        select(Artifact)
        .where(
            Artifact.workflow_hash == workflow_hash,
            Artifact.node_id == node_id,
            Artifact.is_pinned.is_(True),
        )
        .order_by(Artifact.id.desc())
        .limit(1)
    )
    return resultado.scalar_one_or_none()


async def desfixar_saida(db: AsyncSession, wf, node_id: str) -> dict:
    """Unpins the node and deletes the cache object — in that order, on purpose.

    The order is this module's central decision, and it diverges from its sibling
    `artifacts_router`, which deletes from storage first with `delete_strict_async`
    and returns 502 on failure. Here it is the opposite, because the two failure modes
    do not weigh the same:

    - **orphan object in MinIO** (commit ok, storage failed): wasted
      bytes. The reconcile sweeps it, and nothing in the product breaks.
    - **dangling reference** (storage ok, commit failed): `pinned_outputs`
      still has a `__pin_s3_key__` pointing to an object that no longer
      exists. The executor asks for the object, does not find it, and the pin is broken
      **forever** — `_safe_pinned_outputs` only fires auto-pin with an empty ref, and
      nothing clears the ref on its own.

    So the database closes first and the storage afterwards. The storage failure becomes
    `storage_warning` in the response, not an exception: the pin is already gone, and
    answering with an error would make the client repeat an unpin that already happened.
    """
    pinned = dict(wf.pinned_outputs or {})
    estava = node_id in pinned
    ref = pinned.pop(node_id, None)
    wf.pinned_outputs = pinned or None
    flag_modified(wf, "pinned_outputs")

    meta = dict(wf.pin_metadata or {})
    tinha_meta = meta.pop(node_id, None) is not None
    wf.pin_metadata = meta or None
    flag_modified(wf, "pin_metadata")

    artefato = await _artefato_de_pin(db, wf.id_hash, node_id)
    # The two keys may diverge; deleting both is what leaves no object
    # behind. `dict.fromkeys` preserves order and removes repetition.
    #
    # Audit (SEG-10): only deletes keys INSIDE the workspace prefix of this
    # workflow. Legitimate keys are derived on the server as
    # `pin-cache/{workspace_id}/…`; any key outside that (an old forged
    # entry) is ignored, not deleted.
    prefixo = f"pin-cache/{wf.workspace_id}/"
    chaves = dict.fromkeys(
        k for k in (
            ref.get("__pin_s3_key__") if isinstance(ref, dict) else None,
            getattr(artefato, "s3_key", None),
        )
        if isinstance(k, str) and k.startswith(prefixo) and ".." not in k
    )
    if artefato is not None:
        await db.delete(artefato)

    await db.commit()

    aviso: Optional[str] = None
    if chaves:
        from app.core import storage as s3

        falhas = []
        for chave in chaves:
            try:
                await s3.delete_strict_async(chave, allow_missing=True)
            except Exception as exc:  # noqa: BLE001 — the pin is already gone; this is reporting
                logger.error(
                    "Unpin de %s/%s: objeto %s ficou no storage (%s). O pin já foi "
                    "removido; o reconcile recolhe o órfão.",
                    wf.id_hash, node_id, chave, exc,
                )
                falhas.append(chave)
        if falhas:
            aviso = (
                f"O pin foi removido, mas {len(falhas)} objeto(s) de cache não "
                f"puderam ser apagados do storage e serão recolhidos depois."
            )

    return {
        "unpinned": node_id,
        "outcome": "unpinned" if (estava or tinha_meta) else "not_pinned",
        "total_pinned": len(pinned),
        **({"storage_warning": aviso} if aviso else {}),
    }
