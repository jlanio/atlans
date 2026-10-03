# flow/nodes/control/change_detector.py
"""
ChangeDetector — a fork that compares the input with the last run.

Computes a deterministic SHA-256 of the current input, atomically swaps it with
the previous run's hash in the server's Redis, compares, and forks:

- `true`  (labeled "Mudou")     → branch executed when the input CHANGED
                                    or it's the first run (configurable).
- `false` (labeled "Sem mudança") → branch executed when the input is
                                    IDENTICAL to the last run.

Where the hash lives
----------------
Redis on the server — key `change_detector:{wf|ws}:{scope_id}:{ident}`.

How the executor accesses it
--------------------
ONE HTTP call: `POST /internal/change-detector/{key}` writes the current hash and
returns the previous one in the same operation (atomic SET ... GET in Redis). Half
the latency of the old GET+PUT pair and, more importantly, without the race in
which two simultaneous runs of the same workflow read the same old hash and BOTH
decided "Mudou". Authenticated via mTLS (client cert + `X-Forwarded-Tls-Client-Cert-Info`);
the executor has no access to the server's Redis.

Behavior on failure
----------------------
Configurable via `on_backend_error`:
- `mudou` (default) — fail-closed: recomputes what it would have recomputed
  anyway before the feature existed. Never treats as `unchanged` by mistake.
- `sem_mudanca` — for workflows with an expensive/irreversible side effect downstream
  of the "Mudou" branch (email, publishing): an infra blip triggers nothing.
- `falhar` — the run fails visibly instead of deciding blindly.

The `reason` output says WHY the branch came out the way it did:
`mudou | sem_mudanca | primeira_execucao | backend_indisponivel | tipo_nao_hashavel`.

State hygiene
-----------------
Deleting the workflow clears the `wf:*` keys; deleting the workspace also clears the
`ws:*` ones (workflow_service). Removing only the NODE from the canvas leaves the key
orphaned until the TTL expires (default 168h) — deliberate: tracking definition diffs
on every save doesn't pay off for a cache that expires on its own.

Fork convention
-----------------------
Follows exactly the pattern of `Conditional` (flow/nodes/control/conditional.py):
output `{"branch": bool, ...}`, edges with `condition: bool`. The executor
filters `active_edges` by `condition == branch` and propagates skip to the losing
branch via `_propagate_skip` — zero new code in the execution pipeline.
"""
import datetime as _dt
import hashlib
import json
import re
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from typing import Any, Dict, Iterable
from uuid import UUID

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.logger import get_logger
from flow.utils.parameter_validation import requested_columns

logger = get_logger(__name__)

_CHANGE_DETECTOR_PATH = "/internal/change-detector"

# Formato esperado de um hash gravado: SHA-256 hex lowercase (64 chars).
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ChangeDetectorTypeError(TypeError):
    """Input type has no stable canonicalization — convert it before the node.

    Raised when the input contains an object with no deterministic representation
    (e.g.: an instance of a custom class whose repr() includes the heap id(), which
    changes on every run). Hashing that would produce a false 'mudou' on every run.
    """


# ── Deterministic hash of the input ──────────────────────────────────────────

def _stable_hash(
    value: Any,
    fields_filter: Iterable[str] | None = None,
    ignore_paths: Iterable[str] | None = None,
) -> str:
    """Lowercase hex SHA-256 of any input, after recursive canonicalization.

    Canonicalization ensures that two semantically equal inputs produce the
    same hash (e.g.: a dict with keys in a different order, a float with precision
    noise, a DataFrame with the same rows in a different order).

    `ignore_paths` removes fields BEFORE the hash — dotted paths descend into
    nested dicts and into lists of dicts, and the last segment also removes a
    DataFrame column. It's the way to ignore volatile timestamps without listing
    all the other fields (which is what `fields_filter`, an inclusion filter, requires).

    Raises ChangeDetectorTypeError if the input contains a type without stable
    canonicalization — better to fail clearly than to silently produce an unstable hash.
    """
    value = _apply_ignored(value, list(ignore_paths) if ignore_paths else None)
    canonical = _canonicalize(value, list(fields_filter) if fields_filter else None)
    if isinstance(canonical, bytes):
        return hashlib.sha256(canonical).hexdigest()
    # No default= : every type is handled in _canonicalize or raises an error there.
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _e_dataframe(value: Any) -> bool:
    import pandas as pd  # type: ignore
    return isinstance(value, pd.DataFrame)


