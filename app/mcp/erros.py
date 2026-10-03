# app/mcp/erros.py
"""
MCP errors: a single format, readable by people and parseable by integrators.

The MCP protocol has no status code — what reaches the client is the text of the
`ToolError`. If each tool wrote its own sentence, an integrator would have no way
to tell "missing scope" from "workflow does not exist" without reading
Portuguese. That is why the message is always a compact JSON
`{code, message, hint?, ...extras}`: `code` is the stable contract, `message`
is for the human, `hint` says the next step and the extras carry what the tool
knows (the lint report, the missing scope, the seconds until it frees up).

`to_tool_error` is the single translation of the core's exceptions into this
format. It exists because the SDK's `ToolManager` wraps any exception that is
not a `ToolError` in a generic `UnexpectedToolError` — the mapping has to
happen INSIDE the tool, before the SDK sees the exception.

Security rule: no secrets in the message. Only `str(exc)` of domain exceptions
(written by us) and `exc.detail` of `HTTPException` go in — and everything goes
through `scrub_text` inside `erro()`, which is the single funnel through which
every MCP error leaves. Redaction at the funnel covers both destinations at
once: the client and the SDK log, which prints the `ToolError` text through a
logger that does not have the house secret filter. It also matters because the
message echoes arguments written by people (node name, topic, workflow name) —
the same path through which a connection string would get in by accident.
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from mcp.server.mcpserver.exceptions import ToolError

from app.core.exceptions import (
    AtlasBaseError,
    ConteudoNoExecutorError,
    CredentialAccessDeniedError,
    DefinicaoInvalidaError,
    DisabledNodesInWorkflowError,
    InvalidDateFormatError,
    NoExecutorAvailableError,
    RunNotFoundError,
    WorkflowInactiveError,
    WorkflowInputValidationError,
    WorkflowNameConflictError,
    WorkflowNotFoundError,
    WorkspaceAccessDeniedError,
)
from app.core.utils.logger import scrub_text
from app.mcp.saida import higienizar

# HTTP status → MCP `code`. It is the table that translates any `AtlasBaseError`
# and any `HTTPException` without needing a branch per exception.
CODIGO_POR_STATUS: dict[int, str] = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation",
    429: "rate_limited",
    503: "unavailable",
}

# The workflow name appears in single quotes in the conflict message
# ("Já existe um workflow chamado 'X' neste workspace.") — that is where the
# suggestion comes from. With no match, the error goes without `suggestion`,
# never with an invented one.
_NOME_ENTRE_ASPAS = re.compile(r"'([^']{1,120})'")


def erro(code: str, message: str, hint: str | None = None, **extras: Any) -> ToolError:
    """Builds the `ToolError` in the standard format. Null keys are left out of the JSON.

    `message`, `hint` and every extra that is text go through `scrub_text`. It
    is the only point through which an MCP error leaves, and redacting here
    covers the client and the log — the SDK records the `ToolError` text
    through a logger that does not carry the house secret filter.

    What is NOT a string (the lint report, the candidate list, the number of
    seconds) goes through intact, because descending into those structures here
    would destroy the format the client reads. In exchange, redacting them is
    the CALLER's responsibility, with `higienizar` from `app.mcp.saida`: the
    premise that every structure already came clean from its origin failed —
    the lint report built by `validate_service` comes out raw, and the fatal
    message of `invalid_credential_id` echoes the received value, which in this
    error is precisely a credential pasted into the wrong field. `to_tool_error`
    sanitizes before embedding; every tool that passes a structured extra must
    do the same.
    """
    corpo: dict[str, Any] = {"code": code, "message": scrub_text(message)}
    if hint:
        corpo["hint"] = scrub_text(hint)
    for chave, valor in extras.items():
        if valor is None:
            continue
        corpo[chave] = scrub_text(valor) if isinstance(valor, str) else valor
    return ToolError(json.dumps(corpo, ensure_ascii=False))


# The SDK's tool manager re-raises any `ToolError` from inside a tool prefixed
# with "Error executing tool <nome>: ". The prefix is noise for whoever reads
# the error: the contract published in docs/mcp.md says the message IS the
# JSON `{code, message, hint}`, and errors raised in the guards (scope, quota)
# arrive with no prefix at all. `sem_prefixo_do_sdk` brings both forms to the
# same format.
_PREFIXO_DO_SDK = re.compile(r"^Error executing tool [^:]+: ")


def sem_prefixo_do_sdk(mensagem: str) -> str:
    return _PREFIXO_DO_SDK.sub("", mensagem, count=1)


def codigo_do_erro(exc: BaseException) -> str:
    """The `code` of one of our `ToolError`s — "erro" when the message is not JSON.

    Serves auditing and tests; never changes the error that reaches the client.
    """
    try:
        corpo = json.loads(sem_prefixo_do_sdk(str(exc)))
    except (ValueError, TypeError):
        return "erro"
    codigo = corpo.get("code") if isinstance(corpo, dict) else None
    return codigo if isinstance(codigo, str) else "erro"


def to_tool_error(exc: BaseException) -> ToolError:
    """Translates a core exception into the MCP error.

    An already formatted `ToolError` passes through intact: whoever raised it
    knew more about the case than this generic table.
    """
    if isinstance(exc, ToolError):
        return exc

    if isinstance(exc, WorkflowInactiveError):
        return erro(
            "workflow_inactive",
            str(exc) or "Este workflow está inativo.",
            "ative com set_workflow_active(active=true) antes de executar",
        )

    if isinstance(exc, NoExecutorAvailableError):
        # This exception's `error_code` is "no_agent_available" (the executor's old
        # name). MCP exposes the current vocabulary, not the database's history.
        return erro(
            "no_executor",
            str(exc) or "Nenhum executor disponível.",
            "nenhum executor online; tente depois",
        )

    if isinstance(exc, DefinicaoInvalidaError):
        # The report goes sanitized because it is NOT born clean: the lint items
        # echo the received value so whoever reads finds the wrong field — and
        # `invalid_credential_id` quotes the `credential_id` itself, which only
        # reaches this error when someone pasted a connection string there instead
        # of the credential id. Without this pass, the same secret went out as
        # `<REDACTED>` in `message` (which goes through `scrub_text` at the funnel)
        # and in the clear inside `report.errors[].message` — to the client and
        # to the SDK log.
        return erro(
            "validation",
            str(exc) or "Definição inválida.",
            "corrija os itens de report.errors e valide de novo",
            report=higienizar(exc.report) or None,
        )

    if isinstance(exc, (WorkflowInputValidationError, DisabledNodesInWorkflowError, InvalidDateFormatError)):
        return erro("validation", str(exc) or "Entrada inválida.")

    if isinstance(exc, CredentialAccessDeniedError):
        return erro(
            "forbidden",
            str(exc) or "Credencial fora do seu alcance.",
            "use uma credencial sua ou compartilhada com o workspace",
        )

    if isinstance(exc, WorkspaceAccessDeniedError):
        return erro("forbidden", str(exc) or "Acesso negado a este workspace.")

    if isinstance(exc, (WorkflowNotFoundError, RunNotFoundError)):
        return erro("not_found", str(exc) or "Recurso não encontrado.")

    if isinstance(exc, WorkflowNameConflictError):
        mensagem = str(exc) or "Já existe um workflow com este nome."
        achado = _NOME_ENTRE_ASPAS.search(mensagem)
        return erro(
            "conflict",
            mensagem,
            "escolha outro nome",
            suggestion=f"{achado.group(1)} (2)" if achado else None,
        )

    if isinstance(exc, ConteudoNoExecutorError):
        return erro(
            "unavailable_local",
            str(exc) or "O conteúdo está no executor.",
            "conteúdo só no executor; sem download remoto",
        )

    if isinstance(exc, HTTPException):
        detalhe = exc.detail if isinstance(exc.detail, str) else "Requisição recusada."
        return erro(CODIGO_POR_STATUS.get(exc.status_code, "erro"), detalhe)

    if isinstance(exc, AtlasBaseError):
        # `atlas_code` preserves the domain code for integrators who want to
        # distinguish two cases that fall under the same status.
        return erro(
            CODIGO_POR_STATUS.get(exc.status_code, "erro"),
            str(exc) or "Operação recusada.",
            atlas_code=exc.error_code,
        )

    # Nothing known: the caller decides whether to wrap it or let it blow up. A
    # generic message on purpose — `str(exc)` of a library exception may
    # carry a URL with a credential.
    if isinstance(exc, FileNotFoundError):
        # `drive_service` raises the built-in FileNotFoundError for a file that
        # does not exist (or went out of reach); it is a 404, not an internal failure.
        return erro("not_found", "Recurso não encontrado.")
    return erro("internal_error", "Erro interno ao atender a chamada.")


def erro_de_segredo(caminhos: list[str]) -> ToolError:
    """The refusal of a definition that carries a secret in clear text.

    It exists as a helper (and not as a call to `erro` scattered across each
    write tool) because of the message: it cites the field's PATH and never
    the value. Whoever reads the error goes precisely to where the password is
    to fix it, and returning the value "to help" would make the secret take
    one more trip — through the transport, the client's history and the SDK log.

    `caminhos` is what `definition_contem_segredo` returns
    (`nodes[2].properties.connectionString`); even so each one goes through
    `scrub_text`, because a property name is text written by people.
    """
    return erro(
        "secret_in_definition",
        "A definição traz segredo em texto claro (ou o marcador <REDACTED> de uma leitura "
        "redigida) nos campos listados em paths.",
        "remova o valor e referencie a credencial por credential_id (list_credentials); um "
        "<REDACTED> vindo de uma leitura precisa do valor original, ou de não ser enviado",
        paths=[scrub_text(caminho) for caminho in caminhos],
    )
