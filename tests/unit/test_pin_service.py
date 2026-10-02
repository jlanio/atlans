# tests/unit/test_pin_service.py
"""
Os pins como serviço — a regra que os dois transportes usam.

Este arquivo existe por causa de uma ausência medida: antes dele,
`grep -rn '/pin\\b|/pins|pin_node_output|unpin_node_output|list_pinned_nodes|
PinOutputPayload' tests/` devolvia **um** acerto, e era um comentário. As três
rotas de pin nunca foram exercitadas — o que é exatamente como cinco defeitos
ficaram armados nelas sem ninguém notar.

Cada bloco abaixo trava um deles. Todos falham contra o código anterior.
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
            # Um nó de saída de verdade, pelo nome que o registro conhece.
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
    """Uma base que ainda NÃO rodou a migração do índice único parcial.

    O índice `uq_artifact_pin_por_no` torna a duplicata de pin-cache impossível
    de criar — mas o deploy não roda migração, então existe base em produção
    sem ele até alguém rodar `alembic upgrade head`. A tolerância do código
    (colapso no consumer, `ORDER BY id DESC LIMIT 1` na leitura) existe
    exatamente para esse mundo, e testá-la exige reproduzi-lo.

    Derrubar o índice depois do `create_all` é o jeito honesto de dizer isso:
    o teste declara em qual base está, em vez de o modelo divergir do schema
    de produção para acomodá-lo.
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


# ── Defeito 1: o GET /pins estourava 500 com data malformada ─────────────────
#
# O escritor de hoje grava `utc_now_naive().isoformat()`, então nenhum destes
# vem dele. Vêm do banco: a coluna é JSON, já viu outras versões do código, e
# `datetime.fromisoformat` nu quebra de quatro jeitos — todos virando 500 numa
# LISTAGEM, que é a operação que mais precisa ser robusta, porque é a que a
# pessoa abre justamente quando algo está errado.


@pytest.mark.parametrize("sufixo, rotulo", [
    ("Z", "sufixo Z"),
    ("+00:00", "offset — TypeError ao comparar ciente com o ingênuo de utc_now_naive"),
])
def test_fuso_explicito_e_lido_em_vez_de_derrubar(sufixo, rotulo):
    """Estes dois são LEGÍVEIS — e derrubavam a rota mesmo assim.

    Não basta não levantar: a data tem de ser de fato comparada, senão um
    `except` que devolvesse `None` para tudo passaria aqui e ainda assim não
    saberia dizer que o pin venceu. Por isso o caso é de vencido, e a asserção
    é `True` e não "não levantou".
    """
    ontem = (utc_now_naive() - timedelta(days=1)).isoformat() + sufixo

    pins = pin_service.listar_pins({"n1": {"expires_at": ontem}}, {})

    assert pins[0]["expired"] is True, rotulo


def test_o_sufixo_Z_e_normalizado_antes_do_parse(monkeypatch):
    """O caso acima NÃO prova este, e a diferença é o runtime.

    Do 3.11 em diante `datetime.fromisoformat` já aceita `Z`; no **3.10** — o
    runtime e o CI antes do 3.12 — ele é o restrito e levanta `ValueError`. O
    `.replace("Z", "+00:00")` é o que separava "funciona" de "500" lá, e
    apagá-lo passaria batido por qualquer teste de comportamento rodado num
    Python novo (medido: a mutação sobrevive).

    Então o 3.10 é simulado: um `datetime` cujo `fromisoformat` recusa `Z`, que
    é a única diferença relevante entre as duas versões. Com a normalização, o
    parse recebe `+00:00` e passa; sem ela, recebe o `Z` cru e a data vira
    ilegível.
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
    # `None` e não `False`: "há uma data e eu não consigo lê-la" não é "não
    # expirou". Achatar os dois esconderia dado corrompido atrás de uma
    # resposta tranquilizadora.
    #
    # A string vazia é a exceção justa: `expires_at: ""` é indistinguível de
    # "não gravei prazo", e aí `False` é a leitura certa.
    esperado = False if valor == "" else None
    assert pins[0]["expired"] is esperado, rotulo


def test_entrada_de_metadata_que_nao_e_dict_nao_derruba_a_listagem():
    """O quinto jeito de quebrar: `meta.get(nid, {})` devolvia o valor solto, e
    o `.get` seguinte era AttributeError."""
    pins = pin_service.listar_pins({"n1": "isto não é um dict"}, {})

    assert pins[0]["node_id"] == "n1"
    assert pins[0]["expires_at"] is None


def test_pin_no_prazo_nao_e_marcado_como_vencido():
    """O contraponto do caso de cima: `expired` tem de saber dizer NÃO."""
    amanha = (utc_now_naive() + timedelta(days=1)).isoformat() + "Z"
    assert pin_service.listar_pins({"n1": {"expires_at": amanha}}, {})[0]["expired"] is False


def test_sem_data_gravada_o_pin_nao_expira():
    assert pin_service.listar_pins({"n1": {"expires_at": None}}, {})[0]["expired"] is False


# ── Defeito 2: ttl_hours sem faixa ───────────────────────────────────────────


async def test_ttl_zero_e_recusado_em_vez_de_virar_sem_expiracao(banco):
    """`0` caía no ramo falsy e gravava `expires_at: None`.

    Quem digita `0` está pedindo "vence imediatamente" ou errou; nas duas
    leituras, "nunca vence" é o oposto — e era o que acontecia, calado.
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