def _apply_ignored(value: Any, ignore_paths: list[str] | None) -> Any:
    if not ignore_paths:
        return value
    for raw in ignore_paths:
        segmentos = [s for s in raw.split(".") if s]
        if segmentos:
            value = _without_path(value, segmentos)
    return value


def _without_path(value: Any, path: list[str]) -> Any:
    """Removes a dotted path without MUTATING the user's input.

    Copies only along the affected path; untouched branches are
    shared. A list applies the same path to each item (the
    `items.timestamp` case in a list of records). In a DataFrame the final
    segment is a column name — `drop(errors="ignore")`, because a missing
    column is not an error, it's an input that is already as the filter wants it.
    """
    if not path:
        return value
    head, resto = path[0], path[1:]

    if _e_dataframe(value):
        if resto:
            return value  # a column is a leaf; a deeper path doesn't apply
        return value.drop(columns=[head], errors="ignore")

    if isinstance(value, dict):
        if head not in value:
            return value
        novo = dict(value)
        if resto:
            novo[head] = _without_path(value[head], resto)
        else:
            novo.pop(head)
        return novo

    if isinstance(value, (list, tuple)):
        return [_without_path(item, path) for item in value]

    return value


def _canonicalize(value: Any, fields_filter: list[str] | None) -> Any:
    """Reduces value to a stable JSON-serializable form."""
    # 1. None / bool / int / str — primitivos passam direto.
    if value is None or isinstance(value, (bool, int, str)):
        return value

    # 2. Float — normalizes precision to avoid 0.1+0.2 != 0.3.
    if isinstance(value, float):
        if value != value:  # NaN
            return "__NaN__"
        if value == float("inf"):
            return "__inf__"
        if value == float("-inf"):
            return "__-inf__"
        # 12 decimal places: geographic resolution < 0.1mm in any typical projection.
        return round(value, 12)

    # 3. Bytes — prefixo discrimina de string ("abc" != b"abc").
    if isinstance(value, bytes):
        return b"\x00bytes\x00" + value

    # 3b. Common types with a deterministic canonical representation.
    # datetime/date/time → isoformat; an Enum subclass must come before
    # int/str (but primitives already left above — a plain Enum lands here).
    if isinstance(value, Enum):
        return {"__enum__": f"{type(value).__module__}.{type(value).__name__}",
                "name": value.name,
                "value": _canonicalize(value.value, None)}
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return {"__dt__": value.isoformat()}
    if isinstance(value, _dt.timedelta):
        return {"__td__": round(value.total_seconds(), 12)}
    if isinstance(value, UUID):
        return {"__uuid__": str(value)}
    if isinstance(value, PurePath):
        return {"__path__": value.as_posix()}
    if isinstance(value, Decimal):
        # str() preserves exact precision (unlike float()).
        return {"__decimal__": str(value)}

    # 4. GeoDataFrame — incremental hash (doesn't materialize GBs of WKB).
    import geopandas as gpd  # type: ignore
    if isinstance(value, gpd.GeoDataFrame):
        return _hash_geodataframe(value)

    # 5. Plain DataFrame — pandas.util.hash_pandas_object is vectorized.
    import pandas as pd  # type: ignore
    if isinstance(value, pd.DataFrame):
        return _hash_dataframe(value)
    if isinstance(value, pd.Series):
        return _hash_dataframe(value.to_frame())

    # 6. dict — sorts by key; the optional filter applies ONLY at the root.
    if isinstance(value, dict):
        if fields_filter:
            items = [(k, value[k]) for k in fields_filter if k in value]
        else:
            items = list(value.items())
        return {k: _canonicalize(v, None) for k, v in sorted(items, key=lambda x: x[0])}

    # 7. list/tuple preservam ordem; set ordena por str(item).
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item, None) for item in value]
    if isinstance(value, set):
        return sorted([_canonicalize(item, None) for item in value], key=str)

    # 8. Type without stable canonicalization → fail-fast. repr()/str() of custom
    # objects usually includes the heap id(), which changes on every run and would
    # produce a false "mudou". Better to fail clearly: the workflow should convert the
    # object to dict/list/primitives before passing it to ChangeDetector.
    type_path = f"{type(value).__module__}.{type(value).__name__}"
    raise ChangeDetectorTypeError(
        f"ChangeDetector: tipo '{type_path}' nao tem canonizacao estavel. "
        f"Converta para dict/list/primitivos (ou datetime/UUID/Decimal/Path) "
        f"antes do node — hashear este tipo produziria 'mudou' falso a cada run."
    )


