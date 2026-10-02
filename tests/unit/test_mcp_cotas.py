# tests/unit/test_mcp_cotas.py
"""
Cotas por token: contagem por minuto e teto de esperas simultâneas.

O que cada teste protege:

- a chave é do TOKEN, nunca do IP — dois clientes atrás do mesmo NAT não podem
  dividir (nem roubar) o mesmo balde;
- o prazo nasce na primeira chamada e as seguintes não o empurram, senão a
  janela nunca fecharia (cada chamada empurraria o prazo à frente e o balde
  ficaria cheio para sempre);
- estourar devolve `retry_after_seconds` do TTL real, para o cliente esperar em
  vez de repetir;
- a fronteira é onde o teto de verdade está: a chamada de número LIMITE passa e
  a seguinte recusa (um `<` no lugar de um `<=` passaria despercebido de outra
  forma);
- uma chave que ficou sem prazo (o `EXPIRE` se perdeu no tempo em que ele saía
  separado do `INCR`) ganha prazo na contagem seguinte — senão o token ficaria
  travado para sempre;
- uma falha entre os dois `INCR` da reserva não deixa vaga pendurada;
- sem Redis tudo degrada ABERTO, com aviso no máximo uma vez por minuto — a
  política já usada pelo WebSocket de logs;
- a espera devolve a reserva mesmo quando o corpo levanta, e a recusa por teto
  não deixa contador pendurado.
"""
from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp import cotas
from tests.unit._mcp_harness import RedisFalso


@pytest.fixture(autouse=True)
def _zera_estado_do_processo():
    """O aviso e o semáforo local são globais do módulo; cada teste começa limpo."""
    cotas._ultimo_aviso = 0.0
    cotas._esperas_locais.clear()
    cotas._esperas_locais_total = 0
    yield
    cotas._ultimo_aviso = 0.0
    cotas._esperas_locais.clear()
    cotas._esperas_locais_total = 0


def _corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


# ── verificar() ───────────────────────────────────────────────────────────────


async def test_primeira_chamada_cria_a_janela_de_um_minuto():
    redis = RedisFalso()
    await cotas.verificar(redis, "tok-1", None)
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1
    assert redis.ttls["ratelimit:mcp:tok-1:geral"] == 60


async def test_chamadas_seguintes_nao_empurram_o_prazo_para_a_janela_poder_fechar():
    redis = RedisFalso()
    chave = "ratelimit:mcp:tok-1:geral"
    await cotas.verificar(redis, "tok-1", None)
    redis.ttls[chave] = 25  # passaram 35 s da janela
    for _ in range(3):
        await cotas.verificar(redis, "tok-1", None)
    assert redis.dados[chave] == 4
    assert redis.ttls[chave] == 25


async def test_baldes_sao_por_token():
    redis = RedisFalso()
    await cotas.verificar(redis, "tok-1", None)
    await cotas.verificar(redis, "tok-2", None)
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1
    assert redis.dados["ratelimit:mcp:tok-2:geral"] == 1


async def test_estourar_o_geral_levanta_rate_limited_com_o_ttl():
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL
    redis.ttls["ratelimit:mcp:tok-1:geral"] = 17
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)
    corpo = _corpo(exc.value)
    assert corpo["code"] == "rate_limited"
    assert corpo["retry_after_seconds"] == 17


async def test_a_fronteira_exata_do_balde_geral():
    """A chamada de número LIMITE_GERAL passa; a seguinte recusa."""
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL - 1
    redis.ttls["ratelimit:mcp:tok-1:geral"] = 30

    await cotas.verificar(redis, "tok-1", None)  # a de número LIMITE_GERAL
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == cotas.LIMITE_GERAL

    with pytest.raises(ToolError) as exc:  # a LIMITE_GERAL + 1
        await cotas.verificar(redis, "tok-1", None)
    assert _corpo(exc.value)["code"] == "rate_limited"


