# app/mcp/erros.py
"""
Erros do MCP: um formato só, legível por quem lê e parseável por quem integra.

O protocolo MCP não tem código de status — o que chega ao cliente é o texto do
`ToolError`. Se cada tool escrevesse a sua frase, quem integra não teria como
distinguir "falta escopo" de "workflow não existe" sem ler português. Por isso
a mensagem é sempre um JSON compacto `{code, message, hint?, ...extras}`:
`code` é o contrato estável, `message` é para o humano, `hint` diz o próximo
passo e os extras carregam o que a tool sabe (o relatório do lint, o escopo
que falta, os segundos até liberar).

`to_tool_error` é a tradução única das exceções do núcleo para esse formato.
Ela existe porque o `ToolManager` do SDK embrulha qualquer exceção que não
seja `ToolError` num `UnexpectedToolError` genérico — o mapeamento precisa
acontecer DENTRO da tool, antes de o SDK ver a exceção.

Regra de segurança: nada de segredo na mensagem. Só entram `str(exc)` de
exceções de domínio (escritas por nós) e `exc.detail` de `HTTPException` — e
tudo passa por `scrub_text` dentro de `erro()`, que é o funil único por onde
todo erro do MCP sai. A redação no funil cobre de uma vez os dois destinos: o
cliente e o log do SDK, que imprime o texto do `ToolError` por um logger que
não tem o filtro de segredos da casa. Vale também porque a mensagem ecoa
argumento escrito por gente (nome de nó, tópico, nome de workflow) — o mesmo
caminho por onde uma string de conexão entraria sem querer.
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

# Status HTTP → `code` do MCP. É a tabela que traduz qualquer `AtlasBaseError`
# e qualquer `HTTPException` sem precisar de um ramo por exceção.
CODIGO_POR_STATUS: dict[int, str] = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation",
    429: "rate_limited",
    503: "unavailable",
}

# O nome do workflow aparece entre aspas simples na mensagem do conflito
# ("Já existe um workflow chamado 'X' neste workspace.") — é de onde sai a
# sugestão. Sem casamento, o erro vai sem `suggestion`, nunca com uma inventada.
_NOME_ENTRE_ASPAS = re.compile(r"'([^']{1,120})'")


def erro(code: str, message: str, hint: str | None = None, **extras: Any) -> ToolError:
    """Monta o `ToolError` no formato padrão. Chaves nulas não entram no JSON.

    `message`, `hint` e todo extra que seja texto passam por `scrub_text`. É o
    único ponto por onde um erro do MCP sai, e redigir aqui vale para o cliente
    e para o log — o SDK registra o texto do `ToolError` por um logger que não
    carrega o filtro de segredos da casa.

    O que NÃO é string (o relatório do lint, a lista de candidatos, o número de
    segundos) segue intacto, porque descer nessas estruturas aqui destruiria o
    formato que o cliente lê. Em troca, a redação delas é responsabilidade de
    QUEM CHAMA, com o `higienizar` do `app.mcp.saida`: a premissa de que
    toda estrutura já vinha limpa da origem falhou — o relatório do lint
    montado por `validate_service` sai cru, e a mensagem fatal de
    `invalid_credential_id` ecoa o valor recebido, que nesse erro é justamente
    uma credencial colada no campo errado. `to_tool_error` higieniza antes de
    embarcar; toda tool que passar um extra estruturado precisa fazer o mesmo.
    """
    corpo: dict[str, Any] = {"code": code, "message": scrub_text(message)}
    if hint:
        corpo["hint"] = scrub_text(hint)
    for chave, valor in extras.items():
        if valor is None:
            continue
        corpo[chave] = scrub_text(valor) if isinstance(valor, str) else valor
    return ToolError(json.dumps(corpo, ensure_ascii=False))


# O gerenciador de tools do SDK re-levanta qualquer `ToolError` de dentro de uma
# tool prefixado com "Error executing tool <nome>: ". O prefixo é ruído para
# quem lê o erro: o contrato publicado em docs/mcp.md diz que a mensagem É o
# JSON `{code, message, hint}`, e os erros levantados nas guardas (escopo, cota)
# chegam sem prefixo nenhum. `sem_prefixo_do_sdk` devolve as duas formas ao
# mesmo formato.
_PREFIXO_DO_SDK = re.compile(r"^Error executing tool [^:]+: ")


def sem_prefixo_do_sdk(mensagem: str) -> str:
    return _PREFIXO_DO_SDK.sub("", mensagem, count=1)


def codigo_do_erro(exc: BaseException) -> str:
    """O `code` de um `ToolError` nosso — "erro" quando a mensagem não é JSON.

    Serve à auditoria e aos testes; nunca muda o erro que chega ao cliente.
    """
    try:
        corpo = json.loads(sem_prefixo_do_sdk(str(exc)))
    except (ValueError, TypeError):
        return "erro"
    codigo = corpo.get("code") if isinstance(corpo, dict) else None
    return codigo if isinstance(codigo, str) else "erro"


def to_tool_error(exc: BaseException) -> ToolError:
    """Traduz uma exceção do núcleo para o erro do MCP.

    Um `ToolError` já formatado passa intacto: quem o levantou sabia mais sobre
    o caso do que esta tabela genérica.
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
        # O `error_code` desta exceção é "no_agent_available" (nome antigo do
        # executor). O MCP expõe o vocabulário atual, não o histórico do banco.
        return erro(
            "no_executor",
            str(exc) or "Nenhum executor disponível.",
            "nenhum executor online; tente depois",
        )

    if isinstance(exc, DefinicaoInvalidaError):
        # O relatório vai higienizado porque ele NÃO nasce limpo: os itens do
        # lint ecoam o valor recebido para que quem lê ache o campo errado — e
        # `invalid_credential_id` cita o próprio `credential_id`, que só chega
        # nesse erro quando alguém colou ali uma string de conexão em vez do id
        # da credencial. Sem esta passada, o mesmo segredo saía `<REDACTED>` na
        # `message` (que passa por `scrub_text` no funil) e em claro dentro de
        # `report.errors[].message` — para o cliente e para o log do SDK.
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
        # `atlas_code` preserva o código do domínio para quem integra e quiser
        # distinguir dois casos que caem no mesmo status.
        return erro(
            CODIGO_POR_STATUS.get(exc.status_code, "erro"),
            str(exc) or "Operação recusada.",
            atlas_code=exc.error_code,
        )

    # Nada conhecido: o chamador decide se embrulha ou deixa estourar. Mensagem
    # genérica de propósito — `str(exc)` de uma exceção de biblioteca pode
    # carregar uma URL com credencial.
    if isinstance(exc, FileNotFoundError):
        # `drive_service` levanta o FileNotFoundError embutido para arquivo que
        # não existe (ou saiu do alcance); é 404, não falha interna.
        return erro("not_found", "Recurso não encontrado.")
    return erro("internal_error", "Erro interno ao atender a chamada.")


def erro_de_segredo(caminhos: list[str]) -> ToolError:
    """A recusa de uma definition que traz segredo em texto claro.

    Existe como helper (e não como uma chamada a `erro` espalhada por cada
    tool de escrita) por causa da mensagem: ela cita o CAMINHO do campo e
    nunca o valor. Quem lê o erro vai justamente ao lugar onde a senha está
    para corrigi-la, e devolver o valor "para ajudar" faria o segredo dar mais
    uma volta — pelo transporte, pelo histórico do cliente e pelo log do SDK.

    `caminhos` é o que `definition_contem_segredo` devolve
    (`nodes[2].properties.connectionString`); ainda assim cada um passa por
    `scrub_text`, porque o nome de uma propriedade é texto escrito por gente.
    """
    return erro(
        "secret_in_definition",
        "A definição traz segredo em texto claro (ou o marcador <REDACTED> de uma leitura "
        "redigida) nos campos listados em paths.",
        "remova o valor e referencie a credencial por credential_id (list_credentials); um "
        "<REDACTED> vindo de uma leitura precisa do valor original, ou de não ser enviado",
        paths=[scrub_text(caminho) for caminho in caminhos],
    )
