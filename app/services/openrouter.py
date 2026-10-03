# app/services/openrouter.py
"""
The OpenRouter client — the ONLY module that knows the model's wire format.

The assistant (`assistente_service.conversar`) talks to the model through a single boundary:
`ClienteOpenRouter.transmitir(...)`. It receives the transcript in the project's
format and returns, as a stream, the text and reasoning chunks (`Delta`) and,
last, the whole response (`Resposta`) — also in the project's format.
Nothing outside this module knows what a `chat.completion.chunk`, a `tool_calls` or a
`reasoning_details` is. Switching providers again means rewriting THIS module, and
nothing else: the loop, the quota, the write gate, the replay and the click
confirmation do not change.

**Why OpenRouter's native API (chat completions) and not a compatibility
layer.** OpenRouter is a router: the same request serves a model
from Anthropic, OpenAI, Google or an open one, and the operator switches models by
editing `ASSISTENTE_MODELO`. The native API is the one it documents, measures and
maintains for all of them; a compatibility layer with another vendor's format is
a subset that ages on the outside. The price is this module:
~400 lines that translate the transcript and reassemble the stream.

**The transcript format belongs to the PROJECT, not the provider.** It is what
Redis (editor) and Postgres (Home) store, what the replay reads and what the
click confirmation matches by `tool_use_id`:

    {"role": "user", "content": "o que a pessoa escreveu"}
    {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "...", "reasoning_details": [...]},
        {"type": "text", "text": "..."},
        {"type": "tool_use", "id": "call_…", "name": "search_nodes", "input": {...}},
    ]}
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "call_…", "content": "...", "is_error": false},
    ]}

On the way out, `montar_mensagens` translates that into `system`/`user`/`assistant`
(`tool_calls`)/`tool`; on the way back, the accumulator reassembles the SSE `chunks` into
the three blocks above. `reasoning_details` travels VERBATIM in both directions: it is
what OpenRouter asks for so the model can continue its reasoning from one tool
round to the next (and, on Anthropic models, it is mandatory in the
last assistant message when that message requests a tool). An old `thinking`
block — from the time when the transcript came from another API and carried a
`signature` — has no `reasoning_details` and is simply omitted on the way out: what
was already thought in past turns is not needed, and resending it in a
format the provider does not recognize would bring down the whole conversation.

**What the client guarantees the loop:**

- `Delta("texto")`/`Delta("pensando")` come out in the order they arrive, and the
  `Resposta` is always the last item — or an `ErroDoOpenRouter` exception, never
  a half response. A stream that dies midway is an exception, not a truncated
  success: the loop does not store what did not arrive whole.
- `Resposta.parada` is the `finish_reason` normalized by OpenRouter: `stop`,
  `tool_calls`, `length` (cut off by `max_tokens`) or `content_filter`
  (refusal). `error` becomes an exception.
- Network failures, 429 and 5xx BEFORE the body starts are retried
  (`TENTATIVAS`); a 400 with `reasoning_details` in the request is retried ONCE
  without them — if the provider refuses the stored reasoning, the conversation loses the
  old reasoning, not the conversation.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.core.utils.logger import get_logger

logger = get_logger("app.assistente.openrouter")

URL_PADRAO = "https://openrouter.ai/api/v1"
CAMINHO = "/chat/completions"

# Attempts to OPEN the conversation (up to the response headers). Once the
# body has started arriving there is no retry: what already went out on the SSE cannot be
# unsaid, and the loop treats the drop as `modelo_indisponivel`.
TENTATIVAS = 3
RETENTAVEIS = frozenset({408, 429, 500, 502, 503, 504})
MAX_WAIT_S = 10.0

# Streaming with a large `max_tokens` takes minutes; what matters is the silence BETWEEN
# two chunks (`read`), and OpenRouter sends `: OPENROUTER PROCESSING` comments
# while the provider has not started answering yet.
TIMEOUT = httpx.Timeout(connect=30.0, read=180.0, write=60.0, pool=30.0)

# What the model reads in a tool result that failed. The wire format
# has no `is_error` flag; without the prefix, a scope refusal and a
# normal result would arrive looking the same.
PREFIXO_DE_ERRO = "[erro] "


@dataclass(frozen=True)
class Delta:
    """A stream chunk: `texto` (what the model writes) or `pensando` (the reasoning)."""

    tipo: str
    texto: str


@dataclass(frozen=True)
class Resposta:
    """The whole response, reassembled, in the project's format."""

    blocos: list[dict[str, Any]]
    parada: str
    uso: dict[str, Any] = field(default_factory=dict)
    modelo: str | None = None
    provedor: str | None = None


