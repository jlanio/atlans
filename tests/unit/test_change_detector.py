# tests/unit/test_change_detector.py
"""Testes do node ChangeDetector — bifurcação por mudança de input.

Cobre:
  - Determinismo do _stable_hash (dict reordenado, float precision, sets)
  - Hash incremental de DataFrame/GeoDataFrame
  - Branching: primeira run, idêntico, mudou, fields filter
  - Fail-closed quando o backend de estado falha

O node fala com o servidor via /internal/change-detector (mTLS) — o executor nao
tem acesso ao Redis. Os testes de branching usam _FakeBackend, um duplo do
endpoint de SWAP (POST unico que grava o hash atual e devolve o anterior).
"""
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from flow.nodes.control.change_detector import (
    ChangeDetector,
    _stable_hash,
    _canonicalize,
)


# ── _stable_hash: determinismo ────────────────────────────────────────────────

def test_dict_chaves_em_ordem_diferente_mesmo_hash():
    a = {"foo": 1, "bar": 2}
    b = {"bar": 2, "foo": 1}
    assert _stable_hash(a) == _stable_hash(b)


def test_dict_aninhado_mesmo_hash():
    a = {"x": {"y": 1, "z": 2}}
    b = {"x": {"z": 2, "y": 1}}
    assert _stable_hash(a) == _stable_hash(b)


def test_dict_valor_diferente_hash_diferente():
    a = {"foo": 1}
    b = {"foo": 2}
    assert _stable_hash(a) != _stable_hash(b)


def test_float_precision_normalizado():
    # 0.1 + 0.2 == 0.30000000000000004 != 0.3 em float — round(x, 12) cobre.
    a = {"v": 0.1 + 0.2}
    b = {"v": 0.3}
    assert _stable_hash(a) == _stable_hash(b)


def test_nan_inf_estaveis():
    nan = float("nan")
    assert _stable_hash({"v": nan}) == _stable_hash({"v": float("nan")})
    assert _stable_hash({"v": float("inf")}) == _stable_hash({"v": float("inf")})


def test_bytes_diferente_de_string():
    assert _stable_hash(b"abc") != _stable_hash("abc")


def test_set_ordem_irrelevante():
    assert _stable_hash({1, 2, 3}) == _stable_hash({3, 1, 2})


def test_fields_filter_ignora_campos_volateis():
    base = {"feature_count": 150, "bbox": [10.0, 20.0]}
    com_timestamp = {**base, "queried_at": "2026-04-28T10:00:00Z"}
    # Sem filter, hashes são diferentes (timestamp muda).
    assert _stable_hash(base) != _stable_hash(com_timestamp)
    # Com filter incluindo só os campos estáveis, hashes são iguais.
    assert _stable_hash(base, ["feature_count", "bbox"]) == _stable_hash(
        com_timestamp, ["feature_count", "bbox"]
    )


def test_lista_ordem_importa():
    """Lista preserva ordem: [1,2,3] != [3,2,1]."""
    assert _stable_hash([1, 2, 3]) != _stable_hash([3, 2, 1])


def test_hash_eh_sha256_hex_64_chars():
    h = _stable_hash({"v": 1})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ── DataFrame ─────────────────────────────────────────────────────────────────

def test_dataframe_mesma_estrutura_mesmo_hash():
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df2 = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert _stable_hash(df1) == _stable_hash(df2)


def test_dataframe_linhas_em_ordem_diferente_mesmo_hash():
    """XOR cumulativo é insensível a ordem das linhas — desejado."""
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2, 3]})
    df2 = pd.DataFrame({"a": [3, 1, 2]})
    assert _stable_hash(df1) == _stable_hash(df2)


def test_dataframe_linha_diferente_hash_diferente():
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2, 3]})
    df2 = pd.DataFrame({"a": [1, 2, 4]})
    assert _stable_hash(df1) != _stable_hash(df2)


def test_dataframe_coluna_a_mais_hash_diferente():
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert _stable_hash(df1) != _stable_hash(df2)


