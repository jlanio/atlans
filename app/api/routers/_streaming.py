# app/api/routers/_streaming.py
"""Utilitario de streaming SSE compartilhado entre os roteadores do assistente.

`com_batimento` intercala `: ping` no silencio de um gerador SSE. O risco de um
SSE atras de proxy nao e o erro, e o SILENCIO: undici derruba aos 300 s, a
Cloudflare por volta de 100 s. Uma execucao longa (o assistente montando e
rodando um fluxo) pode ficar minutos sem um quadro. O `: ping` e um comentario
SSE — o decodificador ignora a linha que comeca com `:`.

Vive aqui, e nao dentro de um roteador, porque as DUAS superficies do assistente
precisam do MESMO batimento: o editor em /assistente e a Home em /assistente. O /assistente
ja o tinha; o /assistente/editor ficava calado e um turno longo derrubava a conexao no
proxy antes do primeiro quadro.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import AsyncIterator


async def com_batimento(
    gerador: AsyncIterator[bytes], intervalo: float = 15.0
) -> AsyncIterator[bytes]:
    """Cede o que o `gerador` emite e, a cada `intervalo` de silencio, um `: ping`.

    O `gerador` ja emite bytes com o enquadramento SSE (`event:`/`data:`); o ping
    e um comentario, entao nao vira quadro no cliente. O `intervalo` e parametro
    para os testes poderem forcar o timeout sem esperar 15 s de relogio.
    """
    fila: asyncio.Queue = asyncio.Queue()

    async def bombear() -> None:
        try:
            async for item in gerador:
                await fila.put(("dado", item))
        except Exception as exc:  # pragma: no cover - o gerador ja trata os seus
            await fila.put(("erro", exc))
        finally:
            await fila.put(("fim", None))

    tarefa = asyncio.create_task(bombear())
    try:
        while True:
            try:
                tipo, valor = await asyncio.wait_for(fila.get(), timeout=intervalo)
            except asyncio.TimeoutError:
                yield b": ping\n\n"
                continue
            if tipo == "dado":
                yield valor
            elif tipo == "erro":  # pragma: no cover
                raise valor
            else:
                break
    finally:
        tarefa.cancel()
        with suppress(asyncio.CancelledError):
            await tarefa
