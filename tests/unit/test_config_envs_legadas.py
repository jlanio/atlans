# tests/unit/test_config_envs_legadas.py
"""The fallback for the envs renamed by F4 (COPILOTO_* -> ASSISTENTE_*).

Without it, a server .env still using the old names reconfigured the assistant
SILENTLY (enabled by default, factory model/language) — a finding of the
2026-09-24 adversarial review. The fallback is temporary; the warnings at
startup are the reminder to migrate the .env.
"""
import logging

from app.core import config


def test_nova_vence_e_avisa_que_a_legada_sobrou(monkeypatch, caplog):
    monkeypatch.setenv("T_NOVA", "das-novas")
    monkeypatch.setenv("T_LEGADA", "das-antigas")
    with caplog.at_level(logging.WARNING, logger="atlans.config"):
        assert config._env_ou_legado("T_NOVA", "T_LEGADA") == "das-novas"
    assert "ignorada" in caplog.text and "T_LEGADA" in caplog.text


def test_legada_cai_no_fallback_com_aviso(monkeypatch, caplog):
    monkeypatch.delenv("T_NOVA", raising=False)
    monkeypatch.setenv("T_LEGADA", "valor-antigo")
    with caplog.at_level(logging.WARNING, logger="atlans.config"):
        assert config._env_ou_legado("T_NOVA", "T_LEGADA") == "valor-antigo"
    assert "LEGADO" in caplog.text and "T_NOVA" in caplog.text


def test_vazia_conta_como_ausente(monkeypatch):
    # Compose defines the variable as an empty string when the .env lacks it —
    # the same reason for the `.strip() or` that the config already used.
    monkeypatch.setenv("T_NOVA", "   ")
    monkeypatch.setenv("T_LEGADA", "antigo")
    assert config._env_ou_legado("T_NOVA", "T_LEGADA") == "antigo"


def test_sem_nenhuma_devolve_vazio(monkeypatch):
    monkeypatch.delenv("T_NOVA", raising=False)
    monkeypatch.delenv("T_LEGADA", raising=False)
    assert config._env_ou_legado("T_NOVA", "T_LEGADA") == ""