# ── _canonicalize: tipos primitivos ───────────────────────────────────────────

def test_canonicalize_preserva_primitivos():
    assert _canonicalize(None, None) is None
    assert _canonicalize(True, None) is True
    assert _canonicalize(42, None) == 42
    assert _canonicalize("foo", None) == "foo"


# ── Node ChangeDetector — branching ──────────────────────────────────────────

class _FakeBackend:
    """Duplo do endpoint POST /internal/change-detector/{key} (swap atomico).

    `stored=None` → previous_hash None (primeira execução). `swap_exc` simula
    backend indisponível — o node decide o branch pela política
    `on_backend_error`. Cada swap grava o hash recebido como novo `stored`,
    então dois swaps seguidos exercitam o ciclo real de duas runs.
    """

    def __init__(self, stored: str | None = None, *, swap_exc=None):
        self.stored = stored
        self.swap_exc = swap_exc
        self.swaps: list[tuple[str, dict]] = []

    @property
    def client_cls(self):
        backend = self

        class FakeAsyncClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def request(self, method, url, *a, **kwargs):
                assert method == "POST", f"esperado POST de swap, veio {method}"
                if backend.swap_exc:
                    raise backend.swap_exc
                body = kwargs.get("json") or {}
                backend.swaps.append((url, body))
                anterior = backend.stored
                backend.stored = body.get("hash")
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"previous_hash": anterior}
                return resp

        return FakeAsyncClient


def _make_node(properties=None):
    """Instancia ChangeDetector com properties padrão de teste."""
    node = ChangeDetector(node_id="n-test", parameters=properties or {})
    node._workflow_hash = "wfh-test"
    node._workspace_id = "ws-test"
    return node


async def _run(node, inputs, backend: _FakeBackend):
    """Executa o node contra o backend fake."""
    with patch("flow.utils.executor_http.get_agent_http_config",
               return_value=("https://srv", {}, True)), \
            patch("httpx.AsyncClient", backend.client_cls):
        return await node.execute(inputs)


@pytest.mark.asyncio
async def test_primeira_execucao_branch_true():
    backend = _FakeBackend(stored=None)  # nunca rodou
    result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    assert result["branch"] is True
    assert result["previous_hash"] is None
    assert len(result["current_hash"]) == 64
    assert len(backend.swaps) == 1
    assert result["reason"] == "primeira_execucao"


@pytest.mark.asyncio
async def test_input_identico_branch_false():
    same_hash = _stable_hash({"a": 1})
    backend = _FakeBackend(stored=same_hash)
    result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    assert result["branch"] is False
    assert result["previous_hash"] == same_hash
    assert result["current_hash"] == same_hash
    assert result["reason"] == "sem_mudanca"


@pytest.mark.asyncio
async def test_input_mudou_branch_true():
    backend = _FakeBackend(stored="a" * 64)  # hash antigo qualquer
    result = await _run(_make_node(), {"data": {"a": 999}}, backend)

    assert result["branch"] is True
    assert result["previous_hash"] == "a" * 64
    assert result["current_hash"] != "a" * 64
    assert result["reason"] == "mudou"


@pytest.mark.asyncio
async def test_data_passada_adiante():
    """O input original é exposto como 'data' no output em ambos branches."""
    payload = {"foo": "bar", "n": 42}
    result = await _run(_make_node(), {"x": payload}, _FakeBackend())

    assert result["output"] == payload


@pytest.mark.asyncio
async def test_fields_filter_aplicado():
    """Com fields_filter, mudanças em campos fora da lista NÃO marcam changed."""
    expected_hash = _stable_hash({"a": 1, "b": 2}, ["a", "b"])
    backend = _FakeBackend(stored=expected_hash)

    # Mesmos a/b, mas com timestamp adicional. fields_filter deve ignorar.
    result = await _run(
        _make_node({"fields": "a,b"}),
        {"data": {"a": 1, "b": 2, "ts": "2026-04-28T10:00"}},
        backend,
    )

    assert result["branch"] is False  # mudou só timestamp, fields ignora