class ErroDoOpenRouter(Exception):
    """Failure talking to OpenRouter. The message is for the LOG; the loop shows the
    person only the class — the provider's text may carry a URL and headers."""

    def __init__(self, mensagem: str, *, status: int | None = None, codigo: Any = None) -> None:
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo


# ── Outbound: from transcript to request ─────────────────────────────────────


def e_openrouter(base_url: str | None) -> bool:
    """Is the base URL OpenRouter's?

    `usage`, `reasoning` and `cache_control` are ITS parameters. An API that only
    follows OpenAI's may refuse an unknown field (OpenAI itself
    refuses), and does not send `usage` in the stream without `stream_options`: the token
    quota would count nothing. For those, the request carries only the standard format.
    """
    host = (urlsplit(base_url or URL_PADRAO).hostname or "").lower()
    return host == "openrouter.ai" or host.endswith(".openrouter.ai")


def ferramenta(nome: str, descricao: str | None, parametros: dict[str, Any] | None) -> dict[str, Any]:
    """A tool in the wire format (`function`), built from the MCP's `input_schema`."""
    return {
        "type": "function",
        "function": {
            "name": nome,
            "description": descricao or "",
            "parameters": parametros or {"type": "object", "properties": {}},
        },
    }


def montar_pedido(
    *,
    modelo: str,
    sistema: list[dict[str, Any]],
    conversa: list[dict[str, Any]],
    ferramentas: list[dict[str, Any]],
    max_tokens: int,
    esforco: str | None,
    openrouter: bool = True,
) -> dict[str, Any]:
    """The body of POST /chat/completions. Pure: it is what the tests check.

    `openrouter=False` (see `e_openrouter`) drops OpenRouter's own parameters
    and asks for `usage` the way the OpenAI API does.
    """
    corpo: dict[str, Any] = {
        "model": modelo,
        "messages": montar_mensagens(sistema, conversa, cache=openrouter),
        "max_tokens": max_tokens,
        "stream": True,
    }
    if openrouter:
        # `usage.include` puts the count (and the cost in credits) in the last
        # frame of the stream. It is the quota's source.
        corpo["usage"] = {"include": True}
    else:
        # The same last frame with `usage`, in the OpenAI API format
        # (and vLLM's, LiteLLM's, Ollama's). Without it, the quota counts nothing.
        corpo["stream_options"] = {"include_usage": True}
    if ferramentas:
        corpo["tools"] = list(ferramentas)
    if esforco and openrouter:
        # The model's reasoning, in OpenRouter's unified parameter: it
        # translates it into what each family accepts (adaptive thinking, effort,
        # budget). A model without reasoning ignores it.
        corpo["reasoning"] = {"effort": esforco}
    return corpo


def montar_mensagens(
    sistema: list[dict[str, Any]], conversa: list[dict[str, Any]], *, cache: bool = True,
) -> list[dict[str, Any]]:
    """The project's transcript turned into `messages`.

    `cache=False` (outside OpenRouter) marks no breakpoint at all, and the
    `system` goes as plain text, which every compatible API accepts.

    The `system` goes as a list of text parts so the cache breakpoints
    (`cache_control`) survive — that is how OpenRouter passes the
    prompt cache on to the providers that have it; the others ignore the field.

    The second breakpoint goes on the LAST human message (the person's text,
    or Home's synthetic confirmation). It closes a prefix that is the same
    across ALL tool rounds of this turn: system, tools, the
    history and the question. What is left out is only the current turn's calls and
    results.
    """
    mensagens: list[dict[str, Any]] = []
    if sistema and cache:
        mensagens.append({"role": "system", "content": [_text_part(b) for b in sistema]})
    elif sistema:
        mensagens.append({
            "role": "system",
            "content": "\n\n".join(str(b.get("text") or "") for b in sistema),
        })

    last_human = _last_human_message_index(conversa) if cache else None
    for indice, mensagem in enumerate(conversa):
        papel = mensagem.get("role")
        conteudo = mensagem.get("content")
        if papel == "assistant":
            traduzida = _from_assistant(conteudo)
            if traduzida is not None:
                mensagens.append(traduzida)
        elif papel == "user":
            mensagens.extend(_from_human(conteudo, mark_cache=(indice == last_human)))
        else:
            logger.warning("Mensagem de papel desconhecido no transcrito (%r); ignorada.", papel)
    return mensagens


def _text_part(bloco: dict[str, Any]) -> dict[str, Any]:
    parte: dict[str, Any] = {"type": "text", "text": str(bloco.get("text") or "")}
    if bloco.get("cache_control"):
        # Only the type: the TTL is the decision of the provider behind the router, and a field
        # it does not know is a risk of refusal on every conversation.
        parte["cache_control"] = {"type": "ephemeral"}
    return parte


