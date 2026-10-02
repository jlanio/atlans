# app/services/disabled_nodes_service.py
"""
Servico de gerenciamento de nodes desabilitados pelo admin.

Persistencia: SystemConfig com key `disabled_nodes` -> dict de
metadata por nome de node:

    {
      "SendEmail": {
        "disabled_at": "2026-06-18T14:30:00Z",
        "disabled_by": "<user_id_hash>",
        "reason": "Auditoria de seguranca em andamento"
      }
    }

Sem migracao — reusa tabela existente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_config import get_config, set_config
from app.core.utils.logger import get_logger

_logger = get_logger(__name__)

_CONFIG_KEY = "disabled_nodes"

# ── Cache em memoria, coordenado entre workers por uma epoca no Redis ────────
#
# Sintoma que o CACHE resolve: TODO disparo de workflow (POST /execute, webhook
# e cron) fazia um SELECT em SystemConfig no caminho quente so para descobrir um
# valor que muda uma vez por mes — um round-trip inteiro ao Postgres somado a
# latencia entre o clique em "Executar" e o job sair do servidor.
#
# Sintoma que a EPOCA resolve: a producao sobe a API com `uvicorn --workers 4`,
# entao `_cache` existe em 4 copias independentes e `invalidate_cache()` so
# alcanca o processo que atendeu o PATCH do admin. Com TTL puro isso dava (a) um
# node desabilitado por incidente continuando a ser despachado pelos outros 3
# workers por ate 30 s — e o snapshot `disabled_nodes` que vai no envelope do job
# sai DESTE mesmo cache, entao o executor revalida contra a lista velha e libera
# igual (nao ha segunda fonte independente) — e (b) leitura-apos-escrita
# quebrada na UI: o GET /admin/nodes seguinte caia noutro worker, voltava
# `enabled: true` e o toggle desfazia-se sozinho na tela.
#
# Como funciona: toda escrita faz INCR na chave de epoca; a leitura confere a
# epoca (um GET no Redis — que o dispatch ja usa e custa uma fracao do
# SELECT+desserializacao no Postgres) e so vai ao banco quando ela mudou. O TTL
# local sobrou como degradacao para Redis indisponivel: nesse caso volta a valer
# o teto de defasagem de 30 s, e o dispatch nao quebra por causa disso.
_EPOCH_KEY = "disabled_nodes:epoch"
_CACHE_TTL_S = 30.0
_cache: dict[str, dict[str, Any]] | None = None
_cache_epoca: str | None = None
_cache_expira_em: float = 0.0


def _redis():
    from app.core.redis import get_redis_pool
    return get_redis_pool()


async def _ler_epoca() -> str | None:
    """Epoca corrente, ou None quando o Redis nao pode ser consultado.

    Chave ausente vale "0" (estado inicial, nenhuma escrita ainda) — e diferente
    de None, que significa "nao deu para saber" e cai no TTL local.
    """
    try:
        valor = await _redis().get(_EPOCH_KEY)
    except Exception as exc:
        # Rebaixado a debug de proposito: acontece uma vez por leitura e o
        # caminho de degradacao (TTL local) e o comportamento documentado acima.
        _logger.debug("Epoca de disabled_nodes indisponivel no Redis: %s", exc)
        return None
    return valor if valor is not None else "0"


async def _publicar_invalidacao() -> None:
    """Avisa os OUTROS workers que o mapa mudou, incrementando a epoca."""
    try:
        await _redis().incr(_EPOCH_KEY)
    except Exception as exc:
        _logger.warning(
            "Falha ao publicar invalidacao de disabled_nodes no Redis (%s): os "
            "demais workers so verao a mudanca quando o TTL de %.0fs vencer.",
            exc, _CACHE_TTL_S,
        )


def invalidate_cache() -> None:
    """Descarta o cache do processo. Toda escrita chama; testes tambem."""
    global _cache, _cache_epoca, _cache_expira_em
    _cache = None
    _cache_epoca = None
    _cache_expira_em = 0.0


async def list_disabled(db: AsyncSession) -> dict[str, dict[str, Any]]:
    """Retorna o mapa atual de nodes desabilitados {name: metadata}.

    O dict devolvido e o proprio objeto cacheado — quem precisa alterar copia
    antes (ver `set_disabled`/`set_enabled`).
    """
    global _cache, _cache_epoca, _cache_expira_em

    # A epoca e lida ANTES do SELECT de proposito: se uma escrita entrar no meio,
    # o mapa novo fica gravado sob a epoca antiga e a proxima leitura recarrega
    # (custo: um SELECT extra). Ler a epoca DEPOIS carimbaria dado velho como
    # atual e o cache ficaria stale ate o TTL vencer.
    epoca = await _ler_epoca()
    agora = monotonic()

    if _cache is not None:
        if epoca is not None:
            if epoca == _cache_epoca:
                return _cache
        elif agora < _cache_expira_em:
            return _cache

    raw = await get_config(db, _CONFIG_KEY, default={})
    # Defesa: tipo retornado do JSON pode vir como list em config corrompida
    if not isinstance(raw, dict):
        raw = {}

    _cache = raw
    _cache_epoca = epoca
    _cache_expira_em = agora + _CACHE_TTL_S
    return _cache


async def disabled_names(db: AsyncSession) -> set[str]:
    """Atalho: apenas os nomes (para uso em filtros set-based)."""
    cfg = await list_disabled(db)
    return set(cfg.keys())


async def set_disabled(
    db: AsyncSession, name: str, *, by: str, reason: str
) -> dict[str, Any]:
    """Marca um node como desabilitado. Idempotente: atualiza metadata."""
    cfg = dict(await list_disabled(db))
    entry = {
        "disabled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "disabled_by": by,
        "reason": reason,
    }
    cfg[name] = entry
    await set_config(db, _CONFIG_KEY, cfg)
    invalidate_cache()
    # Depois do commit do set_config: quem ler a epoca nova tem de encontrar o
    # mapa novo no banco, nunca o contrario.
    await _publicar_invalidacao()
    return entry


async def set_enabled(db: AsyncSession, name: str) -> bool:
    """Remove o node do mapa. Retorna True se removeu algo."""
    cfg = dict(await list_disabled(db))
    if name not in cfg:
        return False
    cfg.pop(name)
    await set_config(db, _CONFIG_KEY, cfg)
    invalidate_cache()
    await _publicar_invalidacao()
    return True
