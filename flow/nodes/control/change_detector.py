# flow/nodes/control/change_detector.py
"""
ChangeDetector — bifurcação que compara o input com a última execução.

Calcula um SHA-256 determinístico do input atual, troca-o atomicamente pelo
hash da execução anterior no Redis do servidor, compara, e bifurca:

- `true`  (rotulado "Mudou")     → branch executado quando o input MUDOU
                                    ou é a primeira execução (configurável).
- `false` (rotulado "Sem mudança") → branch executado quando o input é
                                    IDÊNTICO à última run.

Onde o hash vive
----------------
Redis no servidor — chave `change_detector:{wf|ws}:{scope_id}:{ident}`.

Como o executor acessa
--------------------
UMA chamada HTTP: `POST /internal/change-detector/{key}` grava o hash atual e
devolve o anterior na mesma operação (SET ... GET atômico no Redis). Metade da
latência do antigo par GET+PUT e, mais importante, sem a corrida em que duas
runs simultâneas do mesmo workflow liam o mesmo hash antigo e AMBAS decidiam
"Mudou". Autenticado por mTLS (cert client + `X-Forwarded-Tls-Client-Cert-Info`);
o executor não tem acesso ao Redis do servidor.

Comportamento em falha
----------------------
Configurável por `on_backend_error`:
- `mudou` (default) — fail-closed: recomputa o que recomputaria de qualquer
  jeito antes da feature existir. Nunca trata como `unchanged` por engano.
- `sem_mudanca` — para fluxos com efeito colateral caro/irreversível a jusante
  do branch "Mudou" (e-mail, publicação): um piscar de infra não dispara nada.
- `falhar` — a run erra visivelmente em vez de decidir às cegas.

O output `reason` diz POR QUE o branch saiu como saiu:
`mudou | sem_mudanca | primeira_execucao | backend_indisponivel | tipo_nao_hashavel`.

Higiene de estado
-----------------
Deletar o workflow limpa as chaves `wf:*`; deletar o workspace limpa também as
`ws:*` (workflow_service). Remover só o NÓ do canvas deixa a chave órfã até o
TTL vencer (default 168h) — deliberado: rastrear diffs de definição a cada save
não paga o custo de um cache que expira sozinho.

Convenção de bifurcação
-----------------------
Segue exatamente o padrão de `Conditional` (flow/nodes/control/conditional.py):
output `{"branch": bool, ...}`, edges com `condition: bool`. O executor
filtra `active_edges` por `condition == branch` e propaga skip ao branch
perdedor via `_propagate_skip` — zero código novo na pipeline de execução.
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
from flow.utils.parameter_validation import colunas_pedidas

logger = get_logger(__name__)

_CHANGE_DETECTOR_PATH = "/internal/change-detector"

# Formato esperado de um hash gravado: SHA-256 hex lowercase (64 chars).
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ChangeDetectorTypeError(TypeError):
    """Tipo do input nao tem canonizacao estavel — converter antes do node.

    Levantada quando o input contem um objeto sem representacao deterministica
    (ex: instancia de classe custom cujo repr() inclui o id() do heap, que muda
    a cada execucao). Hashear isso produziria 'mudou' falso em toda run.
    """


# ── Hash determinístico do input ─────────────────────────────────────────────

def _stable_hash(
    value: Any,
    fields_filter: Iterable[str] | None = None,
    ignore_paths: Iterable[str] | None = None,
) -> str:
    """SHA-256 hex lowercase de qualquer input, após canonização recursiva.

    A canonização garante que dois inputs semanticamente iguais produzam o
    mesmo hash (ex: dict com chaves em ordem diferente, float com ruído de
    precisão, DataFrame com mesmas linhas em ordem diferente).

    `ignore_paths` remove campos ANTES do hash — caminhos com ponto descem em
    dicts aninhados e em listas de dicts, e o último segmento também remove
    coluna de DataFrame. É o jeito de ignorar timestamps voláteis sem listar
    todos os outros campos (que é o que `fields_filter`, de inclusão, exige).

    Levanta ChangeDetectorTypeError se o input contiver um tipo sem canonização
    estável — melhor falhar claro do que gerar hash instável silenciosamente.
    """
    value = _aplicar_ignorados(value, list(ignore_paths) if ignore_paths else None)
    canonical = _canonicalize(value, list(fields_filter) if fields_filter else None)
    if isinstance(canonical, bytes):
        return hashlib.sha256(canonical).hexdigest()
    # Sem default= : todo tipo é tratado em _canonicalize ou levanta erro lá.
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _e_dataframe(value: Any) -> bool:
    import pandas as pd  # type: ignore
    return isinstance(value, pd.DataFrame)


def _aplicar_ignorados(value: Any, ignore_paths: list[str] | None) -> Any:
    if not ignore_paths:
        return value
    for raw in ignore_paths:
        segmentos = [s for s in raw.split(".") if s]
        if segmentos:
            value = _sem_caminho(value, segmentos)
    return value


def _sem_caminho(value: Any, path: list[str]) -> Any:
    """Remove um caminho pontilhado sem MUTAR o input do usuário.

    Copia apenas ao longo do caminho afetado; ramos intactos são
    compartilhados. Lista aplica o mesmo caminho a cada item (o caso
    `items.timestamp` numa lista de registros). Em DataFrame o segmento
    final é nome de coluna — `drop(errors="ignore")`, porque a coluna
    ausente não é erro, é um input que já está como o filtro quer.
    """
    if not path:
        return value
    head, resto = path[0], path[1:]

    if _e_dataframe(value):
        if resto:
            return value  # coluna é folha; caminho mais fundo não se aplica
        return value.drop(columns=[head], errors="ignore")

    if isinstance(value, dict):
        if head not in value:
            return value
        novo = dict(value)
        if resto:
            novo[head] = _sem_caminho(value[head], resto)
        else:
            novo.pop(head)
        return novo

    if isinstance(value, (list, tuple)):
        return [_sem_caminho(item, path) for item in value]

    return value


def _canonicalize(value: Any, fields_filter: list[str] | None) -> Any:
    """Reduz value a uma forma JSON-serializável estável."""
    # 1. None / bool / int / str — primitivos passam direto.
    if value is None or isinstance(value, (bool, int, str)):
        return value

    # 2. Float — normaliza precisão para evitar 0.1+0.2 != 0.3.
    if isinstance(value, float):
        if value != value:  # NaN
            return "__NaN__"
        if value == float("inf"):
            return "__inf__"
        if value == float("-inf"):
            return "__-inf__"
        # 12 casas: resolução geográfica < 0.1mm em qualquer projeção típica.
        return round(value, 12)

    # 3. Bytes — prefixo discrimina de string ("abc" != b"abc").
    if isinstance(value, bytes):
        return b"\x00bytes\x00" + value

    # 3b. Tipos comuns com representação canônica determinística.
    # datetime/date/time → isoformat; subclasse de Enum precisa vir antes de
    # int/str (mas primitivos já saíram acima — Enum puro cai aqui).
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
        # str() preserva precisão exata (ao contrário de float()).
        return {"__decimal__": str(value)}

    # 4. GeoDataFrame — hash incremental (não materializa GB de WKB).
    import geopandas as gpd  # type: ignore
    if isinstance(value, gpd.GeoDataFrame):
        return _hash_geodataframe(value)

    # 5. DataFrame puro — pandas.util.hash_pandas_object é vetorizado.
    import pandas as pd  # type: ignore
    if isinstance(value, pd.DataFrame):
        return _hash_dataframe(value)
    if isinstance(value, pd.Series):
        return _hash_dataframe(value.to_frame())

    # 6. dict — ordena por chave; filtro opcional aplica APENAS na raiz.
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

    # 8. Tipo sem canonização estável → fail-fast. repr()/str() de objetos
    # custom costuma incluir o id() do heap, que muda a cada run e produziria
    # "mudou" falso. Melhor falhar claro: o workflow deve converter o objeto
    # para dict/list/primitivos antes de passar ao ChangeDetector.
    type_path = f"{type(value).__module__}.{type(value).__name__}"
    raise ChangeDetectorTypeError(
        f"ChangeDetector: tipo '{type_path}' nao tem canonizacao estavel. "
        f"Converta para dict/list/primitivos (ou datetime/UUID/Decimal/Path) "
        f"antes do node — hashear este tipo produziria 'mudou' falso a cada run."
    )


def _soma_u64(hashes) -> int:
    """Soma modular 2^64 dos hashes de linha — agregador insensível à ordem.

    Substitui o XOR da v1: `h ^ h == 0`, então qualquer PAR de linhas idênticas
    se anulava e trocar {x, x} por {y, y} passava como "sem mudança" (n_rows,
    cols e dtypes iguais, xor igual). Na soma, duplicatas contribuem 2h — a
    troca só passaria despercebida numa colisão de 64 bits.
    """
    import numpy as np  # type: ignore
    return int(np.asarray(hashes, dtype="uint64").sum(dtype="uint64"))


def _hash_dataframe(df) -> dict:
    """Assinatura compacta de DataFrame — vetorizado em C, não materializa.

    Versão 2: agregador é soma modular (ver _soma_u64). Insensível à ordem das
    linhas de propósito — queries paralelas podem reordenar entre runs sem que
    isso seja "mudança real". O bump de versão invalida todos os hashes v1 uma
    única vez após o deploy ("Mudou" espúrio, uma vez por workflow).
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


