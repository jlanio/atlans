# app/mcp/tools/pins.py
"""
Pins: freezing a node's output for the next run to reuse.

This is what makes iterating on an expensive workflow cheap. Tweaking the final
node of a pipeline that starts with a forty-second query costs forty seconds
per attempt; with the query pinned, it costs the final node. An agent that edits
workflows without this tool pays for the whole workflow every round.

And, in the opposite direction, a forgotten pin makes the workflow return
**stale data without warning anyone** — the run finishes green, with
yesterday's result. That is why `list_pins` exists even for those who will
never pin anything: it is the only way for an agent to find out that the
answer it is reading was frozen.

Three decisions shape the module:

- **`pin_node_output` always sends `outputs={}`.** `{}` means "pin on the next
  run": the node runs once and the executor writes the cache. The tool has no
  way to fabricate a legitimate output payload — it has not seen the data —
  and the field is stored unfiltered on the other side, so leaving it open
  would let an agent inject arbitrary content into the execution cache of a
  production workflow. Dispatch coerces anything else to `{}` anyway
  (`workflow_execution_service._safe_pinned_outputs`).
- **Output nodes are refused.** Pinning the output of a node that writes a
  file makes the executor reuse the frozen value and SKIP the write: the
  workflow finishes successfully and the file does not show up. The pin sits
  there looking like it is helping. The rule holds for both transports — the
  REST route started refusing in the same diff, so there is no path left
  through which the phantom pin can get in.
- **`expired` is a report, not an action.** Whoever honors the TTL is the
  executor, and it deliberately does NOT clear the reference on expiry
  (contract pinned in `tests/unit/test_pin_ciclo_de_vida.py`). A tool that
  "cleaned up expired pins" would break that contract; this one reports and
  leaves the decision to the reader.
"""
from __future__ import annotations

from typing import Any, Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import exigir_papel
from app.core.rbac import ROLE_EDITOR, ROLE_VIEWER
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow
from app.mcp.saida import envelope
from app.mcp.tools.base import anotacoes, ferramenta
from app.services import pin_service

_MENSAGEM_PAPEL_LEITURA = "Requer papel 'viewer' ou superior neste workspace."
_MENSAGEM_PAPEL_ESCRITA = "Requer papel 'editor' ou superior neste workspace."


def _ids_dos_nos(definition: Any) -> set[str]:
    """The `id`s of the nodes the definition has now."""
    if not isinstance(definition, dict):
        return set()
    nos = definition.get("nodes")
    if not isinstance(nos, list):
        return set()
    return {str(no.get("id")) for no in nos if isinstance(no, dict) and no.get("id")}


# ── Leitura ──────────────────────────────────────────────────────────────────


