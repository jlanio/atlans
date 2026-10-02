# app/core/authorization/pat.py
"""
Token pessoal de acesso (PAT) — constantes e primitivas puras.

Um PAT é o que um agente (Claude Code, Cursor, um script) usa para falar com o
Atlans em nome de um usuário, sem sessão de navegador. Este módulo não conhece
FastAPI nem banco: só define o formato do segredo, os escopos possíveis e como
o segredo vira o hash que fica no banco.

Formato do segredo: ``atl_pat_`` + 43 caracteres url-safe (32 bytes aleatórios,
256 bits de entropia — o mesmo `secrets.token_urlsafe(32)` do OTP de enrollment).
No banco fica apenas o SHA-256 do segredo (hex, 64 chars) e um prefixo curto
para o usuário reconhecer o token na tela. Com 256 bits de entropia um hash sem
salt basta: um dump do banco não permite recuperar o segredo.
"""
from __future__ import annotations

import hashlib
import re
import secrets

PREFIXO = "atl_pat_"

# Ordem é a de exibição na tela. Efetivo = escopo ∩ papel do usuário no
# workspace (write exige editor; execute/triggers exigem operator) — a
# interseção é aplicada por quem consome o token (Fase 1), não aqui.
ESCOPOS: tuple[str, ...] = (
    "workflows:read",
    "workflows:write",
    "runs:execute",
    "triggers:manage",
    "drive:read",
    "drive:write",
)

VALIDADE_PADRAO_DIAS = 90
VALIDADE_MAX_DIAS = 365
MAX_TOKENS_ATIVOS_POR_USUARIO = 20
TAMANHO_PREFIXO_EXIBIVEL = 12  # "atl_pat_" + 4 chars — suficiente para reconhecer, inútil para adivinhar

# 43 = len(base64url(32 bytes)) sem o padding.
REGEX_SEGREDO = re.compile(r"atl_pat_[A-Za-z0-9_-]{43}")


def gerar_segredo() -> str:
    """Novo segredo: prefixo + 43 chars url-safe. Só existe em memória e na resposta de criação."""
    return PREFIXO + secrets.token_urlsafe(32)


def hash_segredo(segredo: str) -> str:
    """SHA-256 hex do segredo — é o que fica na coluna `token_hash`."""
    return hashlib.sha256(segredo.encode("utf-8")).hexdigest()


def prefixo_exibivel(segredo: str) -> str:
    """Os primeiros 12 caracteres, para a tela mostrar `atl_pat_Ab3d…`."""
    return segredo[:TAMANHO_PREFIXO_EXIBIVEL]


def e_segredo_pat(valor: str | None) -> bool:
    """True se o valor tem exatamente o formato de um PAT (sem consultar o banco)."""
    return bool(valor) and REGEX_SEGREDO.fullmatch(valor) is not None


def escopos_invalidos(escopos: list[str]) -> list[str]:
    """Os escopos que não existem, na ordem em que apareceram."""
    return [e for e in escopos if e not in ESCOPOS]


def status_de(revoked_at, expires_at, agora) -> str:
    """"revoked" | "expired" | "active" — a revogação prevalece sobre a expiração."""
    if revoked_at is not None:
        return "revoked"
    if expires_at is not None and expires_at <= agora:
        return "expired"
    return "active"