# ── Backend bridge: troca o hash no Redis via REST (uma operação) ────────────

def _validate_hash(raw: str | None, key: str) -> str | None:
    """Aceita só SHA-256 hex (64 chars). Valor corrompido vira None (= primeira run).

    Protege contra corruption no Redis ou colisão de chave que capture um valor
    de outro formato — sem isso, a comparação falharia silenciosamente e o node
    decidiria errado.
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
    """Grava `hash_value` para `key` e devolve o hash ANTERIOR (None = primeira).

    Uma operação atômica no servidor (SET ... GET do Redis): decisão e gravação
    na mesma ida, sem a janela em que duas runs simultâneas liam o mesmo valor
    antigo e ambas decidiam "Mudou". ttl_seconds=0 = sem expiração.
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
        # 503/5xx persistente apos retry = backend indisponível. Propaga; o
        # node decide conforme `on_backend_error`.
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
                    # O nó não declara portas (aceita o que for ligado, e com
                    # várias entradas hasheia todas): '*' é a única sugestão
                    # que faz sentido — as colunas que chegaram, de onde vierem.
                    "suggest_columns": "*",
                    # Default "" (e não []) de propósito: um executor com flow/
                    # ANTERIOR ainda valida este campo como type "string" — uma
                    # lista no default derrubava a run inteira só por o
                    # workflow ter sido salvo na UI nova. "" passa lá e o
                    # parser novo lê "" -> [].
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
                    # Default "" pela mesma compat de versão do campo acima.
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

    def _ttl_horas(self) -> int:
        """TTL em horas, tolerante a campo limpo/ilegível — cai no default 168.

        `get_param_int` levanta ValueError para ""/None, e derrubar a run
        porque o usuário limpou um campo opcional é punição desproporcional.
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
        on_erro        = (self.get_param("on_backend_error", "mudou") or "mudou").strip().lower()
        ttl_hours      = self._ttl_horas()

        # Campos de fichas: aceitam lista, JSON-string (o que a tela grava) e o
        # CSV das definitions antigas.
        fields_filter = colunas_pedidas(self.get_param("fields", [])) or None
        ignore_paths  = colunas_pedidas(self.get_param("ignore_fields", [])) or None

        node_id = self.node_id

        # Uma entrada: hasheia o payload dela (convenção do projeto). Mais de
        # uma: TODAS entram, ordenadas por nome — descartar as demais em
        # silêncio (comportamento antigo) escondia mudança real de quem ligou
        # duas fontes no detector.
        if len(inputs) > 1:
            logger.info(
                "ChangeDetector(%s): %d entradas ligadas — todas entram no hash, ordenadas por nome.",
                node_id, len(inputs),
            )
            data: Any = {k: inputs[k] for k in sorted(inputs)}
        else:
            data = next(iter(inputs.values())) if inputs else None

        def _resultado(branch: bool, prev, cur, reason: str) -> Dict[str, Any]:
            # `output` PRIMEIRO, `branch` depois. A aresta de bifurcação nasce
            # sem `from_key`, então o executor espalha este dict no nó seguinte
            # e quem lê `next(iter(inputs.values()))` pegava o booleano em vez
            # do dado que este nó existe para deixar passar adiante.
            return {
                "output":        data,
                "previous_hash": prev,
                "current_hash":  cur,
                "reason":        reason,
                "branch":        branch,
            }

        # Calcula o hash. Tipo sem canonização estável (ChangeDetectorTypeError)
        # ou qualquer falha inesperada → fail-safe (branch=True), com erro claro
        # no log para o operador converter o input antes do node.
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
            # workspace_id ausente em workflow legado → fallback para workflow
            # com warning, mantendo a feature funcional.
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

        # Troca o hash (grava o atual, recebe o anterior) numa operação só.
        # Gravar mesmo em "sem mudança" é deliberado: refresh do TTL — workflow
        # ativo nunca tem o hash expirando enquanto roda regularmente.
        ttl_seconds = ttl_hours * 3600
        try:
            previous_hash = await _swap_hash(key, current_hash, ttl_seconds)
        except Exception as exc:
            if on_erro == "falhar":
                raise RuntimeError(
                    f"ChangeDetector({node_id}): backend de estado indisponível "
                    f"({exc}). 'Em erro de backend' está configurado como 'Falhar'."
                ) from exc
            branch = on_erro != "sem_mudanca"
            logger.error(
                "ChangeDetector(%s): falha ao trocar hash (%s) — decidindo branch=%s por política '%s'.",
                node_id, exc, branch, on_erro,
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