@pytest.mark.asyncio
@pytest.mark.parametrize("guardado", [
    "a,b",           # formato ANTIGO (CSV), ja salvo nas definitions
    ["a", "b"],      # lista de verdade (editor de objeto)
    '["a","b"]',     # JSON-string — o que o campo de fichas grava
])
async def test_fields_aceita_fichas_lista_json_e_csv(guardado):
    """O campo virou fichas ("chips") e passou a gravar JSON-string. Os tres
    formatos tem de filtrar IGUAL — workflow salvo antes nao muda de
    comportamento."""
    expected_hash = _stable_hash({"a": 1, "b": 2}, ["a", "b"])
    backend = _FakeBackend(stored=expected_hash)
    result = await _run(
        _make_node({"fields": guardado}),
        {"data": {"a": 1, "b": 2, "ts": "2026-04-28T10:00"}},
        backend,
    )
    assert result["branch"] is False


@pytest.mark.asyncio
async def test_ttl_em_horas_convertido_para_segundos():
    backend = _FakeBackend()
    await _run(_make_node({"ttl_hours": 2}), {"data": {"a": 1}}, backend)

    assert backend.swaps[0][1]["ttl_seconds"] == 7200


@pytest.mark.asyncio
async def test_ttl_zero_sem_expiracao():
    backend = _FakeBackend()
    await _run(_make_node({"ttl_hours": 0}), {"data": {"a": 1}}, backend)

    # ttl_seconds=0 → servidor grava sem expiração.
    assert backend.swaps[0][1]["ttl_seconds"] == 0


@pytest.mark.asyncio
async def test_backend_fora_default_fail_closed_branch_true():
    """Backend indisponível com política default → branch=True (fail-closed)."""
    backend = _FakeBackend(swap_exc=httpx.ConnectError("backend down"))
    with patch("asyncio.sleep", AsyncMock()):
        result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    assert result["branch"] is True
    assert result["previous_hash"] is None  # não conseguimos ler
    assert result["reason"] == "backend_indisponivel"


@pytest.mark.asyncio
async def test_backend_fora_politica_sem_mudanca():
    """on_backend_error=sem_mudanca: infra piscou NÃO dispara o efeito caro."""
    backend = _FakeBackend(swap_exc=httpx.ConnectError("backend down"))
    with patch("asyncio.sleep", AsyncMock()):
        result = await _run(
            _make_node({"on_backend_error": "sem_mudanca"}), {"data": {"a": 1}}, backend
        )

    assert result["branch"] is False
    assert result["reason"] == "backend_indisponivel"


@pytest.mark.asyncio
async def test_backend_fora_politica_falhar():
    """on_backend_error=falhar: a run erra visivelmente em vez de decidir às cegas."""
    backend = _FakeBackend(swap_exc=httpx.ConnectError("backend down"))
    with patch("asyncio.sleep", AsyncMock()), pytest.raises(RuntimeError) as exc:
        await _run(
            _make_node({"on_backend_error": "falhar"}), {"data": {"a": 1}}, backend
        )

    assert "backend de estado indisponível" in str(exc.value)


@pytest.mark.asyncio
async def test_escopo_workspace_usa_shared_key():
    backend = _FakeBackend()
    await _run(
        _make_node({"scope": "workspace", "shared_key": "monitor_zones"}),
        {"data": {"a": 1}},
        backend,
    )

    # Verifica formato da chave — deve usar prefixo ws e a shared_key.
    assert backend.swaps[0][0].endswith("/internal/change-detector/ws:ws-test:monitor_zones")


@pytest.mark.asyncio
async def test_escopo_workspace_sem_shared_key_usa_node_id():
    backend = _FakeBackend()
    await _run(
        _make_node({"scope": "workspace", "shared_key": ""}),
        {"data": {"a": 1}},
        backend,
    )

    assert backend.swaps[0][0].endswith("/internal/change-detector/ws:ws-test:n-test")


