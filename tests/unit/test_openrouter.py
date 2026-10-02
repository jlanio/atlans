# tests/unit/test_openrouter.py
"""
O cliente do OpenRouter — a única fronteira do assistente com a rede.

Tudo aqui roda contra um `httpx.MockTransport`: o que se mede é a TRADUÇÃO nos
dois sentidos (o transcrito do projeto virando o pedido; o SSE virando blocos)
e a disciplina de falha (retentar só antes do corpo, nunca devolver resposta
pela metade). Nenhum teste toca a rede.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.services import openrouter
from app.services.openrouter import (
    ClienteOpenRouter,
    Delta,
    ErroDoOpenRouter,
    Resposta,
    montar_mensagens,
    montar_pedido,
)

pytestmark = pytest.mark.asyncio

SISTEMA = [
    {"type": "text", "text": "politica"},
    {"type": "text", "text": "guia", "cache_control": {"type": "ephemeral", "ttl": "1h"}},
]
FERRAMENTAS = [openrouter.ferramenta("search_nodes", "procura", {"type": "object", "properties": {}})]


# ── Dublês ────────────────────────────────────────────────────────────────────


def _sse(*eventos, done: bool = True, comentarios: bool = False) -> bytes:
    """Um corpo `text/event-stream`, quadro a quadro, como o OpenRouter manda."""
    partes: list[str] = []
    if comentarios:
        partes.append(": OPENROUTER PROCESSING\n\n")
    for evento in eventos:
        if comentarios:
            partes.append(": OPENROUTER PROCESSING\n\n")
        partes.append(f"data: {json.dumps(evento, ensure_ascii=False)}\n\n")
    if done:
        partes.append("data: [DONE]\n\n")
    return "".join(partes).encode("utf-8")


def _quadro(delta: dict, *, parada=None, usage=None, **extras) -> dict:
    corpo = {
        "id": "gen-1",
        "object": "chat.completion.chunk",
        "model": "anthropic/claude-opus-5",
        "provider": "Anthropic",
        "choices": [{"index": 0, "delta": delta, "finish_reason": parada}],
    }
    if usage is not None:
        corpo["usage"] = usage
    corpo.update(extras)
    return corpo


def _stream(corpo: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=corpo, headers={"content-type": "text/event-stream"})


class Roteiro:
    """O servidor de mentira: uma resposta (ou exceção) por pedido, na ordem."""

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.pedidos: list[httpx.Request] = []

    async def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        if not self._respostas:
            raise AssertionError("o cliente pediu mais do que o roteiro previa")
        proxima = self._respostas.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return proxima

    def corpo(self, indice: int = 0) -> dict:
        return json.loads(self.pedidos[indice].content)


def _cliente(roteiro: Roteiro, **kw) -> tuple[ClienteOpenRouter, list[float]]:
    esperas: list[float] = []

    async def dormir(segundos: float) -> None:
        esperas.append(segundos)

    http = httpx.AsyncClient(transport=httpx.MockTransport(roteiro))
    cliente = ClienteOpenRouter("sk-or-v1-teste", http=http, dormir=dormir, **kw)
    return cliente, esperas


async def _colher(cliente: ClienteOpenRouter, conversa=None, **kw):
    base = dict(
        modelo="anthropic/claude-opus-5",
        sistema=SISTEMA,
        conversa=conversa or [{"role": "user", "content": "monta um fluxo"}],
        ferramentas=FERRAMENTAS,
        max_tokens=1000,
        esforco="high",
    )
    base.update(kw)
    return [pedaco async for pedaco in cliente.transmitir(**base)]


# ── A ida: o pedido ───────────────────────────────────────────────────────────


def test_o_pedido_leva_modelo_stream_uso_raciocinio_e_ferramentas():
    corpo = montar_pedido(
        modelo="openai/gpt-5",
        sistema=SISTEMA,
        conversa=[{"role": "user", "content": "oi"}],
        ferramentas=FERRAMENTAS,
        max_tokens=4321,
        esforco="high",
    )

    assert corpo["model"] == "openai/gpt-5"
    assert corpo["stream"] is True
    assert corpo["max_tokens"] == 4321
    # A contagem (e o custo) vem no último quadro do stream: é a fonte da cota.
    assert corpo["usage"] == {"include": True}
    assert corpo["reasoning"] == {"effort": "high"}
    assert corpo["tools"] == FERRAMENTAS
    assert corpo["tools"][0] == {
        "type": "function",
        "function": {"name": "search_nodes", "description": "procura", "parameters": {"type": "object", "properties": {}}},
    }


def test_sem_esforco_nem_ferramentas_o_pedido_nao_leva_os_campos():
    corpo = montar_pedido(
        modelo="m", sistema=[], conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[], max_tokens=10, esforco=None,
    )

    assert "reasoning" not in corpo
    assert "tools" not in corpo
    assert corpo["messages"] == [{"role": "user", "content": [
        {"type": "text", "text": "oi", "cache_control": {"type": "ephemeral"}},
    ]}]


def test_o_sistema_vai_em_partes_e_o_corte_de_cache_perde_o_ttl():
    """Só o tipo: a duração do cache é do provedor por trás do roteador, e um
    campo que ele não reconhece seria uma recusa a cada conversa."""
    mensagens = montar_mensagens(SISTEMA, [])

    assert mensagens == [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "politica"},
                {"type": "text", "text": "guia", "cache_control": {"type": "ephemeral"}},
            ],
        }
    ]


def test_a_ultima_mensagem_humana_leva_o_segundo_corte_e_os_resultados_viram_tool():
    """O prefixo que é o mesmo em todas as voltas de um turno termina na pergunta
    da pessoa. Resultados de ferramenta viram mensagens `tool`, com o texto cru."""
    conversa = [
        {"role": "user", "content": "primeira pergunta"},
        {"role": "assistant", "content": [{"type": "text", "text": "certo"}]},
        {"role": "user", "content": "monta um fluxo"},
        {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "call_1", "name": "search_nodes", "input": {"q": "buffer"}}],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "achei 3", "is_error": False},
            ],
        },
    ]

    mensagens = montar_mensagens([], conversa)

    assert mensagens[0] == {"role": "user", "content": "primeira pergunta"}
    assert mensagens[1] == {"role": "assistant", "content": "certo"}
    # A ÚLTIMA humana, e só ela, leva o corte.
    assert mensagens[2] == {
        "role": "user",
        "content": [{"type": "text", "text": "monta um fluxo", "cache_control": {"type": "ephemeral"}}],
    }
    assert mensagens[3] == {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "search_nodes", "arguments": '{"q": "buffer"}'}}
        ],
    }
    assert mensagens[4] == {"role": "tool", "tool_call_id": "call_1", "content": "achei 3"}


def test_o_assistente_leva_texto_chamadas_e_o_raciocinio_verbatim():
    detalhes = [
        {"type": "reasoning.text", "text": "preciso do catálogo", "signature": "assin-1", "format": "anthropic-claude-v1", "index": 0},
        {"type": "reasoning.encrypted", "data": "xyz==", "id": "rs_1", "format": "openai-responses-v1", "index": 1},
    ]
    conversa = [
        {"role": "user", "content": "oi"},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "preciso do catálogo", "reasoning_details": detalhes},
                {"type": "text", "text": "vou "},
                {"type": "text", "text": "montar"},
                {"type": "tool_use", "id": "c1", "name": "search_nodes", "input": {"q": "x"}},
                {"type": "tool_use", "id": "c2", "name": "describe_node", "input": "texto cru"},
            ],
        },
    ]

    [_, assistente] = montar_mensagens([], conversa)

    assert assistente["content"] == "vou montar"
    assert assistente["reasoning_details"] == detalhes
    # O texto cru de uma chamada cortada fica no transcrito, mas na ida vira `{}`:
    # reenviado como veio seria JSON inválido em toda volta seguinte.
    assert [c["function"]["arguments"] for c in assistente["tool_calls"]] == ['{"q": "x"}', "{}"]


def test_mensagem_do_assistente_sem_texto_e_sem_chamada_e_omitida_na_ida():
    """Só raciocínio (corte por `length` ainda pensando), lista vazia (recusa sem
    saída) ou string vazia: mandar `content: ""` é recusa certa do provedor, e
    recusa que o plano B do 400 não conserta."""
    conversa = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "x", "reasoning_details": [{"type": "reasoning.text", "text": "x", "index": 0}]},
        ]},
        {"role": "user", "content": "de novo"},
        {"role": "assistant", "content": []},
        {"role": "user", "content": "e agora"},
        {"role": "assistant", "content": ""},
        {"role": "user", "content": "por fim"},
    ]

    mensagens = montar_mensagens([], conversa)

    assert [m["role"] for m in mensagens] == ["user", "user", "user", "user"]
    # O corte de cache continua na ÚLTIMA humana.
    assert mensagens[-1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert all(isinstance(m["content"], str) for m in mensagens[:-1])


def test_o_raciocinio_antigo_com_assinatura_e_omitido_na_ida():
    """Um bloco `thinking` de outra API (com `signature`, sem `reasoning_details`)
    fica no transcrito para o replay e não vai ao provedor."""
    conversa = [
        {"role": "user", "content": "oi"},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "pensei", "signature": "assin-antiga"},
                {"type": "text", "text": "pronto"},
            ],
        },
    ]

    [_, assistente] = montar_mensagens([], conversa)

    assert assistente == {"role": "assistant", "content": "pronto"}
    assert "reasoning_details" not in assistente


def test_resultado_com_erro_ganha_o_prefixo_e_lista_de_blocos_e_juntada():
    """O formato de rede não tem `is_error`; sem o prefixo, uma recusa de escopo
    chegaria ao modelo igual a um resultado normal."""
    conversa = [
        {"role": "user", "content": "roda"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "c1", "name": "run_workflow", "input": {}}]},
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "c1", "is_error": True,
                 "content": [{"type": "text", "text": "sem"}, {"type": "text", "text": "permissão"}]},
            ],
        },
    ]

    mensagens = montar_mensagens([], conversa)

    assert mensagens[-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": openrouter.PREFIXO_DE_ERRO + "sem\npermissão",
    }


# ── A volta: o stream ─────────────────────────────────────────────────────────


async def test_o_stream_remonta_texto_raciocinio_e_chamadas_por_indice():
    """Chamadas chegam por `index` — `id`/`name` no primeiro pedaço, argumentos gota
    a gota, DUAS intercaladas; o `reasoning_details` também vem por índice, e a
    `signature` só no fim. O que sai é o formato do projeto, inteiro."""
    corpo = _sse(
        _quadro({"role": "assistant", "reasoning": "preciso ", "reasoning_details": [
            {"type": "reasoning.text", "text": "preciso ", "format": "anthropic-claude-v1", "index": 0}]}),
        _quadro({"reasoning": "do catálogo", "reasoning_details": [
            {"type": "reasoning.text", "text": "do catálogo", "format": "anthropic-claude-v1", "index": 0}]}),
        _quadro({"reasoning_details": [
            {"type": "reasoning.text", "text": "", "signature": "assin-9", "format": "anthropic-claude-v1", "index": 0}]}),
        _quadro({"content": "Vou "}),
        _quadro({"content": "procurar."}),
        _quadro({"tool_calls": [{"index": 0, "id": "call_a", "type": "function", "function": {"name": "search_nodes", "arguments": ""}}]}),
        _quadro({"tool_calls": [{"index": 1, "id": "call_b", "type": "function", "function": {"name": "describe_node", "arguments": '{"name":'}}]}),
        _quadro({"tool_calls": [{"index": 0, "function": {"arguments": '{"q": "buf'}}]}),
        _quadro({"tool_calls": [{"index": 1, "function": {"arguments": ' "Buffer"}'}}]}),
        _quadro({"tool_calls": [{"index": 0, "function": {"arguments": 'fer"}'}}]}),
        _quadro({}, parada="tool_calls", usage={
            "prompt_tokens": 1500, "completion_tokens": 80, "total_tokens": 1580, "cost": 0.0123,
            "prompt_tokens_details": {"cached_tokens": 1200},
            "completion_tokens_details": {"reasoning_tokens": 30},
        }),
        comentarios=True,
    )
    roteiro = Roteiro([_stream(corpo)])
    cliente, esperas = _cliente(roteiro)

    pedacos = await _colher(cliente)

    deltas = [p for p in pedacos if isinstance(p, Delta)]
    assert deltas == [
        Delta("pensando", "preciso "),
        Delta("pensando", "do catálogo"),
        Delta("texto", "Vou "),
        Delta("texto", "procurar."),
    ]
    resposta = pedacos[-1]
    assert isinstance(resposta, Resposta)
    assert resposta.parada == "tool_calls"
    assert resposta.modelo == "anthropic/claude-opus-5"
    assert resposta.provedor == "Anthropic"
    assert resposta.blocos == [
        {
            "type": "thinking",
            "thinking": "preciso do catálogo",
            "reasoning_details": [
                {"type": "reasoning.text", "text": "preciso do catálogo", "signature": "assin-9",
                 "format": "anthropic-claude-v1", "index": 0},
            ],
        },
        {"type": "text", "text": "Vou procurar."},
        {"type": "tool_use", "id": "call_a", "name": "search_nodes", "input": {"q": "buffer"}},
        {"type": "tool_use", "id": "call_b", "name": "describe_node", "input": {"name": "Buffer"}},
    ]
    # `entrada` já inclui o cache; `cache_leitura` é um recorte informativo.
    assert resposta.uso == {
        "entrada": 1500, "saida": 80, "cache_leitura": 1200, "cache_escrita": 0,
        "raciocinio": 30, "custo": 0.0123,
    }
    assert esperas == [], "sucesso de primeira não espera nada"
    # E o pedido que saiu é o traduzido: o cabeçalho de autenticação, e nenhum
    # de atribuição — sem título nem referer, nada identifica a instalação.
    pedido = roteiro.pedidos[0]
    assert pedido.headers["authorization"] == "Bearer sk-or-v1-teste"
    assert "x-title" not in pedido.headers and "http-referer" not in pedido.headers
    assert pedido.headers["accept"] == "text/event-stream"
    assert str(pedido.url) == "https://openrouter.ai/api/v1/chat/completions"


async def test_argumento_que_nao_fecha_vira_texto_cru_e_nao_objeto():
    """Metade de uma definição não pode chegar à ferramenta como se fosse inteira.
    O laço trata o que não é objeto como erro de chamada."""
    corpo = _sse(
        _quadro({"tool_calls": [{"index": 0, "id": "call_a", "type": "function",
                                 "function": {"name": "validate_workflow", "arguments": '{"definition": {"nodes": ['}}]}),
        _quadro({}, parada="length"),
    )
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    resposta = (await _colher(cliente))[-1]

    assert resposta.parada == "length"
    assert resposta.blocos[0]["input"] == '{"definition": {"nodes": ['


async def test_argumento_vazio_vira_objeto_e_chamada_sem_indice_e_aceita():
    corpo = _sse(
        _quadro({"content": "pronto"}),
        _quadro({"tool_calls": [{"id": "call_x", "type": "function", "function": {"name": "list_workflows", "arguments": ""}}]},
                parada="tool_calls"),
        done=False,
    )
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    resposta = (await _colher(cliente))[-1]

    assert resposta.parada == "tool_calls"
    assert resposta.blocos == [
        {"type": "text", "text": "pronto"},
        {"type": "tool_use", "id": "call_x", "name": "list_workflows", "input": {}},
    ]


async def test_stream_sem_finish_reason_e_erro_e_nao_resposta_vazia():
    """O OpenRouter sempre manda `finish_reason` antes do `[DONE]`. Sem ele, o que
    chegou não é resposta — e inferir `stop` gravaria uma mensagem vazia do
    assistente e emitiria um `fim` ok."""
    corpo = _sse(_quadro({"content": "pronto"}))
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente)

    assert "finish_reason" in str(exc.value)


async def test_200_de_gateway_com_html_e_erro_e_nao_resposta_vazia():
    """Um proxy que responde 200 com HTML não tem quadro SSE nenhum."""
    roteiro = Roteiro([httpx.Response(200, content=b"<html>gateway</html>", headers={"content-type": "text/html"})])
    cliente, _ = _cliente(roteiro)

    with pytest.raises(ErroDoOpenRouter):
        await _colher(cliente)


async def test_separador_de_linha_unicode_dentro_do_JSON_nao_corta_o_quadro():
    """U+2028, U+2029 e U+0085 são válidos SEM escape numa string JSON, e o
    `aiter_lines()` do httpx quebrava a linha neles (`str.splitlines()`). O
    leitor próprio quebra só em `\\n`, `\\r\\n` e `\\r`."""
    texto = "antes\u2028meio\u2029fim\u0085ponto"
    corpo = _sse(_quadro({"content": texto}), _quadro({}, parada="stop"))
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    pedacos = await _colher(cliente)

    assert pedacos[0] == Delta("texto", texto)
    assert pedacos[-1].blocos == [{"type": "text", "text": texto}]


async def test_terminadores_CRLF_e_pedacos_partidos_no_meio_sao_remontados():
    """`\\r\\n` como terminador, um `\\r\\n` partido entre dois pedaços da rede e um
    caractere multibyte partido entre dois pedaços: tudo remonta igual."""
    quadro_a = json.dumps(_quadro({"content": "olá ção"}), ensure_ascii=False).encode("utf-8")
    quadro_b = json.dumps(_quadro({}, parada="stop")).encode("utf-8")
    corpo = b"data: " + quadro_a + b"\r\n\r\ndata: " + quadro_b + b"\r\n\r\ndata: [DONE]\r\n\r\n"
    # Parte o corpo em pedaços pequenos: um deles cai no meio do `ção` e outro
    # entre o `\r` e o `\n`.
    corte_no_multibyte = corpo.index("ção".encode("utf-8")) + 1
    corte_no_crlf = corpo.index(b"\r\n") + 1
    cortes = sorted({corte_no_multibyte, corte_no_crlf, len(corpo) - 7})
    pedacos_bytes = [corpo[a:b] for a, b in zip([0, *cortes], [*cortes, len(corpo)])]

    async def corpo_em_pedacos():
        for pedaco in pedacos_bytes:
            yield pedaco

    roteiro = Roteiro([httpx.Response(200, content=corpo_em_pedacos(), headers={"content-type": "text/event-stream"})])
    cliente, _ = _cliente(roteiro)

    pedacos = await _colher(cliente)

    assert pedacos[0] == Delta("texto", "olá ção")
    assert pedacos[-1].parada == "stop"


async def test_reasoning_details_sem_indice_mas_com_id_nao_se_fundem():
    """Itens distintos sem `index` (o raciocínio criptografado de alguns
    provedores) ficam distintos, chaveados pelo `id`; pedaços sem `index` e sem
    `id` continuam sendo do mesmo bloco."""
    corpo = _sse(
        _quadro({"reasoning_details": [{"type": "reasoning.encrypted", "data": "AAA", "id": "rs_1"}]}),
        _quadro({"reasoning_details": [{"type": "reasoning.encrypted", "data": "BBB", "id": "rs_2"}]}),
        _quadro({"reasoning_details": [{"type": "reasoning.text", "text": "pen"}]}),
        _quadro({"reasoning_details": [{"type": "reasoning.text", "text": "sei"}]}),
        _quadro({"content": "ok"}, parada="stop"),
    )
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    resposta = (await _colher(cliente))[-1]

    assert resposta.blocos[0]["reasoning_details"] == [
        {"type": "reasoning.encrypted", "data": "AAA", "id": "rs_1"},
        {"type": "reasoning.encrypted", "data": "BBB", "id": "rs_2"},
        {"type": "reasoning.text", "text": "pensei"},
    ]
    assert resposta.blocos[0]["thinking"] == "pensei"


async def test_stream_so_de_texto_termina_em_stop_e_sem_bloco_de_raciocinio():
    corpo = _sse(_quadro({"content": "olá"}), _quadro({}, parada="stop", usage={"prompt_tokens": 5, "completion_tokens": 1}))
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    pedacos = await _colher(cliente)

    assert pedacos == [Delta("texto", "olá"), pedacos[-1]]
    assert pedacos[-1].parada == "stop"
    assert pedacos[-1].blocos == [{"type": "text", "text": "olá"}]
    assert pedacos[-1].uso["entrada"] == 5 and pedacos[-1].uso["custo"] == 0.0


async def test_erro_no_meio_do_stream_vira_excecao_e_nao_resposta():
    """Um quadro `error` depois de texto já emitido: o que saiu, saiu; mas não
    há `Resposta` — o laço não grava uma mensagem pela metade."""
    corpo = _sse(
        _quadro({"content": "Vou "}),
        {"id": "gen-1", "error": {"code": 502, "message": "Provider returned error"},
         "choices": [{"index": 0, "delta": {}, "finish_reason": "error"}]},
    )
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente)

    assert exc.value.codigo == 502
    assert "Provider returned error" in str(exc.value)


async def test_quadro_ilegivel_vira_excecao():
    corpo = b"data: {isto nao e json\n\n"
    cliente, _ = _cliente(Roteiro([_stream(corpo)]))

    with pytest.raises(ErroDoOpenRouter):
        await _colher(cliente)


# ── Falhas antes do corpo: retentar; depois do corpo: nunca ───────────────────


async def test_429_e_5xx_sao_retentados_com_espera_e_o_retry_after_manda():
    corpo_ok = _sse(_quadro({"content": "ok"}), _quadro({}, parada="stop"))
    roteiro = Roteiro([
        httpx.Response(429, json={"error": {"code": 429, "message": "slow down"}}, headers={"retry-after": "2"}),
        httpx.Response(503, json={"error": {"code": 503, "message": "provider down"}}),
        _stream(corpo_ok),
    ])
    cliente, esperas = _cliente(roteiro)

    pedacos = await _colher(cliente)

    assert pedacos[-1].blocos == [{"type": "text", "text": "ok"}]
    assert len(roteiro.pedidos) == 3
    # O `Retry-After` do 429 manda; o 503 cai no recuo exponencial (2ª tentativa).
    assert esperas == [2.0, 1.0]


async def test_depois_da_ultima_tentativa_o_erro_sobe_com_o_status():
    roteiro = Roteiro([
        httpx.Response(502, json={"error": {"code": 502, "message": "bad gateway"}}),
        httpx.Response(502, json={"error": {"code": 502, "message": "bad gateway"}}),
    ])
    cliente, esperas = _cliente(roteiro, tentativas=2)

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente)

    assert exc.value.status == 502
    assert exc.value.codigo == 502
    assert len(roteiro.pedidos) == 2
    assert esperas == [0.5]


async def test_401_e_402_nao_sao_retentados():
    """Chave errada e crédito zerado não melhoram esperando."""
    for status in (401, 402):
        roteiro = Roteiro([httpx.Response(status, json={"error": {"code": status, "message": "nope"}})])
        cliente, esperas = _cliente(roteiro)

        with pytest.raises(ErroDoOpenRouter) as exc:
            await _colher(cliente)

        assert exc.value.status == status
        assert len(roteiro.pedidos) == 1
        assert esperas == []


async def test_falha_de_rede_antes_do_corpo_e_retentada():
    corpo_ok = _sse(_quadro({"content": "ok"}), _quadro({}, parada="stop"))
    roteiro = Roteiro([httpx.ConnectError("sem rota"), _stream(corpo_ok)])
    cliente, esperas = _cliente(roteiro)

    pedacos = await _colher(cliente)

    assert pedacos[-1].parada == "stop"
    assert esperas == [0.5]


async def test_falha_de_rede_persistente_vira_erro_do_openrouter():
    roteiro = Roteiro([httpx.ConnectError("sem rota")] * 3)
    cliente, _ = _cliente(roteiro)

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente)

    assert "ConnectError" in str(exc.value)
    assert len(roteiro.pedidos) == 3


async def test_erro_de_corpo_nao_json_e_encurtado_na_mensagem():
    roteiro = Roteiro([httpx.Response(500, content=b"<html>" + b"x" * 1000)])
    cliente, _ = _cliente(roteiro, tentativas=1)

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente)

    assert exc.value.status == 500
    assert len(str(exc.value)) < 400


async def test_400_com_raciocinio_guardado_e_refeito_uma_vez_sem_ele():
    """Se o provedor recusar o raciocínio guardado, a conversa perde o raciocínio
    antigo — não a conversa."""
    conversa = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "x", "reasoning_details": [{"type": "reasoning.text", "text": "x", "index": 0}]},
            {"type": "tool_use", "id": "c1", "name": "search_nodes", "input": {}},
        ]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "ok", "is_error": False}]},
    ]
    corpo_ok = _sse(_quadro({"content": "seguindo"}), _quadro({}, parada="stop"))
    roteiro = Roteiro([
        httpx.Response(400, json={"error": {"code": 400, "message": "invalid reasoning signature"}}),
        _stream(corpo_ok),
    ])
    cliente, esperas = _cliente(roteiro)

    pedacos = await _colher(cliente, conversa=conversa)

    assert pedacos[-1].blocos == [{"type": "text", "text": "seguindo"}]
    assert esperas == [], "o 400 não é espera: é outro pedido"
    primeiro, segundo = roteiro.corpo(0), roteiro.corpo(1)
    assert "reasoning_details" in primeiro["messages"][2]
    assert "reasoning_details" not in segundo["messages"][2]
    # Fora do raciocínio, o pedido é o MESMO.
    assert segundo["messages"][2]["tool_calls"] == primeiro["messages"][2]["tool_calls"]
    assert segundo["tools"] == primeiro["tools"]


async def test_400_sem_raciocinio_guardado_nao_e_refeito():
    roteiro = Roteiro([httpx.Response(400, json={"error": {"code": 400, "message": "bad model"}})])
    cliente, _ = _cliente(roteiro)

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente)

    assert exc.value.status == 400
    assert len(roteiro.pedidos) == 1


async def test_o_400_refeito_e_recusado_de_novo_sobe_sem_terceiro_pedido():
    conversa = [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "x", "reasoning_details": [{"type": "reasoning.text", "text": "x"}]},
            {"type": "text", "text": "ok"},
        ]},
        {"role": "user", "content": "e agora?"},
    ]
    roteiro = Roteiro([
        httpx.Response(400, json={"error": {"code": 400, "message": "a"}}),
        httpx.Response(400, json={"error": {"code": 400, "message": "b"}}),
    ])
    cliente, _ = _cliente(roteiro)

    with pytest.raises(ErroDoOpenRouter) as exc:
        await _colher(cliente, conversa=conversa)

    assert "b" in str(exc.value)
    assert len(roteiro.pedidos) == 2


# ── Construção e ciclo de vida ────────────────────────────────────────────────


def test_chave_vazia_e_recusada_na_construcao():
    with pytest.raises(ValueError):
        ClienteOpenRouter("")


def test_a_base_url_e_o_referer_sao_respeitados():
    cliente = ClienteOpenRouter("sk-or-v1-x", base_url="https://gateway.interno/api/v1/", referer="https://atlans.example.org")

    assert cliente._url == "https://gateway.interno/api/v1/chat/completions"
    assert cliente._cabecalhos()["HTTP-Referer"] == "https://atlans.example.org"


def test_a_url_completa_do_endpoint_na_configuracao_nao_duplica_o_caminho():
    """`OPENROUTER_BASE_URL` é a base, mas quem colar a URL do endpoint inteira
    não pode ganhar `/chat/completions/chat/completions` em todo pedido."""
    cliente = ClienteOpenRouter("sk-or-v1-x", base_url="https://openrouter.ai/api/v1/chat/completions")

    assert cliente._url == "https://openrouter.ai/api/v1/chat/completions"


async def test_sem_http_injetado_as_conversas_compartilham_um_pool(monkeypatch):
    """Um `AsyncClient` por processo, criado na primeira conversa e reaproveitado:
    abrir um por chamada custava um handshake TCP+TLS a cada volta de ferramenta."""
    corpo_ok = _sse(_quadro({"content": "ok"}), _quadro({}, parada="stop"))
    roteiro = Roteiro([_stream(corpo_ok), _stream(corpo_ok)])
    criados: list[httpx.AsyncClient] = []
    # `openrouter.httpx` E o modulo `httpx`: guardar a classe real antes de
    # trocar, senao a fabrica chama a si mesma.
    ClienteReal = httpx.AsyncClient

    def fabrica(**kw):
        assert kw.get("timeout") is openrouter.TEMPO_LIMITE
        http = ClienteReal(transport=httpx.MockTransport(roteiro))
        criados.append(http)
        return http

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", fabrica)
    monkeypatch.setattr(openrouter, "_http_compartilhado", None)

    primeira = await _colher(ClienteOpenRouter("sk-or-v1-x"))
    segunda = await _colher(ClienteOpenRouter("sk-or-v1-x"))

    assert primeira[-1].parada == "stop" and segunda[-1].parada == "stop"
    assert len(roteiro.pedidos) == 2
    assert len(criados) == 1, "duas conversas, um pool"
    assert not criados[0].is_closed
    await criados[0].aclose()


def test_o_uso_do_projeto_le_o_usage_do_openrouter_com_tolerancia():
    uso = openrouter._uso_do_projeto({
        "prompt_tokens": "12", "completion_tokens": None, "cost": "0.5",
        "prompt_tokens_details": {"cached_tokens": 4, "cache_write_tokens": 2},
        "completion_tokens_details": {"reasoning_tokens": "x"},
    })

    assert uso == {"entrada": 12, "saida": 0, "cache_leitura": 4, "cache_escrita": 2, "raciocinio": 0, "custo": 0.5}
    assert openrouter._uso_do_projeto(None)["entrada"] == 0


# ── O catálogo de modelos ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listar_modelos_converte_o_preco_de_TOKEN_para_MILHAO():
    """O provedor devolve o preço por token, em string (`"0.000003"`). Quem lê
    uma tabela de custo pensa em milhão, e deixar a conversão para cada
    chamador é esperar que um deles erre o fator de um milhão — silenciosamente,
    numa tela de dinheiro."""
    def handler(pedido: httpx.Request) -> httpx.Response:
        assert pedido.url.path.endswith("/models")
        return httpx.Response(200, json={"data": [
            {"id": "x/modelo", "name": "Modelo X", "context_length": 200000,
             "pricing": {"prompt": "0.000003", "completion": "0.000015"}},
        ]})

    catalogo = await openrouter.listar_modelos(
        base_url="https://or.exemplo/api/v1",
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert catalogo == [{
        "id": "x/modelo", "nome": "Modelo X",
        "entrada_por_milhao": 3.0, "saida_por_milhao": 15.0, "contexto": 200000,
    }]


@pytest.mark.asyncio
async def test_preco_ausente_vira_None_e_NUNCA_zero():
    """Zero numa tabela de custo parece «de graça» — e é exatamente a leitura
    que faria alguém escolher o modelo errado."""
    def handler(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [
            {"id": "a/sem-preco", "pricing": {}},
            {"id": "b/preco-quebrado", "pricing": {"prompt": "grátis", "completion": None}},
            {"id": "", "pricing": {"prompt": "1"}},          # sem id: não entra
            "isto não é um objeto",                            # lixo: não entra
        ]})

    catalogo = await openrouter.listar_modelos(
        base_url="https://or.exemplo/api/v1",
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert [m["id"] for m in catalogo] == ["a/sem-preco", "b/preco-quebrado"]
    assert all(m["entrada_por_milhao"] is None for m in catalogo)
    assert all(m["saida_por_milhao"] is None for m in catalogo)
    # Sem nome, o id serve de nome — a lista não pode ter linha em branco.
    assert catalogo[0]["nome"] == "a/sem-preco"


@pytest.mark.asyncio
async def test_a_url_do_catalogo_nao_herda_o_caminho_de_conversa():
    """Quem configurou `OPENROUTER_BASE_URL` com a URL COMPLETA do endpoint de
    conversa não pode acabar pedindo `/chat/completions/models`."""
    visto = {}

    def handler(pedido: httpx.Request) -> httpx.Response:
        visto["url"] = str(pedido.url)
        return httpx.Response(200, json={"data": []})

    await openrouter.listar_modelos(
        base_url="https://or.exemplo/api/v1/chat/completions",
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    assert visto["url"] == "https://or.exemplo/api/v1/models"


@pytest.mark.asyncio
@pytest.mark.parametrize("resposta", [
    httpx.Response(503, text="fora do ar"),
    httpx.Response(200, json={"modelos": []}),        # formato inesperado
])
async def test_catalogo_que_falha_vira_erro_tipado(resposta):
    """Quem chama é uma tela de admin, e ela sabe degradar — mas só se o erro
    chegar como erro, e não como lista vazia que parece «nenhum modelo»."""
    with pytest.raises(openrouter.ErroDoOpenRouter):
        await openrouter.listar_modelos(
            base_url="https://or.exemplo/api/v1",
            http=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: resposta)),
        )