def _is_human(mensagem: dict[str, Any]) -> bool:
    """Human text (or the server's synthetic one) — not a list of `tool_result`s."""
    if mensagem.get("role") != "user":
        return False
    conteudo = mensagem.get("content")
    if isinstance(conteudo, str):
        return True
    return isinstance(conteudo, list) and any(
        isinstance(b, dict) and b.get("type") == "text" for b in conteudo
    )


def _last_human_message_index(conversa: list[dict[str, Any]]) -> int | None:
    for indice in range(len(conversa) - 1, -1, -1):
        if _is_human(conversa[indice]):
            return indice
    return None


def _from_human(conteudo: Any, *, mark_cache: bool) -> list[dict[str, Any]]:
    """A `user` message from the transcript: the person's text, or tool results."""
    if isinstance(conteudo, str):
        return [_human_message(conteudo, mark_cache)]
    if not isinstance(conteudo, list):
        return [_human_message(str(conteudo or ""), mark_cache)]

    saida: list[dict[str, Any]] = []
    textos: list[str] = []
    for bloco in conteudo:
        if not isinstance(bloco, dict):
            continue
        if bloco.get("type") == "tool_result":
            saida.append(
                {
                    "role": "tool",
                    "tool_call_id": str(bloco.get("tool_use_id") or ""),
                    "content": _result_text(bloco),
                }
            )
        elif bloco.get("type") == "text" and bloco.get("text"):
            textos.append(str(bloco["text"]))
    if textos:
        saida.append(_human_message("\n".join(textos), mark_cache))
    return saida


def _human_message(texto: str, mark_cache: bool) -> dict[str, Any]:
    if not mark_cache:
        return {"role": "user", "content": texto}
    return {
        "role": "user",
        "content": [{"type": "text", "text": texto, "cache_control": {"type": "ephemeral"}}],
    }


def _result_text(bloco: dict[str, Any]) -> str:
    conteudo = bloco.get("content")
    if isinstance(conteudo, list):
        texto = "\n".join(
            str(b.get("text")) for b in conteudo if isinstance(b, dict) and b.get("text")
        )
    elif conteudo is None:
        texto = ""
    else:
        texto = str(conteudo)
    if bloco.get("is_error"):
        return PREFIXO_DE_ERRO + texto
    return texto


def _from_assistant(conteudo: Any) -> dict[str, Any] | None:
    """A model message: text + `tool_calls` + `reasoning_details` verbatim.

    `None` when it has neither text nor a call — only reasoning, or nothing (a
    `length` cutoff while still thinking; a refusal with no output). Sending it as
    `content: ""` is a certain refusal from the provider, and one the 400 plan B does not
    fix: the conversation would be stuck forever. What was already thought in
    past turns is not needed, and the omission changes nothing for the model.
    """
    if isinstance(conteudo, str):
        return {"role": "assistant", "content": conteudo} if conteudo.strip() else None

    textos: list[str] = []
    chamadas: list[dict[str, Any]] = []
    detalhes: list[dict[str, Any]] = []
    for bloco in conteudo if isinstance(conteudo, list) else []:
        if not isinstance(bloco, dict):
            continue
        tipo = bloco.get("type")
        if tipo == "text" and bloco.get("text"):
            textos.append(str(bloco["text"]))
        elif tipo == "tool_use":
            chamadas.append(
                {
                    "id": str(bloco.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(bloco.get("name") or ""),
                        "arguments": _arguments_as_text(bloco.get("input")),
                    },
                }
            )
        elif tipo == "thinking":
            # Only what came from OpenRouter. An old block (with `signature` and without
            # `reasoning_details`) stays in the transcript for the replay and is not sent.
            guardados = bloco.get("reasoning_details")
            if isinstance(guardados, list):
                detalhes.extend(d for d in guardados if isinstance(d, dict))

    texto = "".join(textos)
    if not texto.strip() and not chamadas:
        return None
    mensagem: dict[str, Any] = {"role": "assistant", "content": texto if texto else None}
    if chamadas:
        mensagem["tool_calls"] = chamadas
    if detalhes:
        mensagem["reasoning_details"] = detalhes
    return mensagem


def _arguments_as_text(argumentos: Any) -> str:
    """The `input` of a `tool_use` as the JSON string of `function.arguments`.

    Only an OBJECT goes as is. The raw text of a call cut off by
    `max_tokens` (what `_arguments` returns when the JSON does not close) stays in the
    transcript for the replay, but on the way out becomes `{}`: resent as it came, it would be
    invalid JSON on every following round, and the provider would refuse the whole
    conversation. The paired error `tool_result` already told the model that that
    call did not happen.
    """
    if isinstance(argumentos, dict):
        return json.dumps(argumentos, ensure_ascii=False, default=str)
    return "{}"


def _has_reasoning(corpo: dict[str, Any]) -> bool:
    return any(
        m.get("role") == "assistant" and m.get("reasoning_details")
        for m in corpo.get("messages") or []
    )