@pytest.mark.asyncio
async def test_escopo_workflow_default():
    backend = _FakeBackend()
    await _run(_make_node(), {"data": {"a": 1}}, backend)  # scope default = "workflow"

    assert backend.swaps[0][0].endswith("/internal/change-detector/wf:wfh-test:n-test")


# ── Canonização estendida: tipos estáveis ────────────────────────────────────

def test_hash_datetime_estavel():
    import datetime as dt
    a = {"ts": dt.datetime(2025, 1, 1, 12, 0, 0)}
    b = {"ts": dt.datetime(2025, 1, 1, 12, 0, 0)}
    assert _stable_hash(a) == _stable_hash(b)
    # Momento diferente → hash diferente.
    c = {"ts": dt.datetime(2025, 1, 1, 12, 0, 1)}
    assert _stable_hash(a) != _stable_hash(c)
    # date e time também canonizam.
    assert _stable_hash({"d": dt.date(2025, 1, 1)}) == _stable_hash({"d": dt.date(2025, 1, 1)})


def test_hash_uuid_estavel():
    from uuid import UUID
    u = UUID("12345678-1234-5678-1234-567812345678")
    assert _stable_hash({"id": u}) == _stable_hash({"id": UUID(str(u))})
    other = UUID("87654321-4321-8765-4321-876543218765")
    assert _stable_hash({"id": u}) != _stable_hash({"id": other})


def test_hash_decimal_path_enum():
    from decimal import Decimal
    from pathlib import PurePosixPath
    from enum import Enum

    class Color(Enum):
        RED = 1
        BLUE = 2

    # Decimal preserva precisão (str), estável entre instâncias iguais.
    assert _stable_hash({"v": Decimal("1.10")}) == _stable_hash({"v": Decimal("1.10")})
    assert _stable_hash({"v": Decimal("1.10")}) != _stable_hash({"v": Decimal("1.1")})
    # Path canoniza via as_posix.
    assert _stable_hash({"p": PurePosixPath("/a/b")}) == _stable_hash({"p": PurePosixPath("/a/b")})
    # Enum: name + value.
    assert _stable_hash({"c": Color.RED}) == _stable_hash({"c": Color.RED})
    assert _stable_hash({"c": Color.RED}) != _stable_hash({"c": Color.BLUE})


def test_hash_tipo_desconhecido_fail_fast():
    from flow.nodes.control.change_detector import ChangeDetectorTypeError

    class Custom:
        def __init__(self, x):
            self.x = x

    with pytest.raises(ChangeDetectorTypeError) as exc:
        _stable_hash({"obj": Custom(1)})
    # Mensagem inclui o caminho do tipo para diagnóstico.
    assert "Custom" in str(exc.value)


@pytest.mark.asyncio
async def test_hash_tipo_desconhecido_no_node_fail_safe():
    """Input com tipo não-hashable → node cai em branch=True (fail-safe), não quebra."""
    class Custom:
        pass

    result = await _run(_make_node(), {"data": {"obj": Custom()}}, _FakeBackend())

    assert result["branch"] is True
    assert result["previous_hash"] is None


@pytest.mark.asyncio
async def test_hash_corrompido_no_backend():
    """Valor inválido no backend (não-hex/tamanho errado) → tratado como primeira run."""
    backend = _FakeBackend(stored="nao-eh-um-hash-valido")  # lixo
    result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    # Hash corrompido vira None → previous_hash None → branch True (mudou).
    assert result["previous_hash"] is None
    assert result["branch"] is True
    assert result["reason"] == "primeira_execucao"