async def test_chave_estourada_sem_prazo_ganha_o_prazo_na_contagem():
    """Sem prazo de volta, o token ficaria travado para sempre.

    Quando `INCR` e `EXPIRE` eram dois comandos, perder o segundo (Redis
    reiniciou, conexão caiu) deixava a chave sem prazo: o contador nunca zerava
    e todas as chamadas daquele token passavam a ser recusadas — até alguém
    apagar a chave à mão. A contagem arma o prazo de uma chave sem nenhum, na
    mesma transação do `INCR`, estourada ou não.
    """
    redis = RedisFalso()
    chave = "ratelimit:mcp:tok-1:geral"
    redis.dados[chave] = cotas.LIMITE_GERAL + 5  # estourado
    redis.ttls.pop(chave, None)  # e sem prazo nenhum (o EXPIRE se perdeu)

    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)

    assert _corpo(exc.value)["retry_after_seconds"] == cotas.JANELA_SEGUNDOS
    assert ("expire", chave, cotas.JANELA_SEGUNDOS) in redis.chamadas
    assert redis.ttls[chave] == cotas.JANELA_SEGUNDOS


async def test_cota_de_run_tem_teto_proprio_menor_que_o_geral():
    redis = RedisFalso()
    assert cotas.LIMITES_POR_COTA["run"] < cotas.LIMITE_GERAL
    redis.dados["ratelimit:mcp:tok-1:run"] = cotas.LIMITES_POR_COTA["run"]
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", "run")
    assert _corpo(exc.value)["code"] == "rate_limited"
    # O balde geral já foi consumido antes de o específico recusar: é uma
    # chamada, conta uma vez em cada balde.
    assert redis.dados["ratelimit:mcp:tok-1:geral"] == 1


async def test_cota_de_validate_nao_afeta_o_balde_de_run():
    redis = RedisFalso()
    await cotas.verificar(redis, "tok-1", "validate")
    assert redis.dados["ratelimit:mcp:tok-1:validate"] == 1
    assert "ratelimit:mcp:tok-1:run" not in redis.dados


async def test_ttl_ausente_cai_na_janela_cheia_em_vez_de_um_numero_negativo():
    redis = RedisFalso()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.LIMITE_GERAL + 5
    with pytest.raises(ToolError) as exc:
        await cotas.verificar(redis, "tok-1", None)
    assert _corpo(exc.value)["retry_after_seconds"] == cotas.JANELA_SEGUNDOS


async def test_sem_redis_degrada_aberto_e_avisa_uma_vez_por_minuto(caplog):
    with caplog.at_level("WARNING", logger="app.mcp.cotas"):
        for _ in range(5):
            await cotas.verificar(None, "tok-1", "run")
    avisos = [r for r in caplog.records if r.name == "app.mcp.cotas"]
    assert len(avisos) == 1


async def test_falha_do_redis_nao_derruba_a_chamada():
    class RedisQuebrado(RedisFalso):
        async def incrby(self, chave, quanto):
            raise ConnectionError("sem rede")

    await cotas.verificar(RedisQuebrado(), "tok-1", None)  # não levanta


# ── espera() ──────────────────────────────────────────────────────────────────


async def test_espera_reserva_nos_dois_contadores_e_devolve_no_fim():
    redis = RedisFalso()
    async with cotas.espera(redis, "tok-1", ttl_s=120):
        assert redis.dados["mcp:wait:token:tok-1"] == 1
        assert redis.dados["mcp:wait:global"] == 1
    assert redis.dados["mcp:wait:token:tok-1"] == 0
    assert redis.dados["mcp:wait:global"] == 0


async def test_ttl_da_reserva_cobre_o_prazo_maximo_mais_folga():
    redis = RedisFalso()
    async with cotas.espera(redis, "tok-1", ttl_s=120):
        pass
    assert redis.ttls["mcp:wait:token:tok-1"] == 180


async def test_espera_devolve_a_reserva_mesmo_com_erro_no_corpo():
    redis = RedisFalso()
    with pytest.raises(RuntimeError):
        async with cotas.espera(redis, "tok-1", ttl_s=60):
            raise RuntimeError("a execução falhou")
    assert redis.dados["mcp:wait:token:tok-1"] == 0


async def test_quarta_espera_do_mesmo_token_e_recusada_sem_deixar_contador_pendurado():
    redis = RedisFalso()
    redis.dados["mcp:wait:token:tok-1"] = cotas.MAX_ESPERAS_POR_TOKEN
    redis.dados["mcp:wait:global"] = 1
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(redis, "tok-1", ttl_s=60):
            pass
    corpo = _corpo(exc.value)
    assert corpo["code"] == "wait_limit"
    assert "wait=false" in corpo["hint"]
    assert redis.dados["mcp:wait:token:tok-1"] == cotas.MAX_ESPERAS_POR_TOKEN
    assert redis.dados["mcp:wait:global"] == 1