@ferramenta
async def list_pins(ctx: Context, workflow_id: str) -> dict:
    """This workflow's nodes with frozen output.

    A pin makes the next run reuse the stored output instead of recomputing
    the node. Call this before concluding anything about a result: if the node
    that produced the data is pinned, what the run returned may be days old,
    and nothing in the run's response says so.

    Each item carries two states that are not the same thing:

    - `cached: false` — the pin was requested and the cache does not exist
      yet. The next run executes the node normally and stores it. It is the
      state right after `pin_node_output`.
    - `cached: true` — the cache exists, and it is what runs are using.

    `expired` says whether the deadline has passed, and is informational: the
    executor does **not** delete the cache on expiry. `expired: null` means a
    date is stored and could not be read — do not confuse it with "does not
    expire", which is `expires_at: null`.

    Pins of nodes already deleted from the definition do not appear here.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL_LEITURA)
        pins = pin_service.listar_pins(
            wf.pin_metadata,
            wf.pinned_outputs,
            node_ids_existentes=_ids_dos_nos(wf.definition),
        )
        id_do_fluxo = wf.id_hash

    return envelope({
        "workflow_id": id_do_fluxo,
        "items": pins,
        "total": len(pins),
        "cached_count": sum(1 for p in pins if p["cached"]),
    })


# ── Escrita ──────────────────────────────────────────────────────────────────


@ferramenta
async def pin_node_output(
    ctx: Context, workflow_id: str, node_id: str, ttl_hours: Optional[int] = None
) -> dict:
    """Freezes a node's output starting from the next run.

    The node runs one more time and its result is stored; from the following
    run onwards, the workflow reuses that result instead of recomputing. It is
    for iterating on the final part of an expensive workflow without repeating
    the expensive part.

    `ttl_hours` goes from 1 to 8760 (one year); if omitted, the pin does not
    expire. When the deadline passes the executor does **not** delete the
    cache on its own — the deadline is there for `list_pins` to warn that the
    data is stale, and unpinning is the reader's decision. Do not pass `0`: it
    is refused, because "zero hours of validity" and "no expiry" are opposite
    requests.

    You cannot choose WHICH value to freeze, on purpose: the run is what
    stores it. And nodes that produce files (output, map publishing, e-mail,
    webhook response) are refused — freezing their output would make the
    executor skip the write, and the workflow would finish green without
    producing anything.

    After pinning, run the workflow once for the cache to exist: until then
    `list_pins` shows `cached: false` and nothing is reused.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash
        try:
            resultado = await pin_service.fixar_saida(
                db, wf, node_id,
                # Always `{}`: see the module header.
                outputs={},
                ttl_hours=ttl_hours,
                user_id=escopo.user_id,
                exigir_no_existente=True,
            )
        except pin_service.NoInexistenteError as exc:
            raise erro(
                "not_found",
                str(exc),
                "use get_workflow(workflow_id) para ver os ids dos nós",
            )
        except pin_service.PinEmNoDeSaidaError as exc:
            raise erro(
                "validation",
                str(exc),
                "fixe o nó que ALIMENTA a saída, não o de saída em si",
            )
        except ValueError as exc:
            # `_validar_ttl` — range or type.
            raise erro("validation", str(exc), "ttl_hours de 1 a 8760, ou omitido")

    return envelope({
        "workflow_id": id_do_fluxo,
        "node_id": node_id,
        "pinned_at": resultado["pinned_at"],
        "expires_at": resultado["expires_at"],
        "ttl_hours": resultado["ttl_hours"],
        "total_pinned": resultado["total_pinned"],
        # The state right after pinning is ALWAYS this one, and saying so avoids
        # the wrong conclusion that the pin is already in effect.
        "cached": False,
        "hint": (
            "o cache ainda não existe: rode o fluxo uma vez para o nó gravar a "
            "saída; até lá cada execução recalcula normalmente"
        ),
    })


@ferramenta
async def unpin_node_output(ctx: Context, workflow_id: str, node_id: str) -> dict:
    """Unfreezes a node's output and deletes its cache.

    From the next run on, the node really runs again. Use this when the
    frozen data has gone stale, when the workflow changed so that the stored
    value no longer matches, or when finishing the editing round that
    motivated the pin — leaving a pin behind makes the workflow return old
    data with no signal at all.

    `outcome` distinguishes the two outcomes: `unpinned` (there was a pin and
    it was removed) and `not_pinned` (there was nothing). Neither is an error.

    If the cache cannot be deleted from storage, the pin is removed **anyway**
    and the response carries `storage_warning`: the leftover object is
    collected later, and what must not happen is the workflow still pointing
    at a cache that no longer exists.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash
        resultado = await pin_service.desfixar_saida(db, wf, node_id)

    aviso = resultado.get("storage_warning")
    return envelope({
        "workflow_id": id_do_fluxo,
        "node_id": node_id,
        "outcome": resultado["outcome"],
        "total_pinned": resultado["total_pinned"],
        # `envelope` only omits NULL keys, so the insertion is conditional: a
        # `storage_warning: None` at the top would make the reader look for a
        # problem that did not happen.
        **({"storage_warning": aviso} if aviso else {}),
    })


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_pins",
        title="Saídas congeladas",
        description=(
            "Os nós deste workflow com a saída congelada. Consulte antes de concluir "
            "qualquer coisa sobre um resultado: se o nó que produziu o dado está pinado, "
            "a execução devolveu cache, e nada na resposta dela diz isso."
        ),
        annotations=anotacoes("list_pins"),
    )(list_pins)

    server.tool(
        name="pin_node_output",
        title="Congelar a saída de um nó",
        description=(
            "Faz as próximas execuções reaproveitarem a saída de um nó em vez de "
            "recalculá-la — para iterar no fim de um fluxo caro sem repetir a parte cara. "
            "Nós que gravam arquivo são recusados: congelá-los faria o executor pular a "
            "gravação."
        ),
        annotations=anotacoes("pin_node_output"),
    )(pin_node_output)

    server.tool(
        name="unpin_node_output",
        title="Descongelar a saída de um nó",
        description=(
            "Remove o congelamento e apaga o cache: o nó volta a rodar de verdade na "
            "próxima execução. Responde outcome=not_pinned, sem erro, quando não havia pin."
        ),
        annotations=anotacoes("unpin_node_output"),
    )(unpin_node_output)