# ── http_retry helper ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_http_retry_em_503(monkeypatch):
    """503 transitório duas vezes + 200 → retorna 200 após retries."""
    from unittest.mock import MagicMock
    from flow.utils.http_retry import async_request_with_retry

    seq = [503, 503, 200]
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, method, url, *a, **k):
            r = MagicMock()
            r.status_code = seq[calls["n"]]
            calls["n"] += 1
            return r

    # Não dorme de verdade.
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    with patch("httpx.AsyncClient", FakeClient):
        resp = await async_request_with_retry("GET", "https://x/y", base_delay=0)

    assert resp.status_code == 200
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_http_retry_desiste_apos_max(monkeypatch):
    """503 sempre → retorna o último 503 após max_attempts (caller faz fail-closed)."""
    from unittest.mock import MagicMock
    from flow.utils.http_retry import async_request_with_retry

    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, method, url, *a, **k):
            calls["n"] += 1
            r = MagicMock()
            r.status_code = 503
            return r

    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    with patch("httpx.AsyncClient", FakeClient):
        resp = await async_request_with_retry("GET", "https://x/y", max_attempts=3, base_delay=0)

    assert resp.status_code == 503
    assert calls["n"] == 3  # 1 + 2 retries


# ── cleanup pós-delete de workflow ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_keys_no_delete_workflow():
    """delete_workflow remove keys change_detector:wf:{hash}:* do Redis."""
    from app.services.workflow_service import _cleanup_change_detector_keys

    existing = [
        "change_detector:wf:wfh-test:n-1",
        "change_detector:wf:wfh-test:n-2",
    ]
    deleted: list[str] = []

    class FakeRedis:
        async def scan_iter(self, match=None, count=None):
            for k in existing:
                yield k
        async def delete(self, key):
            deleted.append(key)

    with patch("app.core.redis.get_redis_pool", return_value=FakeRedis()):
        removed = await _cleanup_change_detector_keys("wfh-test")

    assert removed == 2
    assert set(deleted) == set(existing)


@pytest.mark.asyncio
async def test_cleanup_keys_falha_redis_nao_propaga():
    """Falha no Redis durante cleanup não propaga (best-effort)."""
    from app.services.workflow_service import _cleanup_change_detector_keys

    class BrokenRedis:
        def scan_iter(self, *a, **k):
            raise ConnectionError("redis down")

    with patch("app.core.redis.get_redis_pool", return_value=BrokenRedis()):
        removed = await _cleanup_change_detector_keys("wfh-test")

    assert removed == 0  # não removeu nada, mas não levantou


# ── v2 do hash de tabela: soma modular em vez de XOR ─────────────────────────

def test_dataframe_par_duplicado_trocado_e_detectado():
    """Regressão da v1: XOR anulava pares de linhas idênticas — trocar {x, x}
    por {y, y} mantinha n_rows/cols/dtypes E o agregado, passando como 'sem
    mudança'. A soma modular detecta."""
    pd = pytest.importorskip("pandas")
    from flow.nodes.control.change_detector import _hash_dataframe

    a = pd.DataFrame({"v": ["x", "x", "z"]})
    b = pd.DataFrame({"v": ["y", "y", "z"]})
    assert _hash_dataframe(a) != _hash_dataframe(b)
    assert _stable_hash(a) != _stable_hash(b)


def test_geodataframe_par_duplicado_trocado_e_detectado():
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("shapely")
    from shapely.geometry import Point
    from flow.nodes.control.change_detector import _hash_geodataframe

    a = gpd.GeoDataFrame({"v": [1, 1, 2]}, geometry=[Point(0, 0), Point(0, 0), Point(1, 1)])
    b = gpd.GeoDataFrame({"v": [1, 1, 2]}, geometry=[Point(2, 2), Point(2, 2), Point(1, 1)])
    assert _hash_geodataframe(a) != _hash_geodataframe(b)


def test_dataframe_assinatura_e_versionada():
    """O bump para v2 é explícito na assinatura — invalida os hashes v1 uma
    única vez após o deploy, de propósito."""
    pd = pytest.importorskip("pandas")
    from flow.nodes.control.change_detector import _hash_dataframe

    assinatura = _hash_dataframe(pd.DataFrame({"v": [1]}))
    assert assinatura["__df__"] == 2
    assert "soma" in assinatura and "xor" not in assinatura


