# app/services/assistente_superficie.py
"""
The assistant's Home surface — the same assistant loop, a different package.

The loop, the quota, the scope that travels in the `ContextVar`, the resumable
transcript: all of it comes from `assistente_service`. This module only builds the
Home `Superficie` and imports `assistente_service` (NEVER the other way around —
the editor does not know about the Home).

What the Home does differently from the editor:

- **The delivery is a LAYER on the globe, not a drawing on the canvas.** The
  assistant creates and runs its OWN workflows (marked `origem="assistente"` by
  identity, hidden from listings) WITHOUT a click — that is how the answer reaches
  the globe — and puts a run output on the globe with `exibir_no_globo`.
- **Full reach, with CONFIRMATION BY CLICK on what already existed.** The
  `Superficie` allows every MCP tool (`permitida = n in GUARDAS`); what holds back
  what it can destroy is the confirmation gate, checked on the server — never a
  text promise. Deleting a schedule, deleting a Drive file, running or editing a
  workflow THE PERSON created: all of that emits a `confirmacao` frame and WAITS
  for the click. Running and editing the assistant's own workflows asks for no click.

The confirmation, in detail: the gate intercepts the confirmable call, stores
`{token, tool, args}` in Redis for 15 min under
`agente:confirmacao:{user}:{conversa}:{tool_use_id}`, emits the `confirmacao` frame
and returns to the model a NON-error "aguardando" (waiting) `tool_result` — an error
would make the model repeat the call and duplicate the button. The click (in the API
PR) validates ownership and token, consumes the key exactly once and executes the
STORED args through `chamar_no_servidor`, under the user's scope. The arguments that
run are the SERVER's, never whatever the client sends with the click.
"""
from __future__ import annotations

import json
import secrets
import unicodedata
from typing import Any

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.mcp import infra
from app.mcp.guardas import GUARDAS
from app.mcp.resolucao import carregar_workflow
from app.services.assistente_service import (
    EstadoDoLaco,
    Evento,
    Superficie,
    _resumo,
)

logger = get_logger("app.agente.superficie")


# ── The delivery: `exibir_no_globo` ──────────────────────────────────────────
# The counterpart of the editor's `desenhar_no_canvas`. It does NOT exist in MCP:
# it is not in `GUARDAS`, an external client never sees it. The globe belongs to
# the Home, and only makes sense to whoever is looking at it. It is a POINTER: it
# emits a `camada` frame with the `artifact_id`, and the globe fetches the geometry
# and metadata via `GET /assistente/camadas/{id}` (member gate).
NOME_DO_GLOBO = "exibir_no_globo"

FERRAMENTA_DO_GLOBO: dict[str, Any] = {
    "name": NOME_DO_GLOBO,
    "description": (
        "Põe uma saída de execução (um artefato GeoJSON, ou uma camada publicada) "
        "no globo da Home, AGORA. É a sua entrega: enquanto você não chamar isto, a "
        "pessoa não vê camada nenhuma no globo.\n\n"
        "Passe o `artifact_id` de um artefato que já existe (de uma execução que "
        "você rodou, ou que a pessoa mencionou). O globo busca a geometria pelo id; "
        "você não precisa mandar o conteúdo. Não grava nada."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "artifact_id": {
                "type": "string",
                "description": "O id do artefato de execução a exibir no globo.",
            },
            "nome": {
                "type": "string",
                "description": "Um rótulo curto para a camada, para a pessoa reconhecer.",
            },
        },
        "required": ["artifact_id"],
    },
}


async def _exibir_no_globo(argumentos: Any, estado: EstadoDoLaco) -> tuple[str, bool]:
    """Validates the arguments and returns the text the model reads. Does not go to the server.

    Does NOT emit the `camada` frame here: what builds it is `_quadros_da_home`,
    from the `argumentos`. An `emitir` from here would go out on the SSE and
    vanish in the replay (which only re-runs `quadros_extras`), and the layer
    would disappear from the globe when the chat is reopened. A single path
    serves both.
    """
    aid = _artefato_pedido(argumentos)
    if aid is None:
        return ("`artifact_id` precisa ser o id de um artefato de execução.", True)
    return (
        f"Camada {aid} enviada ao globo. A pessoa está vendo agora — o globo busca a "
        "geometria e os metadados pelo id.",
        False,
    )


def _artefato_pedido(argumentos: Any) -> str | None:
    aid = argumentos.get("artifact_id") if isinstance(argumentos, dict) else None
    if not isinstance(aid, str) or not aid.strip():
        return None
    return aid.strip()


