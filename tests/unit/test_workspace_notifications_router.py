# tests/unit/test_workspace_notifications_router.py
"""Allowlist de notificacao do workspace: normalizacao e preview de impacto.

`Workspace.notification_url_allowlist` bloqueia webhooks de verdade
(`run_result_consumer._fire_notification_if_configured`) e ate agora nao tinha
endpoint nenhum — so dava para mexer por SQL. Do lado do usuario, o webhook
simplesmente nunca chegava.

O risco de dar UI a isso e aceitar um padrao que o matcher ignora em silencio:
`https://exemplo.com/hook` nunca casa com hostname algum, entao gravar isso
bloquearia TODOS os webhooks do workspace sem nada explicar. `_normalize_allowlist`
existe para transformar esse erro num 400 legivel.
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
    "*",             # nao e curinga para o matcher
    "*exemplo.com",  # sem o ponto, tambem nao
    "*.com",         # curinga sem dominio
    "localhost",     # sem ponto: nunca casaria como escrito
])
def test_rejeita_curinga_que_o_matcher_ignoraria(entrada):
    with pytest.raises(HTTPException) as exc:
        _normalize_allowlist([entrada])
    assert exc.value.status_code == 400


def test_aceita_as_duas_formas_suportadas():
    assert _normalize_allowlist(
        ["exemplo.com", "*.exemplo.com"],
    ) == ["exemplo.com", "*.exemplo.com"]


# ── Preview de impacto ───────────────────────────────────────────────────────
#
# O `allowed` do preview usa `hostname_matches_allowlist`, a mesma funcao que o
# consumer chama ao disparar. Estes testes fixam o contrato que a tela promete.

def _db_com_workflows(linhas):
    db = MagicMock()
    resultado = MagicMock()
    resultado.all.return_value = linhas
    db.execute = AsyncMock(return_value=resultado)
    return db


async def test_allowlist_vazia_permite_todos_os_workflows():
    """Semantica invertida da coluna: sem lista, nao ha politica adicional.

    O matcher sozinho devolveria False para tudo (nada casa com lista vazia);
    quem decide que "vazio = liberado" e o handler, espelhando o `if allowlist:`
    do consumer. Trocar isso barraria todos os webhooks da plataforma.
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
    """Regra facil de perder ao portar para outra linguagem."""
    from app.core.utils.allowlist import hostname_matches_allowlist

    assert hostname_matches_allowlist("api.exemplo.com", ["*.exemplo.com"]) is True
    assert hostname_matches_allowlist("a.b.exemplo.com", ["*.exemplo.com"]) is True
    assert hostname_matches_allowlist("exemplo.com", ["*.exemplo.com"]) is False


def test_host_fora_da_lista_e_bloqueado():
    from app.core.utils.allowlist import hostname_matches_allowlist

    assert hostname_matches_allowlist("evil.com", ["exemplo.com"]) is False
