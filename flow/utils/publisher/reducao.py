# flow/utils/publisher/reducao.py
"""
Reduction of a node_event that exceeded the WS protocol's byte ceiling.

A SINGLE rule for both sides of the wire: the executor applies it before sending
(`_dumps_event` in executor/connection.py) and the server re-applies it before
republishing to Redis (`_serialize_node_event` in
app/api/routers/executor_ws/resultados.py) — a defense against a buggy or
compromised executor, for which the executor's self-limiting is worth nothing.

There were two copies, and they diverged: the executor preserved `duration_ms` and
the stdout lines that fit, but threw away the whole `extra`; the server cut
only the heavy keys of `extra` and kept `output_columns`. With the same ceiling
on both sides, the executor delivered the event already reduced and the server's
rule never ran: a `completed` with a large traceback reached the panel without
the editor's column suggestion.

The ceiling and the field lists are part of the protocol. Server and executors are
updated at different times, and the event one side reduces the other must
accept as is.
"""
import json
from typing import Any, Callable

from flow.utils.publisher.events import KIND_STDOUT

# BYTE ceiling of a node_event (`json.dumps` escapes with ensure_ascii, so
# len(str) == bytes). Applies on both sides: on the executor, a `print()` of a
# large GeoJSON overflowed the WS frame and the server closed with 1009,
# bringing down the whole session; on the server, the run history has a ceiling
# on the NUMBER of events, not bytes, and the compose Redis has no maxmemory —
# an MB-sized event grew until the OOM-kill, taking dispatch, auth and the
# results consumer down with it.
#
# The stdout producer already closes the batch at ~24 KB of text (_STDOUT_FLUSH_BYTES
# in flow/nodes/action/python_script.py), so going past this is an exception.
NODE_EVENT_BYTES_CEILING = 64 * 1024

# Fields that survive until the last step — without them the event is useless to
# the panel. `type` is what routes the message on the server (which removes it
# before republishing, so there it is not even in the event); `duration_ms` is the
# node time the panel shows.
CONTROL_FIELDS = (
    "type", "run_id", "node", "status", "kind", "level", "timestamp", "duration_ms",
)

# Keys of `extra` that carry the event's weight: error stack, debug mode's
# inputs/outputs summary, batch of stdout lines and the schema drift diff
# (`extra` is built by flow/executor/events.py and
# flow/utils/publisher/events.py). `output_columns` is left OUT on purpose: it is
# what the editor uses to suggest column names.
HEAVY_EXTRA_KEYS = ("traceback", "debug_output", "lines", "schema_drift")

# Character ceiling for each preserved control field, so the reduced event
# itself cannot be large (nothing guarantees `node` is short — or
# even a string).
PER_FIELD_CEILING = 512

# Character ceiling for `error` in the first step.
ERROR_CEILING = 8 * 1024

_CUT_MARKER = "…[truncado]"