# ── Defeito 3: o unpin apagava do storage ANTES do commit ────────────────────


async def test_o_banco_fecha_antes_de_o_storage_ser_tocado(banco):
    """A inversão de ordem é a decisão central do módulo, e ela precisa morder.

    Antes: `delete_async` e só vinte linhas depois o `commit()`. Commit falhar
    ali deixava `__pin_s3_key__` apontando para objeto que não existe mais — e
    isso NÃO se cura, porque `_safe_pinned_outputs` só dispara auto-pin com ref
    vazia.

    A asserção é sobre a ORDEM DAS CHAMADAS, e não sobre o que uma segunda
    sessão enxerga. A segunda sessão não serve: o SQLite em memória usa
    `StaticPool`, então todas as sessões compartilham a MESMA conexão e
    enxergam o não-commitado uma da outra — com isso a mutação que remove o
    `commit()` sobrevive (medido). Gravar a sequência é o que distingue.
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
    """O pin já saiu. Responder erro faria o cliente repetir o que já aconteceu."""
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
    """A ref e a linha `Artifact` podem apontar para objetos diferentes.

    O código anterior só apagava a da ref e removia a LINHA — o objeto da linha
    ficava no MinIO sem nada que o referenciasse.
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
    """`scalar_one_or_none()` levantava `MultipleResultsFound` → 500.

    E duas linhas eram alcançáveis: sem o índice único parcial, o
    `_upsert_pin_artifact` do consumidor insere quando não acha, e dois runs do
    mesmo fluxo terminando juntos inserem cada um a sua. A migração de
    2026-09-15 fecha essa porta; esta tolerância continua valendo para a base
    que ainda não a rodou — daí a fixture `banco_sem_indice`.
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
    """Escolher a antiga repontaria o pin para um objeto de uma run passada."""
    async with banco_sem_indice() as db:
        for n in ("velha", "nova"):
            db.add(Artifact(workspace_id=WS, workflow_hash=WF, node_id="n1",
                            output_key="pin-cache-n1", filename=f"{n}.geojson",
                            s3_key=f"pin-cache/{WS}/{n}.geojson", is_pinned=True))
        await db.commit()

        escolhida = await pin_service._artefato_de_pin(db, WF, "n1")

    assert escolhida.filename == "nova.geojson"


# ── A órfã que o unpin ressuscitava ──────────────────────────────────────────


async def test_desfixar_o_ultimo_pin_nao_ressuscita_uma_orfa(banco):
    """Amarra o unpin REAL ao filtro do despacho, que é onde o dano aparecia.

    O teste unitário do filtro (`test_workflow_service.py`) prova a regra. Este
    prova o valor: `desfixar_saida` grava `pin_metadata = None` quando apaga o
    último pin, e era essa coluna vazia que fazia o filtro liberar tudo.

    Cenário: A é um pin de verdade, B é órfã com `__pin_s3_key__` — resto de um
    nó removido da definição. Enquanto A existe, B fica de fora. Desfixar A
    esvazia a metadata, e antes deste conserto B voltava ao executor na
    execução seguinte, como cache que **nunca expira** (a validade é lida de
    `pin_metadata[node_id]`, que não existe para ela).
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

    # Antes do unpin: só A é despachada. B é órfã e já ficava de fora.
    assert set(_safe_pinned_outputs(wf.pinned_outputs, wf.pin_metadata)) == {"A"}

    with patch("app.core.storage.delete_strict_async", new=AsyncMock()):
        saida = await pin_service.desfixar_saida(db, wf, "A")

    assert saida["outcome"] == "unpinned"
    assert wf.pin_metadata is None, "é este None que fazia o filtro liberar tudo"

    # Depois do unpin: NADA é despachado. B não pode voltar.
    assert _safe_pinned_outputs(wf.pinned_outputs, wf.pin_metadata) == {}


# ── O portão do nó de saída ──────────────────────────────────────────────────


def test_o_discriminador_de_no_de_saida_e_o_registro_de_verdade():
    """Sem isto, o portão poderia estar olhando para uma chave que não existe.

    `DataOutput` declara `"type": "output"` em `description()`; `Buffer` não.
    Se o campo mudar de nome no registro, este teste cai — e é ele que impede o
    portão de virar um `if` que nunca fecha.
    """
    assert pin_service.e_no_de_saida("DataOutput") is True
    assert pin_service.e_no_de_saida("Buffer") is False


