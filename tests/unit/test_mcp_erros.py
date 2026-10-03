# tests/unit/test_mcp_erros.py
"""
`to_tool_error` — the table that translates the core into MCP's vocabulary.

Each case here pins a `code`, and the `code` is a contract: whoever integrates decides
what to do next by reading that field (retry, ask for another token, fix the
definition). Silently changing one of them would break integrations without breaking
any test — hence one test per table row.

Four security points are also pinned: an already formatted `ToolError`
passes through intact (whoever raised it knew more), an unknown exception does NOT
become `str(exc)` on the client — a library's message may carry the whole connection
URL, with password —, everything that goes out through `erro()` goes through
`scrub_text`, including the part of the message that echoes a client argument
(node name, topic, workflow name), and the lint report — which is a
dict and therefore does NOT fit the string funnel — comes out sanitized by whoever
embeds it. That redaction also applies to the log: the SDK prints the text of the
`ToolError` through a logger that does not have the in-house secret filter.
"""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
from mcp.server.mcpserver.exceptions import ToolError

from app.core.exceptions import (
    ContentOnExecutorError,
    CredentialAccessDeniedError,
    InvalidDefinitionError,
    DisabledNodesInWorkflowError,
    FileNotFoundError as AppFileNotFoundError,
    InvalidDateFormatError,
    NoExecutorAvailableError,
    RunNotFoundError,
    WorkflowInactiveError,
    WorkflowInputValidationError,
    WorkflowNameConflictError,
    WorkflowNotFoundError,
    WorkspaceAccessDeniedError,
)
from app.mcp.erros import codigo_do_erro, erro, to_tool_error, without_sdk_prefix


def _response_body(exc: ToolError) -> dict:
    return json.loads(str(exc))


# ── erro() ────────────────────────────────────────────────────────────────────


def test_error_builds_json_with_code_and_message():
    corpo = _response_body(erro("not_found", "Não achei."))
    assert corpo == {"code": "not_found", "message": "Não achei."}


def test_error_omits_null_hint_and_extras():
    corpo = _response_body(erro("conflict", "Já existe.", None, suggestion=None, paths=["a"]))
    assert "hint" not in corpo and "suggestion" not in corpo
    assert corpo["paths"] == ["a"]


def test_error_preserves_readable_accents():
    # `ensure_ascii=False`: the message is read by a person in the MCP client.
    assert "inválida" in str(erro("validation", "Definição inválida."))


# The DSN is the format `scrub_text` recognizes and the one that shows up by mistake
# most often: a `connectionString` copied into the name of a node, a workflow or
# a topic comes back through the error message.
_DSN = "postgresql://ana:senha-secreta@db:5432/atlans"  # pragma: allowlist secret


def test_error_redacts_secret_in_the_message():
    """The message echoes a client argument — and the echo goes through the funnel."""
    corpo = _response_body(erro("not_found", f"Nó {_DSN} não existe."))
    assert "senha-secreta" not in json.dumps(corpo)
    assert "<REDACTED>" in corpo["message"]


def test_error_redacts_secret_in_the_hint_and_text_extras():
    corpo = _response_body(
        erro(
            "conflict",
            "Já existe.",
            f"tente outro nome que não {_DSN}",
            suggestion=f"{_DSN} (2)",
        )
    )
    assert "senha-secreta" not in json.dumps(corpo)
    assert "<REDACTED>" in corpo["hint"]
    assert "<REDACTED>" in corpo["suggestion"]


def test_error_does_not_touch_what_is_not_text():
    """The lint report and the numbers stay intact: the client parses them."""
    relatorio = {"ok": False, "errors": [{"code": "unknown_node", "node_id": "n1"}]}
    corpo = _response_body(erro("validation", "Inválido.", report=relatorio, retry_after_seconds=17))
    assert corpo["report"] == relatorio
    assert corpo["retry_after_seconds"] == 17