async def test_teto_global_recusa_mesmo_token_dentro_do_proprio_limite():
    redis = RedisFalso()
    redis.dados["mcp:wait:global"] = cotas.MAX_ESPERAS_GLOBAL
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(redis, "tok-novo", ttl_s=60):
            pass
    assert _corpo(exc.value)["code"] == "wait_limit"
    assert redis.dados["mcp:wait:token:tok-novo"] == 0


async def test_falha_entre_os_dois_incr_nao_deixa_reserva_pendurada():
    """O primeiro balde já foi incrementado quando o segundo falha.

    Sem devolver o que foi contado, cada tentativa durante uma queda do Redis
    comeria uma vaga do token, e o teto travaria assim que a rede voltasse.
    """

    class RedisQueCaiNoGlobal(RedisFalso):
        async def incr(self, chave):
            if chave == "mcp:wait:global":
                raise ConnectionError("caiu no meio da reserva")
            return await super().incr(chave)

    redis = RedisQueCaiNoGlobal()
    async with cotas.espera(redis, "tok-1", ttl_s=60):
        # Degradou para o semáforo local, como manda a política sem Redis.
        assert cotas._esperas_locais["tok-1"] == 1
    assert redis.dados["mcp:wait:token:tok-1"] == 0


async def test_sem_redis_a_espera_usa_semaforo_local_ao_processo():
    import contextlib

    async with contextlib.AsyncExitStack() as pilha:
        for _ in range(cotas.MAX_ESPERAS_POR_TOKEN):
            await pilha.enter_async_context(cotas.espera(None, "tok-1", ttl_s=60))
        with pytest.raises(ToolError) as exc:
            async with cotas.espera(None, "tok-1", ttl_s=60):
                pass
    assert _corpo(exc.value)["code"] == "wait_limit"
    # Saiu da pilha: o semáforo voltou ao zero e o próximo pedido passa.
    async with cotas.espera(None, "tok-1", ttl_s=60):
        pass


async def test_semaforo_local_tem_teto_global_e_volta_ao_zero():
    """Sem Redis o teto global também vale — e o contador desempilha até zero."""
    import contextlib

    cotas._esperas_locais_total = cotas.MAX_ESPERAS_GLOBAL
    with pytest.raises(ToolError) as exc:
        async with cotas.espera(None, "tok-novo", ttl_s=60):
            pass
    assert _corpo(exc.value)["code"] == "wait_limit"
    # A recusa não consome vaga: o total continua onde estava.
    assert cotas._esperas_locais_total == cotas.MAX_ESPERAS_GLOBAL
    assert "tok-novo" not in cotas._esperas_locais

    cotas._esperas_locais_total = 0
    async with contextlib.AsyncExitStack() as pilha:
        for numero in range(cotas.MAX_ESPERAS_POR_TOKEN):
            await pilha.enter_async_context(cotas.espera(None, f"tok-{numero}", ttl_s=60))
        assert cotas._esperas_locais_total == cotas.MAX_ESPERAS_POR_TOKEN
    assert cotas._esperas_locais_total == 0
    assert cotas._esperas_locais == {}


# ── verificar_tokens_do_assistente() ────────────────────────────────────────────


async def test_o_teto_de_tokens_e_do_CHAMADOR_e_o_default_e_o_da_instalacao():
    """O teto passou a depender do plano, e quem o resolve é o chamador.

    Este módulo é só Redis: se ele fosse buscar a assinatura, o laço do assistente
    (que roda dentro de um gerador SSE, sem sessão de request) arrastaria banco
    para dentro de uma checagem que existe para ser barata.
    """
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA

    # Sem `teto`, o comportamento de antes dos planos: o teto da instalação.
    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1")
    assert _corpo(exc.value)["code"] == "rate_limited"

    # Com um teto maior (o de um plano, quando há extensão), o MESMO gasto passa.
    await cotas.verificar_tokens_do_assistente(
        redis, "usr-1", teto=10 * cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    )


async def test_a_fronteira_do_teto_injetado_e_o_proprio_teto():
    """Um `<=` no lugar do `<` daria um turno de graça a cada plano — e a
    fronteira é justamente onde ninguém olha."""
    redis = RedisFalso()
    teto = 22_500_000

    redis.dados["assistente:tokens:usr-1"] = teto - 1
    await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=teto)

    redis.dados["assistente:tokens:usr-1"] = teto
    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=teto)
    assert _corpo(exc.value)["code"] == "rate_limited"