# ── ignore_fields: exclusão com caminho pontilhado ───────────────────────────

def test_ignore_na_raiz():
    com_ts = {"a": 1, "fetched_at": "2026-08-31T10:00"}
    assert _stable_hash(com_ts, None, ["fetched_at"]) == _stable_hash({"a": 1})


def test_ignore_caminho_pontilhado():
    a = {"a": 2, "meta": {"updated_at": "ontem", "fonte": "wfs"}}
    b = {"a": 2, "meta": {"updated_at": "hoje", "fonte": "wfs"}}
    assert _stable_hash(a, None, ["meta.updated_at"]) == _stable_hash(b, None, ["meta.updated_at"])
    # Sem o ignore, os dois diferem — o filtro é quem iguala.
    assert _stable_hash(a) != _stable_hash(b)


def test_ignore_desce_em_lista_de_registros():
    a = {"items": [{"v": 1, "ts": 10}, {"v": 2, "ts": 20}]}
    b = {"items": [{"v": 1, "ts": 99}, {"v": 2, "ts": 77}]}
    assert _stable_hash(a, None, ["items.ts"]) == _stable_hash(b, None, ["items.ts"])


def test_ignore_remove_coluna_de_dataframe():
    pd = pytest.importorskip("pandas")
    a = {"tabela": pd.DataFrame({"v": [1, 2], "fetched_at": ["t1", "t2"]})}
    b = {"tabela": pd.DataFrame({"v": [1, 2], "fetched_at": ["t9", "t8"]})}
    assert _stable_hash(a, None, ["tabela.fetched_at"]) == _stable_hash(b, None, ["tabela.fetched_at"])
    # Coluna ausente não é erro: o input já está como o filtro quer.
    sem_coluna = {"tabela": pd.DataFrame({"v": [1, 2]})}
    assert _stable_hash(sem_coluna, None, ["tabela.fetched_at"]) == _stable_hash(
        a, None, ["tabela.fetched_at"]
    )


def test_ignore_nao_muta_o_input():
    original = {"a": 1, "meta": {"updated_at": "x", "k": 2}}
    _stable_hash(original, None, ["meta.updated_at", "a"])
    assert original == {"a": 1, "meta": {"updated_at": "x", "k": 2}}


@pytest.mark.asyncio
async def test_ignore_fields_aplicado_no_node():
    """Param ignore_fields do nó: mudou só o campo ignorado → 'Sem mudança'."""
    esperado = _stable_hash({"a": 1}, None, None)
    backend = _FakeBackend(stored=esperado)
    result = await _run(
        _make_node({"ignore_fields": "ts"}),
        {"data": {"a": 1, "ts": "2026-08-31T10:00"}},
        backend,
    )
    assert result["branch"] is False
    assert result["reason"] == "sem_mudanca"


@pytest.mark.asyncio
@pytest.mark.parametrize("guardado", ["ts", ["ts"], '["ts"]'])
async def test_ignore_fields_aceita_fichas_lista_json_e_csv(guardado):
    """Mesma tolerância de formato do `fields` — inclusive o CSV antigo."""
    esperado = _stable_hash({"a": 1}, None, None)
    backend = _FakeBackend(stored=esperado)
    result = await _run(
        _make_node({"ignore_fields": guardado}),
        {"data": {"a": 1, "ts": "2026-08-31T10:00"}},
        backend,
    )
    assert result["branch"] is False
    assert result["reason"] == "sem_mudanca"