def _without_reasoning(corpo: dict[str, Any]) -> dict[str, Any]:
    """The same request without the `reasoning_details` — the 400 plan B."""
    mensagens = [
        {k: v for k, v in m.items() if k != "reasoning_details"} for m in corpo.get("messages") or []
    ]
    return {**corpo, "messages": mensagens}


# ── Inbound: from SSE to response ────────────────────────────────────────────


async def _lines(resposta: httpx.Response) -> AsyncIterator[str]:
    """The body's lines, split ONLY on `\\n`, `\\r\\n` and `\\r` — the three
    terminators the SSE specification defines.

    httpx's `aiter_lines()` does not work: it splits like `str.splitlines()`, which
    includes U+2028, U+2029 and U+0085 — characters that are valid UNESCAPED inside
    a JSON string. A model that emitted them (echoing a workflow name,
    a text coming from the web) would have the frame cut in the middle, and the whole turn
    would die with `quadro ilegível` (unreadable frame). Splitting on bytes is safe: in UTF-8
    the bytes 0x0A and 0x0D never appear inside a multibyte character.
    """
    resto = b""
    async for pedaco in resposta.aiter_bytes():
        resto += pedaco
        while resto:
            i_n = resto.find(b"\n")
            i_r = resto.find(b"\r")
            if i_n < 0 and i_r < 0:
                break
            fim = min(i for i in (i_n, i_r) if i >= 0)
            if resto[fim : fim + 1] == b"\r":
                if fim + 1 >= len(resto):
                    # It may be a `\r\n` split across two chunks: wait for the next one.
                    break
                salto = 2 if resto[fim + 1 : fim + 2] == b"\n" else 1
            else:
                salto = 1
            yield resto[:fim].decode("utf-8", "replace")
            resto = resto[fim + salto :]
    if resto:
        if resto.endswith(b"\r"):
            resto = resto[:-1]
        yield resto.decode("utf-8", "replace")


