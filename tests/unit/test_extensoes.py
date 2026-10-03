# tests/unit/test_extensoes.py
"""
Extensions: what an installation has beyond the core (`app/extensoes`).

The core never imports an extension by name. Each subpackage is discovered,
imported and called in `registrar(registro)`; with none, each extension point
has a default. Here the extensions are fake, in a temporary folder — the tests
hold just the same in the free distribution, which ships no extension at all.

  DISCOVERY    subpackages of app/extensoes, except those starting with _
  DISABLED     ATLANS_SEM_EXTENSOES ignores the ones present
  ERRORS       an extension without registrar, or that fails to import, aborts startup
  MODELS       <extensão>/modelos goes into the metadata; its absence does not; and
               <extensão>/schema.sql goes into the alembic zero baseline
  CORE         no extension: no plan, the installation ceiling, nothing to sell
  CEILING      ASSISTENTE_TETO_DE_TOKENS_POR_DIA, positive
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from app import extensoes

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def extensions_folder(tmp_path, monkeypatch):
    """`app.extensoes` looking at a temporary folder, with the registry cleared
    before and after — and without leaving fake modules in `sys.modules`."""
    monkeypatch.setattr(extensoes, "__path__", [str(tmp_path)])
    monkeypatch.setattr(extensoes, "_registro", None)
    monkeypatch.delenv("ATLANS_SEM_EXTENSOES", raising=False)
    antes = set(sys.modules)
    yield tmp_path
    for nome in set(sys.modules) - antes:
        if nome.startswith("app.extensoes."):
            del sys.modules[nome]


def _extension(pasta: Path, nome: str, init: str, arquivos: dict[str, str] | None = None) -> None:
    pacote = pasta / nome
    pacote.mkdir()
    (pacote / "__init__.py").write_text(textwrap.dedent(init))
    for caminho, codigo in (arquivos or {}).items():
        alvo = pacote / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(textwrap.dedent(codigo))


REGISTERS_EVERYTHING = """
    async def plano_e_teto(user_id, *, db=None, redis=None):
        return "ouro", 7

    def registrar(registro):
        registro.rotas.append("rota")
        registro.tarefas_de_fundo.append(("tarefa", lambda: None))
        registro.plano_e_teto = plano_e_teto
        registro.assinaturas_ativas = lambda: True