def _quadro_do_globo(argumentos: Any) -> list[Evento]:
    """The `camada` frame of a successful `exibir_no_globo`.

    `available=True` on purpose: the frame is a POINTER and the truth is
    `GET /assistente/camadas/{id}`. Omitting the field made the front end
    normalize it as `False` and draw the warning card ("sem prévia no globo",
    no preview on the globe) while the layer was showing on the globe.
    """
    aid = _artefato_pedido(argumentos)
    if aid is None:
        return []
    dados: dict[str, Any] = {"artifact_id": aid, "available": True}
    nome = argumentos.get("nome") if isinstance(argumentos, dict) else None
    if isinstance(nome, str) and nome.strip():
        dados["nome"] = nome.strip()[:120]
    return [Evento("camada", dados)]


# ── Quick replies: `sugerir_respostas` ───────────────────────────────────────
# The Home's second LOCAL tool, modeled on `exibir_no_globo`: it does not go to
# the server, is not in `GUARDAS`, and the frame (`respostas_rapidas`) is born
# from the ARGUMENTS in `_quadros_da_home` — never from an `emitir` here —, so
# the replay rebuilds it along the same path. What it does is offer the person
# up to three short continuations (chips under the answer) that become their
# next message with one click. Whether they still apply is decided by the web
# app: only on the last turn.
NOME_DAS_RESPOSTAS = "sugerir_respostas"
TETO_DE_RESPOSTAS = 3
TAMANHO_DA_RESPOSTA = 80

FERRAMENTA_DAS_RESPOSTAS: dict[str, Any] = {
    "name": NOME_DAS_RESPOSTAS,
    "description": (
        "Oferece à pessoa até três RESPOSTAS RÁPIDAS: continuações curtas que ela "
        "escolhe com um clique e que viram a próxima mensagem dela (refinar o "
        "período, cruzar com outra camada, ver por município, agendar). Chame UMA "
        "vez por resposta, DEPOIS do texto final, e só quando houver continuação "
        "natural. Cada opção é o que a pessoa diria, em até 60 caracteres. Não "
        "repita as opções no texto. Perguntas essenciais para continuar você faz "
        "no texto, não aqui."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "opcoes": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": TETO_DE_RESPOSTAS,
                "description": "As frases, como a pessoa as diria. De uma a três.",
            },
        },
        "required": ["opcoes"],
    },
}


def _opcoes_pedidas(argumentos: Any) -> list[str] | None:
    """The valid options, cleaned and capped — or `None` if none is left.

    Strings only; whitespace normalized; empty ones out; duplicates out (the
    first one stays); each cut at `TAMANHO_DA_RESPOSTA`; only the first
    `TETO_DE_RESPOSTAS`. Tolerates `argumentos` that is not a dict (input cut
    off in the stream).
    """
    cru = argumentos.get("opcoes") if isinstance(argumentos, dict) else None
    if not isinstance(cru, list):
        return None
    opcoes: list[str] = []
    for item in cru:
        if not isinstance(item, str):
            continue
        frase = " ".join(item.split())[:TAMANHO_DA_RESPOSTA].strip()
        if frase and frase not in opcoes:
            opcoes.append(frase)
        if len(opcoes) == TETO_DE_RESPOSTAS:
            break
    return opcoes or None


async def _sugerir_respostas(argumentos: Any, estado: EstadoDoLaco) -> tuple[str, bool]:
    """Validates the options and returns the text the model reads. Does not go to the server.

    Does NOT emit the frame here — what builds it is `_quadros_da_home`, from
    the arguments (the same reason as `_exibir_no_globo`: an `emitir` would
    vanish in the replay). The returned text tells the model to END the turn:
    that is what keeps the model from repeating the options in prose after
    putting them on screen.
    """
    opcoes = _opcoes_pedidas(argumentos)
    if opcoes is None:
        return ("`opcoes` precisa ser uma lista de 1 a 3 frases curtas.", True)
    return (
        f"Respostas rápidas na tela ({len(opcoes)}). Encerre o turno: a pessoa "
        "escolhe uma ou digita outra coisa.",
        False,
    )


def _quadro_das_respostas(argumentos: Any) -> list[Evento]:
    """O quadro `respostas_rapidas` de um `sugerir_respostas` bem-sucedido."""
    opcoes = _opcoes_pedidas(argumentos)
    if opcoes is None:
        return []
    return [Evento("respostas_rapidas", {"opcoes": opcoes})]