def _soma_u64(hashes) -> int:
    """Modular 2^64 sum of the row hashes — an order-insensitive aggregator.

    Replaces v1's XOR: `h ^ h == 0`, so any PAIR of identical rows canceled
    out and swapping {x, x} for {y, y} passed as "sem mudança" (n_rows,
    cols and dtypes equal, xor equal). With the sum, duplicates contribute 2h — the
    swap would only go unnoticed in a 64-bit collision.
    """
    import numpy as np  # type: ignore
    return int(np.asarray(hashes, dtype="uint64").sum(dtype="uint64"))


def _hash_dataframe(df) -> dict:
    """Compact DataFrame signature — vectorized in C, doesn't materialize.

    Version 2: the aggregator is a modular sum (see _soma_u64). Insensitive to row
    order on purpose — parallel queries may reorder between runs without
    that being a "real change". The version bump invalidates all v1 hashes once
    after the deploy (a spurious "Mudou", once per workflow).
    """
    import pandas as pd  # type: ignore
    row_hashes = pd.util.hash_pandas_object(df, index=False)
    return {
        "__df__": 2,
        "n_rows": int(len(df)),
        "cols":   sorted(df.columns.tolist()),
        "dtypes": [str(d) for d in df.dtypes.sort_index()],
        "soma":   _soma_u64(row_hashes.astype("uint64").values),
    }


def _hash_geodataframe(gdf) -> dict:
    """Assinatura compacta de GeoDataFrame — geometria + atributos (v2, soma)."""
    import pandas as pd  # type: ignore
    geom_col = gdf.geometry.name
    # Geometria: WKB hex compacto. None vira "" (NULL geometry).
    geom_hex = gdf.geometry.apply(lambda g: g.wkb_hex if g is not None else "")
    geom_soma = _soma_u64(
        pd.util.hash_pandas_object(geom_hex, index=False).astype("uint64").values
    )
    attrs = gdf.drop(columns=[geom_col])
    attrs_soma = 0
    if not attrs.empty:
        attrs_soma = _soma_u64(
            pd.util.hash_pandas_object(attrs, index=False).astype("uint64").values
        )
    return {
        "__gdf__":    2,
        "crs":        str(gdf.crs) if gdf.crs else None,
        "n_rows":     int(len(gdf)),
        "cols":       sorted(attrs.columns.tolist()),
        "dtypes":     [str(d) for d in attrs.dtypes.sort_index()],
        "geom_soma":  geom_soma,
        "attrs_soma": attrs_soma,
    }


# ── Backend bridge: swaps the hash in Redis via REST (one operation) ────────

def _validate_hash(raw: str | None, key: str) -> str | None:
    """Accepts only hex SHA-256 (64 chars). A corrupted value becomes None (= first run).

    Protects against corruption in Redis or a key collision that captures a value
    of another format — without it, the comparison would fail silently and the node
    would decide wrong.
    """
    if raw is None:
        return None
    candidate = raw.strip().lower()
    if _HASH_RE.match(candidate):
        return candidate
    logger.warning(
        "ChangeDetector: hash anterior invalido para key=%s (len=%d) — tratando como primeira execucao.",
        key, len(raw),
    )
    return None


async def _swap_hash(key: str, hash_value: str, ttl_seconds: int) -> str | None:
    """Writes `hash_value` for `key` and returns the PREVIOUS hash (None = first).

    One atomic operation on the server (Redis SET ... GET): decision and write
    in the same round trip, without the window in which two simultaneous runs read
    the same old value and both decided "Mudou". ttl_seconds=0 = no expiration.
    """
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import async_request_with_retry
    base_url, headers, verify = get_agent_http_config()
    resp = await async_request_with_retry(
        "POST",
        f"{base_url}{_CHANGE_DETECTOR_PATH}/{key}",
        client_kwargs={"verify": verify, "timeout": 10},
        json={"hash": hash_value, "ttl_seconds": ttl_seconds},
        headers=headers,
        follow_redirects=True,
        label=f"change-detector SWAP {key}",
    )
    if resp.status_code != 200:
        # Persistent 503/5xx after retry = backend unavailable. Propagates; the
        # node decides according to `on_backend_error`.
        resp.raise_for_status()
    return _validate_hash(resp.json().get("previous_hash"), key)


# ── Node ─────────────────────────────────────────────────────────────────────

