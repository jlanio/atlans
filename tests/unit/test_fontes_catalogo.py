# tests/unit/test_fontes_catalogo.py
"""Catalog at startup and periodic per-endpoint verification (app/core/fontes_catalogo.py).

SQLite (temporary file, one connection per session — the module opens sessions in
parallel) in place of Postgres; `obter_capabilities` doubled — no test touches
the network. The Redis lock becomes a function that records the calls.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import fontes_catalogo as fc
from app.core import tarefas_periodicas
from app.core.utils.datetime_utils import utc_now_naive
from app.models.base import Base
from app.models.fonte_de_dados import DataSource
from app.services import fontes_service as fs
from app.services import fontes_vault

VAULT = Path(__file__).resolve().parents[1] / "fixtures" / "vault"


# ── Doubles ──────────────────────────────────────────────────────────────────────

@pytest.fixture
async def fabrica(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'fontes.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[DataSource.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(fc, "AsyncSessionLocal", fabrica)
    monkeypatch.setattr(fc, "_PAUSA_ENTRE_ENDPOINTS_S", 0.0)
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 3600)
    try:
        yield fabrica
    finally:
        await engine.dispose()


@pytest.fixture
def lock(monkeypatch):
    """The Redis lock becomes a list of calls; `lock.livre` decides the answer.

    A single point: startup calls `tarefas_periodicas.adquirir_lock`, and so does the
    periodic loop (from inside `periodic_loop`)."""
    estado = SimpleNamespace(chamadas=[], livre=True, soltos=[])

    async def _acquire(chave, ttl):
        estado.chamadas.append((chave, ttl))
        return estado.livre

    async def _release(chave):
        estado.soltos.append(chave)

    monkeypatch.setattr(tarefas_periodicas, "adquirir_lock", _acquire)
    monkeypatch.setattr(tarefas_periodicas, "soltar_lock", _release)
    return estado


@pytest.fixture
def capabilities(monkeypatch):
    """`obter_capabilities` doubled: per URL, a `Capabilities` or an exception.
    A URL with no configured response = endpoint down (`ProbeError`)."""
    estado = SimpleNamespace(respostas={}, chamadas=[])

    async def _fetch_capabilities(url, version="2.0.0"):
        estado.chamadas.append(url)
        resposta = estado.respostas.get(url)
        if isinstance(resposta, BaseException):
            raise resposta
        if resposta is None:
            raise fs.ProbeError("rede", f"sem resposta de {url}")
        return resposta

    monkeypatch.setattr(fs, "obter_capabilities", _fetch_capabilities)
    return estado


@pytest.fixture(autouse=True)
def _clean_synonyms():
    fs.set_synonyms({})
    yield
    fs.set_synonyms({})


def _caps(*nomes: str) -> fs.Capabilities:
    return fs.Capabilities(
        version="2.0.0",
        layers=tuple(
            fs.ServiceLayer(name=n, title=n.split(":")[-1], crs="EPSG:4674", bbox=(-74.0, -34.0, -34.0, 5.0))
            for n in nomes
        ),
    )


async def _seed(fabrica, *fontes):
    """`fontes`: (url, type_name, verificada_em)."""
    async with fabrica() as db:
        for url, type_name, verificada_em in fontes:
            await fs.upsert_source(
                db, workspace_id=None, tipo="wfs", url=url, type_name=type_name,
                propriedades={"url": url, "typeName": type_name}, origem="vault",
                verificada_em=verificada_em,
            )
        await db.commit()


async def _states(fabrica) -> dict[str, str]:
    async with fabrica() as db:
        linhas = await db.execute(select(DataSource.type_name, DataSource.estado))
        return dict(linhas.all())


def _registros_do_vault():
    return [r for r in fontes_vault.read_folder(VAULT) if not isinstance(r, fontes_vault.Skipped)]


# ── importar_catalogo_no_arranque ────────────────────────────────────────────────

async def test_empty_flag_or_missing_folder_neither_imports_nor_takes_lock(fabrica, lock, capabilities, monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", "")
    assert await fc.importar_catalogo_no_arranque() is None
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(tmp_path / "nao-existe"))
    assert await fc.importar_catalogo_no_arranque() is None
    assert lock.chamadas == [] and capabilities.chamadas == []
    assert await _states(fabrica) == {}


async def test_imports_the_folder_and_checks_pending_per_endpoint(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    registros = _registros_do_vault()
    by_url: dict[str, list[str]] = {}
    for r in registros:
        by_url.setdefault(fs.normalize_url(r.url), []).append(r.type_name)
    funai = next(u for u in by_url if "funai" in u)
    capabilities.respostas[funai] = _caps(*by_url[funai])  # only Funai responds

    resumo = await fc.importar_catalogo_no_arranque()

    assert resumo.criadas == len(registros) and resumo.erros == []
    assert resumo.ignoradas == {"sem_endpoint_wfs": 2}  # ArcGIS (TIGERweb) e o placeholder (DomiNode)
    assert lock.chamadas == [(fc._IMPORT_LOCK, fc._IMPORT_LOCK_TTL_S)]
    # ONE GetCapabilities per distinct URL, not one per layer.
    assert sorted(capabilities.chamadas) == sorted(by_url)
    estados = await _states(fabrica)
    assert all(estados[t] == "ok" for t in by_url[funai])
    assert all(estados[t] == "falhando" for u, ts in by_url.items() if u != funai for t in ts)
    async with fabrica() as db:
        pendentes = await db.scalar(select(fs.func.count()).where(DataSource.verificada_em.is_(None)))
    assert pendentes == 0
    # The Vault synonyms (`_sinonimos.md`) were loaded in this process.
    assert fs.synonyms_of("unidade de conservação") >= {"uc", "parque", "reserva"}


async def test_busy_lock_skips_the_import_but_loads_the_synonyms(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    lock.livre = False
    assert await fc.importar_catalogo_no_arranque() is None
    assert await _states(fabrica) == {} and capabilities.chamadas == []
    # The synonyms live in the memory of EACH worker: one that did not import also reads them.
    assert fs._extra_synonyms.get("terra indigena") == {"ti", "indigena", "aldeia"}


async def test_second_startup_is_zero_writes_and_does_not_recheck(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    primeiro = await fc.importar_catalogo_no_arranque()
    probes = len(capabilities.chamadas)
    assert primeiro.criadas > 0 and probes > 0

    segundo = await fc.importar_catalogo_no_arranque()
    assert (segundo.criadas, segundo.atualizadas, segundo.removidas) == (0, 0, 0)
    assert segundo.iguais == primeiro.criadas
    # Everything was verified moments ago: the initial verification does not redo it.
    assert len(capabilities.chamadas) == probes


async def test_zero_interval_imports_but_probes_nothing(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0)
    resumo = await fc.importar_catalogo_no_arranque()
    assert resumo.criadas > 0 and capabilities.chamadas == []
    assert set((await _states(fabrica)).values()) == {"nao_verificada"}


async def test_failing_import_does_not_break_startup(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))

    async def _broken_import(db, caminho, **kw):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(fs, "importar_pasta", _broken_import)
    assert await fc.importar_catalogo_no_arranque() is None
    assert capabilities.chamadas == []
    # Whoever failed gives the lock back: the next startup does not wait the 10 min TTL.
    assert lock.soltos == [fc._IMPORT_LOCK]


async def test_import_waits_for_the_schema_and_only_then_takes_the_lock(fabrica, lock, capabilities, monkeypatch):
    # The API starts before `alembic upgrade head` (the guide's order): without the
    # table, the import failed, held on to the lock and the next recreation of the
    # API skipped it — the catalog was born empty. Now it waits for the table to appear.
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0)
    monkeypatch.setattr(fc, "_INTERVALO_DA_ESPERA_S", 0)
    consultas = SimpleNamespace(n=0)
    real_schema = fc._schema_pronto

    async def _late_schema():
        consultas.n += 1
        return consultas.n > 2 and await real_schema()

    monkeypatch.setattr(fc, "_schema_pronto", _late_schema)
    resumo = await fc.importar_catalogo_no_arranque()
    assert resumo.criadas > 0 and consultas.n == 3
    assert lock.chamadas == [(fc._IMPORT_LOCK, fc._IMPORT_LOCK_TTL_S)] and lock.soltos == []


async def test_no_schema_by_end_of_wait_takes_no_lock_and_defers_to_next(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    monkeypatch.setattr(fc, "_INTERVALO_DA_ESPERA_S", 0)
    monkeypatch.setattr(fc, "_ESPERA_PELO_SCHEMA_S", 0)

    async def _never():
        return False

    monkeypatch.setattr(fc, "_schema_pronto", _never)
    assert await fc.importar_catalogo_no_arranque() is None
    assert lock.chamadas == [] and capabilities.chamadas == []
    # The synonyms were loaded anyway.
    assert fs._extra_synonyms.get("terra indigena") == {"ti", "indigena", "aldeia"}


# ── verificar_endpoints ──────────────────────────────────────────────────────────

async def test_initial_check_probes_only_pending_and_periodic_probes_all(fabrica, capabilities):
    agora = utc_now_naive()
    await _seed(
        fabrica,
        ("https://a.gov.br/ows", "a:x", agora),                        # fresca
        ("https://b.gov.br/ows", "b:y", None),                         # never verified
        ("https://c.gov.br/ows", "c:z", agora - timedelta(days=2)),    # vencida
    )
    for u, t in (("https://a.gov.br/ows", "a:x"), ("https://b.gov.br/ows", "b:y"), ("https://c.gov.br/ows", "c:z")):
        capabilities.respostas[u] = _caps(t)

    resumo = await fc.verificar_endpoints(only_pending=True)
    assert sorted(capabilities.chamadas) == ["https://b.gov.br/ows", "https://c.gov.br/ows"]
    assert (resumo.endpoints, resumo.ok, resumo.falhando, resumo.fora, resumo.erros) == (2, 2, 0, 0, 0)

    capabilities.chamadas.clear()
    resumo = await fc.verificar_endpoints()
    assert len(capabilities.chamadas) == 3 and resumo.ok == 3
    assert "3 endpoint(s): 3 camada(s) ok" in resumo.as_text()


async def test_one_endpoint_failure_does_not_stop_the_round(fabrica, capabilities):
    await _seed(
        fabrica,
        ("https://a.gov.br/ows", "a:x", None),
        ("https://b.gov.br/ows", "b:y", None),
        ("https://c.gov.br/ows", "c:z", None),
    )
    capabilities.respostas["https://a.gov.br/ows"] = _caps("a:x")
    capabilities.respostas["https://b.gov.br/ows"] = fs.ProbeError("timeout", "demorou demais")
    capabilities.respostas["https://c.gov.br/ows"] = RuntimeError("bug inesperado")

    resumo = await fc.verificar_endpoints()

    assert (resumo.endpoints, resumo.ok, resumo.falhando, resumo.fora, resumo.erros) == (3, 1, 1, 1, 1)
    # An endpoint that is down marks `falhando`; an unexpected exception leaves the row as it was.
    assert await _states(fabrica) == {"a:x": "ok", "b:y": "falhando", "c:z": "nao_verificada"}


async def test_at_most_two_endpoints_at_the_same_time(fabrica, monkeypatch):
    hosts = "abcdef"
    await _seed(fabrica, *((f"https://{h}.gov.br/ows", f"{h}:x", None) for h in hosts))
    ativos = {"agora": 0, "pico": 0}

    async def _slow(url, version="2.0.0"):
        ativos["agora"] += 1
        ativos["pico"] = max(ativos["pico"], ativos["agora"])
        await asyncio.sleep(0.01)
        ativos["agora"] -= 1
        return _caps(f"{url[8]}:x")

    monkeypatch.setattr(fs, "obter_capabilities", _slow)
    resumo = await fc.verificar_endpoints()
    assert (resumo.endpoints, resumo.ok) == (6, 6)
    assert 1 <= ativos["pico"] <= fc._PARALLELISM == 2


async def test_empty_catalog_is_a_round_without_probing(fabrica, capabilities):
    resumo = await fc.verificar_endpoints()
    assert resumo == fc.RoundSummary() and capabilities.chamadas == []


# ── run_verificacao_loop ─────────────────────────────────────────────────────────

async def test_zero_interval_disables_the_loop(monkeypatch):
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0)
    await asyncio.wait_for(fc.run_verificacao_loop(), 1.0)  # returns right away, without sleeping


async def test_loop_checks_every_interval_with_lock_and_survives_error(lock, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0.01)
    rodadas: list[dict] = []

    async def _round(**kw):
        rodadas.append(kw)
        if len(rodadas) == 1:
            raise RuntimeError("banco fora")   # does not bring down the loop
        if len(rodadas) == 3:
            raise asyncio.CancelledError       # o shutdown chega
        return fc.RoundSummary()

    monkeypatch.setattr(fc, "verificar_endpoints", _round)
    await asyncio.wait_for(fc.run_verificacao_loop(), 2.0)
    assert rodadas == [{}, {}, {}]
    assert lock.chamadas == [(fc._VERIFICATION_LOCK, 0.01)] * 3


async def test_loop_without_lock_skips_the_round(lock, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0.01)
    lock.livre = False
    rodadas: list[dict] = []

    async def _round(**kw):
        rodadas.append(kw)
        return fc.RoundSummary()

    monkeypatch.setattr(fc, "verificar_endpoints", _round)
    tarefa = asyncio.create_task(fc.run_verificacao_loop())
    await asyncio.sleep(0.08)
    tarefa.cancel()
    await tarefa  # o loop trata o CancelledError e encerra sozinho
    assert rodadas == [] and len(lock.chamadas) >= 2


# ── Lifespan ─────────────────────────────────────────────────────────────────────
# The lock itself (SET NX EX on the pool, Redis down = proceed) and the shutdown of
# each background task are in test_tarefas_de_fundo.py.

def test_lifespan_starts_both_tasks():
    from app import main

    factories = [fabrica for _, fabrica in main._tarefas_de_fundo()]
    assert fc.importar_catalogo_no_arranque in factories
    assert fc.run_verificacao_loop in factories
