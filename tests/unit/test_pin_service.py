# tests/unit/test_pin_service.py
"""
Pins as a service — the rule both transports use.

This file exists because of a measured absence: before it,
`grep -rn '/pin\\b|/pins|pin_node_output|unpin_node_output|list_pinned_nodes|
PinOutputPayload' tests/` returned **one** hit, and it was a comment. The three
pin routes were never exercised — which is exactly how five defects stayed
armed in them without anyone noticing.

Each block below locks down one of them. All of them fail against the previous code.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.utils.datetime_utils import utc_now_naive
from app.models.artifact import Artifact
from app.models.base import Base
from app.services.workflow_execution_service import _safe_pinned_outputs
from app.models.models import Workflow
from app.services import pin_service
from tests.unit._mcp_harness import TABELAS

WF = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
WS = "11111111-1111-4111-8111-111111111111"


def _definicao() -> dict:
    return {
        "nodes": [
            {"id": "n1", "type": "action", "name": "PostgresQuery", "properties": {}},
            {"id": "n2", "type": "action", "name": "Buffer", "properties": {}},
            # A real output node, by the name the registry knows.
            {"id": "saida", "type": "output", "name": "DataOutput", "properties": {}},
        ],
        "edges": [{"source": "n1", "target": "n2"}],
    }


@pytest.fixture
async def banco():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as db:
        db.add(Workflow(id_hash=WF, name="Recorte", workspace_id=WS,
                        definition=_definicao(), flag_ative=True))
        await db.commit()
    try:
        yield fabrica
    finally:
        await engine.dispose()


@pytest.fixture
async def banco_sem_indice():
    """A database that has NOT yet run the partial unique index migration.

    The `uq_artifact_pin_por_no` index makes a pin-cache duplicate impossible
    to create — but the deploy does not run migrations, so there are production
    databases without it until someone runs `alembic upgrade head`. The code's
    tolerance (collapsing in the consumer, `ORDER BY id DESC LIMIT 1` on read)
    exists exactly for that world, and testing it requires reproducing it.

    Dropping the index after `create_all` is the honest way to say that:
    the test declares which database it is on, instead of the model diverging
    from the production schema to accommodate it.
    """
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
        await conn.execute(sa_text("DROP INDEX IF EXISTS uq_artifact_pin_por_no"))
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as db:
        db.add(Workflow(id_hash=WF, name="Recorte", workspace_id=WS,
                        definition=_definicao(), flag_ative=True))
        await db.commit()
    try:
        yield fabrica
    finally:
        await engine.dispose()


async def _fluxo(fabrica):
    async with fabrica() as db:
        wf = (await db.execute(select(Workflow).where(Workflow.id_hash == WF))).scalar_one()
        return db, wf


# ── Defect 1: GET /pins blew up with a 500 on a malformed date ───────────────
#
# Today's writer stores `utc_now_naive().isoformat()`, so none of these come
# from it. They come from the database: the column is JSON, it has seen other
# versions of the code, and bare `datetime.fromisoformat` breaks in four ways —
# all becoming a 500 in a LISTING, which is the operation that most needs to be
# robust, because it is the one a person opens precisely when something is wrong.


@pytest.mark.parametrize("sufixo, rotulo", [
    ("Z", "sufixo Z"),
    ("+00:00", "offset — TypeError ao comparar ciente com o ingênuo de utc_now_naive"),
])
def test_fuso_explicito_e_lido_em_vez_de_derrubar(sufixo, rotulo):
    """These two are READABLE — and they brought the route down anyway.

    Not raising is not enough: the date must actually be compared, otherwise an
    `except` returning `None` for everything would pass here and still could
    not tell that the pin expired. That is why the case is an expired one, and
    the assertion is `True` and not "did not raise".
    """
    ontem = (utc_now_naive() - timedelta(days=1)).isoformat() + sufixo

    pins = pin_service.listar_pins({"n1": {"expires_at": ontem}}, {})

    assert pins[0]["expired"] is True, rotulo


def test_o_sufixo_Z_e_normalizado_antes_do_parse(monkeypatch):
    """The case above does NOT prove this one, and the difference is the runtime.

    From 3.11 onward `datetime.fromisoformat` accepts `Z`; on **3.10** — the
    runtime and CI before 3.12 — it is the strict one and raises `ValueError`.
    The `.replace("Z", "+00:00")` is what separated "works" from "500" there,
    and deleting it would slip past any behavior test run on a newer Python
    (measured: the mutation survives).

    So 3.10 is simulated: a `datetime` whose `fromisoformat` rejects `Z`, which
    is the only relevant difference between the two versions. With the
    normalization, the parse gets `+00:00` and passes; without it, it gets the
    raw `Z` and the date becomes unreadable.
    """
    class _ComoNo310(datetime):
        @classmethod
        def fromisoformat(cls, s):
            if s.endswith("Z"):
                raise ValueError(f"Invalid isoformat string: {s!r}")
            return datetime.fromisoformat(s)

    monkeypatch.setattr(pin_service, "datetime", _ComoNo310)
    ontem = (utc_now_naive() - timedelta(days=1)).isoformat() + "Z"

    pins = pin_service.listar_pins({"n1": {"expires_at": ontem}}, {})

    assert pins[0]["expired"] is True, "no 3.10 isto seria 500 antes do conserto"


@pytest.mark.parametrize("valor, rotulo", [
    (1757937600, "número — TypeError no fromisoformat"),
    ("nem data isso é", "lixo — ValueError"),
    ("", "string vazia"),
])
def test_data_ilegivel_nao_derruba_a_listagem(valor, rotulo):
    pins = pin_service.listar_pins({"n1": {"expires_at": valor}}, {})

    assert len(pins) == 1, rotulo
    # `None` and not `False`: "there is a date and I cannot read it" is not "it
    # has not expired". Flattening the two would hide corrupted data behind a
    # reassuring answer.
    #
    # The empty string is the fair exception: `expires_at: ""` is
    # indistinguishable from "I did not store a deadline", and then `False` is
    # the right reading.
    esperado = False if valor == "" else None
    assert pins[0]["expired"] is esperado, rotulo


def test_entrada_de_metadata_que_nao_e_dict_nao_derruba_a_listagem():
    """The fifth way to break: `meta.get(nid, {})` returned the bare value, and
    the following `.get` was an AttributeError."""
    pins = pin_service.listar_pins({"n1": "isto não é um dict"}, {})

    assert pins[0]["node_id"] == "n1"
    assert pins[0]["expires_at"] is None


def test_pin_no_prazo_nao_e_marcado_como_vencido():
    """The counterpart of the case above: `expired` must be able to say NO."""
    amanha = (utc_now_naive() + timedelta(days=1)).isoformat() + "Z"
    assert pin_service.listar_pins({"n1": {"expires_at": amanha}}, {})[0]["expired"] is False


def test_sem_data_gravada_o_pin_nao_expira():
    assert pin_service.listar_pins({"n1": {"expires_at": None}}, {})[0]["expired"] is False


# ── Defect 2: ttl_hours without a range ──────────────────────────────────────


async def test_ttl_zero_e_recusado_em_vez_de_virar_sem_expiracao(banco):
    """`0` fell into the falsy branch and stored `expires_at: None`.

    Whoever types `0` is asking for "expires immediately" or made a mistake;
    under both readings, "never expires" is the opposite — and that is what
    happened, silently.
    """
    db, wf = await _fluxo(banco)
    with pytest.raises(ValueError):
        await pin_service.fixar_saida(db, wf, "n1", ttl_hours=0)


async def test_ttl_absurdo_e_recusado_antes_de_estourar(banco):
    """`now + timedelta(hours=10**9)` levanta OverflowError → 500."""
    db, wf = await _fluxo(banco)
    with pytest.raises(ValueError):
        await pin_service.fixar_saida(db, wf, "n1", ttl_hours=10 ** 9)


async def test_ttl_negativo_e_recusado(banco):
    db, wf = await _fluxo(banco)
    with pytest.raises(ValueError):
        await pin_service.fixar_saida(db, wf, "n1", ttl_hours=-5)


async def test_ttl_valido_grava_a_expiracao_esperada(banco):
    db, wf = await _fluxo(banco)
    saida = await pin_service.fixar_saida(db, wf, "n1", ttl_hours=24)

    assert saida["ttl_hours"] == 24
    delta = (
        pin_service._instante(saida["expires_at"])
        - pin_service._instante(saida["pinned_at"])
    )
    assert abs(delta - timedelta(hours=24)) < timedelta(seconds=2)


async def test_sem_ttl_o_pin_nao_expira(banco):
    db, wf = await _fluxo(banco)
    saida = await pin_service.fixar_saida(db, wf, "n1")
    assert saida["expires_at"] is None


# ── Defect 3: unpin deleted from storage BEFORE the commit ───────────────────


async def test_o_banco_fecha_antes_de_o_storage_ser_tocado(banco):
    """The order inversion is the module's central decision, and it has to bite.

    Before: `delete_async` and only twenty lines later the `commit()`. A commit
    failing there left `__pin_s3_key__` pointing at an object that no longer
    exists — and that does NOT heal, because `_safe_pinned_outputs` only fires
    auto-pin with an empty ref.

    The assertion is about the ORDER OF THE CALLS, not about what a second
    session sees. A second session does not work: in-memory SQLite uses
    `StaticPool`, so all sessions share the SAME connection and see each
    other's uncommitted data — with that, the mutation that removes the
    `commit()` survives (measured). Recording the sequence is what tells them apart.
    """
    db, wf = await _fluxo(banco)
    await pin_service.fixar_saida(db, wf, "n1")
    wf.pinned_outputs = {"n1": {"__pin_s3_key__": f"pin-cache/{WS}/n1.geojson"}}
    await db.commit()

    ordem: list[str] = []
    commit_real = db.commit

    async def _commit():
        ordem.append("commit")
        await commit_real()

    async def _apagar(chave, **kw):
        ordem.append("storage")

    with patch.object(db, "commit", _commit), \
         patch("app.core.storage.delete_strict_async", side_effect=_apagar):
        await pin_service.desfixar_saida(db, wf, "n1")

    assert ordem == ["commit", "storage"], (
        f"ordem observada: {ordem}. O storage antes do commit é o que deixava "
        f"referência pendurada quando o commit falhava depois."
    )


async def test_falha_do_storage_nao_desfaz_o_unpin_e_vira_aviso(banco):
    """The pin is already gone. Answering with an error would make the client repeat what already happened."""
    db, wf = await _fluxo(banco)
    await pin_service.fixar_saida(db, wf, "n1")
    wf.pinned_outputs = {"n1": {"__pin_s3_key__": f"pin-cache/{WS}/n1.geojson"}}
    await db.commit()

    with patch("app.core.storage.delete_strict_async",
               side_effect=RuntimeError("MinIO fora")):
        saida = await pin_service.desfixar_saida(db, wf, "n1")

    assert saida["outcome"] == "unpinned"
    assert "storage_warning" in saida
    async with banco() as outra:
        atual = (await outra.execute(
            select(Workflow).where(Workflow.id_hash == WF)
        )).scalar_one()
    assert not (atual.pinned_outputs or {})


async def test_desfixar_o_que_nao_estava_fixado_nao_e_erro(banco):
    db, wf = await _fluxo(banco)
    saida = await pin_service.desfixar_saida(db, wf, "n1")
    assert saida["outcome"] == "not_pinned"


async def test_as_duas_chaves_sao_apagadas_quando_divergem(banco):
    """The ref and the `Artifact` row can point to different objects.

    The previous code only deleted the ref's object and removed the ROW — the
    row's object stayed in MinIO with nothing referencing it.
    """
    db, wf = await _fluxo(banco)
    wf.pinned_outputs = {"n1": {"__pin_s3_key__": f"pin-cache/{WS}/velho.geojson"}}
    wf.pin_metadata = {"n1": {"pinned_at": utc_now_naive().isoformat()}}
    db.add(Artifact(workspace_id=WS, workflow_hash=WF, node_id="n1",
                    output_key="pin-cache-n1", filename="novo.geojson",
                    s3_key=f"pin-cache/{WS}/novo.geojson", is_pinned=True))
    await db.commit()

    falso = AsyncMock()
    with patch("app.core.storage.delete_strict_async", new=falso):
        await pin_service.desfixar_saida(db, wf, "n1")

    apagadas = {c.args[0] for c in falso.await_args_list}
    assert apagadas == {f"pin-cache/{WS}/velho.geojson", f"pin-cache/{WS}/novo.geojson"}


# ── Defeito 4: leitura levantava com linha duplicada ─────────────────────────


async def test_duas_linhas_de_pin_cache_nao_derrubam_o_unpin(banco_sem_indice):
    """`scalar_one_or_none()` raised `MultipleResultsFound` → 500.

    And two rows were reachable: without the partial unique index, the
    consumer's `_upsert_pin_artifact` inserts when it finds nothing, and two runs
    of the same workflow finishing together each insert their own. The
    2026-09-15 migration closes that door; this tolerance still holds for the
    database that has not run it yet — hence the `banco_sem_indice` fixture.
    """
    db, wf = await _fluxo(banco_sem_indice)
    for n in ("a", "b"):
        db.add(Artifact(workspace_id=WS, workflow_hash=WF, node_id="n1",
                        output_key="pin-cache-n1", filename=f"{n}.geojson",
                        s3_key=f"pin-cache/{WS}/{n}.geojson", is_pinned=True))
    wf.pin_metadata = {"n1": {"pinned_at": utc_now_naive().isoformat()}}
    await db.commit()

    with patch("app.core.storage.delete_strict_async", new=AsyncMock()):
        saida = await pin_service.desfixar_saida(db, wf, "n1")

    assert saida["outcome"] == "unpinned"


async def test_com_duas_linhas_a_mais_nova_e_a_escolhida(banco_sem_indice):
    """Picking the old one would re-point the pin to an object from a past run."""
    async with banco_sem_indice() as db:
        for n in ("velha", "nova"):
            db.add(Artifact(workspace_id=WS, workflow_hash=WF, node_id="n1",
                            output_key="pin-cache-n1", filename=f"{n}.geojson",
                            s3_key=f"pin-cache/{WS}/{n}.geojson", is_pinned=True))
        await db.commit()

        escolhida = await pin_service._artefato_de_pin(db, WF, "n1")

    assert escolhida.filename == "nova.geojson"


# ── The orphan that unpin resurrected ────────────────────────────────────────


async def test_desfixar_o_ultimo_pin_nao_ressuscita_uma_orfa(banco):
    """Ties the REAL unpin to the dispatch filter, which is where the damage showed up.

    The filter's unit test (`test_workflow_service.py`) proves the rule. This
    one proves the value: `desfixar_saida` stores `pin_metadata = None` when it
    deletes the last pin, and it was that empty column that made the filter
    let everything through.

    Scenario: A is a real pin, B is an orphan with `__pin_s3_key__` — left over
    from a node removed from the definition. While A exists, B stays out.
    Unpinning A empties the metadata, and before this fix B went back to the
    executor on the next run, as a cache that **never expires** (the validity
    is read from `pin_metadata[node_id]`, which does not exist for it).
    """
    db, wf = await _fluxo(banco)
    db.add(Artifact(workspace_id=WS, workflow_hash=WF, node_id="A",
                    output_key="pin-cache-A", filename="a.geojson",
                    s3_key=f"pin-cache/{WS}/a.geojson", is_pinned=True))
    wf.pinned_outputs = {
        "A": {"__pin_s3_key__": f"pin-cache/{WS}/a.geojson"},
        "B": {"__pin_s3_key__": f"pin-cache/{WS}/orfa.geojson"},
    }
    wf.pin_metadata = {"A": {"pinned_at": utc_now_naive().isoformat()}}
    await db.commit()

    # Before the unpin: only A is dispatched. B is an orphan and already stayed out.
    assert set(_safe_pinned_outputs(wf.pinned_outputs, wf.pin_metadata)) == {"A"}

    with patch("app.core.storage.delete_strict_async", new=AsyncMock()):
        saida = await pin_service.desfixar_saida(db, wf, "A")

    assert saida["outcome"] == "unpinned"
    assert wf.pin_metadata is None, "é este None que fazia o filtro liberar tudo"

    # After the unpin: NOTHING is dispatched. B must not come back.
    assert _safe_pinned_outputs(wf.pinned_outputs, wf.pin_metadata) == {}


# ── The output-node gate ─────────────────────────────────────────────────────


def test_o_discriminador_de_no_de_saida_e_o_registro_de_verdade():
    """Without this, the gate could be looking at a key that does not exist.

    `DataOutput` declares `"type": "output"` in `description()`; `Buffer` does
    not. If the field is renamed in the registry, this test fails — and it is
    what keeps the gate from becoming an `if` that never closes.
    """
    assert pin_service.e_no_de_saida("DataOutput") is True
    assert pin_service.e_no_de_saida("Buffer") is False


def test_nome_desconhecido_nao_fecha_o_portao():
    """Refusing what is not recognized would make every new node unpinnable."""
    assert pin_service.e_no_de_saida("NoQueNaoExiste") is False
    assert pin_service.e_no_de_saida(None) is False


async def test_fixar_no_de_saida_e_recusado(banco):
    """Freezing the output of a node that writes a file makes the executor SKIP
    the write: the workflow finishes green and the file does not show up."""
    db, wf = await _fluxo(banco)
    with pytest.raises(pin_service.PinEmNoDeSaidaError):
        await pin_service.fixar_saida(db, wf, "saida")


async def test_fixar_no_comum_continua_passando(banco):
    """The gate cannot be a `raise` that catches everyone."""
    db, wf = await _fluxo(banco)
    saida = await pin_service.fixar_saida(db, wf, "n1")
    assert saida["pinned"] == "n1"


async def test_a_rota_nao_passa_a_recusar_no_inexistente(banco):
    """`exigir_no_existente=False` exists so as not to change the screen's contract.

    Pinning an id the definition does not have is useless, but turning that into
    an error on a route that already existed would break compatibility — and
    MCP, which is new, asks for the check.
    """
    db, wf = await _fluxo(banco)
    saida = await pin_service.fixar_saida(db, wf, "fantasma", exigir_no_existente=False)
    assert saida["pinned"] == "fantasma"

    with pytest.raises(pin_service.NoInexistenteError):
        await pin_service.fixar_saida(db, wf, "fantasma2", exigir_no_existente=True)


# ── The read both transports share ───────────────────────────────────────────


def test_a_listagem_percorre_a_uniao_das_duas_colunas():
    """The two previous readers disagreed, and each one lost half.

    The route iterated `pinned_outputs`; MCP iterated `pin_metadata`. An
    auto-pin entry without metadata vanished from MCP's view, and an intent whose
    cache never materialized vanished from the screen's view. Only the union loses none.
    """
    pins = pin_service.listar_pins(
        {"so_intencao": {"pinned_at": "2026-01-01T00:00:00"}},
        {"so_cache": {"__pin_s3_key__": f"pin-cache/{WS}/x.geojson"}},
    )

    assert {p["node_id"] for p in pins} == {"so_intencao", "so_cache"}


def test_cached_distingue_pin_pedido_de_pin_materializado():
    """It is the answer to "why does my workflow keep recomputing"."""
    pins = pin_service.listar_pins(
        {"a": {}, "b": {}},
        {"a": {}, "b": {"__pin_s3_key__": f"pin-cache/{WS}/b.geojson"}},
    )
    por_id = {p["node_id"]: p for p in pins}

    assert por_id["a"]["cached"] is False
    assert por_id["b"]["cached"] is True


def test_o_filtro_de_nos_existentes_e_opcional_e_so_o_MCP_o_usa():
    """The screen needs to see the orphan pin — it is the one that will clean it up."""
    metadata = {"n1": {}, "apagado": {}}

    sem_filtro = pin_service.listar_pins(metadata, {})
    com_filtro = pin_service.listar_pins(metadata, {}, node_ids_existentes={"n1"})

    assert {p["node_id"] for p in sem_filtro} == {"n1", "apagado"}
    assert {p["node_id"] for p in com_filtro} == {"n1"}


async def test_desfixar_nao_apaga_chave_de_outro_workspace(banco):
    """Audit SEG-10: a `__pin_s3_key__` outside the prefix of the workflow's
    workspace (forged input) is IGNORED on delete — it never deletes someone else's object."""
    db, wf = await _fluxo(banco)
    wf.pinned_outputs = {"n1": {"__pin_s3_key__": "pin-cache/OUTRO-WS/segredo.geojson"}}
    wf.pin_metadata = {"n1": {"pinned_at": utc_now_naive().isoformat()}}
    await db.commit()

    falso = AsyncMock()
    with patch("app.core.storage.delete_strict_async", new=falso):
        await pin_service.desfixar_saida(db, wf, "n1")

    assert falso.await_count == 0  # nothing was deleted


async def test_fixar_nao_persiste_chave_forjada_do_cliente(banco):
    """Audit SEG-10: the client's `outputs` is never stored; a forged
    `__pin_s3_key__` is rejected, and the pin stays `{}`."""
    db, wf = await _fluxo(banco)
    with pytest.raises(ValueError):
        await pin_service.fixar_saida(
            db, wf, "n1", outputs={"__pin_s3_key__": "pin-cache/OUTRO-WS/x"},
            exigir_no_existente=False,
        )
    # And the normal path stores {} (not the client's content).
    await pin_service.fixar_saida(db, wf, "n1", outputs={"lixo": 1}, exigir_no_existente=False)
    assert wf.pinned_outputs["n1"] == {}
