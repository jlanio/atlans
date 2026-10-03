# tests/unit/test_llm_generico.py
"""
The assistant talks to any API compatible with OpenAI's, not only to
OpenRouter — and only identifies itself if the installation wants it to.

Before, the key and the base had OpenRouter's name, every request carried
`X-Title: Atlans` and the `FRONTEND_URL` as referer (which puts the installation on
its public app ranking), the catalog never carried the key (a gateway or
a vLLM with a key refused) and the model id had to be `provider/name` —
Ollama's `qwen3:14b` was rejected.

  PROMPT_NAMES       (names) LLM_API_KEY and LLM_BASE_URL; the old names still work
  ATRIBUIÇÃO  (attribution) off by default; ASSISTENTE_ATRIBUICAO turns it on in all three paths
  CATÁLOGO    (catalog) from the configured base, with the key when there is one
  ID          the name in any provider's catalog; a URL or a space, no
  REQUEST      (request) outside OpenRouter, only the OpenAI API format — and the usage comes
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
from app.services.assistente_config_service import is_valid_format

RAIZ = Path(__file__).resolve().parents[2]
OLD_KEY = "sk-or-v1-antiga"  # pragma: allowlist secret
LOCAL_KEY = "local"  # pragma: allowlist secret


# ── PROMPT_NAMES ────────────────────────────────────────────────────────────────────

def _config_with(ambiente: dict[str, str]) -> list[str]:
    """The config is read at import: each combination runs in its own process."""
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


def test_with_nothing_set_assistant_has_no_key_and_base_is_openrouter():
    assert _config_with({}) == ["", "https://openrouter.ai/api/v1", "False"]


def test_old_names_still_work():
    assert _config_with({
        "OPENROUTER_API_KEY": OLD_KEY, "OPENROUTER_BASE_URL": "https://gateway.example.org/v1",
    })[:2] == [OLD_KEY, "https://gateway.example.org/v1"]


def test_generic_names_win_over_old_ones():
    # Compose passes all four; an empty one does not erase the other.
    assert _config_with({
        "LLM_API_KEY": LOCAL_KEY, "LLM_BASE_URL": "http://ollama:11434/v1",
        "OPENROUTER_API_KEY": OLD_KEY, "OPENROUTER_BASE_URL": "",
    })[:2] == [LOCAL_KEY, "http://ollama:11434/v1"]
    assert _config_with({"LLM_API_KEY": "  ", "OPENROUTER_API_KEY": OLD_KEY})[0] == OLD_KEY


@pytest.mark.parametrize("valor, ligada", [
    ("", "False"), ("false", "False"), ("talvez", "False"),
    ("true", "True"), ("1", "True"), ("sim", "True"), (" TRUE ", "True"),
])
def test_attribution_only_with_explicit_value(valor, ligada):
    assert _config_with({"ASSISTENTE_ATRIBUICAO": valor})[2] == ligada


# ── ATRIBUIÇÃO (attribution) ─────────────────────────────────────────────────

def test_client_without_title_or_referer_does_not_identify_itself():
    cabecalhos = openrouter.ClienteOpenRouter("k")._headers()
    assert "X-Title" not in cabecalhos and "HTTP-Referer" not in cabecalhos


def test_client_with_title_and_referer_identifies_itself():
    cabecalhos = openrouter.ClienteOpenRouter(
        "k", titulo="Atlans", referer="https://atlans.example.org",
    )._headers()
    assert cabecalhos["X-Title"] == "Atlans"
    assert cabecalhos["HTTP-Referer"] == "https://atlans.example.org"


@pytest.mark.parametrize("atribuicao", [False, True])
def test_chat_identifies_itself_only_with_attribution(monkeypatch, atribuicao):
    from app.services.assistente_service import criar_cliente

    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(config, "OPENROUTER_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org")
    monkeypatch.setattr(config, "ASSISTENTE_ATRIBUICAO", atribuicao)

    cliente = criar_cliente()
    cabecalhos = cliente._headers()

    assert cliente._url == "http://ollama:11434/v1/chat/completions"
    if atribuicao:
        assert cabecalhos["X-Title"] == "Atlans"
        assert cabecalhos["HTTP-Referer"] == "https://atlans.example.org"
    else:
        assert "X-Title" not in cabecalhos and "HTTP-Referer" not in cabecalhos


@pytest.mark.parametrize("atribuicao", [False, True])
async def test_probe_identifies_itself_only_with_attribution(monkeypatch, atribuicao):
    from app.api.routers import admin_assistente_router as R

    visto: dict = {}

    async def _probe(modelo, **kw):
        visto.update(kw)

    monkeypatch.setattr(R, "OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(R, "OPENROUTER_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.setattr(R.openrouter, "sondar_modelo", _probe)
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org")
    monkeypatch.setattr(config, "ASSISTENTE_ATRIBUICAO", atribuicao)

    await R._probe_or_400("qwen3:14b")

    assert visto["base_url"] == "http://ollama:11434/v1"
    if atribuicao:
        assert (visto["titulo"], visto["referer"]) == ("Atlans", "https://atlans.example.org")
    else:
        assert (visto["titulo"], visto["referer"]) == (None, None)


# ── CATÁLOGO (catalog) ───────────────────────────────────────────────────────

async def _catalog_request(**kw) -> httpx.Request:
    pedidos: list[httpx.Request] = []

    def handler(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        # Ollama's format: no name, no price, no context.
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


async def test_catalog_carries_key_when_present():
    pedido = await _catalog_request(chave="sk-local")
    assert str(pedido.url) == "http://ollama:11434/v1/models"
    assert pedido.headers["authorization"] == "Bearer sk-local"


async def test_catalog_without_key_sends_no_authorization():
    pedido = await _catalog_request()
    assert "authorization" not in pedido.headers


# ── ID ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modelo", [
    "anthropic/claude-opus-5",          # OpenRouter
    "openai/gpt-5:online",              # OpenRouter, with a variant
    "qwen3:14b",                        # Ollama
    "llama3.1",                         # Ollama, without a tag
    "meta-llama/Llama-3.1-8B-Instruct",  # vLLM (o id do Hugging Face)
    "org/grupo/modelo",                 # path with more than one slash
])
def test_any_provider_id_is_accepted(modelo):
    assert is_valid_format(modelo)


@pytest.mark.parametrize("modelo", [
    "", "antropic claude", " anthropic/claude", "anthropic/claude\n",
    "https://openrouter.ai/anthropic/claude-opus-5", "http://ollama:11434",
    "/claude", "anthropic/", "anthropic//claude", "x" * 121,
])
def test_colagem_errada_e_recusada(modelo):
    assert not is_valid_format(modelo)


# ── REQUEST (request) ─────────────────────────────────────────────────────────
#
# `usage`, `reasoning` and `cache_control` are OpenRouter parameters. The OpenAI
# API (and vLLM, LiteLLM, Ollama) only sends `usage` in the stream with
# `stream_options.include_usage` — without it, the daily quota counted nothing on a
# paid gateway. And OpenAI itself rejects fields it does not know.

SYSTEM = [
    {"type": "text", "text": "política"},
    {"type": "text", "text": "guia", "cache_control": {"type": "ephemeral"}},
]
TOOL = openrouter.ferramenta("ping", "responde", {"type": "object", "properties": {}})


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


def test_outside_openrouter_request_is_openai_api_one():
    corpo = openrouter.montar_pedido(
        modelo="qwen3:14b", sistema=SYSTEM, conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[TOOL], max_tokens=100, esforco="high", openrouter=False,
    )
    assert corpo["stream_options"] == {"include_usage": True}
    assert "usage" not in corpo
    assert "reasoning" not in corpo
    assert corpo["tools"] == [TOOL]
    assert corpo["messages"] == [
        {"role": "system", "content": "política\n\nguia"},
        {"role": "user", "content": "oi"},
    ]
    assert "cache_control" not in json.dumps(corpo)


def test_on_openrouter_request_does_not_change():
    corpo = openrouter.montar_pedido(
        modelo="anthropic/claude-opus-5", sistema=SYSTEM, conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[TOOL], max_tokens=100, esforco="high",
    )
    assert corpo["usage"] == {"include": True}
    assert corpo["reasoning"] == {"effort": "high"}
    assert "stream_options" not in corpo
    assert "cache_control" in json.dumps(corpo)


def _sse(*quadros) -> bytes:
    return "".join(f"data: {json.dumps(q)}\n\n" for q in quadros).encode() + b"data: [DONE]\n\n"


def _frame(delta=None, parada=None, usage=None, with_choices=True):
    q = {"object": "chat.completion.chunk", "model": "qwen3:14b",
         "choices": [{"index": 0, "delta": delta or {}, "finish_reason": parada}] if with_choices else []}
    if usage is not None:
        q["usage"] = usage
    return q


async def _chat(base_url: str, response_body: bytes):
    pedidos: list[httpx.Request] = []

    def handler(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return httpx.Response(200, content=response_body, headers={"content-type": "text/event-stream"})

    cliente = openrouter.ClienteOpenRouter(
        LOCAL_KEY, base_url=base_url, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    pedacos = [p async for p in cliente.transmitir(
        modelo="qwen3:14b", sistema=SYSTEM, conversa=[{"role": "user", "content": "oi"}],
        ferramentas=[TOOL], max_tokens=100, esforco="high",
    )]
    (pedido,) = pedidos
    return json.loads(pedido.content), pedacos[-1]


async def test_client_decides_by_base_and_quota_counts_openai_usage():
    """The last frame of the OpenAI API carries `usage` with empty `choices`."""
    resposta = _sse(
        _frame({"content": "ok"}),
        _frame(parada="stop"),
        _frame(usage={"prompt_tokens": 120, "completion_tokens": 7, "total_tokens": 127}, with_choices=False),
    )
    corpo, fim = await _chat("http://ollama:11434/v1", resposta)
    assert corpo["stream_options"] == {"include_usage": True}
    assert "usage" not in corpo and "reasoning" not in corpo
    assert (fim.uso["entrada"], fim.uso["saida"]) == (120, 7)

    corpo, _ = await _chat(openrouter.URL_PADRAO, resposta)
    assert corpo["usage"] == {"include": True}
    assert "stream_options" not in corpo


async def test_without_usage_in_response_log_warns_once(monkeypatch, caplog):
    """A server that ignores `include_usage` leaves the quota uncounted: that is
    what the operator needs to know — once, not on every turn."""
    monkeypatch.setattr(openrouter, "_avisou_sem_uso", False)
    resposta = _sse(_frame({"content": "ok"}), _frame(parada="stop"))
    with caplog.at_level(logging.WARNING, logger="app.assistente.openrouter"):
        await _chat("http://ollama:11434/v1", resposta)
        await _chat("http://ollama:11434/v1", resposta)
    avisos = [r for r in caplog.records if "não informou o uso" in r.getMessage()]
    assert len(avisos) == 1