# ── primeira execução silenciosa ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_primeira_execucao_silenciosa_registra_baseline_sem_disparar():
    backend = _FakeBackend(stored=None)
    result = await _run(
        _make_node({"primeira_execucao": "sem_mudanca"}), {"data": {"a": 1}}, backend
    )

    assert result["branch"] is False                      # não dispara o alerta
    assert result["reason"] == "primeira_execucao"
    assert len(backend.swaps) == 1                        # mas o baseline foi gravado
    # A run seguinte com o MESMO input continua 'Sem mudança'...
    result2 = await _run(
        _make_node({"primeira_execucao": "sem_mudanca"}), {"data": {"a": 1}}, backend
    )
    assert result2["branch"] is False and result2["reason"] == "sem_mudanca"
    # ...e com input DIFERENTE dispara normalmente.
    result3 = await _run(
        _make_node({"primeira_execucao": "sem_mudanca"}), {"data": {"a": 2}}, backend
    )
    assert result3["branch"] is True and result3["reason"] == "mudou"


# ── ttl_hours tolerante a campo limpo ────────────────────────────────────────

@pytest.mark.asyncio
async def test_ttl_hours_vazio_cai_no_default():
    """Campo limpo na UI ('') não pode derrubar a run — usa o default 168h."""
    backend = _FakeBackend()
    result = await _run(_make_node({"ttl_hours": ""}), {"data": {"a": 1}}, backend)

    assert result["branch"] is True
    assert backend.swaps[0][1]["ttl_seconds"] == 168 * 3600


# ── múltiplas entradas ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multiplas_entradas_todas_entram_no_hash():
    """Duas edges ligadas: ambas entram no hash (ordenadas por nome) — antes a
    segunda era descartada em silêncio e mudança nela passava despercebida."""
    backend = _FakeBackend()
    r1 = await _run(_make_node(), {"b": {"y": 2}, "a": {"x": 1}}, backend)
    assert r1["current_hash"] == _stable_hash({"a": {"x": 1}, "b": {"y": 2}})

    # Mudança APENAS na segunda entrada é detectada.
    r2 = await _run(_make_node(), {"a": {"x": 1}, "b": {"y": 999}}, backend)
    assert r2["branch"] is True and r2["reason"] == "mudou"


@pytest.mark.asyncio
async def test_cleanup_ws_keys_no_delete_do_workspace():
    """Chaves ws:* (shared_key) não pertencem a workflow nenhum — o cascade do
    workspace é o único lugar que pode limpá-las; com ttl_hours=0 elas viveriam
    para sempre."""
    from app.services.workflow_service import _cleanup_change_detector_ws_keys

    existing = [
        "change_detector:ws:ws-alvo:monitor_zones",
        "change_detector:ws:ws-alvo:outra-chave",
    ]
    deleted: list[str] = []
    patterns: list[str] = []

    class FakeRedis:
        def scan_iter(self, match=None, count=None):
            patterns.append(match)
            async def _gen():
                for k in existing:
                    yield k
            return _gen()
        async def delete(self, key):
            deleted.append(key)

    with patch("app.core.redis.get_redis_pool", return_value=FakeRedis()):
        removed = await _cleanup_change_detector_ws_keys("ws-alvo")

    assert removed == 2
    assert set(deleted) == set(existing)
    assert patterns == ["change_detector:ws:ws-alvo:*"]


@pytest.mark.asyncio
async def test_soft_delete_do_workspace_dispara_a_limpeza_ws():
    """O cascade do workspace precisa chamar a limpeza ws:* além da por-workflow."""
    from app.services import workflow_service as ws_mod
    import datetime as dt

    db = AsyncMock()
    rows = MagicMock()
    rows.all.return_value = [("wf-1", None)]
    upd = MagicMock()
    upd.rowcount = 1
    db.execute = AsyncMock(side_effect=[rows, MagicMock(), upd])

    with patch.object(ws_mod, "_cleanup_change_detector_keys", new=AsyncMock()) as por_wf, \
            patch.object(ws_mod, "_cleanup_change_detector_ws_keys", new=AsyncMock()) as por_ws:
        await ws_mod.soft_delete_workspace_workflows(db, "ws-alvo", dt.datetime(2026, 8, 31))

    por_wf.assert_awaited_once_with("wf-1")
    por_ws.assert_awaited_once_with("ws-alvo")
