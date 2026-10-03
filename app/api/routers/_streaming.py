# app/api/routers/_streaming.py
"""SSE streaming utility shared between the assistant routers.

`com_batimento` interleaves `: ping` into the silence of an SSE generator. The risk of
an SSE stream behind a proxy is not the error, it is the SILENCE: undici drops it at
300 s, Cloudflare at around 100 s. A long execution (the assistant building and
running a workflow) can go minutes without a frame. `: ping` is an SSE comment
— the decoder ignores a line that starts with `:`.

It lives here, and not inside a router, because BOTH assistant surfaces need the
SAME heartbeat: the editor at /assistente and Home at /assistente. /assistente
already had it; /assistente/editor stayed quiet and a long turn dropped the connection
at the proxy before the first frame.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import AsyncIterator


async def com_batimento(
    gerador: AsyncIterator[bytes], intervalo: float = 15.0
) -> AsyncIterator[bytes]:
    """Yields what `gerador` emits and, after each `intervalo` of silence, a `: ping`.

    `gerador` already emits bytes with SSE framing (`event:`/`data:`); the ping
    is a comment, so it does not become a frame on the client. `intervalo` is a
    parameter so the tests can force the timeout without waiting 15 s of wall clock.
    """
    fila: asyncio.Queue = asyncio.Queue()

    async def bombear() -> None:
        try:
            async for item in gerador:
                await fila.put(("dado", item))
        except Exception as exc:  # pragma: no cover - the generator already handles its own
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
