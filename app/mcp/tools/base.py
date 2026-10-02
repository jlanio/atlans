# app/mcp/tools/base.py
"""
A base compartilhada das tools: o decorador de tradução de erro, a guarda
cronometrada (escopo + cota + auditoria) e as anotações derivadas da tabela.

O módulo mora aqui, e não em `servidor.py`, porque os TRÊS consumidores da
guarda — `ServidorAtlans.call_tool`, os handlers de resource e as próprias
tools — já dependem deste arquivo e nenhum deles pode importar `servidor.py`
sem ciclo (`servidor` importa `tools` e `resources` para registrá-los).

── O decorador que toda tool veste ──

Ele traduz a exceção do núcleo para o erro do MCP. Por que dentro da tool e não
no servidor: o gerenciador de tools do SDK embrulha qualquer exceção que não
seja `ToolError` num erro genérico ANTES de a chamada voltar para `call_tool`.
Quem quiser transformar um `WorkflowInactiveError` num `{"code":
"workflow_inactive"}` legível precisa fazê-lo DENTRO da tool — depois já é
tarde, e o cliente recebe "erro inesperado".

O que sobe intacto, e por quê:
- `ToolError` passa: quem o levantou (uma guarda, `resolver_workspace`, a
  própria tool) sabia mais sobre o caso do que a tabela genérica;
- `AtlasBaseError` e `HTTPException` viram `to_tool_error(exc)` — são as
  exceções que os services do Atlans usam para dizer "404", "403", "422";
- qualquer outra coisa SOBE. Um `KeyError` é defeito nosso, não recusa: o SDK
  registra a falha e o cliente recebe uma mensagem genérica, sem `str(exc)` de
  biblioteca — que é justamente onde uma URL com senha costuma aparecer.

`functools.wraps` não é cosmético: o SDK monta o `inputSchema` da tool por
introspecção da função, e sem ele toda tool chegaria ao cliente como
`(*args, **kwargs)`. Ele também deixa `__wrapped__` no embrulho, que é o fio
por onde `inspect.signature` e `typing.get_type_hints` chegam à função original
— e portanto ao módulo onde `Context` e os demais nomes de fato existem (com
`from __future__ import annotations` as anotações são STRINGS, avaliadas contra
os globais de quem as definiu, nunca deste arquivo).

As anotações já resolvidas são copiadas por cima como segunda linha de defesa:
assim o schema da tool — e o reconhecimento do parâmetro `ctx`, que o servidor
injeta e o cliente nunca preenche — não depende desse detalhe de
desembrulhamento continuar valendo.
"""
from __future__ import annotations

import functools
import time
import typing
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable

from fastapi import HTTPException
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from app.core.exceptions import AtlasBaseError
from app.core.utils.logger import get_logger
from app.mcp import cotas, infra
from app.mcp.erros import codigo_do_erro, to_tool_error
from app.mcp.escopo import EscopoEfetivo, exigir_escopo
from app.mcp.guardas import GUARDAS

auditoria = get_logger("app.mcp.auditoria")


def _anotacoes_resolvidas(fn: Callable[..., Any]) -> dict:
    """As anotações de `fn` já avaliadas (objetos, não strings).

    Falhar aqui não pode derrubar o registro da tool: sem as anotações
    resolvidas o SDK ainda monta um schema a partir da assinatura original.
    """
    try:
        return dict(typing.get_type_hints(fn, include_extras=True))
    except Exception:  # pragma: no cover - anotação exótica ou import circular
        return dict(getattr(fn, "__annotations__", {}) or {})


def ferramenta(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Embrulha a corrotina de uma tool traduzindo as exceções do núcleo."""

    @functools.wraps(fn)
    async def _embrulho(*args: Any, **kwargs: Any):
        try:
            return await fn(*args, **kwargs)
        except ToolError:
            raise
        except (AtlasBaseError, HTTPException) as exc:
            raise to_tool_error(exc) from exc

    _embrulho.__annotations__ = _anotacoes_resolvidas(fn)
    return _embrulho


@asynccontextmanager
async def guarda_da_chamada(
    nome: str,
    escopo: EscopoEfetivo,
    *,
    cobrar_cota: bool = True,
    origem: str = "tool",
) -> AsyncIterator[None]:
    """Escopo → cota → corpo → linha de auditoria, com o desfecho de verdade.

    A ordem importa em dois sentidos. O escopo e a cota são conferidos DENTRO do
    bloco cronometrado para que a recusa também deixe rastro: uma chamada barrada
    por falta de escopo ou por teto de cota é justamente a que mais interessa
    registrar, e enquanto as guardas ficaram antes do `try` ela saía sem linha
    nenhuma. A recusa ganha desfecho próprio (`recusa:<code>`) para não se
    confundir com uma tool que rodou e falhou (`tool_error:<code>`).

    `escopo` chega pronto: quem chama já o resolveu com `escopo_da_chamada`, e é
    de propósito que essa resolução fique FORA daqui — quando ela falha não há
    identidade para nomear na linha de auditoria.

    `cobrar_cota=False` é o caso dos resources, que são alias de leitura de uma
    tool e não têm balde próprio: cobrar duas vezes o mesmo trabalho não mede
    nada, e o balde geral da tool já segura o laço. A auditoria continua valendo.

    A linha nunca carrega os argumentos da chamada — eles carregam dados do
    usuário (nome de arquivo, id de workflow, texto de busca).
    """
    guarda = GUARDAS.get(nome)
    inicio = time.perf_counter()
    desfecho = "ok"
    try:
        try:
            if guarda is not None and guarda.escopo:
                exigir_escopo(escopo, guarda.escopo)
            if cobrar_cota:
                await cotas.verificar(
                    infra.redis_ou_none(), escopo.token_id, guarda.cota if guarda else None
                )
        except ToolError as exc:
            desfecho = f"recusa:{codigo_do_erro(exc)}"
            raise
        yield
    except ToolError as exc:
        if desfecho == "ok":
            desfecho = f"tool_error:{codigo_do_erro(exc)}"
        raise
    except BaseException:
        if desfecho == "ok":
            desfecho = "erro"
        raise
    finally:
        # Prefixo do token (nunca o segredo), usuário, duração e desfecho.
        auditoria.info(
            "mcp %s=%s token=%s user=%s ms=%d desfecho=%s",
            origem,
            nome,
            escopo.token_prefix,
            escopo.user_id,
            int((time.perf_counter() - inicio) * 1000),
            desfecho,
        )


def anotacoes(nome: str) -> ToolAnnotations:
    """As `ToolAnnotations` da tool, derivadas da linha dela em `GUARDAS`.

    Escrever os hints à mão em cada módulo de domínio é o caminho curto para o
    doc e a tabela divergirem em silêncio — a tabela diz `idempotente=False` e a
    anotação publicada continua dizendo `true`. Aqui há um lugar só.

    `destructive_hint` é sempre False por decisão de desenho, não por omissão:
    o MCP do Atlans não apaga nada. `open_world_hint` sai da tabela: False para
    tudo, menos as tools que sondam um WFS (ver a nota de `app/mcp/guardas.py`).
    """
    guarda = GUARDAS[nome]
    return ToolAnnotations(
        read_only_hint=guarda.read_only,
        destructive_hint=False,
        idempotent_hint=guarda.idempotente,
        open_world_hint=guarda.open_world,
    )
