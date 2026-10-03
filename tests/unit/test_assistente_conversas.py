# tests/unit/test_assistente_conversas.py
"""
The assistant's conversation service — persistence, transcript and replay.

What matters most here: the round-trip of the blocks in the project's format. The
transcript crosses the database as JSON and goes back to the model; if persistence
lost the `reasoning_details` of the reasoning block, the model would lose the thread
on the next turn — the same cruel defect as the orphaned `tool_use`, only on resume.
"""
from __future__ import annotations

import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.conversa import Conversa, Mensagem
from app.models.models import Workflow
from app.models.user import User
from app.services import assistente_conversas as svc
from app.services import assistente_superficie as ag

from ._mcp_harness import RedisFalso

pytestmark = pytest.mark.asyncio

USUARIO = "usr-1"


@pytest_asyncio.fixture
async def sessao():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                User.__table__, Conversa.__table__, Mensagem.__table__,
                # O rastro auditavel resolve o workspace do fluxo alvo.
                Workflow.__table__, AuditEvent.__table__,
            ],
        )
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        s.add(User(id_hash=USUARIO, username="ana", email="a@x.test", hashed_password="x"))
        await s.commit()
        yield s
    await engine.dispose()


# ── Titulo ────────────────────────────────────────────────────────────────────


async def test_titulo_automatico_corta_em_60_e_normaliza_espacos():
    assert svc.titulo_automatico("  monta   um fluxo  ") == "monta um fluxo"
    longa = "x" * 200
    assert len(svc.titulo_automatico(longa)) == 60
    assert svc.titulo_automatico("") == "Nova conversa"


# ── Round-trip with the project's blocks ─────────────────────────────────────


async def test_transcrito_round_trip_preserva_os_blocos_e_o_raciocinio(sessao):
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")
    # The blocks as the model client reassembles them and the loop writes them.
    blocos = [
        {
            "type": "thinking",
            "thinking": "preciso do catalogo",
            "reasoning_details": [
                {"type": "reasoning.text", "text": "preciso do catalogo", "signature": "assin-123", "index": 0},
            ],
        },
        {"type": "text", "text": "vou montar"},
        {"type": "tool_use", "id": "tu-1", "name": "search_nodes", "input": {"query": "buffer"}},
    ]
    await svc.anexar_mensagens(
        sessao,
        conv.id_hash,
        [
            {"role": "user", "content": "monta um fluxo"},
            {"role": "assistant", "content": blocos},
        ],
        ordem_inicial=0,
    )

    transcrito = await svc.transcrito_de(sessao, conv.id_hash)

    # Serializable (Redis/JSON require it), and the format the client translates on the way out.
    json.dumps(transcrito)
    assert transcrito[0] == {"role": "user", "content": "monta um fluxo"}
    saidos = transcrito[1]["content"]
    pensamento = next(b for b in saidos if b["type"] == "thinking")
    # The reasoning SURVIVED the database, verbatim — it is what goes back to the provider.
    assert pensamento["reasoning_details"][0]["signature"] == "assin-123"
    assert pensamento["thinking"] == "preciso do catalogo"


async def test_replay_com_blocos_reais_tem_vocabulario_e_nao_vaza_tool_result(sessao):
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")
    conv.tokens_total = 99
    await sessao.commit()
    assistente = [
        {"type": "text", "text": "pronto"},
        {"type": "tool_use", "id": "tu-1", "name": "run_workflow", "input": {"workflow_id": "wf-1"}},
    ]
    await svc.anexar_mensagens(
        sessao,
        conv.id_hash,
        [
            {"role": "user", "content": "roda o fluxo"},
            {"role": "assistant", "content": assistente},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu-1", "content": "{}", "is_error": False}]},
        ],
        ordem_inicial=0,
    )

    quadros = await svc.quadros_do_replay(
        sessao, conv.id_hash, redis=RedisFalso(), user_id=USUARIO, tokens_total=conv.tokens_total
    )

    tipos = [q["tipo"] for q in quadros]
    assert tipos == ["usuario", "texto", "ferramenta", "ferramenta_fim", "fim"]
    assert "tool_result" not in json.dumps(quadros)
    assert quadros[-1]["dados"]["uso"]["total"] == 99


# ── Confirmacao ───────────────────────────────────────────────────────────────