def test_nome_desconhecido_nao_fecha_o_portao():
    """Recusar o que não se reconhece tornaria todo nó novo não-fixável."""
    assert pin_service.e_no_de_saida("NoQueNaoExiste") is False
    assert pin_service.e_no_de_saida(None) is False


async def test_fixar_no_de_saida_e_recusado(banco):
    """Congelar a saída de um nó que grava arquivo faz o executor PULAR a
    gravação: o fluxo termina verde e o arquivo não aparece."""
    db, wf = await _fluxo(banco)
    with pytest.raises(pin_service.PinEmNoDeSaidaError):
        await pin_service.fixar_saida(db, wf, "saida")


async def test_fixar_no_comum_continua_passando(banco):
    """O portão não pode ser um `raise` que pegou todo mundo."""
    db, wf = await _fluxo(banco)
    saida = await pin_service.fixar_saida(db, wf, "n1")
    assert saida["pinned"] == "n1"


async def test_a_rota_nao_passa_a_recusar_no_inexistente(banco):
    """`exigir_no_existente=False` existe para não mudar o contrato da tela.

    Fixar um id que a definition não tem é inútil, mas transformar isso em erro
    numa rota que já existia seria quebra de compatibilidade — e o MCP, que é
    novo, pede a checagem.
    """
    db, wf = await _fluxo(banco)
    saida = await pin_service.fixar_saida(db, wf, "fantasma", exigir_no_existente=False)
    assert saida["pinned"] == "fantasma"

    with pytest.raises(pin_service.NoInexistenteError):
        await pin_service.fixar_saida(db, wf, "fantasma2", exigir_no_existente=True)


# ── A leitura que os dois transportes compartilham ───────────────────────────


def test_a_listagem_percorre_a_uniao_das_duas_colunas():
    """Os dois leitores anteriores discordavam, e cada um perdia metade.

    A rota iterava `pinned_outputs`; o MCP iterava `pin_metadata`. Uma entrada
    de auto-pin sem metadata sumia da visão do MCP, e uma intenção cujo cache
    nunca materializou sumia da visão da tela. Só a união não perde nenhuma.
    """
    pins = pin_service.listar_pins(
        {"so_intencao": {"pinned_at": "2026-01-01T00:00:00"}},
        {"so_cache": {"__pin_s3_key__": f"pin-cache/{WS}/x.geojson"}},
    )

    assert {p["node_id"] for p in pins} == {"so_intencao", "so_cache"}


def test_cached_distingue_pin_pedido_de_pin_materializado():
    """É a resposta para "por que meu fluxo continua recalculando"."""
    pins = pin_service.listar_pins(
        {"a": {}, "b": {}},
        {"a": {}, "b": {"__pin_s3_key__": f"pin-cache/{WS}/b.geojson"}},
    )
    por_id = {p["node_id"]: p for p in pins}

    assert por_id["a"]["cached"] is False
    assert por_id["b"]["cached"] is True


def test_o_filtro_de_nos_existentes_e_opcional_e_so_o_MCP_o_usa():
    """A tela precisa enxergar o pin órfão — é ela que vai limpá-lo."""
    metadata = {"n1": {}, "apagado": {}}

    sem_filtro = pin_service.listar_pins(metadata, {})
    com_filtro = pin_service.listar_pins(metadata, {}, node_ids_existentes={"n1"})

    assert {p["node_id"] for p in sem_filtro} == {"n1", "apagado"}
    assert {p["node_id"] for p in com_filtro} == {"n1"}


async def test_desfixar_nao_apaga_chave_de_outro_workspace(banco):
    """Auditoria SEG-10: um `__pin_s3_key__` fora do prefixo do workspace do
    fluxo (entrada forjada) é IGNORADO no delete — nunca apaga objeto alheio."""
    db, wf = await _fluxo(banco)
    wf.pinned_outputs = {"n1": {"__pin_s3_key__": "pin-cache/OUTRO-WS/segredo.geojson"}}
    wf.pin_metadata = {"n1": {"pinned_at": utc_now_naive().isoformat()}}
    await db.commit()

    falso = AsyncMock()
    with patch("app.core.storage.delete_strict_async", new=falso):
        await pin_service.desfixar_saida(db, wf, "n1")

    assert falso.await_count == 0  # nada foi apagado


async def test_fixar_nao_persiste_chave_forjada_do_cliente(banco):
    """Auditoria SEG-10: `outputs` do cliente nunca é gravado; um
    `__pin_s3_key__` forjado é recusado, e o pin fica `{}`."""
    db, wf = await _fluxo(banco)
    with pytest.raises(ValueError):
        await pin_service.fixar_saida(
            db, wf, "n1", outputs={"__pin_s3_key__": "pin-cache/OUTRO-WS/x"},
            exigir_no_existente=False,
        )
    # E o caminho normal grava {} (não o conteúdo do cliente).
    await pin_service.fixar_saida(db, wf, "n1", outputs={"lixo": 1}, exigir_no_existente=False)
    assert wf.pinned_outputs["n1"] == {}
