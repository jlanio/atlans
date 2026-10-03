# tests/unit/test_assistente_lifecycle_auditoria.py
"""PR 5 — assistant lifecycle (Redis/SSE).

The fixes whose effect is timing or cancellation — not observable in the
buffered `ASGITransport` of the route tests, nor in the clockless `RedisFalso` —
are locked down by an AST SOURCE-CHECK: the mutation each test describes deletes
the structure, and the walk fails. It is the precedent of PR 1/PR 4.

The observable fixes have behavior tests where the harness lives:
  - #2 renewed lock and #5 live progress  → test_assistente_service.py
  - #3 quota that doesn't become immortal → test_mcp_cotas.py
  - #7 confirmation consumed in generator → test_agente_rota.py
"""
import ast
import asyncio
import inspect

from app.api.routers import assistente_router, assistente_editor_router
from app.api.routers._streaming import com_batimento


def _nome_da_call(func) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _arvore(obj) -> ast.AST:
    return ast.parse(inspect.getsource(obj))


def _tem_call_aninhada(obj, externa: str, interna: str) -> bool:
    """Is there an `externa(interna(...))` in the source of `obj` (module or function)?"""
    for node in ast.walk(_arvore(obj)):
        if isinstance(node, ast.Call) and _nome_da_call(node.func) == externa:
            if any(isinstance(a, ast.Call) and _nome_da_call(a.func) == interna for a in node.args):
                return True
    return False


def _chama(obj, nome: str) -> bool:
    return any(
        isinstance(n, ast.Call) and _nome_da_call(n.func) == nome for n in ast.walk(_arvore(obj))
    )


def _chama_dentro_de_asyncwith(func, nome: str) -> bool:
    """Is `nome(...)` called INSIDE some `async with` of `func`?"""
    for aw in (n for n in ast.walk(_arvore(func)) if isinstance(n, ast.AsyncWith)):
        if any(isinstance(s, ast.Call) and _nome_da_call(s.func) == nome for s in ast.walk(aw)):
            return True
    return False


# ── #1: o batimento (helper compartilhado, comportamento) ──────────────────────


async def test_com_batimento_pinga_no_silencio_e_passa_o_dado():
    """Fix #1: a `: ping` every `intervalo` of silence; otherwise the proxy kills
    the SSE of a long turn before the first frame."""

    async def gerador():
        await asyncio.sleep(0.03)  # silencio > intervalo
        yield b"event: fim\ndata: {}\n\n"

    quadros = [q async for q in com_batimento(gerador(), intervalo=0.005)]
    assert b": ping\n\n" in quadros, "nao bateu no silencio"
    assert quadros[-1] == b"event: fim\ndata: {}\n\n", "nao passou o quadro real"


async def test_com_batimento_sem_silencio_nao_pinga():
    async def gerador():
        yield b"event: a\ndata: 1\n\n"
        yield b"event: b\ndata: 2\n\n"

    quadros = [q async for q in com_batimento(gerador(), intervalo=5.0)]
    assert quadros == [b"event: a\ndata: 1\n\n", b"event: b\ndata: 2\n\n"]


# ── #1 (aplicacao no editor) e #4: source-check ────────────────────────────────


def test_a_rota_do_assistente_envolve_transmitir_no_batimento():
    """Mutation (#1): remove the wrap → the editor's SSE goes silent again on a long
    turn and the proxy kills it. The spacing is not testable in ASGITransport."""
    assert _tem_call_aninhada(assistente_editor_router, "com_batimento", "_transmitir")


def test_o_salvar_conversa_do_editor_e_blindado_com_shield():
    """Mutation (#4): remove the shield → the generator's cancellation (tab closed
    mid-response) aborts the write and the turn is lost."""
    assert _chama(assistente_editor_router._transmitir, "shield"), "salvar_conversa sem asyncio.shield"
    assert _chama(assistente_editor_router._transmitir, "salvar_conversa")


# ── #6: persistencia final SOB a trava (source-check) ──────────────────────────


def test_o_fecho_do_agente_corre_dentro_da_trava():
    """Mutation (#6): `_fechar_protegido` in the OUTER `finally`, outside the lock →
    race on `proxima_ordem`/UNIQUE between two tabs. The collision requires real
    concurrency, which the harness (pre-seeded lock) does not simulate."""
    for gerador in (assistente_router._transmitir_conversa, assistente_router._transmitir_confirmacao):
        assert _chama_dentro_de_asyncwith(gerador, "_fechar_protegido"), gerador.__name__
