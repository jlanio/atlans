# tests/unit/test_base_zero.py
"""A base zero (F3 da simplificação): uma revisão, cujo corpo é o init_schema.

O que morre se qualquer um destes falhar:

- Mais de um arquivo em `alembic/versions/` significa que a cadeia voltou a
  crescer POR CIMA da base zero sem decisão — o caminho novo é editar o
  `init_schema.sql` (o corpo) enquanto nada está em produção, ou reabrir a
  discussão de migrações incrementais quando estiver.
- O filtro de `alembic_version` deixando passar um comando faz o upgrade
  duplicar o carimbo (o INSERT do arquivo + o do próprio alembic).
- O carimbo do script divergindo do `revision` faz psql e alembic produzirem
  bancos que discordam sobre a própria versão.

A convergência de CONTEÚDO (tabelas/colunas × models) segue com
`test_init_schema_bootstrap.py` — aqui é a mecânica da revisão única.
"""
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[2]
VERSOES = RAIZ / "alembic" / "versions"
SQL = (RAIZ / "scripts" / "init_schema.sql").read_text(encoding="utf-8")


def _base_zero():
    """Importa a migração pelo caminho — `alembic/` não é pacote."""
    (arquivo,) = [p for p in VERSOES.glob("*.py") if p.name != "__init__.py"]
    spec = importlib.util.spec_from_file_location("base_zero", arquivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ha_exatamente_uma_revisao():
    arquivos = [p.name for p in VERSOES.glob("*.py") if p.name != "__init__.py"]
    assert len(arquivos) == 1, f"a cadeia voltou a crescer: {sorted(arquivos)}"


def test_a_revisao_e_inicial():
    mod = _base_zero()
    assert mod.down_revision is None


def test_o_filtro_tira_todo_comando_sobre_alembic_version():
    mod = _base_zero()
    filtrado = mod._sql_sem_alembic_version(SQL)
    assert not re.search(
        r"^\s*(DROP|CREATE|INSERT)[^\n]*alembic_version", filtrado, re.M | re.I
    )
    # E só isso: o resto do script está lá inteiro.
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in filtrado
    assert "CREATE TABLE users" in filtrado
    assert "DROP TABLE IF EXISTS users CASCADE" in filtrado


def test_o_filtro_nao_engole_o_script_num_regex_guloso():
    """O `CREATE TABLE alembic_version (...)` é removido com re.S; um regex
    guloso comeria dali até o ÚLTIMO `);` do arquivo. As tabelas vizinhas
    (audit_events antes, o INSERT depois) têm de sobreviver.

    A contagem ancora em início de linha porque comentários também dizem
    «CREATE TABLE» — e o filtro remove comentários de propósito."""
    mod = _base_zero()
    filtrado = mod._sql_sem_alembic_version(SQL)
    assert "CREATE TABLE audit_events" in filtrado

    def comandos(texto):
        return len(re.findall(r"^CREATE TABLE ", texto, re.M))

    assert comandos(filtrado) == comandos(SQL) - 1


def test_o_carimbo_do_script_e_a_propria_revisao():
    carimbo = re.search(
        r"INSERT INTO alembic_version \(version_num\) VALUES \('(\w+)'\)", SQL
    )
    assert carimbo
    assert carimbo.group(1) == _base_zero().revision


def test_upgrade_recusa_banco_populado_sem_carimbo():
    """O único caminho destrutivo: tabelas presentes + alembic_version vazia é
    o único estado em que o alembic chega ao corpo da base zero com dados na
    frente — e o corpo é DROP ALL. A guarda tem de existir, consultar o banco
    (to_regclass) e apontar os dois remédios. Provado ao vivo na entrega da
    F3; aqui o texto prende a guarda contra remoção acidental."""
    (arquivo,) = [p for p in VERSOES.glob("*.py") if p.name != "__init__.py"]
    fonte = arquivo.read_text(encoding="utf-8")
    assert "to_regclass('public.users')" in fonte
    assert "APAGARIA" in fonte
    assert "stamp --purge 9ed006ca1660" in fonte
    # E a guarda não pode barrar a geração offline (--sql).
    assert "is_offline_mode" in fonte


def test_upgrade_roda_o_schema_de_cada_extensao_depois_do_nucleo(monkeypatch, tmp_path):
    """As tabelas de uma extensão (app/extensoes) moram no `schema.sql` dela: a
    base zero roda o script do núcleo e, depois, cada um — com o mesmo filtro.
    Sem extensão, só o do núcleo."""
    import app.extensoes

    esquema = tmp_path / "schema.sql"
    esquema.write_text("-- so comentario\nCREATE TABLE de_extensao (id INT);\n", encoding="utf-8")
    mod = _base_zero()
    executados: list[str] = []
    banco_vazio = SimpleNamespace(execute=lambda *_a, **_k: SimpleNamespace(scalar=lambda: False))
    monkeypatch.setattr(mod, "op", SimpleNamespace(execute=executados.append, get_bind=lambda: banco_vazio))
    monkeypatch.setattr(mod, "context", SimpleNamespace(is_offline_mode=lambda: False))

    monkeypatch.setattr(app.extensoes, "esquemas", lambda: [esquema])
    mod.upgrade()
    assert len(executados) == 2
    assert "CREATE TABLE users" in executados[0]
    assert executados[1].strip() == "CREATE TABLE de_extensao (id INT);"

    executados.clear()
    monkeypatch.setattr(app.extensoes, "esquemas", lambda: [])
    mod.upgrade()
    assert len(executados) == 1


def test_downgrade_recusa_com_o_caminho_certo():
    with pytest.raises(RuntimeError, match="init_schema"):
        _base_zero().downgrade()


def test_nenhum_resto_de_atlans_drop():
    """As flags ATLANS_DROP_* eram o opt-in de downgrade destrutivo das
    migrações antigas; morreram com elas. Uma menção executável que sobre é
    caminho de código morto voltando."""
    for arquivo in VERSOES.glob("*.py"):
        assert "ATLANS_DROP" not in arquivo.read_text(encoding="utf-8")


def test_guarda_tambem_no_offline():
    """O --sql é um script EXECUTÁVEL — e roda longe dos olhos do alembic.

    A guarda online (to_regclass) não existe na geração offline; sem o
    preâmbulo, o script gerado aplicado às cegas num banco populado sem carimbo
    fazia o DROP ALL sem uma única pergunta (achado da revisão adversarial de
    2026-09-24). Gerar continua sempre permitido; é a EXECUÇÃO que se recusa.
    """
    mod = _base_zero()
    assert "DO $guarda_base_zero$" in mod._GUARDA_OFFLINE
    assert "RAISE EXCEPTION" in mod._GUARDA_OFFLINE
    fonte = (VERSOES / [p.name for p in VERSOES.glob("*.py") if p.name != "__init__.py"][0]).read_text(
        encoding="utf-8"
    )
    assert re.search(r"if context\.is_offline_mode\(\):\s*\n\s*op\.execute\(_GUARDA_OFFLINE\)", fonte), (
        "o modo offline precisa emitir a guarda como preâmbulo do script"
    )


def test_dockerfile_leva_o_corpo_da_migracao():
    """A migração lê scripts/init_schema.sql EM RUNTIME (`_RAIZ / "scripts"`).

    Sem a cópia no Dockerfile.api o corpo fica FORA da imagem: qualquer
    `alembic upgrade head` em produção — banco novo, ou um deploy que aplique
    as migrações sozinho num banco vazio — morre em FileNotFoundError antes
    de criar o schema. Em produção carimbada ninguém percebe, porque o upgrade
    nunca roda (achado da revisão adversarial de 2026-09-24).
    """
    dockerfile = (RAIZ / "Dockerfile.api").read_text(encoding="utf-8")
    assert re.search(
        r"(?m)^COPY\s+scripts/init_schema\.sql\s+\./scripts/init_schema\.sql\s*$", dockerfile
    ), "Dockerfile.api precisa copiar scripts/init_schema.sql — o corpo da base zero é lido em runtime"
