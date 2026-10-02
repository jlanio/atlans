"""Busca por substring no banco: o termo de quem digita é LITERAL.

`%` e `_` são curingas do LIKE. Sem escapá-los, procurar "a_b" também devolve
"aXb", e "___" casa qualquer linha — a busca parece um filtro quebrado e, numa
lista de contas, vira enumeração da base inteira. O escape (e a `\\` que o
anuncia) era copiado à mão em cada serviço com busca, e a cópia esquecida na
busca de usuários do admin deixava o `_` como curinga. Aqui fica a única versão;
quem busca por substring usa `contem`.
"""
from __future__ import annotations

# O caractere de escape vai explícito no `ESCAPE` da consulta: o padrão do LIKE
# muda de banco para banco (o PostgreSQL já usa `\`, o SQLite não tem nenhum).
_ESCAPE = "\\"


def escapar_like(termo: str) -> str:
    """`termo` com `\\`, `%` e `_` escapados — literais dentro de um LIKE."""
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contem(coluna, termo: str, *, ignorar_caixa: bool = True):
    """Condição "`coluna` contém `termo`", com o termo tratado como texto.

    `ILIKE` por padrão, como as buscas das telas. `ignorar_caixa=False` dá o
    `LIKE` simples, para a coluna que já é gravada normalizada (sem acento, em
    minúsculas) — ali a diferença de caixa já foi resolvida na escrita.
    """
    padrao = f"%{escapar_like(termo)}%"
    if ignorar_caixa:
        return coluna.ilike(padrao, escape=_ESCAPE)
    return coluna.like(padrao, escape=_ESCAPE)
