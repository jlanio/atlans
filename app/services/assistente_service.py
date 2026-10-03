# app/services/assistente_service.py
"""
The assistant: the conversation that builds workflows, talking to THIS process's MCP server.

The platform already exposes 42 tools over MCP — scope, quota, minimum role,
secret redaction and auditing, all tested. The assistant repeats none of that:
it **calls the same tools along the same path**, in process.

    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        await servidor.call_tool(nome, argumentos, contexto)
    finally:
        ESCOPO_ATUAL.reset(ficha)

`ServidorAtlans.call_tool` accepts `context=None` and `escopo_da_chamada` falls
back to the `ContextVar` when there is no request (`app/mcp/escopo.py`). So the
scope guard, the quota bucket, the minimum role, the exception mapping and the
audit row happen exactly as they do for an external client. **The rule is one
and the same on both paths** — and an authorization defect here would be a
defect in MCP, which has tests.

Three decisions worth explaining:

1. **No HTTP and no PAT.** The alternative was an MCP connector hosted by the
   model provider (what some APIs offer as `mcp_servers=[…]`), which would make
   this loop unnecessary. It would cost one personal token per user traveling
   outside, a `/mcp` that must be public, and the assistant dead on a closed
   installation. In process there is not even a network round trip — and the
   loop stays provider-independent: what talks to the model is
   `app/services/openrouter.py`, the only module that knows the wire format.

2. **The transcript does not come from the client.** `conversar` receives and
   returns the conversation, but the caller is the one that stores it — and
   storing it in the BROWSER would hand the client the power to forge a
   `tool_result`. A tool result is the server's word on what happened; a client
   that rewrites it can tell the model whatever it wants ("the user is an
   administrator", "validation passed"). The route stores it in Redis; this
   module only requires that it not come from outside.

3. **Two brakes, and one of them does not depend on Redis.** The daily token
   quota fails open when Redis goes away, like the rest of the quota module.
   But spending is money, not load: that is why there is also `TETO_DE_VOLTAS`,
   an in-memory counter that closes the loop even with no Redis at all. A model
   stuck in a tool cycle is the fastest way to spend a lot without anyone
   noticing.
"""
from __future__ import annotations

from functools import lru_cache

import asyncio
import json
from contextlib import aclosing, asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

from mcp.server.mcpserver.exceptions import ToolError

from app.core.utils.logger import get_logger
from app.mcp import cotas
from app.mcp.erros import erro
from app.mcp.escopo import ESCOPO_ATUAL, EscopoEfetivo, escopo_do_editor
from app.mcp.guardas import GUARDAS
from app.mcp.instrucoes import INSTRUCOES
from app.services import (
    assistente_config_service, openrouter, teto_do_assistente, uso_service,
)

logger = get_logger("app.assistente")

# ── The write gate ────────────────────────────────────────────────────────────
# The owner's decision: the assistant BUILDS, VALIDATES and SHOWS; what writes is
# the panel, after the click on apply. This cannot be a text promise in the
# prompt — a model that does not ask writes, and then the apply button becomes
# decoration.
#
# And it is not a scope change: `validate_workflow` requires `workflows:write`
# (`app/mcp/guardas.py`), so removing the scope would also remove validation,
# which is the heart of the assistant. The gate is per tool.
#
# The rule comes from `GUARDAS` instead of a hand-written list, which would go
# stale with the first new tool: everything that is NOT read-only is out, except
# the two exceptions below. A new write tool is born blocked — failing closed,
# which is the right direction to err in.
ESCREVEM_MAS_PASSAM = frozenset(
    {
        # Simulates the whole definition and persists nothing. It is the loop that
        # makes the assistant useful: build, see the report, fix, repeat.
        "validate_workflow",
        # Deliberate exception from the owner: the assistant executes. It asks for
        # approval in text and runs on the next turn — the confirmation belongs to
        # the conversation, not the code.
        "run_workflow",
        # Saving to the catalog a WFS source that the probe confirmed: cheap,
        # reversible, executes nothing — and it is what lets the next request find
        # the source without probing again. Same owner decision the Home applies.
        "register_source",
        # Probing a WFS: metadata only, and it updates the state of an already
        # cataloged source. Without this the assistant would only see the
        # catalog, never the new source.
        "probe_source",
    }
)


# ── The delivery ─────────────────────────────────────────────────────────────
# The tool that puts the workflow on screen. It does NOT exist in MCP: it is not
# in `GUARDAS`, does not appear in `/mcp`, and an external client never sees it.
# The canvas belongs to the editor, and only makes sense to whoever is looking at it.
#
# Why it exists. Before, putting the workflow on screen was a SIDE EFFECT of a
# call to `validate_workflow`: the panel read the definition from that tool's
# argument and drew it. It worked when the model validated — and nothing forced
# it to validate. Asked to "read the shapefile and make a 500 m buffer", it
# could read the Drive, execute and return the GeoJSON: request fulfilled, empty
# canvas. No instruction fixes that, because the model had no delivery
# AFFORDANCE — there was nothing whose name was "deliver the workflow".
#
# Now there is, and the prompt can require it by name. Validating goes back to
# being a means.
NOME_DO_DESENHO = "desenhar_no_canvas"

FERRAMENTA_DO_DESENHO: dict[str, Any] = {
    "name": NOME_DO_DESENHO,
    "description": (
        "Desenha o fluxo no canvas de quem esta conversando, AGORA. E a sua "
        "entrega: enquanto voce nao chamar isto, a pessoa nao ve fluxo nenhum.\n\n"
        "Chame a cada passo do trabalho, nao so no fim — a pessoa acompanha o "
        "fluxo crescer. Mande sempre a definicao INTEIRA como ela esta ate "
        "agora, e nao um pedaco: o canvas e substituido pelo que voce mandar, "
        "preservando a posicao dos nos que continuarem existindo.\n\n"
        "Nao grava nada. O fluxo so e salvo quando a pessoa clica em Salvar."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "definition": {
                "type": "object",
                "description": (
                    "A definicao inteira ate agora: `nodes` e `edges`, no mesmo "
                    "formato que `validate_workflow` recebe."
                ),
            },
            "nota": {
                "type": "string",
                "description": (
                    "Uma linha sobre o que mudou neste desenho, para a pessoa "
                    "acompanhar. Ex.: 'liguei o buffer na leitura do Drive'."
                ),
            },
        },
        "required": ["definition"],
    },
}


def _ja_desenhou(conversa: list[dict[str, Any]]) -> bool:
    """Has anyone already called `desenhar_no_canvas` in this conversation?

    Read from the TRANSCRIPT, and not from a loop variable, because the
    conversation is resumed between turns: the person sends the second message
    and the loop starts from scratch. An in-memory counter would say "has not
    drawn yet" in a conversation that already has a whole workflow on screen.
    """
    for mensagem in conversa:
        if mensagem.get("role") != "assistant":
            continue
        conteudo = mensagem.get("content")
        if not isinstance(conteudo, list):
            continue
        for bloco in conteudo:
            if (
                isinstance(bloco, dict)
                and bloco.get("type") == "tool_use"
                and bloco.get("name") == NOME_DO_DESENHO
            ):
                return True
    return False


# The refusal to execute before drawing. It is the same path that produced the
# data answer: read the Drive, run, return the artifact — request fulfilled
# without ever building anything. Refusing until there is a workflow on screen
# closes that door without removing execution from the scope, and the cycle the
# owner describes (build, test, decide) stays whole: draw, and then execute.
EXIGEM_DESENHO_ANTES = frozenset({"run_workflow"})

MENSAGEM_DE_EXECUTAR_ANTES = (
    f"Ainda nao ha fluxo no canvas. Chame `{NOME_DO_DESENHO}` com a definicao "
    "antes de executar — a pessoa precisa ver o que vai rodar. Executar para "
    "responder com o dado nao e o trabalho aqui: o trabalho e montar o fluxo."
)


def bloqueada_no_editor(nome: str) -> bool:
    """True if this tool cannot be used by the assistant."""
    guarda = GUARDAS.get(nome)
    if guarda is None:
        # With no row in GUARDAS the tool does not exist for MCP, and `call_tool`
        # would refuse it anyway. Refusing here too keeps the response uniform
        # instead of letting the server's error leak.
        return True
    if guarda.read_only:
        return False
    return nome not in ESCREVEM_MAS_PASSAM