def shrink_node_event(
    evento: dict,
    payload: str,
    teto: int = NODE_EVENT_BYTES_CEILING,
    *,
    default: Callable[[Any], Any] | None = None,
) -> str:
    """JSON of the node_event reduced to at most `teto` bytes.

    `payload` is the JSON of the whole event, which the caller already serialized
    to measure; if it fits, it comes back as is. Otherwise the event steps down,
    each step measured serialized (never estimated), and the first that fits wins:

      1. Without the weight: what is in HEAVY_EXTRA_KEYS leaves `extra` and
         `error` is shortened; the rest stays — `extra.output_columns`,
         `duration_ms`, the error category.
      2. Only the CONTROL_FIELDS, coerced to short scalars: a value that is
         neither a string nor a scalar becomes a cut repr — otherwise the ceiling
         would be bypassed precisely through the path that enforces it.
      3. Safety net, if not even the coerced fields fit: the bare minimum to
         correlate the event. The ceiling is a guarantee, not an intention.

    In a stdout event the lines ARE the content: in steps 1 and 2 the
    longest prefix of `extra['lines']` that still fits comes back, with a marker of
    what was left out. Emptying `extra` showed the node's output tab empty, as if
    the script had printed nothing.

    The reduced event comes out marked with `__truncated__` and `__original_size__`.
    `default` is the one from `json.dumps`: the executor passes its own (Timestamp,
    numpy…); the server does not need to, its event came from JSON.
    """
    if len(payload) <= teto:
        return payload

    def _dumps(obj: dict) -> str:
        return json.dumps(obj, default=default)

    badges = {"__truncated__": True, "__original_size__": len(payload)}
    extra = evento.get("extra")
    linhas = extra.get("lines") if isinstance(extra, dict) else None
    if evento.get("kind") != KIND_STDOUT or not isinstance(linhas, list):
        linhas = []

    # Step 1 — only when there is something to cut: without a cut the candidate would
    # have the original's size and the dumps would be wasted.
    reduzido = dict(evento)
    was_cut = False
    if isinstance(extra, dict) and any(k in extra for k in HEAVY_EXTRA_KEYS):
        reduzido["extra"] = {
            k: v for k, v in extra.items() if k not in HEAVY_EXTRA_KEYS
        }
        was_cut = True
    erro = evento.get("error")
    if isinstance(erro, str) and len(erro) > ERROR_CEILING:
        reduzido["error"] = erro[:ERROR_CEILING] + _CUT_MARKER
        was_cut = True
    if was_cut:
        reduzido.update(badges)
        candidato = _dumps(reduzido)
        if len(candidato) <= teto:
            return _with_lines_that_fit(reduzido, linhas, teto, _dumps) or candidato

    # Degrau 2.
    minimo: dict = {}
    for campo in CONTROL_FIELDS:
        if campo not in evento:
            continue
        valor = evento[campo]
        if isinstance(valor, str):
            minimo[campo] = valor[:PER_FIELD_CEILING]
        elif valor is None or isinstance(valor, (bool, int, float)):
            minimo[campo] = valor
        else:
            minimo[campo] = repr(valor)[:PER_FIELD_CEILING]
    minimo.update(badges)
    resultado = _with_lines_that_fit(minimo, linhas, teto, _dumps) or json.dumps(minimo)
    if len(resultado) <= teto:
        return resultado

    # Degrau 3.
    seguro = {"type": str(evento["type"])[:64]} if "type" in evento else {}
    seguro.update({
        "run_id": str(evento.get("run_id", ""))[:PER_FIELD_CEILING],
        "node": str(evento.get("node", ""))[:PER_FIELD_CEILING],
        "status": str(evento.get("status", ""))[:64],
        **badges,
    })
    return json.dumps(seguro)


def _with_lines_that_fit(
    base: dict, linhas: list, teto: int, dumps: Callable[[dict], str],
) -> str | None:
    """`base` with the longest prefix of `linhas` that fits in the ceiling.

    None when there are no lines or when not even the cut marker fits.

    Cuts by BINARY SEARCH over the already serialized result, not by
    character estimate: `json.dumps` escapes with ensure_ascii, so a
    line of accents/emoji grows up to 6x and a budget counted in `len(str)`
    would blow the ceiling exactly in the case this branch exists to save. It is
    ~log2(n) serializations of a 64 KB payload — irrelevant on a path that
    only runs when the event is already exceptional.
    """
    if not linhas:
        return None
    extra_base = base.get("extra") if isinstance(base.get("extra"), dict) else {}

    def _serializar(quantas: int) -> str:
        corte = [linha if isinstance(linha, str) else str(linha) for linha in linhas[:quantas]]
        perdidas = len(linhas) - quantas
        if perdidas > 0:
            corte.append(f"[{perdidas} linha(s) desta rajada nao couberam no evento]")
        return dumps({**base, "extra": {**extra_base, "lines": corte}})

    if len(_serializar(0)) > teto:
        return None
    baixo, alto = 0, len(linhas)
    while baixo < alto:
        meio = (baixo + alto + 1) // 2
        if len(_serializar(meio)) <= teto:
            baixo = meio
        else:
            alto = meio - 1
    return _serializar(baixo)