async def test_consumir_confirmacao_e_one_shot():
    redis = RedisFalso()
    chave = ag.chave_de_confirmacao(USUARIO, "conv-1", "tu-1")
    redis.dados[chave] = json.dumps({"token": "t", "tool": "delete_schedule", "args": {}})

    ler = await svc.ler_confirmacao(redis, USUARIO, "conv-1", "tu-1")
    assert ler["token"] == "t"
    # O primeiro consumo vence; o segundo perde a corrida.
    assert await svc.consumir_confirmacao(redis, USUARIO, "conv-1", "tu-1") is True
    assert await svc.consumir_confirmacao(redis, USUARIO, "conv-1", "tu-1") is False
    assert chave not in redis.dados


async def test_carregar_conversa_alheia_ou_apagada_e_404(sessao):
    minha = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="minha")
    alheia = await svc.criar_conversa(sessao, user_id="outro", titulo="alheia")

    # A minha carrega.
    assert (await svc.carregar_conversa_da_pessoa(sessao, USUARIO, minha.id_hash)).id_hash == minha.id_hash
    # Someone else's is 404 (not 403: it doesn't reveal that the id exists).
    with pytest.raises(HTTPException) as exc:
        await svc.carregar_conversa_da_pessoa(sessao, USUARIO, alheia.id_hash)
    assert exc.value.status_code == 404
    # A deleted one disappears.
    await svc.apagar_conversa(sessao, USUARIO, minha.id_hash)
    with pytest.raises(HTTPException) as exc2:
        await svc.carregar_conversa_da_pessoa(sessao, USUARIO, minha.id_hash)
    assert exc2.value.status_code == 404


# ── Replay rebuilds the `exibir_no_globo` layer ───────────────────────────────


async def test_replay_reconstroi_a_camada_de_exibir_no_globo(sessao):
    """Reopening the chat has to bring the layer back to the globe.

    The `camada` frame was emitted inline by the local executor: it showed up in
    the SSE and vanished on replay, which only re-runs `quadros_extras`. Now it is
    born from the arguments, and a single path serves both.
    """
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")
    chamada = {
        "type": "tool_use", "id": "tu-globo", "name": ag.NOME_DO_GLOBO,
        "input": {"artifact_id": "art-9", "nome": "Focos"},
    }
    await svc.anexar_mensagens(
        sessao,
        conv.id_hash,
        [
            {"role": "user", "content": "exibe o art-9"},
            {"role": "assistant", "content": [chamada]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu-globo", "content": "ok", "is_error": False}]},
        ],
        ordem_inicial=0,
    )

    quadros = await svc.quadros_do_replay(
        sessao, conv.id_hash, redis=RedisFalso(), user_id=USUARIO, tokens_total=0
    )

    camadas = [q for q in quadros if q["tipo"] == "camada"]
    assert len(camadas) == 1
    assert camadas[0]["dados"] == {"artifact_id": "art-9", "nome": "Focos", "available": True}


# ── Transcript order and closing ─────────────────────────────────────────────


async def test_proxima_ordem_e_max_mais_um(sessao):
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")
    assert await svc.proxima_ordem(sessao, conv.id_hash) == 0

    sessao.add(Mensagem(conversa_id=conv.id_hash, ordem=0, papel="user", blocos="a"))
    sessao.add(Mensagem(conversa_id=conv.id_hash, ordem=9, papel="user", blocos="b"))
    await sessao.commit()

    # The count would be 2 — and would collide with order 0, already used.
    assert await svc.proxima_ordem(sessao, conv.id_hash) == 10


async def test_transcrito_fecha_tool_use_orfao_e_pode_persistir_o_fecho(sessao):
    """An unpaired `tool_use` makes the API reject the whole conversation. Closed on READ."""
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")
    await svc.anexar_mensagens(
        sessao,
        conv.id_hash,
        [
            {"role": "user", "content": "roda"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "tu-orfa", "name": "run_workflow", "input": {}}
            ]},
        ],
        ordem_inicial=0,
    )

    # Leitura pura: fecha em memoria e NAO grava nada.
    somente_leitura = await svc.transcrito_de(sessao, conv.id_hash)
    assert somente_leitura[-1]["content"][0]["tool_use_id"] == "tu-orfa"
    assert await svc.proxima_ordem(sessao, conv.id_hash) == 2

    # To RESUME, the closing has to go to the database: otherwise the new message would
    # land after the orphan and the next read would no longer close anything.
    await svc.transcrito_de(sessao, conv.id_hash, persistir_fecho=True)
    assert await svc.proxima_ordem(sessao, conv.id_hash) == 3
    # Idempotent: already closed, does not write again.
    await svc.transcrito_de(sessao, conv.id_hash, persistir_fecho=True)
    assert await svc.proxima_ordem(sessao, conv.id_hash) == 3