async def _sse_events(resposta: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """The stream's `data:` frames, already decoded. Stops at `[DONE]`.

    Lines starting with `:` are comments — OpenRouter sends
    `: OPENROUTER PROCESSING` as a sign of life while it waits for the provider.
    An event may have several `data:` lines (joined with `\\n`, as the
    specification says) and ends at a blank line.
    """
    dados: list[str] = []
    async for linha in _lines(resposta):
        if linha == "":
            if dados:
                carga = "\n".join(dados)
                dados = []
                if carga.strip() == "[DONE]":
                    return
                yield _decodificar(carga)
            continue
        if linha.startswith(":"):
            continue
        campo, _, valor = linha.partition(":")
        if valor.startswith(" "):
            valor = valor[1:]
        if campo == "data":
            dados.append(valor)
    if dados:
        carga = "\n".join(dados)
        if carga.strip() != "[DONE]":
            yield _decodificar(carga)


def _decodificar(carga: str) -> dict[str, Any]:
    try:
        evento = json.loads(carga)
    except ValueError as exc:
        raise ErroDoOpenRouter("quadro ilegível no stream do OpenRouter") from exc
    if not isinstance(evento, dict):
        raise ErroDoOpenRouter("quadro inesperado no stream do OpenRouter")
    return evento


def _text_of(valor: Any) -> str:
    """`content`/`reasoning` of a delta: a string, or a list of text parts."""
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        return "".join(
            str(p.get("text")) for p in valor if isinstance(p, dict) and isinstance(p.get("text"), str)
        )
    return ""


def _int(valor: Any) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _project_usage(cru: Any) -> dict[str, Any]:
    """OpenRouter's `usage` in the project's keys.

    `prompt_tokens` already INCLUDES what came from the cache — `cached_tokens` is a
    subset of it, informational. That is why the quota sums only input + output (see `Uso` in
    the loop). `cost` comes in credits (dollars) when `usage.include` is on.
    """
    cru = cru if isinstance(cru, dict) else {}
    entrada = cru.get("prompt_tokens_details") or {}
    saida = cru.get("completion_tokens_details") or {}
    try:
        custo = float(cru.get("cost") or 0.0)
    except (TypeError, ValueError):
        custo = 0.0
    return {
        "entrada": _int(cru.get("prompt_tokens")),
        "saida": _int(cru.get("completion_tokens")),
        "cache_leitura": _int(entrada.get("cached_tokens")),
        "cache_escrita": _int(entrada.get("cache_write_tokens") or entrada.get("cache_creation_tokens")),
        "raciocinio": _int(saida.get("reasoning_tokens")),
        "custo": custo,
    }


_avisou_sem_uso = False


def _warn_no_usage() -> None:
    """Once per process: the response arrived without `usage`.

    Without the count, the assistant's daily quota does not charge the turn — the ceiling
    silently stops applying. It happens with a server that ignores
    `stream_options.include_usage` (old versions of some local
    servers). Once is enough: repeating it every turn would drown the log.
    """
    global _avisou_sem_uso
    if _avisou_sem_uso:
        return
    _avisou_sem_uso = True
    logger.warning(
        "O provedor do modelo não informou o uso (usage) da resposta: a cota de "
        "tokens do assistente não conta estes turnos. Confira se o servidor aceita "
        "stream_options.include_usage."
    )


class _Accumulator:
    """Reassembles the `chunks` of ONE response. Each call to `absorb` returns the
    visible deltas of that frame; `resposta()` settles the account.

    Tool calls arrive by `index`: the `id` and the `name` in the first
    chunk, the `arguments` drop by drop. `reasoning_details` arrives the same way
    — one item per chunk, with the `index` of the block it belongs to and the partial
    text; the `signature` (when the model has one) comes in the last one. Joining by
    index rebuilds what the provider generated, and that is what goes back on the next
    round.
    """

    def __init__(self) -> None:
        self.texto: list[str] = []
        self.raciocinio: list[str] = []
        self.chamadas: dict[int, dict[str, Any]] = {}
        self.detalhes: dict[tuple[str, Any], dict[str, Any]] = {}
        self.parada: str | None = None
        self.uso: Any = None
        self.modelo: str | None = None
        self.provedor: str | None = None

    def absorb(self, evento: dict[str, Any]) -> list[Delta]:
        erro = evento.get("error")
        if erro:
            mensagem = erro.get("message") if isinstance(erro, dict) else str(erro)
            codigo = erro.get("code") if isinstance(erro, dict) else None
            raise ErroDoOpenRouter(
                f"o provedor devolveu erro no meio do stream: {str(mensagem)[:300]}", codigo=codigo
            )
        if evento.get("usage"):
            self.uso = evento["usage"]
        self.modelo = evento.get("model") or self.modelo
        self.provedor = evento.get("provider") or self.provedor

        deltas: list[Delta] = []
        for escolha in evento.get("choices") or []:
            if not isinstance(escolha, dict):
                continue
            delta = escolha.get("delta") or escolha.get("message") or {}
            conteudo = _text_of(delta.get("content"))
            if conteudo:
                self.texto.append(conteudo)
                deltas.append(Delta("texto", conteudo))
            thinking = _text_of(delta.get("reasoning"))
            if thinking:
                self.raciocinio.append(thinking)
                deltas.append(Delta("pensando", thinking))
            for item in delta.get("reasoning_details") or []:
                self._absorb_detail(item)
            for chamada in delta.get("tool_calls") or []:
                self._absorb_call(chamada)
            parada = escolha.get("finish_reason")
            if parada:
                self.parada = str(parada)
        return deltas

    def _absorb_call(self, chamada: Any) -> None:
        if not isinstance(chamada, dict):
            return
        indice = chamada.get("index")
        if not isinstance(indice, int):
            # No index: a new `id` opens another call; without an `id`, it is the last one.
            if chamada.get("id") or not self.chamadas:
                indice = len(self.chamadas)
            else:
                indice = max(self.chamadas)
        atual = self.chamadas.setdefault(indice, {"id": None, "name": None, "argumentos": []})
        if chamada.get("id") and not atual["id"]:
            atual["id"] = str(chamada["id"])
        funcao = chamada.get("function") or {}
        if funcao.get("name") and not atual["name"]:
            atual["name"] = str(funcao["name"])
        argumentos = funcao.get("arguments")
        if isinstance(argumentos, str):
            atual["argumentos"].append(argumentos)
        elif isinstance(argumentos, (dict, list)):
            atual["argumentos"].append(json.dumps(argumentos, ensure_ascii=False))

    def _absorb_detail(self, item: Any) -> None:
        if not isinstance(item, dict):
            return
        tipo = str(item.get("type") or "reasoning.text")
        indice = item.get("index")
        if isinstance(indice, int):
            chave: tuple[str, Any] = (tipo, indice)
        elif item.get("id"):
            # No index but with an `id` (the encrypted reasoning of some
            # providers): distinct items, never merged into one.
            chave = (tipo, f"id:{item['id']}")
        else:
            # No index and no `id`: chunks of the same block.
            chave = (tipo, None)
        atual = self.detalhes.get(chave)
        if atual is None:
            atual = {k: v for k, v in item.items() if k not in ("text", "summary", "data")}
            atual["type"] = tipo
            self.detalhes[chave] = atual
        for campo in ("text", "summary", "data"):
            pedaco = item.get(campo)
            if isinstance(pedaco, str):
                atual[campo] = (atual.get(campo) or "") + pedaco
        for campo in ("signature", "id", "format"):
            if item.get(campo):
                atual[campo] = item[campo]

    def resposta(self) -> Resposta:
        detalhes = list(self.detalhes.values())
        raciocinio = "".join(self.raciocinio) or "".join(
            str(d.get("text") or d.get("summary") or "") for d in detalhes
        )
        blocos: list[dict[str, Any]] = []
        if raciocinio or detalhes:
            bloco: dict[str, Any] = {"type": "thinking", "thinking": raciocinio}
            if detalhes:
                bloco["reasoning_details"] = detalhes
            blocos.append(bloco)
        texto = "".join(self.texto)
        if texto:
            blocos.append({"type": "text", "text": texto})
        for indice in sorted(self.chamadas):
            chamada = self.chamadas[indice]
            blocos.append(
                {
                    "type": "tool_use",
                    "id": chamada["id"] or f"call_{uuid4().hex[:16]}",
                    "name": chamada["name"] or "",
                    "input": _arguments(chamada["argumentos"]),
                }
            )

        # OpenRouter always sends a `finish_reason` before `[DONE]`. Without
        # it, what arrived is not a response: it is a gateway 200 with HTML,
        # or a stream that closed before the last frame. Inferring "stop" here
        # would store an empty assistant message and emit an ok `fim` —
        # exactly the half response this module promises not to give.
        if self.parada is None:
            raise ErroDoOpenRouter("o stream terminou sem finish_reason")
        parada = self.parada
        if parada == "error":
            raise ErroDoOpenRouter("o provedor encerrou o stream com erro")
        if not self.uso:
            _warn_no_usage()
        return Resposta(
            blocos=blocos,
            parada=parada,
            uso=_project_usage(self.uso),
            modelo=self.modelo,
            provedor=self.provedor,
        )


def _arguments(pedacos: list[str]) -> Any:
    """The call's argument: an object when the JSON closes; otherwise, the raw text.

    The raw text is NOT an object, and the loop treats it as a call error — the
    model reads "redo it" instead of the tool receiving half a definition.
    """
    texto = "".join(pedacos).strip()
    if not texto:
        return {}
    try:
        return json.loads(texto)
    except ValueError:
        return texto


# ── O cliente ────────────────────────────────────────────────────────────────


def _wait_time(tentativa: int, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), MAX_WAIT_S)
        except ValueError:
            pass
    return min(0.5 * (2 ** (tentativa - 1)), MAX_WAIT_S)


