# tests/unit/test_config_envs_legadas.py
"""O fallback das envs renomeadas pela F4 (COPILOTO_* -> ASSISTENTE_*).

Sem ele, um .env de servidor ainda com os nomes antigos reconfigurava o
assistente EM SILENCIO (ativo por default, modelo/idioma de fabrica) — achado
da revisao adversarial de 2026-09-24. O fallback e temporario; os avisos no
arranque sao o lembrete de migrar o .env.
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
    # O compose define a variavel como string vazia quando o .env nao a tem —
    # o mesmo motivo do `.strip() or` que o config ja usava.
    monkeypatch.setenv("T_NOVA", "   ")
    monkeypatch.setenv("T_LEGADA", "antigo")
    assert config._env_ou_legado("T_NOVA", "T_LEGADA") == "antigo"


def test_sem_nenhuma_devolve_vazio(monkeypatch):
    monkeypatch.delenv("T_NOVA", raising=False)
    monkeypatch.delenv("T_LEGADA", raising=False)
    assert config._env_ou_legado("T_NOVA", "T_LEGADA") == ""