@register_node
class ChangeDetector(BaseNode):

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name":        "ChangeDetector",
            "alias":       "ChangeDetector",
            "type":        "control",
            "description":
                "Compara o input com a última execução. Bifurca em 'Mudou' "
                "(mudou ou primeira vez) ou 'Sem mudança' (igual).",
            "properties": [
                {
                    "name":    "scope",
                    "label":   "Escopo do hash",
                    "type":    "select",
                    "default": "workflow",
                    "options": [
                        {"value": "workflow",  "label": "Por workflow (default)"},
                        {"value": "workspace", "label": "Compartilhado pelo workspace"},
                    ],
                },
                {
                    "name":    "shared_key",
                    "label":   "Chave compartilhada (escopo workspace)",
                    "type":    "string",
                    "default": "",
                    "description":
                        "Identificador para coordenar entre workflows do mesmo "
                        "workspace. Vazio = isolamento por instância de node.",
                },
                {
                    "name":    "fields",
                    "label":   "Campos a hashar (inclusão)",
                    "type":    "chips",
                    # The node declares no ports (it accepts whatever is connected, and with
                    # several inputs it hashes all of them): '*' is the only suggestion
                    # that makes sense — the columns that arrived, wherever they came from.
                    "suggest_columns": "*",
                    # Default "" (and not []) on purpose: an executor with an OLDER
                    # flow/ still validates this field as type "string" — a
                    # list in the default brought down the whole run just because the
                    # workflow had been saved in the new UI. "" passes there and the
                    # new parser reads "" -> [].
                    "default": "",
                    "description":
                        "Lista de campos do input dict a considerar — só a raiz. "
                        "Vazio = todo o input. Para IGNORAR poucos campos, "
                        "prefira 'Campos a ignorar'.",
                },
                {
                    "name":    "ignore_fields",
                    "label":   "Campos a ignorar",
                    "type":    "chips",
                    "suggest_columns": "*",
                    # Default "" for the same version compat as the field above.
                    "default": "",
                    "description":
                        "Campos removidos antes do hash. Aceita caminho com "
                        "ponto (meta.updated_at), desce em listas de registros "
                        "e remove coluna de tabela (ex.: fetched_at). É o jeito "
                        "de ignorar timestamps voláteis sem listar o resto.",
                },
                {
                    "name":    "ttl_hours",
                    "label":   "Validade do hash (horas)",
                    "type":    "integer",
                    "default": 168,
                    "description":
                        "Após esse período sem novas execuções, hash expira e "
                        "a próxima run é 'Mudou'. 0 = sem TTL. "
                        "Recomendado: ≥ 2× o intervalo do schedule.",
                },
                {
                    "name":    "primeira_execucao",
                    "label":   "Primeira execução",
                    "type":    "select",
                    "default": "mudou",
                    "options": [
                        {"value": "mudou",       "label": "Tratar como 'Mudou' (default)"},
                        {"value": "sem_mudanca", "label": "Só registrar o baseline (silenciosa)"},
                    ],
                    "description":
                        "Sem hash anterior não há comparação. 'Silenciosa' grava "
                        "o baseline sem disparar o branch 'Mudou' — útil quando "
                        "ele alerta alguém.",
                },
                {
                    "name":    "on_backend_error",
                    "label":   "Em erro de backend",
                    "type":    "select",
                    "default": "mudou",
                    "options": [
                        {"value": "mudou",       "label": "Tratar como 'Mudou' (default)"},
                        {"value": "sem_mudanca", "label": "Tratar como 'Sem mudança'"},
                        {"value": "falhar",      "label": "Falhar a execução"},
                    ],
                    "description":
                        "O que fazer se o armazenamento de estado estiver fora. "
                        "'Mudou' recomputa (seguro p/ fluxo barato); 'Sem "
                        "mudança' evita disparar efeito caro à toa; 'Falhar' "
                        "torna o problema visível.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "object", "description": "Input original (passa adiante)"},
                {"name": "previous_hash", "type": "string", "description": "Hash anterior (null na primeira execução)"},
                {"name": "current_hash", "type": "string", "description": "Hash da execução atual"},
                {"name": "branch", "type": "boolean", "description": "True=Mudou, False=Sem mudança (lido pelo executor)"},
                {"name": "reason", "type": "string", "description": "Por que o branch saiu assim: mudou | sem_mudanca | primeira_execucao | backend_indisponivel | tipo_nao_hashavel"},
            ],
            "branches": True,
        }

    def _ttl_hours(self) -> int:
        """TTL in hours, tolerant of a cleared/unreadable field — falls back to the default 168.

        `get_param_int` raises ValueError for ""/None, and bringing down the run
        because the user cleared an optional field is a disproportionate punishment.
        """
        try:
            return max(self.get_param_int("ttl_hours", 168), 0)
        except ValueError:
            logger.warning(
                "ChangeDetector(%s): ttl_hours ilegível (%r) — usando o default de 168h.",
                self.node_id, self.parameters.get("ttl_hours"),
            )
            return 168

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        scope          = self.get_param("scope", "workflow") or "workflow"
        shared_key_raw = self.get_param("shared_key", "") or ""
        primeira       = (self.get_param("primeira_execucao", "mudou") or "mudou").strip().lower()
        on_error        = (self.get_param("on_backend_error", "mudou") or "mudou").strip().lower()
        ttl_hours      = self._ttl_hours()

        # Chips fields: accept a list, a JSON string (what the screen writes) and the
        # CSV of old definitions.
        fields_filter = requested_columns(self.get_param("fields", [])) or None
        ignore_paths  = requested_columns(self.get_param("ignore_fields", [])) or None

        node_id = self.node_id

        # One input: hashes its payload (project convention). More than
        # one: ALL of them go in, sorted by name — silently discarding the others
        # (old behavior) hid a real change from whoever connected
        # two sources to the detector.
        if len(inputs) > 1:
            logger.info(
                "ChangeDetector(%s): %d entradas ligadas — todas entram no hash, ordenadas por nome.",
                node_id, len(inputs),
            )
            data: Any = {k: inputs[k] for k in sorted(inputs)}
        else:
            data = next(iter(inputs.values())) if inputs else None

        def _resultado(branch: bool, prev, cur, reason: str) -> Dict[str, Any]:
            # `output` FIRST, `branch` after. The fork edge is created
            # without `from_key`, so the executor spreads this dict into the next node
            # and whoever reads `next(iter(inputs.values()))` got the boolean instead
            # of the data this node exists to pass along.
            return {
                "output":        data,
                "previous_hash": prev,
                "current_hash":  cur,
                "reason":        reason,
                "branch":        branch,
            }

        # Computes the hash. A type without stable canonicalization (ChangeDetectorTypeError)
        # or any unexpected failure → fail-safe (branch=True), with a clear error
        # in the log for the operator to convert the input before the node.
        try:
            current_hash = _stable_hash(data, fields_filter, ignore_paths)
        except ChangeDetectorTypeError as exc:
            logger.error("ChangeDetector(%s): input nao hashable — %s", node_id, exc)
            return _resultado(True, None, None, "tipo_nao_hashavel")

        # Monta a chave conforme o escopo.
        workflow_hash = self._workflow_hash or "unknown"
        workspace_id  = self._workspace_id or "global"

        if scope == "workspace":
            ident = shared_key_raw.strip() or node_id
            # workspace_id missing in a legacy workflow → fall back to workflow
            # with a warning, keeping the feature functional.
            if workspace_id == "global":
                logger.warning(
                    "ChangeDetector(%s): workspace_id ausente, fallback para escopo 'workflow'",
                    node_id,
                )
                key = f"wf:{workflow_hash}:{node_id}"
            else:
                key = f"ws:{workspace_id}:{ident}"
        else:  # "workflow"
            key = f"wf:{workflow_hash}:{node_id}"

        # Swaps the hash (writes the current one, receives the previous) in a single operation.
        # Writing even on "sem mudança" is deliberate: it refreshes the TTL — an active
        # workflow never has its hash expire while it runs regularly.
        ttl_seconds = ttl_hours * 3600
        try:
            previous_hash = await _swap_hash(key, current_hash, ttl_seconds)
        except Exception as exc:
            if on_error == "falhar":
                raise RuntimeError(
                    f"ChangeDetector({node_id}): backend de estado indisponível "
                    f"({exc}). 'Em erro de backend' está configurado como 'Falhar'."
                ) from exc
            branch = on_error != "sem_mudanca"
            logger.error(
                "ChangeDetector(%s): falha ao trocar hash (%s) — decidindo branch=%s por política '%s'.",
                node_id, exc, branch, on_error,
            )
            return _resultado(branch, None, current_hash, "backend_indisponivel")

        if previous_hash is None:
            changed = primeira != "sem_mudanca"
            reason = "primeira_execucao"
        elif previous_hash != current_hash:
            changed, reason = True, "mudou"
        else:
            changed, reason = False, "sem_mudanca"

        logger.info(
            "ChangeDetector(%s): scope=%s key=%s changed=%s reason=%s (prev=%s current=%s)",
            node_id, scope, key, changed, reason,
            (previous_hash or "")[:8] + "..." if previous_hash else "null",
            current_hash[:8] + "...",
        )

        return _resultado(changed, previous_hash, current_hash, reason)
