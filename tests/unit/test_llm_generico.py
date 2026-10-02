# tests/unit/test_llm_generico.py
"""
O assistente fala com qualquer API compatível com a da OpenAI, e não só com o
OpenRouter — e só se identifica se a instalação quiser.

Antes, a chave e a base tinham o nome do OpenRouter, todo pedido levava
`X-Title: Atlans` e o `FRONTEND_URL` como referer (o que põe a instalação no
ranking público de apps dele), o catálogo nunca levava a chave (um gateway ou
um vLLM com chave recusavam) e o id do modelo tinha de ser `fornecedor/nome` —
o `qwen3:14b` do Ollama era recusado.

  NOMES       LLM_API_KEY e LLM_BASE_URL; os nomes antigos continuam valendo
  ATRIBUIÇÃO  desligada por padrão; ASSISTENTE_ATRIBUICAO liga nos três caminhos
  CATÁLOGO    da base configurada, com a chave quando há
  ID          o nome no catálogo de qualquer provedor; URL e espaço, não
  PEDIDO      fora do OpenRouter, só o formato da API da OpenAI — e o uso vem
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app.core import config
from app.services import openrouter
from app.services.assistente_config_service import formato_valido

RAIZ = Path(__file__).resolve().parents[2]
CHAVE_ANTIGA = "sk-or-v1-antiga"  # pragma: allowlist secret
CHAVE_LOCAL = "local"  # pragma: allowlist secret


# ── NOMES ────────────────────────────────────────────────────────────────────

def _config_com(ambiente: dict[str, str]) -> list[str]:
    """O config é lido no import: cada combinação roda num processo próprio."""
    codigo = (
        "import app.core.config as c\n"
        "print(c.OPENROUTER_API_KEY); print(c.OPENROUTER_BASE_URL); print(c.ASSISTENTE_ATRIBUICAO)\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in (
        "LLM_API_KEY", "LLM_BASE_URL", "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "ASSISTENTE_ATRIBUICAO",
    )}
    env.update(ambiente)
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout.splitlines()


def test_sem_nada_o_assistente_nao_tem_chave_e_a_base_e_a_do_openrouter():
    assert _config_com({}) == ["", "https://openrouter.ai/api/v1", "False"]


def test_os_nomes_antigos_continuam_valendo():
    assert _config_com({
        "OPENROUTER_API_KEY": CHAVE_ANTIGA, "OPENROUTER_BASE_URL": "https://gateway.example.org/v1",
    })[:2] == [CHAVE_ANTIGA, "https://gateway.example.org/v1"]


def test_os_nomes_genericos_vencem_os_antigos():
    # O compose passa as quatro; uma vazia não apaga a outra.
    assert _config_com({
        "LLM_API_KEY": CHAVE_LOCAL, "LLM_BASE_URL": "http://ollama:11434/v1",
        "OPENROUTER_API_KEY": CHAVE_ANTIGA, "OPENROUTER_BASE_URL": "",
    })[:2] == [CHAVE_LOCAL, "http://ollama:11434/v1"]
    assert _config_com({"LLM_API_KEY": "  ", "OPENROUTER_API_KEY": CHAVE_ANTIGA})[0] == CHAVE_ANTIGA


@pytest.mark.parametrize("valor, ligada", [
    ("", "False"), ("false", "False"), ("talvez", "False"),
    ("true", "True"), ("1", "True"), ("sim", "True"), (" TRUE ", "True"),
])
def test_atribuicao_so_com_valor_explicito(valor, ligada):
    assert _config_com({"ASSISTENTE_ATRIBUICAO": valor})[2] == ligada


# ── ATRIBUIÇÃO ───────────────────────────────────────────────────────────────

def test_o_cliente_sem_titulo_nem_referer_nao_se_identifica():
    cabecalhos = openrouter.ClienteOpenRouter("k")._cabecalhos()
    assert "X-Title" not in cabecalhos and "HTTP-Referer" not in cabecalhos


def test_o_cliente_com_titulo_e_referer_se_identifica():
    cabecalhos = openrouter.ClienteOpenRouter(
        "k", titulo="Atlans", referer="https://atlans.example.org",
    )._cabecalhos()
    assert cabecalhos["X-Title"] == "Atlans"
    assert cabecalhos["HTTP-Referer"] == "https://atlans.example.org"


@pytest.mark.parametrize("atribuicao", [False, True])
def test_a_conversa_so_se_identifica_com_a_atribuicao(monkeypatch, atribuicao):
    from app.services.assistente_service import criar_cliente

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(config, "OPENROUTER_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org")
    monkeypatch.setattr(config, "ASSISTENTE_ATRIBUICAO", atribuicao)

    cliente = criar_cliente()
    cabecalhos = cliente._cabecalhos()

    assert cliente._url == "http://ollama:11434/v1/chat/completions"
    if atribuicao:
        assert cabecalhos["X-Title"] == "Atlans"
        assert cabecalhos["HTTP-Referer"] == "https://atlans.example.org"
    else:
        assert "X-Title" not in cabecalhos and "HTTP-Referer" not in cabecalhos


@pytest.mark.parametrize("atribuicao", [False, True])
async def test_a_sonda_so_se_identifica_com_a_atribuicao(monkeypatch, atribuicao):
    from app.api.routers import admin_assistente_router as R

    visto: dict = {}

    async def _sondar(modelo, **kw):
        visto.update(kw)

    monkeypatch.setattr(R, "OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(R, "OPENROUTER_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.setattr(R.openrouter, "sondar_modelo", _sondar)
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org")
    monkeypatch.setattr(config, "ASSISTENTE_ATRIBUICAO", atribuicao)

    await R._sondar_ou_400("qwen3:14b")

    assert visto["base_url"] == "http://ollama:11434/v1"
    if atribuicao:
        assert (visto["titulo"], visto["referer"]) == ("Atlans", "https://atlans.example.org")
    else:
        assert (visto["titulo"], visto["referer"]) == (None, None)


# ── CATÁLOGO ─────────────────────────────────────────────────────────────────

async def _pedido_do_catalogo(**kw) -> httpx.Request:
    pedidos: list[httpx.Request] = []

    def handler(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        # O formato do Ollama: sem nome, sem preço, sem contexto.
        return httpx.Response(200, json={"object": "list", "data": [
            {"id": "qwen3:14b", "object": "model", "owned_by": "library"},
        ]})

    catalogo = await openrouter.listar_modelos(
        base_url="http://ollama:11434/v1",
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **kw,
    )
    assert catalogo == [{
        "id": "qwen3:14b", "nome": "qwen3:14b",
        "entrada_por_milhao": None, "saida_por_milhao": None, "contexto": None,
    }]
    (pedido,) = pedidos
    return pedido


async def test_o_catalogo_leva_a_chave_quando_ha():
    pedido = await _pedido_do_catalogo(chave="sk-local")
    assert str(pedido.url) == "http://ollama:11434/v1/models"
    assert pedido.headers["authorization"] == "Bearer sk-local"


async def test_o_catalogo_sem_chave_nao_manda_authorization():
    pedido = await _pedido_do_catalogo()
    assert "authorization" not in pedido.headers


# ── ID ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modelo", [
    "anthropic/claude-opus-5",          # OpenRouter
    "openai/gpt-5:online",              # OpenRouter, com variante
    "qwen3:14b",                        # Ollama
    "llama3.1",                         # Ollama, sem etiqueta
    "meta-llama/Llama-3.1-8B-Instruct",  # vLLM (o id do Hugging Face)
    "org/grupo/modelo",                 # caminho com mais de uma barra
])
def test_id_de_qualquer_provedor_e_aceito(modelo):
    assert formato_valido(modelo)


@pytest.mark.parametrize("modelo", [
    "", "antropic claude", " anthropic/claude", "anthropic/claude\n",
    "https://openrouter.ai/anthropic/claude-opus-5", "http://ollama:11434",
    "/claude", "anthropic/", "anthropic//claude", "x" * 121,
])
def test_colagem_errada_e_recusada(modelo):
    assert not formato_valido(modelo)


# ── PEDIDO ───────────────────────────────────────────────────────────────────
#
# `usage`, `reasoning` e `cache_control` são parâmetros do OpenRouter. A API da
# OpenAI (e o vLLM, o LiteLLM, o Ollama) só manda o `usage` no stream com
# `stream_options.include_usage` — sem ele, a cota diária não contava nada num
# gateway pago. E a própria OpenAI recusa campo que não conhece.

SISTEMA = [
    {"type": "text", "text": "política"},
    {"type": "text", "text": "guia", "cache_control": {"type": "ephemeral"}},
]
FERRAMENTA = openrouter.ferramenta("ping", "responde", {"type": "object", "properties": {}})


@pytest.mark.parametrize("base, e_dele", [
    (None, True),
    ("", True),
    ("https://openrouter.ai/api/v1", True),
    ("https://openrouter.ai/api/v1/chat/completions", True),
    ("https://eu.openrouter.ai/api/v1", True),
    ("http://ollama:11434/v1", False),
    ("https://api.openai.com/v1", False),
    ("http://litellm:4000", False),
    ("https://openrouter.ai.example.org/v1", False),
])
def test_quem_e_o_openrouter(base, e_dele):
    assert openrouter.e_openrouter(base) is e_dele


def test_fora_do_openrouter_o_pedido_e_o_da_api_da_openai():
    corpo = openrouter.montar_pedido(
        modelo="qwen3:14b", sistema=SISTEMA, conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[FERRAMENTA], max_tokens=100, esforco="high", openrouter=False,
    )
    assert corpo["stream_options"] == {"include_usage": True}
    assert "usage" not in corpo
    assert "reasoning" not in corpo
    assert corpo["tools"] == [FERRAMENTA]
    assert corpo["messages"] == [
        {"role": "system", "content": "política\n\nguia"},
        {"role": "user", "content": "oi"},
    ]
    assert "cache_control" not in json.dumps(corpo)


def test_no_openrouter_o_pedido_nao_muda():
    corpo = openrouter.montar_pedido(
        modelo="anthropic/claude-opus-5", sistema=SISTEMA, conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[FERRAMENTA], max_tokens=100, esforco="high",
    )
    assert corpo["usage"] == {"include": True}
    assert corpo["reasoning"] == {"effort": "high"}
    assert "stream_options" not in corpo
    assert "cache_control" in json.dumps(corpo)


def _sse(*quadros) -> bytes:
    return "".join(f"data: {json.dumps(q)}\n\n" for q in quadros).encode() + b"data: [DONE]\n\n"


def _quadro(delta=None, parada=None, usage=None, escolhas=True):
    q = {"object": "chat.completion.chunk", "model": "qwen3:14b",
         "choices": [{"index": 0, "delta": delta or {}, "finish_reason": parada}] if escolhas else []}
    if usage is not None:
        q["usage"] = usage
    return q


async def _conversa(base_url: str, corpo_da_resposta: bytes):
    pedidos: list[httpx.Request] = []

    def handler(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return httpx.Response(200, content=corpo_da_resposta, headers={"content-type": "text/event-stream"})

    cliente = openrouter.ClienteOpenRouter(
        CHAVE_LOCAL, base_url=base_url, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    pedacos = [p async for p in cliente.transmitir(
        modelo="qwen3:14b", sistema=SISTEMA, conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[FERRAMENTA], max_tokens=100, esforco="high",
    )]
    (pedido,) = pedidos
    return json.loads(pedido.content), pedacos[-1]


async def test_o_cliente_decide_pela_base_e_a_cota_conta_o_uso_da_openai():
    """O último quadro da API da OpenAI traz o `usage` com `choices` vazio."""
    resposta = _sse(
        _quadro({"content": "ok"}),
        _quadro(parada="stop"),
        _quadro(usage={"prompt_tokens": 120, "completion_tokens": 7, "total_tokens": 127}, escolhas=False),
    )
    corpo, fim = await _conversa("http://ollama:11434/v1", resposta)
    assert corpo["stream_options"] == {"include_usage": True}
    assert "usage" not in corpo and "reasoning" not in corpo
    assert (fim.uso["entrada"], fim.uso["saida"]) == (120, 7)

    corpo, _ = await _conversa(openrouter.URL_PADRAO, resposta)
    assert corpo["usage"] == {"include": True}
    assert "stream_options" not in corpo


async def test_sem_uso_na_resposta_o_log_avisa_uma_vez(monkeypatch, caplog):
    """Um servidor que ignora `include_usage` deixa a cota sem contar: é o
    que o operador precisa saber — uma vez, não a cada turno."""
    monkeypatch.setattr(openrouter, "_avisou_sem_uso", False)
    resposta = _sse(_quadro({"content": "ok"}), _quadro(parada="stop"))
    with caplog.at_level(logging.WARNING, logger="app.assistente.openrouter"):
        await _conversa("http://ollama:11434/v1", resposta)
        await _conversa("http://ollama:11434/v1", resposta)
    avisos = [r for r in caplog.records if "não informou o uso" in r.getMessage()]
    assert len(avisos) == 1