# ── What requires a click ────────────────────────────────────────────────────
# Two lists, and the difference is deliberate:
#
# - ALWAYS: touches what already existed, with no ambiguous target —
#   delete/create/change a schedule, delete a Drive file, restore a version,
#   turn a workflow on/off, publish to the portal, re-execute. Every action here
#   destroys or exposes data of another person in the workspace, or incurs cost
#   — and "clean up the old schedules" is a sentence someone types without thinking.
# - IF THE WORKFLOW BELONGS TO THE PERSON: editing or running a workflow. The
#   assistant edits and runs its OWN workflows (origem="assistente") without a
#   click — that is what makes the answer reach the globe. Only when the target
#   is a workflow the PERSON created does the click come in: then it is touching
#   what already existed.
#
# The DEFAULT IS INVERTED on purpose: `CONFIRMAVEIS_SEMPRE` is DERIVED from
# `GUARDAS` — every tool that is not `read_only` confirms, except the two in the
# allowlist below. While the list was hand-written, a new write tool was born
# FREE (that is what happened with `cancel_run`, `pin_node_output`,
# `unpin_node_output`, `duplicate_workflow` and the Drive upload pair: the
# assistant cancelled another member's run with no card at all). Now it is born
# confirmable, and freeing it requires an explicit name here.
CONFIRMAVEIS_SE_FLUXO_DA_PESSOA: frozenset[str] = frozenset({"update_workflow", "run_workflow"})

# The allowlist: the ONLY writes the assistant makes without a click. Two are the
# path for it to build its OWN workflows — `validate_workflow` writes nothing
# (it simulates), and `create_workflow` is born `origem="assistente"`, hidden from
# the person's listings. Neither of the two touches what already existed. The
# third, `register_source`, is the owner's decision: saving to the catalog a
# source that the probe confirmed is cheap, reversible and executes nothing — and
# asking for a click on every new source would bring back the cost the catalog
# came to remove. `probe_source` comes in for the same reason: probing is free
# (metadata only; it updates the state of an already cataloged source).
ESCRITAS_SEM_CLIQUE: frozenset[str] = frozenset({"validate_workflow", "create_workflow", "probe_source", "register_source"})

CONFIRMAVEIS_SEMPRE: frozenset[str] = frozenset(
    nome
    for nome, guarda in GUARDAS.items()
    if not guarda.read_only
    and nome not in ESCRITAS_SEM_CLIQUE
    and nome not in CONFIRMAVEIS_SE_FLUXO_DA_PESSOA
)


# ── The confirmation gate ────────────────────────────────────────────────────
# The Redis key is (user, conversation, tool_use_id): the click matches the exact
# call by `tool_use_id`, and the (user, conversation) pair keeps one
# conversation's token from being valid in another. 15 min is slack for the
# person to read and decide, and short enough for a forgotten decision to vanish
# on its own.
TTL_DA_CONFIRMACAO_S = 15 * 60

MENSAGEM_AGUARDANDO = (
    "Aguardando a confirmação da pessoa pelo botão. Diga em uma linha o que está "
    "pendente e ENCERRE o turno — não repita esta chamada nem peça confirmação por texto."
)

MENSAGEM_SEM_CONFIRMACAO = (
    "Não foi possível abrir a confirmação desta ação agora. Explique à pessoa que a "
    "ação não pôde ser preparada e siga sem executá-la."
)

MENSAGEM_FORA_DO_ALCANCE = (
    "Esta ferramenta não está disponível no assistente da Home."
)


def chave_de_confirmacao(user_id: str, conversa_id: str | None, tool_use_id: str) -> str:
    return f"agente:confirmacao:{user_id}:{conversa_id or 'novo'}:{tool_use_id}"