# ── A chave da cota do assistente nao pode ficar imortal (PR 5, #3) ─────────────
#
# Quando a cobranca fazia INCRBY e, so na 1a escrita da janela, EXPIRE — dois
# comandos —, perder o segundo (Redis reiniciou, conexao caiu, SSE cancelado no
# meio) deixava a chave sem prazo: ao cruzar o teto, o usuario perdia o
# assistente PARA SEMPRE. Hoje o prazo sai na mesma transacao do INCRBY
# (`contar_na_janela`); o que sobra de uma chave antiga sem prazo e armado na
# cobranca seguinte, na recusa ou na leitura do `/estado` (`gasto_e_prazo`).


async def test_abaixo_do_teto_a_cobranca_arma_o_prazo_de_uma_chave_que_ficou_sem():
    """Abaixo do teto o turno segue, e a cobranca dele poe o prazo que faltava —
    senao a chave imortal so seria notada tarde demais, ja travada."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 10  # abaixo do teto, mas SEM prazo (o EXPIRE se perdeu)

    await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=1000)  # nao recusa
    assert await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 5) == 15

    assert redis.ttls[chave] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS
    assert await cotas.gasto_e_prazo(redis, "usr-1") == (15, cotas.JANELA_DO_ASSISTENTE_SEGUNDOS)


async def test_a_recusa_arma_o_prazo_de_uma_chave_estourada_que_ficou_sem():
    """Estourada, o turno e recusado ANTES da cobranca — que e quem arma o
    prazo. Se a recusa nao o armasse, quem cruzou o teto com uma chave dessas
    nunca mais teria o assistente; e ela ainda diz quando a janela reabre."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 1000  # no teto, e SEM prazo

    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=1000)

    assert _corpo(exc.value)["retry_after_seconds"] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS
    assert redis.ttls[chave] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS


async def test_cobrar_e_recusar_nao_reabrem_uma_janela_com_prazo_vivo():
    """So a chave SEM prazo ganha um; uma janela viva NAO e reaberta — reabrir
    estenderia o teto de graca a cada turno."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 10
    redis.ttls[chave] = 3600  # prazo vivo

    await cotas.cobrar_tokens_do_assistente(redis, "usr-1", 5)
    assert redis.ttls[chave] == 3600

    with pytest.raises(ToolError) as exc:
        await cotas.verificar_tokens_do_assistente(redis, "usr-1", teto=15)
    assert _corpo(exc.value)["retry_after_seconds"] == 3600
    assert redis.ttls[chave] == 3600


async def test_o_estado_arma_o_prazo_de_uma_chave_estourada_que_ficou_sem():
    """Com a cota cheia, a interface le o `/estado` (que vem daqui) e trava o
    envio: a recusa, que tambem armaria o prazo, nunca roda. Sem a cura aqui,
    a chave antiga sem prazo nunca expiraria, e a pessoa perderia o assistente
    para sempre, com o medidor dizendo "sem prazo"."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 1_600_000  # acima do teto, e SEM prazo

    assert await cotas.gasto_e_prazo(redis, "usr-1") == (1_600_000, cotas.JANELA_DO_ASSISTENTE_SEGUNDOS)
    assert redis.ttls[chave] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS


async def test_o_estado_nao_reabre_uma_janela_com_prazo_vivo():
    """Ler o medidor nao estende o teto: uma janela viva fica como esta."""
    redis = RedisFalso()
    chave = cotas.chave_de_tokens("usr-1")
    redis.dados[chave] = 10
    redis.ttls[chave] = 3600

    assert await cotas.gasto_e_prazo(redis, "usr-1") == (10, 3600)
    assert redis.ttls[chave] == 3600


async def test_gasto_e_prazo_de_chave_ausente_nao_inventa_prazo():
    """Sem chave (nada gasto), nao ha prazo a mostrar, e a leitura nao cria a
    chave."""
    redis = RedisFalso()
    gasto, prazo = await cotas.gasto_e_prazo(redis, "usr-1")

    assert gasto == 0
    assert prazo is None
    assert not any(c[0] == "expire" for c in redis.chamadas)
    assert redis.dados == {}