def test_conflicting_workflow_name_comes_out_redacted():
    """Real finding: the name written by people was echoed whole to the client and the log."""
    corpo = _response_body(
        to_tool_error(
            WorkflowNameConflictError(f"Já existe um workflow chamado '{_DSN}' neste workspace.")
        )
    )
    assert corpo["code"] == "conflict"
    assert "senha-secreta" not in json.dumps(corpo)


def test_error_code_of_message_that_is_not_json():
    assert codigo_do_erro(ToolError("falha qualquer")) == "erro"


# ── to_tool_error() ───────────────────────────────────────────────────────────


def test_already_formatted_tool_error_passes_intact():
    original = erro("ambiguous", "Dois workflows com esse nome.", candidates=[{"id": "a"}])
    assert to_tool_error(original) is original


def test_inactive_workflow_becomes_workflow_inactive_with_a_way_out():
    corpo = _response_body(to_tool_error(WorkflowInactiveError("Workflow inativo.")))
    assert corpo["code"] == "workflow_inactive"
    assert "set_workflow_active" in corpo["hint"]


def test_without_executor_becomes_no_executor_not_the_old_database_code():
    # The core's exception is still called `no_agent_available`; MCP speaks the
    # platform's current vocabulary.
    assert NoExecutorAvailableError.error_code == "no_agent_available"
    corpo = _response_body(to_tool_error(NoExecutorAvailableError("Ninguém online.")))
    assert corpo["code"] == "no_executor"
    assert "no_agent_available" not in json.dumps(corpo)


def test_invalid_definition_carries_the_lint_report():
    relatorio = {"ok": False, "errors": [{"code": "unknown_node", "node_id": "n1"}]}
    corpo = _response_body(to_tool_error(InvalidDefinitionError("Definição inválida.", report=relatorio)))
    assert corpo["code"] == "validation"
    assert corpo["report"] == relatorio


def test_invalid_definition_report_comes_out_sanitized():
    """Real finding: the SAME secret came out redacted in `message` and in the clear in `report`.

    `erro()` only applies `scrub_text` to what is a string at the top level of the body;
    the report is a dict and went through intact, on the premise that whoever builds it
    already sanitizes it — and `validate_service` does not. The fatal message of
    `invalid_credential_id` ECHOES the received `credential_id`, and that error only
    exists when someone pasted a connection string in place of the credential's id: the
    echoed value IS a real secret. It went whole to the client and to the SDK's log,
    which does not have the in-house secret filter.
    """
    relatorio = {
        "ok": False,
        "errors": [
            {
                "code": "invalid_credential_id",
                "message": f"credential_id '{_DSN}' de 'Consulta' (id=n1) não é um UUID.",
                "node_id": "n1",
            }
        ],
    }

    corpo = _response_body(to_tool_error(InvalidDefinitionError("Definição inválida.", report=relatorio)))

    assert "senha-secreta" not in json.dumps(corpo, ensure_ascii=False)
    assert "<REDACTED>" in corpo["report"]["errors"][0]["message"]
    # Only the text changes: the format the client parses to find the wrong field
    # still stands — without that, the redaction would have cost the diagnosis.
    assert corpo["report"]["ok"] is False
    assert corpo["report"]["errors"][0]["code"] == "invalid_credential_id"
    assert corpo["report"]["errors"][0]["node_id"] == "n1"


@pytest.mark.parametrize(
    "excecao",
    [
        WorkflowInputValidationError("Entrada inválida."),
        DisabledNodesInWorkflowError("Nó desabilitado."),
        InvalidDateFormatError("Data inválida."),
    ],
)
def test_validation_family_becomes_validation(excecao):
    assert _response_body(to_tool_error(excecao))["code"] == "validation"


def test_denied_credential_becomes_forbidden_with_sharing_hint():
    corpo = _response_body(to_tool_error(CredentialAccessDeniedError("Sem acesso.")))
    assert corpo["code"] == "forbidden"
    assert "compartilhada" in corpo["hint"]


