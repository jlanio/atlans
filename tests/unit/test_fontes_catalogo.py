# tests/unit/test_fontes_catalogo.py
"""Catálogo no arranque e verificação periódica por endpoint (app/core/fontes_catalogo.py).

SQLite (arquivo temporário, uma conexão por sessão — o módulo abre sessões em
paralelo) no lugar do Postgres; `obter_capabilities` dublado — nenhum teste toca
a rede. O lock Redis vira uma função que registra as chamadas.
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
from app.models.fonte_de_dados import FonteDeDados
from app.services import fontes_service as fs
from app.services import fontes_vault

VAULT = Path(__file__).resolve().parents[1] / "fixtures" / "vault"


# ── Dublês ───────────────────────────────────────────────────────────────────────

@pytest.fixture
async def fabrica(monkeypatch, tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'fontes.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[FonteDeDados.__table__])
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
    """O lock Redis vira uma lista de chamadas; `lock.livre` decide a resposta.

    Um ponto só: o arranque chama `tarefas_periodicas.adquirir_lock`, e o laço
    periódico também (de dentro de `laco_periodico`)."""
    estado = SimpleNamespace(chamadas=[], livre=True, soltos=[])

    async def _adquirir(chave, ttl):
        estado.chamadas.append((chave, ttl))
        return estado.livre

    async def _soltar(chave):
        estado.soltos.append(chave)

    monkeypatch.setattr(tarefas_periodicas, "adquirir_lock", _adquirir)
    monkeypatch.setattr(tarefas_periodicas, "soltar_lock", _soltar)
    return estado


@pytest.fixture
def capabilities(monkeypatch):
    """`obter_capabilities` dublado: por URL, uma `Capabilities` ou uma exceção.
    URL sem resposta configurada = endpoint fora do ar (`SondagemError`)."""
    estado = SimpleNamespace(respostas={}, chamadas=[])

    async def _obter(url, version="2.0.0"):
        estado.chamadas.append(url)
        resposta = estado.respostas.get(url)
        if isinstance(resposta, BaseException):
            raise resposta
        if resposta is None:
            raise fs.SondagemError("rede", f"sem resposta de {url}")
        return resposta

    monkeypatch.setattr(fs, "obter_capabilities", _obter)
    return estado


@pytest.fixture(autouse=True)
def _sinonimos_limpos():
    fs.definir_sinonimos({})
    yield
    fs.definir_sinonimos({})


def _caps(*nomes: str) -> fs.Capabilities:
    return fs.Capabilities(
        version="2.0.0",
        layers=tuple(
            fs.CamadaDoServico(name=n, title=n.split(":")[-1], crs="EPSG:4674", bbox=(-74.0, -34.0, -34.0, 5.0))
            for n in nomes
        ),
    )


async def _semear(fabrica, *fontes):
    """`fontes`: (url, type_name, verificada_em)."""
    async with fabrica() as db:
        for url, type_name, verificada_em in fontes:
            await fs.upsert_fonte(
                db, workspace_id=None, tipo="wfs", url=url, type_name=type_name,
                propriedades={"url": url, "typeName": type_name}, origem="vault",
                verificada_em=verificada_em,
            )
        await db.commit()


async def _estados(fabrica) -> dict[str, str]:
    async with fabrica() as db:
        linhas = await db.execute(select(FonteDeDados.type_name, FonteDeDados.estado))
        return dict(linhas.all())


def _registros_do_vault():
    return [r for r in fontes_vault.ler_pasta(VAULT) if not isinstance(r, fontes_vault.Ignorada)]


# ── importar_catalogo_no_arranque ────────────────────────────────────────────────

async def test_flag_vazia_ou_pasta_inexistente_nao_importa_nem_pega_lock(fabrica, lock, capabilities, monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", "")
    assert await fc.importar_catalogo_no_arranque() is None
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(tmp_path / "nao-existe"))
    assert await fc.importar_catalogo_no_arranque() is None
    assert lock.chamadas == [] and capabilities.chamadas == []
    assert await _estados(fabrica) == {}


async def test_importa_a_pasta_e_verifica_o_pendente_por_endpoint(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    registros = _registros_do_vault()
    por_url: dict[str, list[str]] = {}
    for r in registros:
        por_url.setdefault(fs.normalizar_url(r.url), []).append(r.type_name)
    funai = next(u for u in por_url if "funai" in u)
    capabilities.respostas[funai] = _caps(*por_url[funai])  # só a Funai responde

    resumo = await fc.importar_catalogo_no_arranque()

    assert resumo.criadas == len(registros) and resumo.erros == []
    assert resumo.ignoradas == {"sem_endpoint_wfs": 2}  # ArcGIS (TIGERweb) e o placeholder (DomiNode)
    assert lock.chamadas == [(fc._LOCK_IMPORTACAO, fc._TTL_LOCK_IMPORTACAO_S)]
    # UM GetCapabilities por URL distinta, não um por camada.
    assert sorted(capabilities.chamadas) == sorted(por_url)
    estados = await _estados(fabrica)
    assert all(estados[t] == "ok" for t in por_url[funai])
    assert all(estados[t] == "falhando" for u, ts in por_url.items() if u != funai for t in ts)
    async with fabrica() as db:
        pendentes = await db.scalar(select(fs.func.count()).where(FonteDeDados.verificada_em.is_(None)))
    assert pendentes == 0
    # Os sinônimos do Vault (`_sinonimos.md`) foram carregados neste processo.
    assert fs.sinonimos_de("unidade de conservação") >= {"uc", "parque", "reserva"}


async def test_lock_ocupado_pula_a_importacao_mas_carrega_os_sinonimos(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    lock.livre = False
    assert await fc.importar_catalogo_no_arranque() is None
    assert await _estados(fabrica) == {} and capabilities.chamadas == []
    # Os sinônimos moram na memória de CADA worker: quem não importou também lê.
    assert fs._sinonimos_extra.get("terra indigena") == {"ti", "indigena", "aldeia"}


async def test_segunda_subida_e_zero_escritas_e_nao_reverifica(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    primeiro = await fc.importar_catalogo_no_arranque()
    sondagens = len(capabilities.chamadas)
    assert primeiro.criadas > 0 and sondagens > 0

    segundo = await fc.importar_catalogo_no_arranque()
    assert (segundo.criadas, segundo.atualizadas, segundo.removidas) == (0, 0, 0)
    assert segundo.iguais == primeiro.criadas
    # Tudo foi verificado há instantes: a verificação inicial não refaz.
    assert len(capabilities.chamadas) == sondagens


async def test_intervalo_zero_importa_mas_nao_sonda_nada(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0)
    resumo = await fc.importar_catalogo_no_arranque()
    assert resumo.criadas > 0 and capabilities.chamadas == []
    assert set((await _estados(fabrica)).values()) == {"nao_verificada"}


async def test_importacao_que_falha_nao_derruba_a_subida(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))

    async def _quebra(db, caminho, **kw):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(fs, "importar_pasta", _quebra)
    assert await fc.importar_catalogo_no_arranque() is None
    assert capabilities.chamadas == []
    # Quem falhou devolve o lock: a próxima subida não espera os 10 min do TTL.
    assert lock.soltos == [fc._LOCK_IMPORTACAO]


async def test_a_importacao_espera_o_schema_e_so_entao_pega_o_lock(fabrica, lock, capabilities, monkeypatch):
    # A API sobe antes do `alembic upgrade head` (a ordem do guia): sem a
    # tabela, a importação falhava, prendia o lock e a recriação seguinte da
    # API pulava — o catálogo nascia vazio. Agora espera a tabela aparecer.
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0)
    monkeypatch.setattr(fc, "_INTERVALO_DA_ESPERA_S", 0)
    consultas = SimpleNamespace(n=0)
    schema_de_verdade = fc._schema_pronto

    async def _schema_atrasado():
        consultas.n += 1
        return consultas.n > 2 and await schema_de_verdade()

    monkeypatch.setattr(fc, "_schema_pronto", _schema_atrasado)
    resumo = await fc.importar_catalogo_no_arranque()
    assert resumo.criadas > 0 and consultas.n == 3
    assert lock.chamadas == [(fc._LOCK_IMPORTACAO, fc._TTL_LOCK_IMPORTACAO_S)] and lock.soltos == []


async def test_sem_schema_ate_o_fim_da_espera_nao_pega_lock_e_fica_para_a_proxima(fabrica, lock, capabilities, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_CATALOGO_DIR", str(VAULT))
    monkeypatch.setattr(fc, "_INTERVALO_DA_ESPERA_S", 0)
    monkeypatch.setattr(fc, "_ESPERA_PELO_SCHEMA_S", 0)

    async def _nunca():
        return False

    monkeypatch.setattr(fc, "_schema_pronto", _nunca)
    assert await fc.importar_catalogo_no_arranque() is None
    assert lock.chamadas == [] and capabilities.chamadas == []
    # Os sinônimos foram carregados mesmo assim.
    assert fs._sinonimos_extra.get("terra indigena") == {"ti", "indigena", "aldeia"}


# ── verificar_endpoints ──────────────────────────────────────────────────────────

async def test_verificacao_inicial_so_sonda_o_pendente_e_a_periodica_sonda_tudo(fabrica, capabilities):
    agora = utc_now_naive()
    await _semear(
        fabrica,
        ("https://a.gov.br/ows", "a:x", agora),                        # fresca
        ("https://b.gov.br/ows", "b:y", None),                         # nunca verificada
        ("https://c.gov.br/ows", "c:z", agora - timedelta(days=2)),    # vencida
    )
    for u, t in (("https://a.gov.br/ows", "a:x"), ("https://b.gov.br/ows", "b:y"), ("https://c.gov.br/ows", "c:z")):
        capabilities.respostas[u] = _caps(t)

    resumo = await fc.verificar_endpoints(apenas_pendentes=True)
    assert sorted(capabilities.chamadas) == ["https://b.gov.br/ows", "https://c.gov.br/ows"]
    assert (resumo.endpoints, resumo.ok, resumo.falhando, resumo.fora, resumo.erros) == (2, 2, 0, 0, 0)

    capabilities.chamadas.clear()
    resumo = await fc.verificar_endpoints()
    assert len(capabilities.chamadas) == 3 and resumo.ok == 3
    assert "3 endpoint(s): 3 camada(s) ok" in resumo.como_texto()


async def test_falha_de_um_endpoint_nao_para_a_rodada(fabrica, capabilities):
    await _semear(
        fabrica,
        ("https://a.gov.br/ows", "a:x", None),
        ("https://b.gov.br/ows", "b:y", None),
        ("https://c.gov.br/ows", "c:z", None),
    )
    capabilities.respostas["https://a.gov.br/ows"] = _caps("a:x")
    capabilities.respostas["https://b.gov.br/ows"] = fs.SondagemError("timeout", "demorou demais")
    capabilities.respostas["https://c.gov.br/ows"] = RuntimeError("bug inesperado")

    resumo = await fc.verificar_endpoints()

    assert (resumo.endpoints, resumo.ok, resumo.falhando, resumo.fora, resumo.erros) == (3, 1, 1, 1, 1)
    # Endpoint fora do ar marca `falhando`; exceção inesperada deixa a linha como estava.
    assert await _estados(fabrica) == {"a:x": "ok", "b:y": "falhando", "c:z": "nao_verificada"}


async def test_no_maximo_dois_endpoints_ao_mesmo_tempo(fabrica, monkeypatch):
    hosts = "abcdef"
    await _semear(fabrica, *((f"https://{h}.gov.br/ows", f"{h}:x", None) for h in hosts))
    ativos = {"agora": 0, "pico": 0}

    async def _lento(url, version="2.0.0"):
        ativos["agora"] += 1
        ativos["pico"] = max(ativos["pico"], ativos["agora"])
        await asyncio.sleep(0.01)
        ativos["agora"] -= 1
        return _caps(f"{url[8]}:x")

    monkeypatch.setattr(fs, "obter_capabilities", _lento)
    resumo = await fc.verificar_endpoints()
    assert (resumo.endpoints, resumo.ok) == (6, 6)
    assert 1 <= ativos["pico"] <= fc._PARALELISMO == 2


async def test_catalogo_vazio_e_uma_rodada_sem_sondagem(fabrica, capabilities):
    resumo = await fc.verificar_endpoints()
    assert resumo == fc.ResumoDaRodada() and capabilities.chamadas == []


# ── run_verificacao_loop ─────────────────────────────────────────────────────────

async def test_intervalo_zero_desliga_o_loop(monkeypatch):
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0)
    await asyncio.wait_for(fc.run_verificacao_loop(), 1.0)  # volta na hora, sem dormir


async def test_loop_verifica_a_cada_intervalo_com_lock_e_sobrevive_a_erro(lock, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0.01)
    rodadas: list[dict] = []

    async def _rodada(**kw):
        rodadas.append(kw)
        if len(rodadas) == 1:
            raise RuntimeError("banco fora")   # não derruba o loop
        if len(rodadas) == 3:
            raise asyncio.CancelledError       # o shutdown chega
        return fc.ResumoDaRodada()

    monkeypatch.setattr(fc, "verificar_endpoints", _rodada)
    await asyncio.wait_for(fc.run_verificacao_loop(), 2.0)
    assert rodadas == [{}, {}, {}]
    assert lock.chamadas == [(fc._LOCK_VERIFICACAO, 0.01)] * 3


async def test_loop_sem_lock_pula_a_rodada(lock, monkeypatch):
    monkeypatch.setattr(fc, "FONTES_VERIFICACAO_INTERVAL", 0.01)
    lock.livre = False
    rodadas: list[dict] = []

    async def _rodada(**kw):
        rodadas.append(kw)
        return fc.ResumoDaRodada()

    monkeypatch.setattr(fc, "verificar_endpoints", _rodada)
    tarefa = asyncio.create_task(fc.run_verificacao_loop())
    await asyncio.sleep(0.08)
    tarefa.cancel()
    await tarefa  # o loop trata o CancelledError e encerra sozinho
    assert rodadas == [] and len(lock.chamadas) >= 2


# ── Lifespan ─────────────────────────────────────────────────────────────────────
# O lock em si (SET NX EX no pool, Redis fora = prossegue) e o encerramento de
# cada tarefa de fundo estão em test_tarefas_de_fundo.py.

def test_lifespan_sobe_as_duas_tarefas():
    from app import main

    fabricas = [fabrica for _, fabrica in main._tarefas_de_fundo()]
    assert fc.importar_catalogo_no_arranque in fabricas
    assert fc.run_verificacao_loop in fabricas