# The refusal text says what to do instead. Without it the model tries
# again, spends a round and ends the conversation without delivering the workflow.
MENSAGEM_DO_PORTAO = (
    "Esta ferramenta nao esta disponivel no assistente: quem grava o fluxo e a "
    "pessoa, pelo botao de aplicar no editor. Mostre a definicao final e ofereca "
    "aplicar."
)


# Streaming is mandatory with a large `max_tokens`: without it the request hits
# the HTTP timeout before the model finishes.
MAX_TOKENS = 64_000

# The reasoning effort requested from the model (`reasoning.effort` on
# OpenRouter, which translates it into what each family accepts). High because
# building a workflow is planning: the model reads the catalog, picks nodes,
# matches ports and fixes validation — saving here shows up as a wrong workflow,
# not as a slow answer.
ESFORCO_DO_RACIOCINIO = "high"

# How many tools of the SAME round run at the same time. The ceiling protects
# the rest of the worker: each task can open its own database session (the Home
# gate reads the workflow's origin; tool bodies query at will) and the process
# pool is a single one (POOL_SIZE + MAX_OVERFLOW). What decides HOW MANY calls
# come in the round is the model; what decides how many run AT A TIME is this ceiling.
TETO_DO_LOTE_EM_PARALELO = 5

# One round = one call to the model. Building a real workflow takes 6 to 12
# (understand, guide, catalog, `describe_node` for each node, validate, fix,
# validate again). The ceiling exists for the pathological case: the model that
# validates, fixes and revalidates without converging. When it is hit, the
# conversation ends with an explanation instead of continuing to spend.
TETO_DE_VOLTAS = 24

# A large tool result (the catalog index, a whole definition) enters the
# history and is resent on every round. Cutting protects the context and the
# bill; the cut is announced so the model knows there was a cut — a silent
# truncation would make the model conclude the data simply does not exist.
MAX_CHARS_POR_RESULTADO = 60_000
AVISO_DE_CORTE = "\n\n[resultado cortado: use um filtro mais estreito para ver o resto]"


@dataclass(frozen=True)
class Uso:
    """What a turn cost, summed over the conversation.

    The keys are the ones `openrouter._uso_do_projeto` produces. `entrada` already
    INCLUDES what came from the cache (`cache_leitura` and `cache_escrita` are
    slices of it, informational), and `raciocinio` is a slice of `saida`. `custo`
    comes in OpenRouter credits (dollars) — it is information for the log and for
    the person, not for the quota, which is in tokens.
    """

    entrada: int = 0
    saida: int = 0
    cache_leitura: int = 0
    cache_escrita: int = 0
    raciocinio: int = 0
    custo: float = 0.0

    @classmethod
    def de(cls, uso: dict[str, Any] | None) -> "Uso":
        uso = uso or {}
        return cls(
            entrada=int(uso.get("entrada") or 0),
            saida=int(uso.get("saida") or 0),
            cache_leitura=int(uso.get("cache_leitura") or 0),
            cache_escrita=int(uso.get("cache_escrita") or 0),
            raciocinio=int(uso.get("raciocinio") or 0),
            custo=float(uso.get("custo") or 0.0),
        )

    def __add__(self, outro: "Uso") -> "Uso":
        return Uso(
            entrada=self.entrada + outro.entrada,
            saida=self.saida + outro.saida,
            cache_leitura=self.cache_leitura + outro.cache_leitura,
            cache_escrita=self.cache_escrita + outro.cache_escrita,
            raciocinio=self.raciocinio + outro.raciocinio,
            custo=self.custo + outro.custo,
        )

    @property
    def cobravel(self) -> int:
        """The total that counts toward the quota: everything that went in plus everything that came out.

        The cache read COUNTS — it costs 10% of the input price, but it costs,
        and the quota is about what the platform pays. It is already inside
        `entrada`, so it is not added again.
        """
        return self.entrada + self.saida

    def como_dict(self) -> dict[str, Any]:
        return {
            "entrada": self.entrada,
            "saida": self.saida,
            "cache_leitura": self.cache_leitura,
            "cache_escrita": self.cache_escrita,
            "raciocinio": self.raciocinio,
            "custo": round(self.custo, 6),
            "total": self.cobravel,
        }


@dataclass(frozen=True)
class Evento:
    """An SSE frame. `tipo` is the contract with the web panel."""

    tipo: str
    dados: dict[str, Any] = field(default_factory=dict)