async def _fluxo_e_da_pessoa(estado: EstadoDoLaco, argumentos: Any) -> bool:
    """True when the target is NOT one of the assistant's own workflows — so it asks for a click.

    Fails CLOSED: with no clear target, or when the workflow does not load
    (nonexistent id, database error), it treats it as "the person's" and
    confirms. Running someone's workflow without a click because of a transient
    error would be the worst side to err on. Only a positive
    `origem == "assistente"` waives the confirmation.

    The READ of `origem` lives INSIDE the `async with`, and that is not style.
    `infra.sessao()` calls `rollback()` in the `finally`, and a rollback EXPIRES
    every object in the session — even in a session that only read. Outside the
    block, any attribute triggers a refresh on an already detached instance and
    raises `DetachedInstanceError`. Worse: `getattr(wf, "origem", <default>)`
    does NOT protect, because the default only covers `AttributeError`. The
    effect in production was the assistant being unable to run ANY of its own
    workflows — which is the Home's entire path (create the workflow, run it,
    send the layer to the globe).
    """
    ref = argumentos.get("workflow_id") if isinstance(argumentos, dict) else None
    if not ref:
        return True
    try:
        async with infra.sessao() as db:
            wf, _papel = await carregar_workflow(db, estado.escopo, str(ref))
            origem = getattr(wf, "origem", "usuario")
    except Exception:
        logger.exception("Nao foi possivel ler a origem do fluxo %s; exigindo clique.", ref)
        return True
    return origem != "assistente"


async def _confirmavel(estado: EstadoDoLaco, nome: str, argumentos: Any) -> bool:
    if nome in CONFIRMAVEIS_SEMPRE:
        return True
    if nome in CONFIRMAVEIS_SE_FLUXO_DA_PESSOA:
        return await _fluxo_e_da_pessoa(estado, argumentos)
    return False


def _alvo(argumentos: Any) -> str | None:
    """An identifier of the target, for the confirmation card to show what it touches."""
    if not isinstance(argumentos, dict):
        return None
    for chave in ("workflow_id", "job_id", "schedule_id", "file_id", "run_id", "version_number", "source_id", "url", "id"):
        valor = argumentos.get(chave)
        if valor not in (None, ""):
            return str(valor)[:120]
    return None


async def _pedir_confirmacao(
    estado: EstadoDoLaco, nome: str, argumentos: Any, tool_use_id: str | None
) -> tuple[str, bool]:
    """Stores `{token, tool, args}` in Redis, emits the `confirmacao` frame and returns
    to the model a NON-error "aguardando" (waiting) `tool_result`.

    Non-error on purpose: an `is_error=True` would make the model try again and
    duplicate the button. What holds the model back is the instruction
    (`INSTRUCOES_DA_HOME`), which tells it to end the turn on seeing "aguardando".

    The `tool_use_id` arrives as an ARGUMENT, and not from a "current call" field
    in the state: the tools of a round run in parallel, and a shared field would
    match the confirmation click with the wrong call.
    """
    if estado.redis is None or not tool_use_id:
        # Without Redis there is no way to store the token to validate the click
        # later; without `tool_use_id` there is no way to match the click with the
        # call. A closed refusal, and not a confirmation that can never be honored.
        return (MENSAGEM_SEM_CONFIRMACAO, True)

    token = secrets.token_urlsafe(24)
    payload = json.dumps(
        {
            "token": token,
            "tool": nome,
            # The STORED args: this is what the click executes, never whatever the
            # client sends in the confirmation POST.
            "args": argumentos if isinstance(argumentos, dict) else {},
            "criado_em": utc_now_naive().isoformat(),
        },
        ensure_ascii=False,
    )
    chave = chave_de_confirmacao(estado.escopo.user_id, estado.conversa_id, tool_use_id)
    try:
        await estado.redis.set(chave, payload, ex=TTL_DA_CONFIRMACAO_S)
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao guardar a confirmação: %s", exc.__class__.__name__)
        return (MENSAGEM_SEM_CONFIRMACAO, True)

    await estado.emitir(
        Evento(
            "confirmacao",
            {
                "tool_use_id": tool_use_id,
                "token": token,
                "acao": {"tool": nome, "argumentos": _resumo(argumentos), "alvo": _alvo(argumentos)},
            },
        )
    )
    return (MENSAGEM_AGUARDANDO, False)


async def _portao_da_home(
    estado: EstadoDoLaco, nome: str, argumentos: Any, tool_use_id: str | None = None
) -> tuple[str, bool] | None:
    """The Home's gate: confirmation by click for whatever touches what already existed.

    `None` when the tool may go straight to the server (the assistant creates
    and runs its own workflows without a click).
    """
    if nome not in GUARDAS:
        # `permitida` already filters the list the model sees; refusing here too keeps
        # the response uniform and is the same `list_tools`/`call_tool` separation as MCP.
        return (MENSAGEM_FORA_DO_ALCANCE, True)
    if not await _confirmavel(estado, nome, argumentos):
        return None
    return await _pedir_confirmacao(estado, nome, argumentos, tool_use_id)


