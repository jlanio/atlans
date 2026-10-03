# app/core/config_em_cache.py
"""Reads with a short Redis cache — and the global configuration that lives in it.

The skeleton that `assistente_config_service` (the model) repeated line by line
with an extension's configuration services (the shape of the quota, each
person's plan): GET in Redis → on a miss, the database, in its own
session when the caller has none → SET with a TTL. Each service keeps only
what is its own: validating the value and saying how it becomes text.

Three rules apply to all of them — and the second had already diverged between the copies:

1. **Fail open.** Redis down means reading the database every time; database down
   means the default. Never an exception for someone who only wanted to read.
2. **What came from a database failure does not go into the cache.** Writing it would pin
   the default for an entire TTL AFTER the database came back: the admin's choice
   would vanish with nothing on screen explaining it. One of the copies already followed the rule; the
   model's and the quota's wrote the failure default.
3. **Readers write with `NX`; savers overwrite.** Between a reader's miss and
   SET, the admin may have saved another value and written the new one to the
   cache: a reader's blind SET would repaint the OLD one and pin it for the TTL — the
   change "wouldn't take", and whoever saved would conclude the button is broken. That is
   why `ConfigEmCache.definir` WRITES the new value instead of just deleting the
   key: by deleting, the late reader would find it free and `NX` would not
   stop it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_config import get_config, set_config
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def _texto(guardado) -> str:
    return guardado.decode() if isinstance(guardado, bytes) else str(guardado)


def _o_proprio_texto(texto: str) -> str:
    return texto


async def gravar_no_cache(
    redis, chave: str, texto: str, *, ttl_s: int, rotulo: str, so_se_vazio: bool = False,
) -> None:
    """SET with a TTL. A Redis failure becomes a warning in the log, never an exception.

    `so_se_vazio` is the `NX` of a reader (rule 3)."""
    if redis is None:
        return
    try:
        if so_se_vazio:
            await redis.set(chave, texto, ex=ttl_s, nx=True)
        else:
            await redis.set(chave, texto, ex=ttl_s)
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("%s: falha ao gravar o cache (%s).", rotulo, exc.__class__.__name__)


async def invalidar_cache(redis, chave: str, *, rotulo: str) -> None:
    """Deletes the key. For callers that don't have the new value in hand to write (someone's
    plan, changed by checkout or webhook) — callers that have it overwrite
    (rule 3)."""
    if redis is None:
        return
    try:
        await redis.delete(chave)
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("%s: falha ao invalidar o cache (%s).", rotulo, exc.__class__.__name__)


async def ler_com_cache(
    redis,
    chave: str,
    ler_do_banco: Callable[[], Awaitable[Optional[T]]],
    *,
    ttl_s: int,
    rotulo: str,
    serializar: Callable[[T], str] = str,
    desserializar: Callable[[str], Optional[T]] = _o_proprio_texto,
    so_se_vazio: bool = False,
) -> Optional[T]:
    """The value of `chave`: from the cache or, on a miss, from `ler_do_banco()` — written.

    `ler_do_banco` returns `None` when it could NOT read (the database failed). That
    `None` goes back to the caller, who decides the default, and does not go into the cache
    (rule 2). A cached value that `desserializar` rejects — by returning `None`
    or raising — counts as a miss.
    """
    if redis is not None:
        try:
            guardado = await redis.get(chave)
            if guardado:
                lido = desserializar(_texto(guardado))
                if lido is not None:
                    return lido
        except Exception as exc:
            logger.warning("%s: cache indisponível (%s) — indo ao banco.", rotulo, exc.__class__.__name__)

    valor = await ler_do_banco()
    if valor is not None:
        await gravar_no_cache(
            redis, chave, serializar(valor), ttl_s=ttl_s, rotulo=rotulo, so_se_vazio=so_se_vazio,
        )
    return valor


@dataclass(frozen=True)
class Carimbo(Generic[T]):
    """The saved value currently in effect, and who saved it and when."""

    valor: T
    por: Optional[str]
    em: Optional[str]


class ConfigEmCache(Generic[T]):
    """A global configuration in `SystemConfig`, with a default underneath.

    What gets written is the envelope `{campo: valor, "por": quem, "em": quando}` — or
    `None`, which goes back to the default. It is the format the installations already have saved. The
    stamp sits next to the value because the question "since when has it been like this?"
    comes up exactly when the month's bill is a surprise, and by then it is too late to
    search the logs.

    What is specific to each configuration comes from outside:

    - `ler(valor_cru)`: the `SystemConfig` row as is (envelope or not) →
      the validated value, or `None` when nothing there is usable;
    - `padrao()`: the floor (env, code) — anyone who never configured starts up working;
    - `serializar`/`desserializar`: the value ↔ the cache text. `desserializar`
      returns `None` (or raises) for what it doesn't recognize.
    """

    def __init__(
        self,
        *,
        chave: str,
        chave_cache: str,
        ttl_s: int,
        campo: str,
        ler: Callable[[Any], Optional[T]],
        padrao: Callable[[], T],
        rotulo: str,
        serializar: Callable[[T], str] = str,
        desserializar: Callable[[str], Optional[T]] = _o_proprio_texto,
    ) -> None:
        self.chave = chave
        self.chave_cache = chave_cache
        self.ttl_s = ttl_s
        self.campo = campo
        self.ler = ler
        self.padrao = padrao
        self.rotulo = rotulo
        self.serializar = serializar
        self.desserializar = desserializar

    async def em_uso(self, *, db: AsyncSession | None = None, redis=None) -> T:
        """The value in effect now. Never raises and never returns empty: any
        failure — Redis, database, corrupted row — falls back to the default.

        `db=None` is the case of the assistant loop, which runs inside an SSE
        generator and has no request session: it opens its own, only on a miss."""
        valor = await ler_com_cache(
            redis, self.chave_cache, lambda: self._do_banco(db),
            ttl_s=self.ttl_s, rotulo=self.rotulo,
            serializar=self.serializar, desserializar=self.desserializar,
            so_se_vazio=True,
        )
        return valor if valor is not None else self.padrao()

    async def _do_banco(self, db: AsyncSession | None) -> Optional[T]:
        """The saved value or, if nothing saved is usable, the default — both go into the cache.
        `None` only when the database failed (rule 2)."""
        try:
            if db is not None:
                escolhido = self.ler(await get_config(db, self.chave))
            else:
                # Late import: `app.mcp.infra` is the session patch point
                # in the tests, and importing it at the top would drag the whole MCP
                # server into `app.core`.
                from app.mcp import infra

                async with infra.sessao() as propria:
                    escolhido = self.ler(await get_config(propria, self.chave))
        except Exception as exc:
            logger.warning(
                "%s: falha ao ler a configuração salva (%s) — usando o padrão.",
                self.rotulo, exc.__class__.__name__,
            )
            return None
        return escolhido if escolhido is not None else self.padrao()

    async def definir(
        self, db: AsyncSession, valor: Optional[T], *, por: str | None = None, redis=None,
    ) -> None:
        """Writes `valor`, already validated by the caller (`None` goes back to the default), and
        pins it in the cache — without this the change would take a TTL to apply."""
        from app.core.utils.datetime_utils import utc_now_naive

        gravado = None if valor is None else {
            self.campo: valor, "por": por, "em": utc_now_naive().isoformat(),
        }
        await set_config(db, self.chave, gravado)
        # WRITES instead of just deleting (rule 3).
        await gravar_no_cache(
            redis, self.chave_cache,
            self.serializar(valor if valor is not None else self.padrao()),
            ttl_s=self.ttl_s, rotulo=self.rotulo,
        )

    async def carimbo(self, db: AsyncSession) -> Optional[Carimbo[T]]:
        """The saved value in effect, with who and when — or `None` when
        the default applies. It is what the admin screen shows.

        Reads through the same `ler` as `em_uso`: the screen must not say "default"
        while the conversation uses a saved value."""
        bruto = await get_config(db, self.chave)
        valor = self.ler(bruto)
        if valor is None:
            return None
        envelope = bruto if isinstance(bruto, dict) else {}
        return Carimbo(valor=valor, por=envelope.get("por"), em=envelope.get("em"))
