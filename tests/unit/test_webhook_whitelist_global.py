"""The global webhook whitelist (admin → Configurações) now applies at trigger time.

It was saved and displayed — the screen warned when it was empty —, but no
trigger consulted it: the restriction the admin configured restricted nothing.
Empty still means no restriction; with items, the host must be in it AND in the
workspace's allowlist.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core import run_result_consumer as rrc
from app.core.utils.allowlist import normalize_domain, valid_patterns, validate_allowlist


# ── Normalization and validation ─────────────────────────────────────────────


@pytest.mark.parametrize("entrada, esperado", [
    ("https://Hooks.Slack.com/services/T000/B000", "hooks.slack.com"),
    ("http://exemplo.com:8443/", "exemplo.com"),
    ("  *.Interno.Corp ", "*.interno.corp"),
    ("exemplo.com", "exemplo.com"),
])
def test_normalize_domain_keeps_only_the_host(entrada, esperado):
    assert normalize_domain(entrada) == esperado


@pytest.mark.parametrize("entrada", ["*", "localhost", "*.com", "*exemplo.com"])
def test_validate_refuses_what_the_matcher_would_ignore(entrada):
    with pytest.raises(ValueError):
        validate_allowlist([entrada])


def test_valid_patterns_discards_the_legacy_that_never_matched():
    """A `*` saved earlier (to "allow everything") must not start blocking everything."""
    assert valid_patterns(["*", "https://hooks.slack.com/x", "localhost", "hooks.slack.com"]) == [
        "hooks.slack.com",
    ]
    assert valid_patterns(["*"]) == []


# ── Admin PATCH ─────────────────────────────────────────────────────────────


async def test_patch_stores_the_host_of_the_pasted_url():
    from app.api.routers import health_router

    with patch.object(health_router, "_set_config", new=AsyncMock()) as gravar:
        saida = await health_router.update_webhook_whitelist(
            domains=["https://Hooks.Slack.com/services/x", "hooks.slack.com", ""], db=MagicMock(),
        )
    assert saida == {"webhook_whitelist": ["hooks.slack.com"]}
    gravar.assert_awaited_once()


async def test_get_returns_the_effective_list():
    """The screen shows what the trigger applies: the legacy `*` does not show up
    as a restriction (and the screen warns "sem restrição" (no restriction))."""
    from app.api.routers import health_router

    gravada = ["*", "https://Hooks.Slack.com/x", "hooks.slack.com"]
    with patch.object(health_router, "_get_config", new=AsyncMock(return_value=gravada)):
        saida = await health_router.system_health(db=MagicMock())
    assert saida == {"webhook_whitelist": ["hooks.slack.com"]}

    with patch.object(health_router, "_get_config", new=AsyncMock(return_value=None)):
        assert await health_router.system_health(db=MagicMock()) == {"webhook_whitelist": []}


async def test_patch_refuses_lone_wildcard_with_400():
    from app.api.routers import health_router

    with patch.object(health_router, "_set_config", new=AsyncMock()) as gravar:
        with pytest.raises(HTTPException) as exc:
            await health_router.update_webhook_whitelist(domains=["*"], db=MagicMock())
    assert exc.value.status_code == 400
    gravar.assert_not_awaited()


# ── Disparo ─────────────────────────────────────────────────────────────────


def _db(url: str, workspace_allowlist=None):
    """Two queries: the workflow's (`first`) and the workspace's (`scalar_one_or_none`)."""
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


async def test_host_outside_the_global_whitelist_does_not_receive_the_webhook():
    agendar = await _disparar("https://coletor.atacante.exemplo/hook", ["hooks.slack.com"])
    agendar.assert_not_called()


async def test_host_in_the_global_whitelist_receives():
    agendar = await _disparar("https://hooks.slack.com/services/x", ["hooks.slack.com"])
    agendar.assert_called_once()


async def test_empty_global_whitelist_does_not_restrict():
    agendar = await _disparar("https://qualquer.exemplo/hook", [])
    agendar.assert_called_once()


async def test_legacy_with_only_wildcard_does_not_block_everything():
    agendar = await _disparar("https://qualquer.exemplo/hook", ["*"])
    agendar.assert_called_once()


async def test_both_lists_apply_together():
    """In the global list but not in the workspace's: blocked by the workspace's."""
    agendar = await _disparar(
        "https://hooks.slack.com/services/x", ["hooks.slack.com"], workspace_allowlist=["api.exemplo.com"],
    )
    agendar.assert_not_called()


@pytest.mark.parametrize("entrada", [
    "hooks.slack.com, api.exemplo.com", "a b.com", "exemplo.com;", ".x.com", "x..com",
])
def test_entry_that_would_never_match_is_refused(entrada):
    """With the list enforced, an entry like this would block EVERY webhook without explanation."""
    with pytest.raises(ValueError):
        validate_allowlist([entrada])


def test_pasted_line_with_several_domains_becomes_several_items():
    assert valid_patterns(["hooks.slack.com, api.exemplo.com"]) == ["hooks.slack.com", "api.exemplo.com"]


async def test_patch_splits_the_pasted_line():
    from app.api.routers import health_router

    with patch.object(health_router, "_set_config", new=AsyncMock()):
        saida = await health_router.update_webhook_whitelist(
            domains=["hooks.slack.com; api.exemplo.com"], db=MagicMock(),
        )
    assert saida == {"webhook_whitelist": ["hooks.slack.com", "api.exemplo.com"]}
