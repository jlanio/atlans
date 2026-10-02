# tests/unit/test_assistente_lifecycle_auditoria.py
"""PR 5 — ciclo de vida do assistente (Redis/SSE).

Os consertos cujo efeito e timing ou cancelamento — nao observavel no
`ASGITransport` bufferizado dos testes de rota, nem no `RedisFalso` sem relogio —
sao travados por SOURCE-CHECK de AST: a mutacao que cada teste descreve apaga a
estrutura, e o walk falha. E o precedente do PR 1/PR 4.

Os consertos observaveis tem teste de comportamento onde mora o harness:
  - #2 trava renovada e #5 progresso ao vivo → test_assistente_service.py
  - #3 cota que nao fica imortal            → test_mcp_cotas.py
  - #7 confirmacao consumida no gerador     → test_agente_rota.py
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
    """Existe `externa(interna(...))` no fonte de `obj` (modulo ou funcao)?"""
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
    """`nome(...)` e chamado DENTRO de algum `async with` de `func`?"""
    for aw in (n for n in ast.walk(_arvore(func)) if isinstance(n, ast.AsyncWith)):
        if any(isinstance(s, ast.Call) and _nome_da_call(s.func) == nome for s in ast.walk(aw)):
            return True
    return False


# ── #1: o batimento (helper compartilhado, comportamento) ──────────────────────


async def test_com_batimento_pinga_no_silencio_e_passa_o_dado():
    """Fix #1: um `: ping` a cada `intervalo` de silencio; senao o proxy derruba
    o SSE de um turno longo antes do primeiro quadro."""

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
    """Mutacao (#1): tirar o wrap → o SSE do editor volta a ficar mudo num turno
    longo e o proxy o derruba. O espacamento nao e testavel no ASGITransport."""
    assert _tem_call_aninhada(assistente_editor_router, "com_batimento", "_transmitir")


def test_o_salvar_conversa_do_editor_e_blindado_com_shield():
    """Mutacao (#4): tirar o shield → o cancelamento do gerador (aba fechada no
    meio da resposta) aborta a gravacao e o turno se perde."""
    assert _chama(assistente_editor_router._transmitir, "shield"), "salvar_conversa sem asyncio.shield"
    assert _chama(assistente_editor_router._transmitir, "salvar_conversa")


# ── #6: persistencia final SOB a trava (source-check) ──────────────────────────


def test_o_fecho_do_agente_corre_dentro_da_trava():
    """Mutacao (#6): `_fechar_protegido` no `finally` EXTERNO, fora da trava →
    corrida em `proxima_ordem`/UNIQUE entre duas abas. A colisao exige
    concorrencia real, que o harness (trava pre-semeada) nao simula."""
    for gerador in (assistente_router._transmitir_conversa, assistente_router._transmitir_confirmacao):
        assert _chama_dentro_de_asyncwith(gerador, "_fechar_protegido"), gerador.__name__