async def _read_error(resposta: httpx.Response) -> tuple[Any, str]:
    """`(code, message)` from OpenRouter's error envelope, or the raw body, shortened."""
    try:
        bruto = await resposta.aread()
    finally:
        await resposta.aclose()
    try:
        corpo = json.loads(bruto)
    except ValueError:
        return None, bruto[:300].decode("utf-8", "replace")
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    if isinstance(erro, dict):
        return erro.get("code"), str(erro.get("message") or "")[:300]
    return None, str(corpo)[:300]


# The process's connection pool, created on the first conversation and reused
# by all of them. Opening an `AsyncClient` per call cost a TCP+TLS handshake
# with openrouter.ai on every tool round — six to twelve per conversation.
# The API runs a single event loop per worker, so one pool per process is
# safe; the tests inject their own `http` and never get here.
_http_compartilhado: httpx.AsyncClient | None = None


def _default_http() -> httpx.AsyncClient:
    global _http_compartilhado
    if _http_compartilhado is None or _http_compartilhado.is_closed:
        _http_compartilhado = httpx.AsyncClient(timeout=TIMEOUT)
    return _http_compartilhado


MODELS_PATH = "/models"

# The catalog is large and changes slowly. This limit exists so the request does not hang
# on an admin screen: it is not a conversation path, and failing fast
# there is better than a three-minute spinner.
CATALOG_TIMEOUT = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)


