"""A whitelist global de webhooks (admin → Configurações) passa a valer no disparo.

Ela era gravada e exibida — a tela avisava quando estava vazia —, mas nenhum
disparo a consultava: a restrição que o admin configurava não restringia nada.
Vazia continua sem restrição; com itens, o host precisa estar nela E na
allowlist do workspace.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core import run_result_consumer as rrc
from app.core.utils.allowlist import normalizar_dominio, padroes_validos, validar_allowlist


# ── Normalização e validação ─────────────────────────────────────────────────


@pytest.mark.parametrize("entrada, esperado", [
    ("https://Hooks.Slack.com/services/T000/B000", "hooks.slack.com"),
    ("http://exemplo.com:8443/", "exemplo.com"),
    ("  *.Interno.Corp ", "*.interno.corp"),
    ("exemplo.com", "exemplo.com"),
])
def test_normalizar_dominio_fica_so_com_o_host(entrada, esperado):
    assert normalizar_dominio(entrada) == esperado


@pytest.mark.parametrize("entrada", ["*", "localhost", "*.com", "*exemplo.com"])
def test_validar_recusa_o_que_o_matcher_ignoraria(entrada):
    with pytest.raises(ValueError):
        validar_allowlist([entrada])


def test_padroes_validos_descarta_o_legado_que_nunca_casou():
    """Um `*` gravado antes (para "liberar tudo") não pode passar a bloquear tudo."""
    assert padroes_validos(["*", "https://hooks.slack.com/x", "localhost", "hooks.slack.com"]) == [
        "hooks.slack.com",
    ]
    assert padroes_validos(["*"]) == []


# ── PATCH do admin ──────────────────────────────────────────────────────────


async def test_patch_grava_o_host_da_url_colada():
    from app.api.routers import health_router

    with patch.object(health_router, "_set_config", new=AsyncMock()) as gravar:
        saida = await health_router.update_webhook_whitelist(
            domains=["https://Hooks.Slack.com/services/x", "hooks.slack.com", ""], db=MagicMock(),
        )
    assert saida == {"webhook_whitelist": ["hooks.slack.com"]}
    gravar.assert_awaited_once()


async def test_get_devolve_a_lista_efetiva():
    """A tela mostra o que o disparo aplica: o `*` legado não aparece como
    restrição (e a tela avisa "sem restrição")."""
    from app.api.routers import health_router

    gravada = ["*", "https://Hooks.Slack.com/x", "hooks.slack.com"]
    with patch.object(health_router, "_get_config", new=AsyncMock(return_value=gravada)):
        saida = await health_router.system_health(db=MagicMock())
    assert saida == {"webhook_whitelist": ["hooks.slack.com"]}

    with patch.object(health_router, "_get_config", new=AsyncMock(return_value=None)):
        assert await health_router.system_health(db=MagicMock()) == {"webhook_whitelist": []}


async def test_patch_recusa_curinga_sozinho_com_400():
    from app.api.routers import health_router

    with patch.object(health_router, "_set_config", new=AsyncMock()) as gravar:
        with pytest.raises(HTTPException) as exc:
            await health_router.update_webhook_whitelist(domains=["*"], db=MagicMock())
    assert exc.value.status_code == 400
    gravar.assert_not_awaited()


# ── Disparo ─────────────────────────────────────────────────────────────────


def _db(url: str, workspace_allowlist=None):
    """Duas consultas: a do workflow (`first`) e a do workspace (`scalar_one_or_none`)."""
    workflow = MagicMock()
    workflow.first.return_value = (url, "ws-1")
    workspace = MagicMock()
    workspace.scalar_one_or_none.return_value = workspace_allowlist
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[workflow, workspace])
    return db


async def _disparar(url: str, global_list, workspace_allowlist=None):
    run = SimpleNamespace(task_id="t1", workflow_hash="wf1", status="completed",
                          duration_seconds=1.0, error_message=None)
    with patch("app.core.system_config.get_config", new=AsyncMock(return_value=global_list)), \
         patch.object(rrc, "_schedule_webhook_notification") as agendar:
        await rrc._fire_notification_if_configured(_db(url, workspace_allowlist), run)
    return agendar


async def test_host_fora_da_whitelist_global_nao_recebe_o_webhook():
    agendar = await _disparar("https://coletor.atacante.exemplo/hook", ["hooks.slack.com"])
    agendar.assert_not_called()


async def test_host_na_whitelist_global_recebe():
    agendar = await _disparar("https://hooks.slack.com/services/x", ["hooks.slack.com"])
    agendar.assert_called_once()


async def test_whitelist_global_vazia_nao_restringe():
    agendar = await _disparar("https://qualquer.exemplo/hook", [])
    agendar.assert_called_once()


async def test_legado_so_com_curinga_nao_bloqueia_tudo():
    agendar = await _disparar("https://qualquer.exemplo/hook", ["*"])
    agendar.assert_called_once()


async def test_as_duas_listas_valem_juntas():
    """Na global mas fora da do workspace: bloqueado pela do workspace."""
    agendar = await _disparar(
        "https://hooks.slack.com/services/x", ["hooks.slack.com"], workspace_allowlist=["api.exemplo.com"],
    )
    agendar.assert_not_called()


@pytest.mark.parametrize("entrada", [
    "hooks.slack.com, api.exemplo.com", "a b.com", "exemplo.com;", ".x.com", "x..com",
])
def test_entrada_que_nunca_casaria_e_recusada(entrada):
    """Com a lista aplicada, uma entrada assim bloquearia TODO webhook sem explicar."""
    with pytest.raises(ValueError):
        validar_allowlist([entrada])


def test_linha_colada_com_varios_dominios_vira_varios_itens():
    assert padroes_validos(["hooks.slack.com, api.exemplo.com"]) == ["hooks.slack.com", "api.exemplo.com"]


async def test_patch_divide_a_linha_colada():
    from app.api.routers import health_router

    with patch.object(health_router, "_set_config", new=AsyncMock()):
        saida = await health_router.update_webhook_whitelist(
            domains=["hooks.slack.com; api.exemplo.com"], db=MagicMock(),
        )
    assert saida == {"webhook_whitelist": ["hooks.slack.com", "api.exemplo.com"]}