class ContextoLocal:
    """The `ctx` the tools receive when the assistant calls them in process.

    It exists because of ONE tool: `run_workflow` calls
    `ctx.report_progress(...)` to report progress node by node
    (`app/mcp/tools/execucao.py`). All the others only use `ctx` to find the
    scope — and `escopo_da_chamada` looks for `ctx.request_context.request.state`,
    does not find it (this class has none of that, on purpose) and falls back to
    the `ContextVar`.

    The SDK's tool manager calls no method on this object: it passes it on as an
    argument to the tool function and nothing more (`Tool.run`). That is why a
    stand-in this simple is enough.

    And here progress works BETTER than on the MCP path: there
    `report_progress` is silent without a `progressToken` from the client; here
    each completed node becomes a frame in the SSE the browser is reading.
    """

    def __init__(self, emitir, ferramenta_id: str | None = None) -> None:
        self._emitir = emitir
        # The `tool_use_id` of the call that owns this context. With the tools of
        # a round running in PARALLEL, the `progresso` frame needs to say whose
        # it is — without the id, the browser paints the bar on the wrong tool
        # (the reducer matched "the one that is running", and now several run).
        self._ferramenta_id = ferramenta_id

    async def report_progress(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        dados: dict[str, Any] = {
            "concluidos": int(progress),
            "total": int(total) if total is not None else None,
            "mensagem": message,
        }
        if self._ferramenta_id is not None:
            dados["id"] = self._ferramenta_id
        await self._emitir(Evento("progresso", dados))


def criar_cliente() -> openrouter.ClienteOpenRouter:
    """The model client, built from the platform's key.

    The configuration is read HERE, on every conversation, and not at import:
    that is what lets the test swap it with `monkeypatch` and the operator swap
    it with a restart. With ASSISTENTE_ATRIBUICAO, the name and `FRONTEND_URL` go
    as the app attribution on the OpenRouter dashboard; without it, nothing
    identifies the installation.
    """
    from app.core.config import (
        ASSISTENTE_ATRIBUICAO, FRONTEND_URL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    )

    return openrouter.ClienteOpenRouter(
        OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        referer=(FRONTEND_URL or None) if ASSISTENTE_ATRIBUICAO else None,
        titulo="Atlans" if ASSISTENTE_ATRIBUICAO else None,
    )


def escopo_do_editor_para(usuario, workspace_ids) -> EscopoEfetivo:
    """This conversation's scope, built from the session's user.

    A one-line bridge between the database `User` and the pure constructor in
    `app/mcp/escopo.py`, which knows no model at all on purpose. Without it the
    route would have to know the names of the user's fields — and would start
    breaking when they changed.
    """
    return escopo_do_editor(
        user_id=usuario.id_hash,
        username=getattr(usuario, "username", None),
        workspace_ids=workspace_ids,
    )


async def ferramentas_para_o_modelo(
    servidor, escopo: EscopoEfetivo, superficie: "Superficie | None" = None
) -> list[dict[str, Any]]:
    """The MCP tools in the format the model's API expects.

    `list_tools()` already filters by the `ContextVar` — the same mechanism that
    serves the external client serves here, so the assistant's catalog is exactly
    what its scope reaches, without a second list to go stale.

    The `superficie` decides TWO things: which MCP tools come in (`permitida` —
    in the editor, everything except what the write gate blocks; on the Home,
    everything in `GUARDAS`) and which LOCAL tools open the list
    (`ferramentas_extras` — drawing in the editor, the globe on the Home). The
    default is the editor, so its catalog stays byte-for-byte the same.

    The format is the wire one (`{"type": "function", "function": {...}}`), built
    by `openrouter.ferramenta` from the MCP `input_schema` — the same schema, with
    no content translation. The argument arrives streamed, drop by drop, and so a
    cut by `max_tokens` can deliver half an argument that still looks well
    formed; the defense is in the loop (`length`).
    """
    superficie = superficie or EDITOR
    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        tools = await servidor.list_tools()
    finally:
        ESCOPO_ATUAL.reset(ficha)

    do_mcp = [
        openrouter.ferramenta(t.name, t.description or "", t.input_schema)
        for t in tools
        if superficie.permitida(t.name)
    ]
    # The surface's tools come FIRST in the list, and that is not aesthetics:
    # what opens the list is what the model reads first when deciding what to do.
    # The tool that defines the delivery cannot be buried among 38 others.
    extras = [
        openrouter.ferramenta(f["name"], f.get("description"), f.get("input_schema"))
        for f in superficie.ferramentas_extras
    ]
    return [*extras, *do_mcp]


# What changes compared to an external MCP client. Short on purpose: it fixes
# the ONLY point where `INSTRUCOES` stops applying here, which is the sentence
# "only call create_workflow/update_workflow after validation passes" — those
# tools do not exist for the assistant. Without this correction the model looks
# for a tool that is not in the list and ends the conversation delivering nothing.
INSTRUCOES_DO_EDITOR = """\
Voce esta dentro do editor do Atlans, olhando para o mesmo canvas que a pessoa.
Nao e um cliente externo, e o trabalho aqui e outro.

SUA ENTREGA E O FLUXO NO CANVAS
`desenhar_no_canvas` e a unica coisa que a pessoa ve acontecer. Enquanto voce
nao chamar, a tela dela esta vazia — por mais que voce tenha explicado bem.

- Desenhe CEDO e desenhe VARIAS VEZES. Assim que souber o primeiro no, desenhe.
  Ligou o segundo, desenhe de novo. A pessoa esta acompanhando o fluxo crescer;
  um unico desenho no fim desperdica isso.
- Mande sempre a definicao INTEIRA como ela esta, nunca so a parte nova.
- Use a `nota` para dizer em uma linha o que mudou.

NAO E ENTREGA:
- Responder com o DADO. Se pedirem "lê o shapefile e faz buffer de 500 m", o
  pedido e um FLUXO que faz isso, nao o GeoJSON do resultado. Executar para
  produzir a resposta e o erro mais facil de cometer aqui.
- Mostrar a definicao em texto ou em bloco de codigo. Ela vai no canvas.
- Descrever o que voce faria. Desenhe.

A ORDEM DO TRABALHO
1. Entenda o que a pessoa quer. Pergunte se faltar algo essencial.
2. Dado externo (WFS)? `search_sources` pelo tema e `describe_source` ANTES de
   qualquer outra coisa — nunca invente url/typeName. So sem resultado:
   `probe_source` (sonda) e `register_source` (guarda para a proxima vez).
3. `search_nodes` / `describe_node` para os nos que voce nao domina — e peca as
   fichas de TODOS os nos do fluxo numa chamada so (`name` aceita lista, ate 8
   por chamada; mais que isso, divida em dois lotes), em vez de uma rodada por no.
4. `desenhar_no_canvas` — mesmo incompleto, mesmo com um no so.
5. Continue montando, desenhando a cada passo.
6. `validate_workflow` quando o desenho estiver completo. Corrija o que ela
   apontar e DESENHE DE NOVO.
7. Diga o que ficou pronto. Nao prometa ter salvo: salvar e da pessoa.

O QUE VOCE NAO FAZ
- Voce NAO grava. `create_workflow` e `update_workflow` nao existem aqui, e o
  desenho no canvas nao e gravacao — e o rascunho dela, que ela salva ou joga
  fora.
- Voce pode executar, e execucao e REAL: dispara nos que escrevem em banco e
  publicam mapa. So depois de o fluxo estar desenhado, so depois de perguntar
  com todas as letras, e so com um "pode rodar" explicito na mensagem seguinte.
"""


def montar_sistema(
    instrucoes_extras: str | None = None, *, superficie: "Superficie | None" = None
) -> list[dict[str, Any]]:
    """The system prompt — the MCP server's instructions, not a second copy.

    `INSTRUCOES` (`app/mcp/instrucoes.py`) already says everything that needs to
    be said before the first call: validate before saving, ask for confirmation
    before creating or executing, never invent a property, credentials by
    identifier, and — what matters most here — that `untrusted_data` is DATA and
    not instruction. Writing a new text would create two policies to diverge.

    On top of it comes `superficie.instrucoes`, which corrects the point where
    the MCP policy does not apply on that surface: in the editor, the write gate
    (`INSTRUCOES_DO_EDITOR`); on the Home, the delivery being a layer on the
    globe and confirmation by click (`INSTRUCOES_DA_HOME`). The default is the
    editor.

    The guide does NOT come in: it is 25 KB across eight topics
    (`app/mcp/guia/`), reachable through `get_authoring_guide`. Loading it whole
    would double the prefix of every conversation to serve the topic one of them
    will read.
    """
    from app.core.config import ASSISTENTE_IDIOMA

    superficie = superficie or EDITOR
    blocos: list[dict[str, Any]] = [
        {"type": "text", "text": INSTRUCOES},
        {"type": "text", "text": superficie.instrucoes},
        # The reasoning too: it is SHOWN to the person (the "Raciocínio"
        # (reasoning) section of the panel), and a model that converses in
        # Portuguese tends to think in English. No API chooses the language of
        # the reasoning; asking is the only control, and it works most of the time.
        {"type": "text", "text": f"Responda sempre em {ASSISTENTE_IDIOMA}, seja qual "
                                 "for o idioma da pergunta. Raciocine também em "
                                 f"{ASSISTENTE_IDIOMA}: o seu raciocínio é mostrado à pessoa."},
        # The cache breakpoint of the STABLE PREFIX. It goes on the last
        # always-present block of BOTH surfaces — the four above are byte-for-byte
        # identical across every conversation and every user OF THE SAME SURFACE
        # (the surface block is a constant per surface, the language is config,
        # the guide is `lru_cache`). Since the cache is by prefix and the render
        # order is `tools` -> `system` -> `messages`, a marker here caches
        # everything that comes before: the tools + these three blocks, the
        # ~15k-token prefix. Editor and Home have distinct prefixes (block [1]
        # differs), so two stable prefixes, one per surface — neither
        # contaminates the other.
        #
        # OpenRouter passes the marker on to providers that have explicit prompt
        # caching and ignores it for those that cache on their own — in both
        # cases anyone's second conversation (within the window) READS the
        # prefix instead of rewriting it at full price. The second marker goes on
        # the last human message (`openrouter.montar_mensagens`), and closes the
        # prefix that is the same across all tool rounds of a turn.
        #
        # Only the type, no `ttl`: the cache duration is the decision of the
        # provider behind the router, and a field it does not recognize would be
        # a rejection on every conversation.
        {
            "type": "text",
            "text": _guia_do_prefixo(),
            "cache_control": {"type": "ephemeral"},
        },
    ]
    if instrucoes_extras:
        # Stays OUTSIDE the cache on purpose: it is optional, never passed today,
        # and can be dynamic. The breakpoint above already closed the stable prefix.
        blocos.append({"type": "text", "text": instrucoes_extras})
    return blocos


@lru_cache(maxsize=1)
def _guia_do_prefixo() -> str:
    """The two guide topics that go into the prompt, against the six that do not.

    `recipes` are FOUR complete workflows, written out. It is the demonstration of
    how a deliverable ends up finished — and it was exactly what a model that
    answered with data was missing. `overview` gives the vocabulary to read them.

    The other six (edges, credentials, expressions, inputs, SQL, pitfalls)
    remain on demand through `get_authoring_guide`: they are reference for a
    one-off question, not material that changes the shape of the work.

    It costs ~10 KB (~3k tokens) in a STABLE prefix, which the cache keeps at 10% —
    it is the cheap part of a conversation. `lru_cache` because the disk does not
    need to be read on every turn.
    """
    from app.mcp import guia

    partes = [
        "Guia de autoria — o essencial. Os demais tópicos (arestas, credenciais,",
        "expressoes, entradas, SQL, armadilhas) estao em `get_authoring_guide`.",
        "",
        guia.ler_topico("overview"),
        "",
        guia.ler_topico("recipes"),
    ]
    return "\n".join(partes)


# ── Surfaces ──────────────────────────────────────────────────────────────────
# There is a single loop; what changes between the editor assistant and the Home
# assistant is a PACKAGE of six things, gathered here. The editor (`EDITOR`) is
# the default for everything — `conversar`, `montar_sistema` and
# `ferramentas_para_o_modelo` fall back to it when nobody passes a surface —, so
# the editor stays byte-for-byte the same and the current tests pass without
# edits. The Home lives in `assistente_superficie.py`, which imports this module
# (never the other way around) and builds its own `Superficie`.


@dataclass
class EstadoDoLaco:
    """The MUTABLE state of a conversation, which the surface package reads and writes.

    It lives once per `conversar` call, outside the round loop: `desenhou`
    survives across turns (a workflow drawn on the previous turn is still on
    screen). What belongs to ONE CALL (the `tool_use_id`) does not live here on
    purpose: the tools of a round run in parallel, and a shared "current call"
    field would be a race — the id travels as an argument of the gate.
    """

    escopo: EscopoEfetivo
    redis: Any
    conversa_id: str | None
    # Output channel of the tools and the gates: enqueues an `Evento` that the
    # loop drains and yields on the SSE. It is the same `emitir` that `ContextoLocal` uses.
    emitir: Callable[["Evento"], Any]
    desenhou: bool = False


@dataclass(frozen=True)
class Superficie:
    """The package that sets one surface apart from the other. Frozen: it is configuration.

    - `instrucoes`: block [1] of the system prompt (corrects where the MCP policy
      does not apply there).
    - `ferramentas_extras`: the LOCAL tools that open the model's list (the
      drawing, the globe) — they do not exist in MCP.
    - `executores_locais`: name → coroutine `(argumentos, estado) -> (texto,
      erro)`, for the tools that do NOT go to the server.
    - `permitida`: `(nome) -> bool`, which MCP tools go into the list.
    - `portao`: coroutine `(estado, nome, argumentos, tool_use_id) -> (texto,
      erro) | None`, called before dispatching to the server. `None` = may
      proceed. The `tool_use_id` identifies the exact call (the Home's
      confirmation matches the click by it) and travels as an argument because
      the tools of a round run in parallel — shared state here would be a race.
      The field's annotation declares the four arguments on purpose: a new gate
      written with three would typecheck and break on EVERY call.
    - `quadros_extras`: `(estado, nome, argumentos, resultado, erro) ->
      list[Evento]`, the frames that surface emits after a tool (the `proposta`
      in the editor; `fluxo`/`camada` on the Home).
    """

    nome: str
    instrucoes: str
    ferramentas_extras: tuple[dict[str, Any], ...]
    executores_locais: dict[str, Callable[[Any, EstadoDoLaco], Any]]
    permitida: Callable[[str], bool]
    portao: Callable[[EstadoDoLaco, str, Any, str | None], Any]
    quadros_extras: Callable[[EstadoDoLaco, str, Any, str, bool], list["Evento"]]


async def _desenhar(argumentos: Any, estado: EstadoDoLaco) -> tuple[str, bool]:
    """The editor's delivery: puts the workflow on the canvas. Does not go to the server.

    The visible effect is the `proposta` frame (emitted by `_quadros_do_editor`);
    what goes back to the model is the confirmation that the person is seeing it.
    Sets `estado.desenhou` on success — that is what unlocks `run_workflow` later.
    """
    definicao = argumentos.get("definition") if isinstance(argumentos, dict) else None
    if not isinstance(definicao, dict):
        return ("`definition` precisa ser um objeto com `nodes` e `edges`.", True)
    nos = len(definicao.get("nodes") or [])
    arestas = len(definicao.get("edges") or [])
    estado.desenhou = True
    return (
        f"Desenhado no canvas: {nos} nó(s) e {arestas} aresta(s). A pessoa está "
        "vendo agora. Continue montando e chame de novo a cada mudança; valide "
        "com `validate_workflow` quando o desenho estiver completo.",
        False,
    )


async def _portao_do_editor(
    estado: EstadoDoLaco, nome: str, argumentos: Any, tool_use_id: str | None = None
) -> tuple[str, bool] | None:
    """The editor's gate: order (draw before executing) + write blocking.

    It is the body that used to live inline in `_executar_ferramenta`. `None` when
    the tool may proceed to the server.
    """
    if nome in EXIGEM_DESENHO_ANTES and not estado.desenhou:
        logger.info("Assistente barrou %s antes do desenho (usuário %s).", nome, estado.escopo.user_id)
        return (MENSAGEM_DE_EXECUTAR_ANTES, True)
    if bloqueada_no_editor(nome):
        # The gate's GUARANTEE, not the convenience. Hiding the tool from the list
        # keeps the model from wanting it; refusing here prevents it from running
        # when the model names it anyway — because it read it in an example,
        # hallucinated, or someone ordered it in a workflow's text. It is the
        # same separation MCP makes between `list_tools` and `call_tool`.
        logger.info("Assistente barrou %s (usuário %s).", nome, estado.escopo.user_id)
        return (MENSAGEM_DO_PORTAO, True)
    return None


def _quadros_do_editor(
    estado: EstadoDoLaco, nome: str, argumentos: Any, resultado: str, deu_erro: bool
) -> list["Evento"]:
    """The `proposta` frame — the definition the Apply button receives."""
    proposta = _proposta_de(nome, argumentos, resultado, deu_erro)
    return [Evento("proposta", proposta)] if proposta is not None else []


EDITOR = Superficie(
    nome="editor",
    instrucoes=INSTRUCOES_DO_EDITOR,
    ferramentas_extras=(FERRAMENTA_DO_DESENHO,),
    executores_locais={NOME_DO_DESENHO: _desenhar},
    permitida=lambda nome: not bloqueada_no_editor(nome),
    portao=_portao_do_editor,
    quadros_extras=_quadros_do_editor,
)


async def conversar(
    *,
    escopo: EscopoEfetivo,
    transcrito: list[dict[str, Any]],
    servidor,
    cliente,
    redis=None,
    instrucoes_extras: str | None = None,
    superficie: "Superficie | None" = None,
    conversa_id: str | None = None,
    ao_fechar_turno: Callable[[list[dict[str, Any]]], Any] | None = None,
) -> AsyncIterator[Evento]:
    """Runs the conversation until the model stops asking for tools.

    `transcrito` comes in with the history (including the new message from the
    person using it) and the last event returns the updated history, for the
    caller to store. See note 2 of the module: this history **cannot** come from
    the browser.

    Emits, in this order and as many times as needed:
      `pensando` · `texto` · `cota` · `ferramenta` · `progresso` · `ferramenta_fim`
    (`cota` goes out after each model response, with the window's running total —
    only when there is Redis to count; it does not enter the transcript or the replay.)

    The last frame is ALWAYS `fim`, even when the conversation ended badly — it is
    the one that carries the transcript, and losing the transcript because the
    model stumbled on the eighth round would make the person start over from
    scratch. When there was a failure, an `erro` frame comes first and `fim`
    carries `ok=False`.

    The loop itself lives in `LacoDaConversa`.
    """
    laco = LacoDaConversa(
        escopo=escopo,
        transcrito=transcrito,
        servidor=servidor,
        cliente=cliente,
        redis=redis,
        superficie=superficie or EDITOR,
        conversa_id=conversa_id,
        ao_fechar_turno=ao_fechar_turno,
    )
    async with aclosing(laco.rodar(instrucoes_extras)) as eventos:
        async for evento in eventos:
            yield evento


class LacoDaConversa:
    """One `conversar` call: what spans the rounds and the phases of each one.

    Each round is a call to the model (`_chamar_modelo`), its charge
    (`_cobrar`), the response entering the conversation (`_anexar_resposta`) and,
    if the model asked, the tools (`_executar_chamadas`); `fim` comes out of
    `_encerrar`. The turn-closing hook, which was a closure of the generator,
    became a method; the channel for the tools and gates is the queue's `put`.

    It is still a generator PULLED by the SSE: the phases that emit frames are
    generators too, and each effect (the charge, the hook, the tool) only happens
    when the consumer asks for the next frame. Each nested phase is opened with
    `aclosing`: if the consumer closes the generator midway, it closes along with
    it, right away — as it did when the loop was a single body.
    """

    def __init__(
        self,
        *,
        escopo: EscopoEfetivo,
        transcrito: list[dict[str, Any]],
        servidor,
        cliente,
        redis,
        superficie: "Superficie",
        conversa_id: str | None,
        ao_fechar_turno: Callable[[list[dict[str, Any]]], Any] | None,
    ) -> None:
        self.escopo = escopo
        self.servidor = servidor
        self.cliente = cliente
        self.redis = redis
        self.superficie = superficie
        self.ao_fechar_turno = ao_fechar_turno
        self.conversa = list(transcrito)
        self.uso_total = Uso()
        self.voltas = 0
        self.falhou = False

        # ASYNC queue (not a list): the tool runs in a task and the loop drains
        # this queue IN PARALLEL, yielding each frame as soon as it arrives. With
        # the list drained only after the tool's `await`, the `report_progress`
        # of a long run stayed buffered and arrived all at once, at the end of
        # the execution.
        #
        # Its `put` is the output channel of the tools and gates (the
        # `report_progress`, the Home's confirmation frame): it enqueues instead
        # of yielding directly because an async generator can only yield from
        # within its own body. And it is the queue's `put`, not a method of the
        # loop: a bound method, stored in the state and in the tools' context,
        # would tie the whole loop (the conversation, the catalog, the client)
        # into a reference cycle that only the cycle collector undoes, well
        # after the end.
        self.fila: asyncio.Queue = asyncio.Queue()
        # Sentinel put in place when the tool finishes (the `com_batimento` pattern):
        # the loop drains until it sees it, NEVER cancelling `fila.get()` — so no
        # enqueued frame gets lost in a cancellation race.
        self._fim_da_ferramenta = object()

        self.conversa_id = conversa_id

        # Resolved ONCE per conversation, in `_preparar`; the tools' state
        # (`EstadoDoLaco`) is also born there, last.
        self.teto_de_tokens: int | None = None
        self.modelo: str | None = None
        self.ferramentas: list[dict[str, Any]] = []
        self.sistema: list[dict[str, Any]] = []

    async def _fechar_turno(self) -> None:
        """Hook called after each message enters the conversation, so the caller can
        persist incrementally (the assistant PR uses it; the editor passes
        nothing). Always in try/except: failing to persist must not bring down
        the conversation that is already live."""
        if self.ao_fechar_turno is None:
            return
        try:
            await self.ao_fechar_turno(self.conversa)
        except Exception:
            logger.exception("Falha no gancho ao_fechar_turno (usuário %s).", self.escopo.user_id)

    async def rodar(self, instrucoes_extras: str | None) -> AsyncIterator[Evento]:
        """The loop: one round per model response, until it stops asking for
        tools — or until an error exit, which still ends in `fim`."""
        await self._preparar(instrucoes_extras)
        while True:
            self.voltas += 1
            if self.voltas > TETO_DE_VOLTAS:
                self.falhou = True
                yield self._erro_do_teto()
                break

            resposta: openrouter.Resposta | None = None
            async with aclosing(self._chamar_modelo()) as pedacos:
                async for pedaco in pedacos:
                    if isinstance(pedaco, openrouter.Resposta):
                        resposta = pedaco
                    else:
                        yield pedaco
            if resposta is None:
                break  # the model failed, and the `erro` frame has already gone out

            cota = await self._cobrar(resposta)
            if cota is not None:
                yield cota
            await self._anexar_resposta(resposta)

            erro = self._erro_da_parada(resposta.parada)
            if erro is not None:
                self.falhou = True
                yield erro
                break
            if resposta.parada != "tool_calls":
                break
            chamadas = [b for b in resposta.blocos if b.get("type") == "tool_use"]
            if not chamadas:
                break

            async with aclosing(self._executar_chamadas(chamadas)) as quadros:
                async for quadro in quadros:
                    yield quadro

        yield self._encerrar()

    async def _preparar(self, instrucoes_extras: str | None) -> None:
        """The quota, the model, the tools and the system — once per conversation."""
        # The ceiling can come from the PLAN, and it is resolved ONCE per
        # conversation: the check now and the `cota` frame of each round use the
        # SAME value. Resolving it again mid-turn would make the donut wobble if
        # the plan changed between rounds, and would cost one query per model
        # response.
        #
        # There is no database session here — this loop runs inside an SSE
        # generator, and the handler's one is already dead. `teto_de` opens its
        # own when it needs one.
        self.teto_de_tokens = await teto_do_assistente.teto_de(self.escopo.user_id, redis=self.redis)
        await cotas.verificar_tokens_do_assistente(
            self.redis, self.escopo.user_id, teto=self.teto_de_tokens
        )
        # ONCE per conversation, and not on every round: the admin can switch the
        # model in the middle of an ongoing conversation, and switching models
        # between two rounds of the SAME reasoning changes behavior midway.
        # Whoever has started finishes on the model they started on — that is
        # what the screen promises.
        self.modelo = await assistente_config_service.modelo_em_uso(redis=self.redis)

        self.ferramentas = await ferramentas_para_o_modelo(self.servidor, self.escopo, self.superficie)
        self.sistema = montar_sistema(instrucoes_extras, superficie=self.superficie)
        # Last, as before: `_ja_desenhou` reads the transcript, and whatever goes
        # wrong in it comes after the quota (the refusal the route knows how to show).
        self.estado = EstadoDoLaco(
            escopo=self.escopo,
            redis=self.redis,
            conversa_id=self.conversa_id,
            emitir=self.fila.put,
            # From the TRANSCRIPT, not from zero: the conversation is resumed between
            # turns, and a workflow drawn in the previous message is still on
            # screen. The Home never draws, so for it this is always False (and
            # nobody reads it).
            desenhou=_ja_desenhou(self.conversa),
        )

    def _erro_do_teto(self) -> Evento:
        """The `erro` for when the conversation goes past `TETO_DE_VOLTAS`."""
        logger.warning(
            "Assistente interrompido no teto de voltas (usuário %s, %d tokens).",
            self.escopo.user_id,
            self.uso_total.cobravel,
        )
        return Evento(
            "erro",
            {
                "code": "loop_limit",
                "message": (
                    f"A conversa passou de {TETO_DE_VOLTAS} rodadas de ferramenta "
                    "sem concluir."
                ),
                "hint": "descreva o fluxo em partes menores, ou diga o que ficou faltando",
                # The number separately: the Home translates the sentence and needs to cite it.
                "teto": TETO_DE_VOLTAS,
            },
        )

    async def _chamar_modelo(self) -> AsyncIterator[Evento | openrouter.Resposta]:
        """One call to the model: yields `pensando` and `texto` as they arrive and,
        last, the whole `Resposta`. A failure becomes the `erro` frame — and then
        the `Resposta` does not come."""
        resposta: openrouter.Resposta | None = None
        try:
            # The client yields the visible pieces as they arrive and, last, the
            # whole response already in the project's format. A stream that dies
            # midway is an exception — never a half response.
            async for pedaco in self.cliente.transmitir(
                modelo=self.modelo,
                sistema=self.sistema,
                conversa=self.conversa,
                ferramentas=self.ferramentas,
                max_tokens=MAX_TOKENS,
                esforco=ESFORCO_DO_RACIOCINIO,
            ):
                if isinstance(pedaco, openrouter.Resposta):
                    resposta = pedaco
                elif pedaco.tipo == "texto":
                    yield Evento("texto", {"texto": pedaco.texto})
                elif pedaco.tipo == "pensando":
                    yield Evento("pensando", {"texto": pedaco.texto})
            if resposta is None:
                raise openrouter.ErroDoOpenRouter("o stream terminou sem a resposta final")
        except Exception as exc:
            logger.exception("Falha ao falar com o modelo (usuário %s).", self.escopo.user_id)
            self.falhou = True
            yield Evento(
                "erro",
                {
                    "code": "modelo_indisponivel",
                    "message": "Não consegui falar com o modelo agora.",
                    "hint": "tente de novo em alguns instantes",
                    "detalhe": exc.__class__.__name__,
                },
            )
            return
        yield resposta

    async def _cobrar(self, resposta: openrouter.Resposta) -> Evento | None:
        """Sums the round's usage, records it and charges the quota. Returns the
        `cota` frame with the window's running total, or `None` without Redis to count."""
        uso_da_volta = Uso.de(resposta.uso)
        self.uso_total = self.uso_total + uso_da_volta
        # At the SAME point as the quota charge, and not at the end of the
        # conversation: the two then count the same thing and cannot diverge,
        # and a conversation abandoned midway (tab closed, dead stream) has
        # already recorded what it spent so far. Summing only at the end would
        # lose those — and would err LOW, the wrong side to err on for data
        # that turns into a pricing decision.
        await uso_service.registrar_volta(
            user_id=self.escopo.user_id,
            modelo=self.modelo,
            superficie=self.superficie.nome,
            entrada=uso_da_volta.entrada,
            saida=uso_da_volta.saida,
            cache_leitura=uso_da_volta.cache_leitura,
            raciocinio=uso_da_volta.raciocinio,
            custo_usd=uso_da_volta.custo,
        )
        acumulado = await cotas.cobrar_tokens_do_assistente(
            self.redis, self.escopo.user_id, uso_da_volta.cobravel
        )
        if acumulado is None:
            return None
        # The quota donut goes up DURING the turn, on each model response,
        # with no GET: the running total INCRBY returned goes to the screen now.
        # Without Redis there is no counter — and no frame.
        return Evento("cota", {"gasto": acumulado, "teto": self.teto_de_tokens})

    async def _anexar_resposta(self, resposta: openrouter.Resposta) -> None:
        """The model's response enters the conversation, and the turn closes."""
        # The blocks already come in the project's format (plain dicts): it is
        # what Redis and the database store and what goes back to the model on
        # the next round. A response with NO block at all (refusal without
        # output, `stop` without text) does not enter: an empty assistant
        # message is rejected by the provider on every resume, and there is
        # nothing in it for the person to see.
        if resposta.blocos:
            self.conversa.append({"role": "assistant", "content": list(resposta.blocos)})
            await self._fechar_turno()
        else:
            logger.warning(
                "Modelo devolveu uma resposta sem conteúdo (parada=%s, usuário %s).",
                resposta.parada,
                self.escopo.user_id,
            )

    def _erro_da_parada(self, parada: str) -> Evento | None:
        """The `erro` for the stops that end the conversation badly — the model's
        refusal and the cut by `max_tokens`. `None` for the others."""
        if parada == "content_filter":
            return Evento(
                "erro",
                {
                    "code": "recusado",
                    "message": "O modelo recusou este pedido.",
                },
            )
        if parada == "length":
            # Do NOT run tools here, even if there are `tool_use` blocks in the
            # response. The argument arrives streamed, so a cut in the middle of
            # generation delivers a HALF argument that may still look well
            # formed — a definition with half the nodes, for example. Writing
            # that would destroy someone's workflow for the sake of a truncated
            # response.
            logger.warning("Assistente cortado por max_tokens (usuário %s).", self.escopo.user_id)
            return Evento(
                "erro",
                {
                    "code": "resposta_truncada",
                    "message": "A resposta foi cortada no meio e não é segura de aplicar.",
                    "hint": "peça o fluxo em partes menores",
                },
            )
        return None

    async def _executar_chamadas(self, chamadas: list[dict[str, Any]]) -> AsyncIterator[Evento]:
        """The tools the model asked for in a round, with each one's frames;
        the results go back to the conversation, and the turn closes."""
        resultados: list[dict[str, Any]] = []
        # Two lanes. A LOCAL call (the drawing in the editor, the globe on the
        # Home) mutates `estado` and the ORDER between calls matters — the model
        # draws and executes in the SAME round, and the `run_workflow` gate reads
        # the `desenhou` the drawing has just written. With any local call in the
        # batch, the round runs as it always did: in sequence. With no local
        # call, the calls are independent (gate + server, without writing to the
        # state) and run TOGETHER — the round costs the slowest tool, not the sum.
        tem_local = any(
            self.superficie.executores_locais.get(str(c.get("name") or "")) is not None
            for c in chamadas
        )
        pista = self._em_fila if tem_local else self._em_paralelo
        async with aclosing(pista(chamadas, resultados)) as quadros:
            async for quadro in quadros:
                yield quadro

        # All results in a SINGLE message. Splitting into several silently teaches
        # the model to stop asking for tools in parallel.
        self.conversa.append({"role": "user", "content": resultados})
        await self._fechar_turno()

    def _executar(self, chamada: dict[str, Any]) -> Awaitable[tuple[str, bool]]:
        """The dispatch of ONE call (`_executar_ferramenta`), with the
        `ContextoLocal` that stamps its id on the `progresso` frames."""
        ident = chamada.get("id")
        return _executar_ferramenta(
            servidor=self.servidor,
            escopo=self.escopo,
            nome=chamada.get("name"),
            argumentos=chamada.get("input"),
            contexto=ContextoLocal(self.fila.put, ferramenta_id=ident),
            superficie=self.superficie,
            estado=self.estado,
            tool_use_id=ident,
        )

    async def _em_fila(
        self, chamadas: list[dict[str, Any]], resultados: list[dict[str, Any]]
    ) -> AsyncIterator[Evento]:
        """The sequential lane: each call is announced, runs and closes before the next one."""
        for chamada in chamadas:
            ident, nome, argumentos = chamada.get("id"), chamada.get("name"), chamada.get("input")
            yield Evento(
                "ferramenta",
                {"id": ident, "nome": nome, "argumentos": _resumo(argumentos)},
            )
            # The tool runs in a task and the loop yields what it enqueues WHILE
            # it is still running — this is what makes the `report_progress` of a
            # long run arrive live, instead of all at once at the end. The
            # sentinel (put in place when the task finishes) closes the drain; the
            # result comes from the task's `await`, which has already completed.
            tarefa = asyncio.ensure_future(self._executar(chamada))
            tarefa.add_done_callback(lambda _: self.fila.put_nowait(self._fim_da_ferramenta))
            while True:
                enfileirado = await self.fila.get()
                if enfileirado is self._fim_da_ferramenta:
                    break
                yield enfileirado
            resultado, deu_erro = await tarefa
            evento_fim, quadros, bloco = _fecho_da_chamada(
                self.superficie, self.estado, chamada, resultado, deu_erro
            )
            yield evento_fim
            for quadro in quadros:
                yield quadro
            resultados.append(bloco)

    async def _em_paralelo(
        self, chamadas: list[dict[str, Any]], resultados: list[dict[str, Any]]
    ) -> AsyncIterator[Evento]:
        """The parallel lane: the whole batch is announced, runs together (up to
        `TETO_DO_LOTE_EM_PARALELO` at a time) and closes in the order of the calls."""
        # Announces all of them BEFORE firing: the browser sees the whole batch
        # "running", and each `progresso` finds the right card by the `id` the
        # call's `ContextoLocal` stamps.
        for chamada in chamadas:
            yield Evento(
                "ferramenta",
                {
                    "id": chamada.get("id"),
                    "nome": chamada.get("name"),
                    "argumentos": _resumo(chamada.get("input")),
                },
            )
        # The concurrency ceiling protects the rest of the worker: N comes from
        # the model, and each task can open its own database session — without
        # the slot, a round with 13+ calls would exhaust the process pool and
        # block requests that are not even from this conversation.
        vaga = asyncio.Semaphore(TETO_DO_LOTE_EM_PARALELO)
        tarefas = [asyncio.ensure_future(self._executar_com_vaga(vaga, chamada)) for chamada in chamadas]
        # One sentinel PER task (distinct objects, compared by identity): the
        # drain knows WHICH one finished, and each `ferramenta_fim` goes out
        # IN THE ORDER of the calls but as soon as its task (and the previous
        # ones) are done — the end of the fast one does not wait for the slow
        # one that came after. The `tool_result`s keep matching the `tool_use`s.
        fims = [object() for _ in tarefas]
        for tarefa, marca in zip(tarefas, fims):
            tarefa.add_done_callback(lambda _t, marca=marca: self.fila.put_nowait(marca))
        # Identity (`is`), never hash: an `Evento` is a frozen dataclass with
        # a dict inside — unhashable — and an `in set` would blow up on the
        # first drained progress frame.
        vistos: list[object] = []
        for chamada, tarefa, marca in zip(chamadas, tarefas, fims):
            # Drains the queue (live progress, interleaved) until THIS task's
            # marker shows up; markers of later tasks that arrive earlier are
            # remembered. `fila.get()` is never cancelled midway (same reason as
            # the sentinel in the sequential lane).
            while not any(marca is v for v in vistos):
                enfileirado = await self.fila.get()
                if any(enfileirado is m for m in fims):
                    vistos.append(enfileirado)
                    continue
                yield enfileirado
            resultado, deu_erro = await tarefa
            evento_fim, quadros, bloco = _fecho_da_chamada(
                self.superficie, self.estado, chamada, resultado, deu_erro
            )
            yield evento_fim
            for quadro in quadros:
                yield quadro
            resultados.append(bloco)

    async def _executar_com_vaga(self, vaga: asyncio.Semaphore, chamada: dict[str, Any]) -> tuple[str, bool]:
        async with vaga:
            return await self._executar(chamada)

    def _encerrar(self) -> Evento:
        """The `fim` frame: the transcript (with pending items closed), the summed
        usage, the rounds and whether the conversation ended well."""
        logger.info(
            "Assistente: %d volta(s), %d tokens, US$ %.4f (usuário %s, superfície %s).",
            self.voltas,
            self.uso_total.cobravel,
            self.uso_total.custo,
            self.escopo.user_id,
            self.superficie.nome,
        )
        return Evento(
            "fim",
            {
                "transcrito": _fechar_pendencias(self.conversa),
                "uso": self.uso_total.como_dict(),
                "voltas": self.voltas,
                "ok": not self.falhou,
            },
        )


def _fecho_da_chamada(
    superficie: "Superficie",
    estado: EstadoDoLaco,
    chamada: dict[str, Any],
    resultado: str,
    deu_erro: bool,
) -> tuple[Evento, list[Evento], dict[str, Any]]:
    """The SINGLE epilogue of a call, shared by the loop's two lanes.

    Returns the `ferramenta_fim` event, the surface's extra frames and the
    `tool_result` block that goes back to the model. Existing only once is what
    keeps the output contract from forking between the sequential and the
    parallel lane.
    """
    ident, nome, argumentos = chamada.get("id"), chamada.get("name"), chamada.get("input")
    evento_fim = Evento("ferramenta_fim", {"id": ident, "nome": nome, "erro": deu_erro})
    quadros = list(superficie.quadros_extras(estado, nome, argumentos, resultado, deu_erro))
    bloco = {
        "type": "tool_result",
        "tool_use_id": ident,
        "content": resultado,
        "is_error": deu_erro,
    }
    return evento_fim, quadros, bloco


async def _executar_ferramenta(
    *,
    servidor,
    escopo: EscopoEfetivo,
    nome: str,
    argumentos: Any,
    contexto: ContextoLocal,
    superficie: "Superficie",
    estado: EstadoDoLaco,
    tool_use_id: str | None = None,
) -> tuple[str, bool]:
    """Dispatches a tool call, under the surface package.

    Three stages, and the surface decides the first two:
    1. LOCAL tool (drawing in the editor, globe on the Home) — does not go to the server;
    2. the surface's GATE (order+blocking in the editor; confirmation on the Home) —
       when it returns something, that is the result, and the server is not even touched;
    3. the real call, through `chamar_no_servidor`.

    A malformed argument needs no validation from us: `Tool.run` validates
    against the `input_schema` before running the function and raises
    `ToolError`. It becomes an error result, the model reads it and fixes it —
    which is what should happen.

    Stages 1 and 2 run under the SAME net that stage 3 already had in
    `chamar_no_servidor`: an exception becomes an error result, never an
    exception that propagates. Without that, a defect in the gate or in the
    local executor brought down the WHOLE conversation — and worse than the
    crash was the trail: the model's `tool_use` had already been appended to the
    transcript and the `tool_result` never arrived, so the next message hit an
    API rejection (tool call without a result). An error in a gate is
    information for the model to correct course, just like a scope refusal.
    """
    try:
        executor_local = superficie.executores_locais.get(nome)
        if executor_local is not None:
            return await executor_local(argumentos, estado)

        veredito = await superficie.portao(estado, nome, argumentos, tool_use_id)
    except ToolError as exc:
        return (str(exc), True)
    except Exception as exc:
        logger.exception(
            "Portao da superficie %s quebrou em %s (usuário %s).",
            superficie.nome, nome, escopo.user_id,
        )
        return (f"A ferramenta {nome} falhou de forma inesperada ({exc.__class__.__name__}).", True)

    if veredito is not None:
        return veredito

    if not isinstance(argumentos, dict):
        # The argument arrives streamed; when the JSON does not close, the client
        # returns the raw text instead of an object (`openrouter._argumentos`).
        return ("O argumento não chegou como objeto JSON. Refaça a chamada.", True)

    return await chamar_no_servidor(servidor, escopo, nome, argumentos, contexto)


async def chamar_no_servidor(
    servidor, escopo: EscopoEfetivo, nome: str, argumentos: dict[str, Any], contexto
) -> tuple[str, bool]:
    """Calls the tool through the MCP path and returns `(texto, deu_erro)`.

    Public because the Home reuses it on the confirmation click: when the person
    confirms, the server is called with the STORED arguments, along the same path
    and under the same scope, without going through the model loop again.

    The `set`/`reset` of the `ContextVar` is narrow on purpose — around the call
    and not the whole conversation. A scope that outlives the call is a scope
    that can be read by the NEXT task on the same worker, and the effect would be
    one user seeing another's workspace. The `finally` here is the only thing
    between that defect and production.
    """
    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        resultado = await servidor.call_tool(nome, argumentos, contexto)
    except ToolError as exc:
        # Scope, quota or role refusal, or a failure declared by the tool itself.
        # All of that is information the model uses to correct course — it goes
        # as an error result, never as an exception that brings down the
        # conversation.
        return (str(exc), True)
    except Exception as exc:
        logger.exception("Ferramenta %s quebrou no assistente (usuário %s).", nome, escopo.user_id)
        return (f"A ferramenta {nome} falhou de forma inesperada ({exc.__class__.__name__}).", True)
    finally:
        ESCOPO_ATUAL.reset(ficha)

    return (_texto_do_resultado(resultado), bool(getattr(resultado, "is_error", False)))


def _fechar_pendencias(conversa: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Answers the tool calls the loop left without an answer.

    Every abnormal exit from the loop — truncated response, model refusal, round
    ceiling, network failure — happens AFTER the model's message has already
    entered the conversation. If that message asked for a tool, the transcript is
    left with an orphan `tool_use`, and a tool call without the corresponding
    result is rejected by the provider the next time the conversation is
    resumed: the person would lose everything when sending the next message.

    Closing with an error result is better than discarding the model's message,
    for two reasons: what it has already written stays on screen, and on resume
    it reads why that call did not happen — instead of assuming it ran.
    """
    if not conversa:
        return conversa
    ultima = conversa[-1]
    if ultima.get("role") != "assistant":
        return conversa

    pendentes = [
        b
        for b in (ultima.get("content") or [])
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]
    if not pendentes:
        return conversa

    return conversa + [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": b["id"],
                    "content": "A chamada não chegou a acontecer: a conversa foi interrompida.",
                    "is_error": True,
                }
                for b in pendentes
            ],
        }
    ]


def _texto_do_resultado(resultado) -> str:
    """The SDK's `CallToolResult` turned into the text the model reads."""
    pedacos: list[str] = []
    for bloco in getattr(resultado, "content", None) or []:
        texto = getattr(bloco, "text", None)
        if texto:
            pedacos.append(texto)
    if not pedacos:
        estruturado = getattr(resultado, "structured_content", None)
        if estruturado is not None:
            pedacos.append(json.dumps(estruturado, ensure_ascii=False, default=str))
    junto = "\n".join(pedacos) if pedacos else "(sem conteúdo)"
    if len(junto) > MAX_CHARS_POR_RESULTADO:
        return junto[:MAX_CHARS_POR_RESULTADO] + AVISO_DE_CORTE
    return junto


# Validation stays in the loop — but as a MEANS, not as delivery. What puts it
# on the canvas is `desenhar_no_canvas`; this constant was kept for the verdict,
# which the panel shows next to the drawn workflow.
NOME_DA_VALIDACAO = "validate_workflow"


def _proposta_de(
    nome: str, argumentos: Any, resultado: str, deu_erro: bool
) -> dict[str, Any] | None:
    """The definition that goes to the canvas. `None` when there is none.

    It comes from TWO tools, with different roles: `desenhar_no_canvas` asks to
    draw now (`desenhar: true`), and `validate_workflow` sends the verdict on
    what is already drawn. Before, only the second existed, and so putting
    something on screen depended on the model having decided to validate.

    **A deliberate and narrow exception to `_resumo`.** Every other call goes to
    the SSE with keys and sizes, never content — the stream is someone's log at
    some point. Here the definition goes WHOLE, because without it the "Aplicar"
    (Apply) button has nothing to apply, and the write gate made that button the
    only bridge between the conversation and the workflow. Only for this tool,
    and only when it did not fail.

    The definition comes from the ARGUMENT, not from the result: it is what the
    model asked to validate, it is what the server validated, and it is exactly
    what will be applied. Reading from the result would leave room for the two
    to diverge.
    """
    if deu_erro or nome not in (NOME_DO_DESENHO, NOME_DA_VALIDACAO):
        return None
    definicao = argumentos.get("definition") if isinstance(argumentos, dict) else None
    if not isinstance(definicao, dict):
        return None

    proposta: dict[str, Any] = {
        "definicao": definicao,
        "nos": len(definicao.get("nodes") or []),
        "arestas": len(definicao.get("edges") or []),
        # The panel draws ON ITS OWN what comes from the drawing, and only shows
        # the verdict of what comes from validation. Without this mark it would
        # have no way to tell "put this on screen now" from "here is what
        # validation found".
        "desenhar": nome == NOME_DO_DESENHO,
    }
    if nome == NOME_DO_DESENHO:
        nota = argumentos.get("nota")
        if isinstance(nota, str) and nota.strip():
            proposta["nota"] = nota.strip()[:200]
        return proposta

    proposta.update(_veredito(resultado))
    return proposta


def _veredito(resultado: str) -> dict[str, Any]:
    """`ok`, `erros` and `avisos` from the report — tolerant of what does not parse.

    The format comes from `_resumo_da_validacao` (`app/mcp/tools/construcao.py`).
    If it changes some day, the panel loses the count and keeps working: `None`
    becomes "don't know", and the button stays enabled based on what the person
    sees in the explanation. An exception here would bring down the whole
    conversation because of a label.
    """
    try:
        corpo = json.loads(resultado)
    except (TypeError, ValueError):
        return {"ok": None, "erros": None, "avisos": None}
    if not isinstance(corpo, dict):
        return {"ok": None, "erros": None, "avisos": None}
    return {
        "ok": corpo.get("ok"),
        "erros": corpo.get("error_count"),
        "avisos": corpo.get("warning_count"),
    }


def _resumo(argumentos: Any) -> dict[str, Any]:
    """What the panel shows of the call — keys and sizes, never the content.

    An argument carries a workflow definition and text from the person using it.
    The panel wants to say "validating a 7-node workflow", not dump the JSON; and
    the summary also goes to the SSE, which is someone's log at some point.
    """
    if not isinstance(argumentos, dict):
        return {}
    resumo: dict[str, Any] = {}
    for chave, valor in argumentos.items():
        if isinstance(valor, (str, int, float, bool)) or valor is None:
            texto = str(valor)
            resumo[chave] = texto if len(texto) <= 120 else f"{texto[:117]}…"
        elif isinstance(valor, dict):
            resumo[chave] = {"__campos__": len(valor)}
        elif isinstance(valor, (list, tuple)):
            resumo[chave] = {"__itens__": len(valor)}
        else:
            resumo[chave] = {"__tipo__": type(valor).__name__}
    return resumo


# ── The transcript, in Redis ──────────────────────────────────────────────────
# Key per (user, workflow): reopening the editor resumes that workflow's
# conversation, which is what the person expects from a panel that lives next to
# the canvas. The create screen uses `novo`.
#
# Never in the browser — see note 2 at the top of this module. A client that
# stores the transcript can rewrite a `tool_result`, and a `tool_result` is the
# SERVER's word on what happened.

TTL_DA_CONVERSA_S = 24 * 60 * 60
FLUXO_NOVO = "novo"

# Short on purpose: it protects against two tabs on the same workflow, not
# against a worker that died. An abandoned conversation releases on its own in
# minutes, instead of leaving the workflow locked until someone notices.
TTL_DA_TRAVA_S = 300


def chave_da_conversa(user_id: str, workflow_id: str | None) -> str:
    return f"assistente:conversa:{user_id}:{workflow_id or FLUXO_NOVO}"


def chave_da_trava(user_id: str, workflow_id: str | None) -> str:
    return f"assistente:trava:{user_id}:{workflow_id or FLUXO_NOVO}"


async def carregar_conversa(redis, user_id: str, workflow_id: str | None) -> list[dict[str, Any]]:
    """That workflow's history, or empty. Never raises.

    Without Redis the conversation has no memory: each message starts from
    scratch. It is worse than normal and better than refusing — the same
    degradation policy as the quota module.
    """
    if redis is None:
        return []
    try:
        cru = await redis.get(chave_da_conversa(user_id, workflow_id))
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao ler a conversa: %s", exc.__class__.__name__)
        return []
    if not cru:
        return []
    try:
        carregado = json.loads(cru)
    except (TypeError, ValueError):
        # Corrupted value or one from an older format: starting clean is better
        # than bringing down someone's conversation forever.
        logger.warning("Conversa ilegível para %s; recomeçando.", user_id)
        return []
    return carregado if isinstance(carregado, list) else []


async def salvar_conversa(
    redis, user_id: str, workflow_id: str | None, transcrito: list[dict[str, Any]]
) -> None:
    """Stores the history. Never raises — failing here must not lose the response."""
    if redis is None or not transcrito:
        return
    try:
        await redis.set(
            chave_da_conversa(user_id, workflow_id),
            json.dumps(transcrito, ensure_ascii=False),
            ex=TTL_DA_CONVERSA_S,
        )
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao salvar a conversa: %s", exc.__class__.__name__)


async def esquecer_conversa(redis, user_id: str, workflow_id: str | None) -> None:
    """Starts over from scratch. Used by the panel's clear button."""
    if redis is None:
        return
    try:
        await redis.delete(chave_da_conversa(user_id, workflow_id))
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao esquecer a conversa: %s", exc.__class__.__name__)


# Renews at TTL/3: plenty of margin for one renewal to fail and the next one
# to still land before expiry.
_INTERVALO_DE_RENOVACAO_DA_TRAVA_S = TTL_DA_TRAVA_S / 3


async def _renovar_trava(redis, chave: str) -> None:
    """Reissues the lock's EXPIRE while the section runs.

    The lock expires in `TTL_DA_TRAVA_S` (300 s), but a turn can go beyond that —
    `TETO_DE_VOLTAS` model rounds at `high` take minutes. Without renewing, the
    lock would expire midway and a 2nd tab would get into the SAME transcript,
    saving over it. Runs until cancelled at the end of the section; since it
    lives in the worker's event loop, it dies with it — an ABANDONED lock (a
    worker that crashed) still expires on its own via the TTL, which is the point
    of the lock being short on purpose."""
    while True:
        await asyncio.sleep(_INTERVALO_DE_RENOVACAO_DA_TRAVA_S)
        try:
            await redis.expire(chave, TTL_DA_TRAVA_S)
        except Exception as exc:  # pragma: no cover - depends on Redis
            logger.warning("Falha ao renovar a trava: %s", exc.__class__.__name__)
            return


@asynccontextmanager
async def trava_exclusiva(redis, chave: str) -> AsyncIterator[None]:
    """One section at a time, per key — and always released. `SET NX` is the
    cheapest lock that does the job.

    Generic on purpose: the editor locks per (user, workflow) and the Home
    assistant per (user, conversation), but the mechanics are the same — two
    tabs on the same conversation would write to the same transcript and
    scramble it, the second one saving over the first.

    Without Redis there is no lock — the same degradation as everything else.
    The possible damage is a scrambled transcript, not a leak.
    """
    if redis is None:
        yield
        return
    try:
        peguei = await redis.set(chave, "1", nx=True, ex=TTL_DA_TRAVA_S)
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao travar a conversa: %s", exc.__class__.__name__)
        yield
        return
    if not peguei:
        raise erro(
            "conversa_em_andamento",
            "Já há uma conversa em andamento para este fluxo.",
            "espere a resposta terminar, ou recarregue a aba que ficou aberta",
        )
    # Keeps the lock alive while the turn runs — without renewing, it would
    # expire in the middle of a long conversation and a 2nd tab would get into
    # the same transcript.
    renovador = asyncio.create_task(_renovar_trava(redis, chave))
    try:
        yield
    finally:
        renovador.cancel()
        with suppress(asyncio.CancelledError):
            await renovador
        try:
            await redis.delete(chave)
        except Exception as exc:  # pragma: no cover - depends on Redis
            logger.warning("Falha ao soltar a trava: %s", exc.__class__.__name__)


def conversa_exclusiva(redis, user_id: str, workflow_id: str | None):
    """The editor's lock, with today's key. Thin alias of `trava_exclusiva`."""
    return trava_exclusiva(redis, chave_da_trava(user_id, workflow_id))


__all__ = [
    "ContextoLocal",
    "EDITOR",
    "ESCREVEM_MAS_PASSAM",
    "ESFORCO_DO_RACIOCINIO",
    "EXIGEM_DESENHO_ANTES",
    "EstadoDoLaco",
    "FERRAMENTA_DO_DESENHO",
    "NOME_DO_DESENHO",
    "MENSAGEM_DE_EXECUTAR_ANTES",
    "Evento",
    "INSTRUCOES_DO_EDITOR",
    "MENSAGEM_DO_PORTAO",
    "Superficie",
    "Uso",
    "bloqueada_no_editor",
    "carregar_conversa",
    "chamar_no_servidor",
    "conversa_exclusiva",
    "conversar",
    "criar_cliente",
    "escopo_do_editor_para",
    "ferramentas_para_o_modelo",
    "esquecer_conversa",
    "montar_sistema",
    "salvar_conversa",
    "trava_exclusiva",
    "TETO_DE_VOLTAS",
]
