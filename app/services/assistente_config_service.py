# app/services/assistente_config_service.py
"""Qual modelo o assistente usa — e quem manda nisso.

**Env como piso, banco por cima.** `ASSISTENTE_MODELO` continua sendo o padrão:
uma instalação nova sobe funcionando sem ninguém configurar nada. Existindo uma
escolha salva pelo admin, ela vence. É a mesma precedência dos preços dos
planos, só que com o banco na frente — porque trocar de modelo é decisão de
operação, e exigir deploy para isso é o que fazia o operador não trocar.

Não há tabela nova: `SystemConfig` já é o chaveiro de configuração global do
sistema (`app/core/system_config.py`), com os mesmos requisitos — uma linha,
lida muito e escrita raramente.

**O cache existe porque isto é lido a cada conversa**, e o laço do assistente não
tem sessão de request (ele roda dentro de um gerador SSE). A leitura, o cache e
a gravação são os de `app/core/config_em_cache.py` — Redis com TTL curto, sessão
própria no miss, degradação aberta: Redis fora do ar significa ler o banco toda
vez, nunca significa ficar sem modelo. Aqui fica só o que é do modelo: a forma
de um id válido.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ASSISTENTE_MODELO
from app.core.config_em_cache import ConfigEmCache

CHAVE = "assistente.modelo"
_CACHE = "assistente:modelo"
_TTL_S = 300

# Um id de modelo é o nome no catálogo do provedor: `fornecedor/nome[:variante]`
# no OpenRouter, `qwen3:14b` no Ollama. A validação é de FORMA, não de
# existência: quem diz o que existe é o catálogo do provedor, consultado na
# rota. Ela serve para barrar o acidente óbvio — um campo colado com espaço,
# uma URL inteira, um texto vazio — antes de virar erro em toda conversa.
TAMANHO_MAXIMO = 120


def formato_valido(modelo: str) -> bool:
    if not modelo or len(modelo) > TAMANHO_MAXIMO:
        return False
    if any(c.isspace() for c in modelo) or "://" in modelo:
        return False
    # Barra no começo, no fim ou dobrada é colagem errada.
    return all(modelo.split("/"))


def _ler(valor: Any) -> str | None:
    """O modelo da linha salva, se tiver forma de id — senão, nada (o padrão)."""
    if isinstance(valor, dict):
        valor = valor.get("modelo")
    if isinstance(valor, str) and formato_valido(valor):
        return valor
    return None


_CONFIG: ConfigEmCache[str] = ConfigEmCache(
    chave=CHAVE,
    chave_cache=_CACHE,
    ttl_s=_TTL_S,
    campo="modelo",
    ler=_ler,
    padrao=lambda: ASSISTENTE_MODELO,
    rotulo="Assistente",
)


async def modelo_em_uso(*, db: AsyncSession | None = None, redis=None) -> str:
    """O modelo que vale agora. Nunca devolve vazio.

    Qualquer falha — Redis, banco, linha corrompida — cai no padrão do
    ambiente. Ficar sem modelo significaria o assistente inteiro fora do ar por
    causa de uma configuração; o padrão é sempre melhor que nada.
    """
    return await _CONFIG.em_uso(db=db, redis=redis)


async def definir_modelo(db: AsyncSession, modelo: str | None, *, por: str | None = None,
                         redis=None) -> dict[str, Any]:
    """Salva a escolha do admin. `None` volta ao padrão do ambiente.

    Grava o carimbo de quem e quando junto do valor e fixa o modelo novo no
    cache na hora (`ConfigEmCache.definir`).
    """
    if modelo is not None and not formato_valido(modelo):
        raise ValueError(
            "Id de modelo inválido: o nome no catálogo do provedor (ex.: `fornecedor/nome` "
            "no OpenRouter), sem espaços nem URL."
        )
    await _CONFIG.definir(db, modelo, por=por, redis=redis)
    return await situacao(db=db)


async def situacao(*, db: AsyncSession) -> dict[str, Any]:
    """O que a tela de admin mostra: o modelo, de onde ele veio, e o carimbo.

    `origem` não é enfeite: «do ambiente» e «definido aqui» pedem botões
    diferentes (um oferece definir, o outro oferece voltar ao padrão), e sem o
    campo a tela teria de adivinhar comparando strings.
    """
    carimbo = await _CONFIG.carimbo(db)
    if carimbo is not None:
        return {
            "modelo": carimbo.valor,
            "origem": "banco",
            "definido_por": carimbo.por,
            "definido_em": carimbo.em,
            "padrao_do_ambiente": ASSISTENTE_MODELO,
        }
    return {
        "modelo": ASSISTENTE_MODELO,
        "origem": "ambiente",
        "definido_por": None,
        "definido_em": None,
        "padrao_do_ambiente": ASSISTENTE_MODELO,
    }
