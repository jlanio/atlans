# app/core/config_em_cache.py
"""Leitura com cache Redis curto — e a configuração global que vive nela.

O esqueleto que `assistente_config_service` (o modelo) repetia linha a linha
com os serviços de configuração de uma extensão (a forma da cota, o plano de
cada pessoa): GET no Redis → no miss, o banco, numa sessão
própria quando quem chama não tem uma → SET com TTL. Cada serviço fica só com o
que é dele: validar o valor e dizer como ele vira texto.

Três regras valem para todos — e a segunda já divergiu entre as cópias:

1. **Degradação aberta.** Redis fora do ar é ler o banco toda vez; banco fora
   do ar é o padrão. Nunca uma exceção para quem só queria ler.
2. **O que veio de uma falha do banco não vai para o cache.** Gravá-lo prenderia
   o padrão por um TTL inteiro DEPOIS de o banco voltar: a escolha do admin
   sumiria sem nada na tela explicando. Uma das cópias já seguia a regra; as
   do modelo e da cota gravavam o padrão da falha.
3. **Quem só lê grava com `NX`; quem salva grava por cima.** Entre o miss e o
   SET de um leitor, o admin pode ter salvo outro valor e gravado o novo no
   cache: um SET cego do leitor repintaria o VELHO e o fixaria pelo TTL — a
   troca «não pegaria», e quem salvou concluiria que o botão está quebrado. Por
   isso `ConfigEmCache.definir` ESCREVE o valor novo em vez de só apagar a
   chave: apagando, o leitor atrasado a encontraria livre e o `NX` não o
   deteria.
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
    """SET com TTL. Falha do Redis vira aviso no log, nunca exceção.

    `so_se_vazio` é o `NX` de quem só leu (regra 3)."""
    if redis is None:
        return
    try:
        if so_se_vazio:
            await redis.set(chave, texto, ex=ttl_s, nx=True)
        else:
            await redis.set(chave, texto, ex=ttl_s)
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("%s: falha ao gravar o cache (%s).", rotulo, exc.__class__.__name__)


async def invalidar_cache(redis, chave: str, *, rotulo: str) -> None:
    """Apaga a chave. Para quem não tem o valor novo em mãos para gravar (o
    plano de alguém, mudado por checkout ou webhook) — quem tem, grava por cima
    (regra 3)."""
    if redis is None:
        return
    try:
        await redis.delete(chave)
    except Exception as exc:  # pragma: no cover - depende do Redis
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
    """O valor de `chave`: do cache ou, no miss, de `ler_do_banco()` — gravado.

    `ler_do_banco` devolve `None` quando NÃO deu para ler (o banco falhou). Esse
    `None` volta a quem chamou, que decide o padrão, e não vai para o cache
    (regra 2). Um valor no cache que `desserializar` recusa — devolvendo `None`
    ou levantando — conta como miss.
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
    """O valor salvo que está valendo, e quem e quando o salvou."""

    valor: T
    por: Optional[str]
    em: Optional[str]


class ConfigEmCache(Generic[T]):
    """Uma configuração global no `SystemConfig`, com um padrão por baixo.

    O que se grava é o envelope `{campo: valor, "por": quem, "em": quando}` — ou
    `None`, que volta ao padrão. É o formato que as instalações já têm salvo. O
    carimbo fica junto do valor porque a pergunta «desde quando está assim?»
    aparece exatamente quando a conta do mês surpreende, e aí é tarde para
    procurar em log.

    O que é de cada configuração vem de fora:

    - `ler(valor_cru)`: a linha do `SystemConfig` como está (envelope ou não) →
      o valor validado, ou `None` quando nada ali serve;
    - `padrao()`: o piso (env, código) — quem nunca configurou sobe funcionando;
    - `serializar`/`desserializar`: o valor ↔ o texto do cache. `desserializar`
      devolve `None` (ou levanta) para o que não reconhece.
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
        """O valor que vale agora. Nunca levanta e nunca devolve vazio: qualquer
        falha — Redis, banco, linha corrompida — cai no padrão.

        `db=None` é o caso do laço do assistente, que roda dentro de um gerador
        SSE e não tem sessão de request: abre-se uma própria, só no miss."""
        valor = await ler_com_cache(
            redis, self.chave_cache, lambda: self._do_banco(db),
            ttl_s=self.ttl_s, rotulo=self.rotulo,
            serializar=self.serializar, desserializar=self.desserializar,
            so_se_vazio=True,
        )
        return valor if valor is not None else self.padrao()

    async def _do_banco(self, db: AsyncSession | None) -> Optional[T]:
        """O salvo ou, se nada salvo serve, o padrão — os dois vão para o cache.
        `None` só quando o banco falhou (regra 2)."""
        try:
            if db is not None:
                escolhido = self.ler(await get_config(db, self.chave))
            else:
                # Import tardio: `app.mcp.infra` é o ponto de patch da sessão
                # nos testes, e importá-lo no topo arrastaria o servidor MCP
                # inteiro para dentro de `app.core`.
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
        """Grava `valor`, já validado por quem chama (`None` volta ao padrão), e
        o fixa no cache — sem isto a troca demoraria um TTL para valer."""
        from app.core.utils.datetime_utils import utc_now_naive

        gravado = None if valor is None else {
            self.campo: valor, "por": por, "em": utc_now_naive().isoformat(),
        }
        await set_config(db, self.chave, gravado)
        # ESCREVE em vez de só apagar (regra 3).
        await gravar_no_cache(
            redis, self.chave_cache,
            self.serializar(valor if valor is not None else self.padrao()),
            ttl_s=self.ttl_s, rotulo=self.rotulo,
        )

    async def carimbo(self, db: AsyncSession) -> Optional[Carimbo[T]]:
        """O valor salvo que está valendo, com quem e quando — ou `None` quando
        vale o padrão. É o que a tela de admin mostra.

        Lê pelo mesmo `ler` de `em_uso`: a tela não pode dizer «padrão»
        enquanto a conversa usa um valor salvo."""
        bruto = await get_config(db, self.chave)
        valor = self.ler(bruto)
        if valor is None:
            return None
        envelope = bruto if isinstance(bruto, dict) else {}
        return Carimbo(valor=valor, por=envelope.get("por"), em=envelope.get("em"))