# ── The frames the Home emits after a tool ───────────────────────────────────


def _json_ou_none(resultado: str) -> Any:
    try:
        return json.loads(resultado)
    except (TypeError, ValueError):
        return None


def _quadro_fluxo(corpo: dict) -> list[Evento]:
    """`create_workflow` bem-sucedido → um quadro `fluxo` (o badge junto do chat)."""
    wid = corpo.get("id")
    if not wid:
        return []
    nome = (corpo.get("untrusted_data") or {}).get("name")
    return [Evento("fluxo", {"workflow_id": wid, "nome": nome})]


def _quadros_camada(corpo: dict) -> list[Evento]:
    """The GeoJSON artifacts of a run → one `camada` frame each.

    It is what makes "the answer reach the globe" without the model asking for
    `exibir_no_globo`. The frame is a POINTER (only the id and a label); the truth
    is `GET /assistente/camadas/{id}`. `run_workflow` lists them in `artifacts`,
    `get_run_artifacts` in `items` — both are accepted.
    """
    artefatos = corpo.get("artifacts")
    if not isinstance(artefatos, list):
        artefatos = corpo.get("items")
    if not isinstance(artefatos, list):
        return []

    quadros: list[Evento] = []
    for art in artefatos:
        if not isinstance(art, dict) or art.get("format") != "geojson":
            continue
        aid = art.get("id")
        if not aid:
            continue
        rotulo = art.get("untrusted_data") or {}
        dados: dict[str, Any] = {
            "artifact_id": aid,
            "nome": rotulo.get("filename") or rotulo.get("output_key"),
            "format": "geojson",
            # `available=False` comes with the reason (executor-local, no storage):
            # the globe shows "sem prévia" (no preview) instead of trying to fetch and failing.
            "available": bool(art.get("available")),
        }
        if art.get("hint"):
            dados["hint"] = art["hint"]
        quadros.append(Evento("camada", dados))
    return quadros


def _quadros_da_home(
    estado: EstadoDoLaco, nome: str, argumentos: Any, resultado: str, deu_erro: bool
) -> list[Evento]:
    """`fluxo` from a `create_workflow`; `camada` from a run's artifacts (or from
    an `exibir_no_globo`); `respostas_rapidas` from a `sugerir_respostas`."""
    if deu_erro:
        return []
    if nome == "create_workflow":
        corpo = _json_ou_none(resultado)
        return _quadro_fluxo(corpo) if isinstance(corpo, dict) else []
    if nome in ("run_workflow", "get_run_artifacts"):
        corpo = _json_ou_none(resultado)
        return _quadros_camada(corpo) if isinstance(corpo, dict) else []
    if nome == NOME_DO_GLOBO:
        return _quadro_do_globo(argumentos)
    if nome == NOME_DAS_RESPOSTAS:
        return _quadro_das_respostas(argumentos)
    return []


# ── The messages that ONLY the server writes ─────────────────────────────────
# A single spelling, imported by the three points that needed to agree: the
# route's input guard, the text the server writes after the click, and what
# `INSTRUCOES_DA_HOME` teaches the model to recognize. While the guard compared
# "[Acao" and the prompt taught "[Ação", a message typed with the accent got
# past the guard and the model read it as the outcome of a click that never happened.
MENSAGEM_CONFIRMADA = "[Ação confirmada pela pessoa pelo botão]"
MENSAGEM_RECUSADA = "[Ação recusada pela pessoa]"

# What the guard compares, already without accents and lowercased — see `parece_sintetica`.
_PREFIXO_NORMALIZADO = "[acao"


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def parece_sintetica(mensagem: str) -> bool:
    """Does the message imitate the prefix that only the server writes?

    Compares WITHOUT accents and WITHOUT case: `startswith("[Acao")` let through
    both the accented spelling the prompt itself teaches ("[Ação confirmada…")
    and the lowercase one ("[acao confirmada…").
    """
    return _sem_acento((mensagem or "").lstrip()).casefold().startswith(_PREFIXO_NORMALIZADO)