def test_denied_workspace_becomes_forbidden():
    assert _response_body(to_tool_error(WorkspaceAccessDeniedError("Sem acesso.")))["code"] == "forbidden"


@pytest.mark.parametrize(
    "excecao",
    [
        WorkflowNotFoundError("Não existe."),
        RunNotFoundError("Não existe."),
        AppFileNotFoundError("Não existe."),
    ],
)
def test_absence_family_becomes_not_found(excecao):
    assert _response_body(to_tool_error(excecao))["code"] == "not_found"


def test_duplicate_name_becomes_conflict_with_suggestion_taken_from_the_message():
    corpo = _response_body(to_tool_error(WorkflowNameConflictError("Já existe um workflow chamado 'Buffer' neste workspace.")))
    assert corpo["code"] == "conflict"
    assert corpo["suggestion"] == "Buffer (2)"


def test_duplicate_name_without_name_in_message_does_not_invent_suggestion():
    corpo = _response_body(to_tool_error(WorkflowNameConflictError("Nome em uso.")))
    assert corpo["code"] == "conflict"
    assert "suggestion" not in corpo


def test_content_on_the_executor_becomes_unavailable_local():
    corpo = _response_body(to_tool_error(ContentOnExecutorError("Só no executor.")))
    assert corpo["code"] == "unavailable_local"


@pytest.mark.parametrize(
    "status,codigo",
    [
        (401, "unauthorized"),
        (403, "forbidden"),
        (404, "not_found"),
        (409, "conflict"),
        (422, "validation"),
        (429, "rate_limited"),
        (503, "unavailable"),
    ],
)
def test_http_exception_maps_by_status_and_uses_the_detail(status, codigo):
    corpo = _response_body(to_tool_error(HTTPException(status_code=status, detail="Motivo do núcleo.")))
    assert corpo["code"] == codigo
    assert corpo["message"] == "Motivo do núcleo."


def test_http_exception_with_structured_detail_does_not_leak_the_object():
    corpo = _response_body(to_tool_error(HTTPException(status_code=422, detail={"segredo": "nao-mostrar"})))
    assert "nao-mostrar" not in json.dumps(corpo)


def test_other_domain_error_falls_back_to_status_and_preserves_the_atlas_code():
    from app.services.api_token_service import ApiTokenLimitError

    corpo = _response_body(to_tool_error(ApiTokenLimitError("Limite atingido.")))
    assert corpo["code"] == "conflict"
    assert corpo["atlas_code"] == "api_token_limit"


def test_unknown_exception_does_not_repeat_the_original_message():
    corpo = _response_body(to_tool_error(RuntimeError("postgresql://ana:senha@db:5432/atlans caiu")))
    assert corpo["code"] == "internal_error"
    assert "senha" not in json.dumps(corpo)


def test_sdk_prefix_is_removed_so_the_client_sees_only_the_json():
    """The SDK re-raises the error from inside a tool prefixed with prose.

    Without the cleanup the client would get two formats: pure JSON when the scope
    or quota guard refuses, and JSON preceded by text when the tool itself
    fails — and a direct `json.loads` would break only in the second case.
    """
    corpo = erro("validation", "Definição inválida.", hint="confira o relatório")
    prefixado = f"Error executing tool validate_workflow: {corpo}"

    assert without_sdk_prefix(prefixado) == str(corpo)
    assert json.loads(without_sdk_prefix(prefixado))["code"] == "validation"
    # A message without a prefix passes through intact, and only the first prefix is removed.
    assert without_sdk_prefix(str(corpo)) == str(corpo)
    assert codigo_do_erro(ToolError(prefixado)) == "validation"


def test_nonexistent_drive_file_becomes_not_found():
    """`drive_service` raises the embedded FileNotFoundError; it is a 404, not a failure."""
    convertido = to_tool_error(FileNotFoundError("arquivo sumiu"))

    assert json.loads(str(convertido))["code"] == "not_found"
    assert "sumiu" not in str(convertido)
