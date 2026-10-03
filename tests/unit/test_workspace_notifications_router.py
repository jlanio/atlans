# tests/unit/test_workspace_notifications_router.py
"""Workspace notification allowlist: normalization and impact preview.

`Workspace.notification_url_allowlist` blocks real webhooks
(`run_result_consumer._fire_notification_if_configured`) and until now had
no endpoint at all — it could only be changed through SQL. On the user's side, the webhook
simply never arrived.

The risk of giving this a UI is accepting a pattern the matcher silently ignores:
`https://exemplo.com/hook` never matches any hostname, so saving it
would block ALL of the workspace's webhooks without explaining anything. `_normalize_allowlist`
exists to turn that mistake into a readable 400.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.routers.workspace_router import _normalize_allowlist, _notification_targets


# ── Normalizacao ─────────────────────────────────────────────────────────────

def test_normaliza_caixa_espacos_e_duplicatas():
    assert _normalize_allowlist(
        ["  Exemplo.COM ", "exemplo.com", "", "   ", "*.Interno.Corp"],
    ) == ["exemplo.com", "*.interno.corp"]


def test_lista_vazia_vira_lista_vazia():
    """O handler grava NULL a partir disto — `None` e `[]` sao o mesmo estado."""
    assert _normalize_allowlist([]) == []
    assert _normalize_allowlist(["", "  "]) == []


@pytest.mark.parametrize("entrada", [
    "https://exemplo.com/hook",   # o erro obvio: colar a URL inteira
    "exemplo.com/hook",
    "exemplo.com:8443",
    "user@exemplo.com",
])
def test_rejeita_o_que_nao_e_hostname(entrada):
    with pytest.raises(HTTPException) as exc:
        _normalize_allowlist([entrada])
    assert exc.value.status_code == 400


@pytest.mark.parametrize("entrada", [
    "*",             # not a wildcard for the matcher
    "*exemplo.com",  # without the dot, not either
    "*.com",         # wildcard with no domain
    "localhost",     # no dot: would never match as written
])
def test_rejeita_curinga_que_o_matcher_ignoraria(entrada):
    with pytest.raises(HTTPException) as exc:
        _normalize_allowlist([entrada])
    assert exc.value.status_code == 400


def test_aceita_as_duas_formas_suportadas():
    assert _normalize_allowlist(
        ["exemplo.com", "*.exemplo.com"],
    ) == ["exemplo.com", "*.exemplo.com"]


# ── Impact preview ───────────────────────────────────────────────────────────
#
# The preview's `allowed` uses `hostname_matches_allowlist`, the same function the
# consumer calls when firing. These tests pin the contract the screen promises.

def _db_com_workflows(linhas):
    db = MagicMock()
    resultado = MagicMock()
    resultado.all.return_value = linhas
    db.execute = AsyncMock(return_value=resultado)
    return db


async def test_allowlist_vazia_permite_todos_os_workflows():
    """Inverted semantics of the column: with no list, there is no additional policy.

    The matcher alone would return False for everything (nothing matches an empty list);
    what decides that "empty = allowed" is the handler, mirroring the consumer's
    `if allowlist:`. Changing that would block every webhook on the platform.
    """
    db = _db_com_workflows([("wf-1", "Diário", "https://qualquer.host/hook")])

    alvos = await _notification_targets(db, "ws-1", [])

    assert [a.allowed for a in alvos] == [True]
    assert alvos[0].host == "qualquer.host"


async def test_preview_marca_bloqueado_o_host_fora_da_lista():
    db = _db_com_workflows([
        ("wf-1", "Permitido", "https://api.exemplo.com/hook"),
        ("wf-2", "Bloqueado", "https://evil.com/hook"),
    ])

    alvos = await _notification_targets(db, "ws-1", ["*.exemplo.com"])

    assert {a.name: a.allowed for a in alvos} == {"Permitido": True, "Bloqueado": False}


async def test_url_sem_host_nao_explode():
    db = _db_com_workflows([("wf-1", "Quebrado", "nao-e-url")])

    alvos = await _notification_targets(db, "ws-1", ["exemplo.com"])

    assert alvos[0].host == ""
    assert alvos[0].allowed is False


def test_curinga_nao_cobre_o_dominio_nu():
    """A rule that is easy to lose when porting to another language."""
    from app.core.utils.allowlist import hostname_matches_allowlist

    assert hostname_matches_allowlist("api.exemplo.com", ["*.exemplo.com"]) is True
    assert hostname_matches_allowlist("a.b.exemplo.com", ["*.exemplo.com"]) is True
    assert hostname_matches_allowlist("exemplo.com", ["*.exemplo.com"]) is False


def test_host_fora_da_lista_e_bloqueado():
    from app.core.utils.allowlist import hostname_matches_allowlist

    assert hostname_matches_allowlist("evil.com", ["exemplo.com"]) is False