async def listar_modelos(
    *, base_url: str = URL_PADRAO, chave: str | None = None, http: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """The provider's catalog, with prices already in dollars per MILLION tokens.

    **Why a module and not a client method:** this is not a conversation.
    It has no reasoning effort nor stream, and the caller is an admin screen —
    tying it to the per-conversation client would mean inventing a conversation to
    list prices. The `chave` is optional: OpenRouter's catalog is public.

    The API returns the price **per token**, as a string (`"0.000003"`). Whoever reads a
    cost table thinks in millions, and converting at the edge is what keeps each
    caller from multiplying by a million in their own way — and one of them forgetting.
    A missing or unreadable price becomes `None`, never zero: a "free" model in the
    cost table is worse than a model with no price.
    """
    base = (base_url or URL_PADRAO).rstrip("/")
    if base.endswith(CAMINHO):
        base = base[: -len(CAMINHO)]
    cliente = http if http is not None else _default_http()
    # Other compatible servers (a gateway, a vLLM with a key) require on the
    # catalog the same key as the conversation. With no price in the response (a local
    # server), the cost columns stay `None`.
    cabecalhos = {"Accept": "application/json"}
    if chave:
        cabecalhos["Authorization"] = f"Bearer {chave}"
    resposta = await cliente.get(
        base + MODELS_PATH,
        headers=cabecalhos,
        timeout=CATALOG_TIMEOUT,
    )
    if resposta.status_code >= 400:
        raise ErroDoOpenRouter(
            f"o provedor respondeu {resposta.status_code} ao listar modelos",
            status=resposta.status_code,
        )
    corpo = resposta.json()
    linhas = corpo.get("data") if isinstance(corpo, dict) else None
    if not isinstance(linhas, list):
        raise ErroDoOpenRouter("a lista de modelos do provedor veio num formato inesperado")

    catalogo: list[dict[str, Any]] = []
    for linha in linhas:
        if not isinstance(linha, dict) or not linha.get("id"):
            continue
        prices = linha.get("pricing") if isinstance(linha.get("pricing"), dict) else {}
        catalogo.append({
            "id": str(linha["id"]),
            "nome": str(linha.get("name") or linha["id"]),
            "entrada_por_milhao": _per_million(prices.get("prompt")),
            "saida_por_milhao": _per_million(prices.get("completion")),
            "contexto": linha.get("context_length"),
        })
    return catalogo


def _per_million(valor: Any) -> float | None:
    """Price per token → per million. `None` when there is no way to know."""
    if valor is None or valor == "":
        return None
    try:
        return round(float(valor) * 1_000_000, 6)
    except (TypeError, ValueError):
        return None


class ClienteOpenRouter:
    """One client per conversation, on top of the process's shared pool. With
    an injected `http` (tests), uses what it was given and does not touch the pool."""

    def __init__(
        self,
        chave: str,
        *,
        base_url: str = URL_PADRAO,
        http: httpx.AsyncClient | None = None,
        referer: str | None = None,
        titulo: str | None = None,
        tentativas: int = TENTATIVAS,
        dormir: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        if not chave:
            raise ValueError("LLM_API_KEY vazia: o assistente não pode falar com o modelo.")
        self._key = chave
        # `base_url` is the BASE (`.../api/v1`); the path is ours. But whoever
        # configures the endpoint's full URL must not be punished with
        # `/chat/completions/chat/completions` on every request.
        base = (base_url or URL_PADRAO).rstrip("/")
        self._url = base if base.endswith(CAMINHO) else base + CAMINHO
        self._openrouter = e_openrouter(base)
        self._http = http
        self._referer = referer
        self._title = titulo
        self._attempts = max(1, int(tentativas))
        self._sleep = dormir

    def _headers(self) -> dict[str, str]:
        cabecalhos = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        # App attribution in the OpenRouter dashboard: only when the installation
        # wants it (ASSISTENTE_ATRIBUICAO), and the caller passes the title and referer.
        if self._title:
            cabecalhos["X-Title"] = self._title
        if self._referer:
            cabecalhos["HTTP-Referer"] = self._referer
        return cabecalhos

    async def transmitir(
        self,
        *,
        modelo: str,
        sistema: list[dict[str, Any]],
        conversa: list[dict[str, Any]],
        ferramentas: list[dict[str, Any]],
        max_tokens: int,
        esforco: str | None = "high",
    ) -> AsyncIterator[Delta | Resposta]:
        """One call to the model, streamed. Yields `Delta`s and, last, the `Resposta`."""
        corpo = montar_pedido(
            modelo=modelo,
            sistema=sistema,
            conversa=conversa,
            ferramentas=ferramentas,
            max_tokens=max_tokens,
            esforco=esforco,
            openrouter=self._openrouter,
        )
        http = self._http if self._http is not None else _default_http()
        async for pedaco in self._stream_with(http, corpo):
            yield pedaco

    async def _stream_with(
        self, http: httpx.AsyncClient, corpo: dict[str, Any]
    ) -> AsyncIterator[Delta | Resposta]:
        resposta = await self._open(http, corpo)
        try:
            accumulator = _Accumulator()
            async for evento in _sse_events(resposta):
                for delta in accumulator.absorb(evento):
                    yield delta
            yield accumulator.resposta()
        finally:
            await resposta.aclose()

    async def _open(self, http: httpx.AsyncClient, corpo: dict[str, Any]) -> httpx.Response:
        """The POST, up to the headers. Retries network/429/5xx; a 400 with stored
        reasoning is redone once without it. Returns the response with the body still
        unread (stream)."""
        tentativa = 0
        reasoning_already_stripped = False
        while True:
            tentativa += 1
            pedido = http.build_request("POST", self._url, json=corpo, headers=self._headers())
            try:
                resposta = await http.send(pedido, stream=True)
            except httpx.TransportError as exc:
                if tentativa < self._attempts:
                    await self._sleep(_wait_time(tentativa))
                    continue
                raise ErroDoOpenRouter(
                    f"falha de rede ao falar com o OpenRouter ({exc.__class__.__name__})"
                ) from exc

            status = resposta.status_code
            if status < 400:
                return resposta

            codigo, mensagem = await _read_error(resposta)
            if status in RETENTAVEIS and tentativa < self._attempts:
                await self._sleep(_wait_time(tentativa, resposta.headers.get("retry-after")))
                continue
            if status == 400 and not reasoning_already_stripped and _has_reasoning(corpo):
                logger.warning(
                    "OpenRouter recusou o pedido (400: %s); refazendo sem o raciocínio guardado.",
                    mensagem,
                )
                corpo = _without_reasoning(corpo)
                reasoning_already_stripped = True
                continue
            raise ErroDoOpenRouter(
                f"OpenRouter respondeu {status}: {mensagem}", status=status, codigo=codigo
            )


# The probe's tool. One is enough: the question is "does this model accept tools
# in any way?", and the answer does not change with how many or which. It is declared
# here, and not built from the MCP server, because the probe runs on an admin screen —
# there is no conversation scope nor workspace to build the real catalog.
_PROBE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "ping",
        "description": "Responde que está tudo bem. Não faz nada.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


async def sondar_modelo(
    modelo: str,
    *,
    chave: str,
    max_tokens: int,
    esforco: str | None,
    base_url: str = URL_PADRAO,
    http: httpx.AsyncClient | None = None,
    referer: str | None = None,
    titulo: str | None = None,
) -> None:
    """Can this model run the assistant? Raises `ErroDoOpenRouter` if not.

    **It exists because "it is in the catalog" does not mean "it works".** The provider's
    catalog carries a few hundred models, and among them are variants that the
    conversation endpoint refuses outright (the `:batch` ones, which respond
    "cannot be used with the chat/completions endpoint"), models without tool
    support — and the assistant sends all 42 on every call — and models whose
    output ceiling is lower than our `max_tokens`. Saving one of them brought down the
    assistant for ALL users, with a generic message, while whoever
    switched saw nothing.

    **The only reliable test of "it works" is calling it.** Filtering by catalog
    fields would require guessing which fields exist and keeping that guess
    up to date; a real call answers correctly about every case at once,
    including the ones nobody foresaw — like the batch variant, which was not
    on any list of suspects.

    The request has the SHAPE of the real conversation — the same tools,
    the same `max_tokens`, the same reasoning effort — because it is the shape that
    the provider refuses. Only the content is minimal: a short message, and reading
    stops at the first chunk. The cost is a few tokens, and `max_tokens` is a
    CEILING, not a target: asking for 64 k does not spend 64 k.
    """
    cliente = ClienteOpenRouter(chave, base_url=base_url, http=http, referer=referer, titulo=titulo,
                                # No retries: the probe is a question, not
                                # a job. A 429 here is an answer — this
                                # model is not available to us right now.
                                tentativas=1)
    fluxo = cliente.transmitir(
        modelo=modelo,
        sistema=[{"type": "text", "text": "Responda apenas: ok."}],
        conversa=[{"role": "user", "content": "ok"}],
        ferramentas=[_PROBE_TOOL],
        max_tokens=max_tokens,
        esforco=esforco,
    )
    try:
        # The first chunk is enough: if the provider were going to refuse, it would have refused
        # on OPENING the stream. Reading to the end would only waste tokens.
        async for _ in fluxo:
            break
    except ErroDoOpenRouter as exc:
        # `status` only exists when the refusal came from HTTP — it is what answers
        # "does this model work?". Without `status`, the provider ACCEPTED the request and the
        # stream ended in a way this function has no business judging
        # (no frame, missing `finish_reason`): the probe's question is about
        # the configuration, not the response. Blocking here would lock the switch
        # over a transmission detail that the real conversation handles on its own.
        if exc.status is None:
            logger.info(
                "Assistente: sonda de %s aceita — o provedor respondeu, e o stream "
                "terminou sem quadro útil (%s).", modelo, exc,
            )
            return
        raise
    finally:
        await fluxo.aclose()


__all__ = [
    "CAMINHO",
    "ClienteOpenRouter",
    "Delta",
    "ErroDoOpenRouter",
    "PREFIXO_DE_ERRO",
    "RETENTAVEIS",
    "Resposta",
    "TENTATIVAS",
    "sondar_modelo",
    "URL_PADRAO",
    "ferramenta",
    "montar_mensagens",
    "montar_pedido",
]