"""


# ── DESCOBERTA ───────────────────────────────────────────────────────────────

def test_each_subpackage_is_an_extension(extensions_folder):
    _extension(extensions_folder, "ouro", REGISTERS_EVERYTHING)
    _extension(extensions_folder, "prata", "def registrar(registro):\n    registro.rotas.append('prata')\n")

    r = extensoes.registro()

    assert r.nomes == ["ouro", "prata"]
    assert r.rotas == ["rota", "prata"]
    assert r.assinaturas_ativas() is True
    assert extensoes.registro() is r, "montado uma vez só"


def test_underscored_subpackage_and_loose_file_are_not_extensions(extensions_folder):
    _extension(extensions_folder, "_rascunho", "raise RuntimeError('não devia importar')\n")
    (extensions_folder / "solto.py").write_text("raise RuntimeError('não devia importar')\n")

    assert extensoes.registro().nomes == []


def test_without_extension_the_core_defaults(extensions_folder):
    r = extensoes.registro()
    assert (r.rotas, r.tarefas_de_fundo, r.templates, r.painel_do_modelo) == ([], [], [], [])
    assert r.plano_e_teto is None
    assert r.assinaturas_ativas() is False


# ── DESLIGADAS ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valor, desligadas", [
    ("1", True), ("true", True), ("sim", True), (" ON ", True),
    ("", False), ("0", False), ("false", False),
])
def test_atlans_without_extensions(extensions_folder, monkeypatch, valor, desligadas):
    _extension(extensions_folder, "ouro", REGISTERS_EVERYTHING)
    monkeypatch.setenv("ATLANS_SEM_EXTENSOES", valor)

    assert extensoes.desligadas() is desligadas
    assert extensoes.registro().nomes == ([] if desligadas else ["ouro"])


# ── ERRORS ────────────────────────────────────────────────────────────────────

def test_extension_without_register_breaks_startup(extensions_folder):
    _extension(extensions_folder, "torta", "VALOR = 1\n")
    with pytest.raises(RuntimeError, match="'torta' não tem registrar"):
        extensoes.registro()


def test_extension_that_fails_to_import_breaks_startup(extensions_folder):
    """Silently disappearing along with billing would be worse than not starting."""
    _extension(extensions_folder, "quebrada", "import modulo_que_nao_existe\n")
    with pytest.raises(ModuleNotFoundError):
        extensoes.registro()


# ── MODELOS ──────────────────────────────────────────────────────────────────

def test_import_models_imports_each_extensions_models(extensions_folder):
    _extension(extensions_folder, "ouro", REGISTERS_EVERYTHING, {"modelos/__init__.py": "CARREGADO = True\n"})
    _extension(extensions_folder, "sem_tabelas", "def registrar(registro):\n    pass\n")

    extensoes.importar_modelos()

    assert sys.modules[f"{extensoes.__name__}.ouro.modelos"].CARREGADO is True


def test_models_that_fail_to_import_do_not_vanish_silently(extensions_folder):
    """Only the absence of its OWN `modelos` is normal; a broken import inside it
    is an error."""
    _extension(extensions_folder, "ouro", REGISTERS_EVERYTHING, {"modelos/__init__.py": "import tabela_que_falta\n"})
    with pytest.raises(ModuleNotFoundError, match="tabela_que_falta"):
        extensoes.importar_modelos()


def test_each_extensions_schema_goes_to_the_base_zero(extensions_folder, monkeypatch):
    """An extension's tables live in its `schema.sql`, which the alembic zero
    baseline runs after the core script — without importing the extension."""
    _extension(extensions_folder, "ouro", "raise RuntimeError('não é para importar')\n",
              {"schema.sql": "CREATE TABLE ouro (id INT);\n"})
    _extension(extensions_folder, "prata", "def registrar(registro):\n    pass\n")

    assert extensoes.esquemas() == [extensions_folder / "ouro" / "schema.sql"]

    monkeypatch.setenv("ATLANS_SEM_EXTENSOES", "1")
    assert extensoes.esquemas() == []


# ── CORE ─────────────────────────────────────────────────────────────────────

async def test_without_extension_the_ceiling_is_the_installations(empty_registry):
    from app.mcp import cotas
    from app.services import teto_do_assistente

    assert await teto_do_assistente.plano_e_teto("usr-1") == (None, cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA)
    assert await teto_do_assistente.teto_de("usr-1") == cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    assert teto_do_assistente.assinaturas_ativas() is False


async def test_with_extension_it_is_the_one_that_answers(empty_registry):
    from app.services import teto_do_assistente

    vistos = []

    async def plano_e_teto(user_id, *, db=None, redis=None):
        vistos.append((user_id, db, redis))
        return "ouro", 7

    empty_registry.plano_e_teto = plano_e_teto
    assert await teto_do_assistente.plano_e_teto("usr-1", db="sessao", redis="pool") == ("ouro", 7)
    assert await teto_do_assistente.teto_de("usr-2") == 7
    assert vistos == [("usr-1", "sessao", "pool"), ("usr-2", None, None)]


def test_core_emails_do_not_see_the_extensions_ones(empty_registry, monkeypatch, tmp_path):
    """The extensions' e-mail template folders go in AFTER the core's."""
    from jinja2 import TemplateNotFound

    from app.services import email_service

    (tmp_path / "so_da_extensao.html").write_text("<p>{{ nome }}</p>")
    monkeypatch.setattr(email_service, "_template_env", None)
    assert email_service._ambiente().get_template("verify_email.html")
    with pytest.raises(TemplateNotFound):
        email_service._ambiente().get_template("so_da_extensao.html")

    monkeypatch.setattr(email_service, "_template_env", None)
    empty_registry.templates.append(tmp_path)
    assert email_service._ambiente().get_template("so_da_extensao.html").render(nome="Ana") == "<p>Ana</p>"


# ── TETO ─────────────────────────────────────────────────────────────────────

def _ceiling_with(valor: str | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "ASSISTENTE_TETO_DE_TOKENS_POR_DIA"}
    if valor is not None:
        env["ASSISTENTE_TETO_DE_TOKENS_POR_DIA"] = valor
    return subprocess.run(
        [sys.executable, "-c", "from app.mcp import cotas; print(cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA)"],
        cwd=RAIZ, env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("valor, teto", [(None, "1500000"), ("", "1500000"), ("2000000", "2000000"), (" 250_000 ", "250000")])
def test_the_installation_ceiling_comes_from_the_environment(valor, teto):
    r = _ceiling_with(valor)
    assert r.returncode == 0, r.stderr[-1500:]
    assert r.stdout.strip() == teto


@pytest.mark.parametrize("valor", ["0", "-5", "muito"])
def test_non_positive_ceiling_prevents_the_api_from_starting(valor):
    """Zero would lock every conversation after the first turn, without warning."""
    r = _ceiling_with(valor)
    assert r.returncode != 0
    assert "ASSISTENTE_TETO_DE_TOKENS_POR_DIA" in r.stderr