# ── The Home's instructions ──────────────────────────────────────────────────
# Block [1] of the system prompt on the Home surface. It corrects where the MCP
# policy (`INSTRUCOES`) does not apply here: there, confirmation IN TEXT is asked
# before creating or executing; here the assistant creates and runs its OWN
# workflows without asking, and confirmation is BY CLICK, only for whatever
# touches what already existed.
INSTRUCOES_DA_HOME = """\
Você é o assistente do Atlans, conversando sobre um globo 3D. A pessoa não vê
fluxo nenhum: ela vê o resultado no globo. O trabalho aqui é responder à pergunta
espacial dela PONDO UMA CAMADA NO GLOBO, não explicando como faria.

SUA ENTREGA É UMA CAMADA NO GLOBO
O caminho normal, e ele é seu, sem pedir permissão:
1. Entenda o pedido. Pergunte só se faltar algo essencial.
2. Dado externo (WFS)? `search_sources` pelo tema e `describe_source` ANTES de
   qualquer outra coisa — nunca invente url/typeName. Só sem resultado:
   `probe_source` (sonda) e `register_source` (guarda para a próxima vez).
3. `search_nodes` / `describe_node` para os nós que você não domina — e peça as
   fichas de TODOS os nós do fluxo numa chamada só (`name` aceita lista, até 8
   por chamada; mais que isso, divida em dois lotes), em vez de uma rodada por nó.
4. `validate_workflow` para conferir a definição.
5. `create_workflow` — um fluxo SEU (nasce escondido das listas). Dê um nome que
   comece com "assistente: ".
6. `run_workflow` com `wait=true`. Prefira saídas GeoJSON — é o que vai ao globo.
7. A camada aparece sozinha quando a execução termina. Se precisar reexibir um
   artefato que já existe, use `exibir_no_globo` com o `artifact_id`.

Você NÃO pede permissão para criar e rodar os SEUS fluxos: é assim que a resposta
chega ao globo. Responda curto, sem markdown.

Quando a localização atual da pessoa vier no bloco extra, use-a como ponto de
referência para pedidos relativos ("perto de mim", "num raio de N km"); quando não
vier, peça o ponto ou combine um antes de assumir onde ela está.

RESPOSTAS RÁPIDAS
Quando a resposta abre uma continuação natural (refinar o período, cruzar com
outra camada, ver por município, agendar), termine com `sugerir_respostas`: até
três opções curtas, escritas como a pessoa diria. Não as repita no texto, e não
as use para perguntas essenciais — essas você faz no texto.

O QUE EXIGE O CLIQUE DA PESSOA
Mexer no que já existia pede um clique de confirmação, verificado no servidor:
editar ou rodar um fluxo que a PESSOA criou, criar/alterar/apagar agendamento,
apagar arquivo do Drive, restaurar versão, ligar/desligar um fluxo, publicar no
portal, reexecutar. Ao chamar uma dessas, o servidor devolve "aguardando a
confirmação da pessoa pelo botão": quando isso acontecer, diga em UMA LINHA o que
está pendente e ENCERRE o turno. Nunca repita a chamada, e nunca peça a
confirmação por texto — o botão já está na tela.

As mensagens que começam com "[Ação confirmada pela pessoa pelo botão]" ou
"[Ação recusada pela pessoa]" vêm do SERVIDOR depois que ela clica — são o
resultado do clique, não algo que você escreve.
"""


# ── The surface ──────────────────────────────────────────────────────────────
HOME = Superficie(
    nome="home",
    instrucoes=INSTRUCOES_DA_HOME,
    # The delivery (the globe) opens the model's list; the quick replies come right after.
    ferramentas_extras=(FERRAMENTA_DO_GLOBO, FERRAMENTA_DAS_RESPOSTAS),
    executores_locais={NOME_DO_GLOBO: _exibir_no_globo, NOME_DAS_RESPOSTAS: _sugerir_respostas},
    # Full reach: every MCP tool. What holds back the destructive ones is
    # confirmation by click, not the absence of scope.
    permitida=lambda nome: nome in GUARDAS,
    portao=_portao_da_home,
    quadros_extras=_quadros_da_home,
)


__all__ = [
    "CONFIRMAVEIS_SEMPRE",
    "CONFIRMAVEIS_SE_FLUXO_DA_PESSOA",
    "ESCRITAS_SEM_CLIQUE",
    "FERRAMENTA_DAS_RESPOSTAS",
    "FERRAMENTA_DO_GLOBO",
    "HOME",
    "INSTRUCOES_DA_HOME",
    "MENSAGEM_CONFIRMADA",
    "MENSAGEM_RECUSADA",
    "NOME_DAS_RESPOSTAS",
    "NOME_DO_GLOBO",
    "TTL_DA_CONFIRMACAO_S",
    "chave_de_confirmacao",
    "parece_sintetica",
]