# ── Rastro auditavel: o workspace da linha ────────────────────────────────────


async def _fluxo(sessao, hash_, workspace, *, deleted_at=None):
    sessao.add(Workflow(
        id_hash=hash_, name=hash_, workspace_id=workspace, deleted_at=deleted_at,
        definition={"nodes": [], "edges": []}, flag_ative=True,
    ))
    await sessao.commit()


async def _auditar(sessao, *, workflow_id, workspace_ids, padrao="ws-da-conversa"):
    await svc.registrar_acao_confirmada(
        sessao,
        user_id=USUARIO,
        conversa_id="conv-1",
        tool="update_workflow",
        args={"workflow_id": workflow_id},
        tool_use_id=f"tu-{workflow_id}",
        decisao="confirmar",
        erro=False,
        workspace_padrao=padrao,
        workspace_ids=workspace_ids,
    )


async def test_alvo_fora_do_alcance_nao_escreve_na_trilha_alheia(sessao):
    """The `workflow_id` comes from the stored args: resolving its workspace without
    scoping put the `AuditEvent` in the trail of a workspace the person isn't even
    a member of — and hid the record from whoever should see it."""
    await _fluxo(sessao, "wf-alheio", "ws-alheio")
    await _fluxo(sessao, "wf-meu", "ws-b")
    await _fluxo(sessao, "wf-lixeira", "ws-b", deleted_at=svc.utc_now_naive())

    alcance = ["ws-da-conversa", "ws-b"]
    await _auditar(sessao, workflow_id="wf-alheio", workspace_ids=alcance)
    await _auditar(sessao, workflow_id="wf-meu", workspace_ids=alcance)
    await _auditar(sessao, workflow_id="wf-lixeira", workspace_ids=alcance)

    trilhas = {
        e.details["argumentos"]["workflow_id"]: e.workspace_id
        for e in (await sessao.execute(select(AuditEvent))).scalars().all()
    }
    assert trilhas == {
        # Out of reach: falls back to the CONVERSATION's workspace, never the target's.
        "wf-alheio": "ws-da-conversa",
        # Within reach: the workflow's own trail.
        "wf-meu": "ws-b",
        # Deleted: does not resolve — the soft delete also takes the workflow out of here.
        "wf-lixeira": "ws-da-conversa",
    }


async def test_tokens_total_soma_e_ignora_none(sessao):
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")

    await svc.tocar_conversa(sessao, conv.id_hash, tokens_total=1_000)
    await svc.tocar_conversa(sessao, conv.id_hash, tokens_total=500)
    await svc.tocar_conversa(sessao, conv.id_hash, tokens_total=None)

    await sessao.refresh(conv)
    assert conv.tokens_total == 1_500


# ── Replay rebuilds the `sugerir_respostas` chips ─────────────────────────────


async def test_replay_reconstroi_as_respostas_rapidas_de_sugerir_respostas(sessao):
    """Reopening the chat brings back the chips of the last turn — through the SAME
    `quadros_extras` of the loop, from the stored (cleaned) arguments."""
    conv = await svc.criar_conversa(sessao, user_id=USUARIO, titulo="t")
    chamada = {
        "type": "tool_use", "id": "tu-chips", "name": ag.NOME_DAS_RESPOSTAS,
        "input": {"opcoes": ["  Só os últimos 7 dias ", "Cruzar com o CAR", "Cruzar com o CAR"]},
    }
    await svc.anexar_mensagens(
        sessao,
        conv.id_hash,
        [
            {"role": "user", "content": "focos de calor em MT"},
            {"role": "assistant", "content": [{"type": "text", "text": "Achei 128 focos."}, chamada]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu-chips", "content": "ok", "is_error": False}]},
        ],
        ordem_inicial=0,
    )

    quadros = await svc.quadros_do_replay(
        sessao, conv.id_hash, redis=RedisFalso(), user_id=USUARIO, tokens_total=0
    )

    tipos = [q["tipo"] for q in quadros]
    assert tipos == ["usuario", "texto", "ferramenta", "ferramenta_fim", "respostas_rapidas", "fim"]
    chips = [q for q in quadros if q["tipo"] == "respostas_rapidas"]
    assert chips[0]["dados"] == {"opcoes": ["Só os últimos 7 dias", "Cruzar com o CAR"]}
