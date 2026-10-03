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
def pasta_de_extensoes(tmp_path, monkeypatch):
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


def _extensao(pasta: Path, nome: str, init: str, arquivos: dict[str, str] | None = None) -> None:
    pacote = pasta / nome
    pacote.mkdir()
    (pacote / "__init__.py").write_text(textwrap.dedent(init))
    for caminho, codigo in (arquivos or {}).items():
        alvo = pacote / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(textwrap.dedent(codigo))


REGISTRA_TUDO = """
    async def plano_e_teto(user_id, *, db=None, redis=None):
        return "ouro", 7

    def registrar(registro):
        registro.rotas.append("rota")
        registro.tarefas_de_fundo.append(("tarefa", lambda: None))
        registro.plano_e_teto = plano_e_teto
        registro.assinaturas_ativas = lambda: True
"""


# ── DESCOBERTA ───────────────────────────────────────────────────────────────

def test_cada_subpacote_e_uma_extensao(pasta_de_extensoes):
    _extensao(pasta_de_extensoes, "ouro", REGISTRA_TUDO)
    _extensao(pasta_de_extensoes, "prata", "def registrar(registro):\n    registro.rotas.append('prata')\n")

    r = extensoes.registro()

    assert r.nomes == ["ouro", "prata"]
    assert r.rotas == ["rota", "prata"]
    assert r.assinaturas_ativas() is True
    assert extensoes.registro() is r, "montado uma vez só"


def test_subpacote_com_sublinhado_e_arquivo_solto_nao_sao_extensao(pasta_de_extensoes):
    _extensao(pasta_de_extensoes, "_rascunho", "raise RuntimeError('não devia importar')\n")
    (pasta_de_extensoes / "solto.py").write_text("raise RuntimeError('não devia importar')\n")

    assert extensoes.registro().nomes == []


def test_sem_extensao_os_padroes_do_nucleo(pasta_de_extensoes):
    r = extensoes.registro()
    assert (r.rotas, r.tarefas_de_fundo, r.templates, r.painel_do_modelo) == ([], [], [], [])
    assert r.plano_e_teto is None
    assert r.assinaturas_ativas() is False


# ── DESLIGADAS ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valor, desligadas", [
    ("1", True), ("true", True), ("sim", True), (" ON ", True),
    ("", False), ("0", False), ("false", False),
])
def test_atlans_sem_extensoes(pasta_de_extensoes, monkeypatch, valor, desligadas):
    _extensao(pasta_de_extensoes, "ouro", REGISTRA_TUDO)
    monkeypatch.setenv("ATLANS_SEM_EXTENSOES", valor)

    assert extensoes.desligadas() is desligadas
    assert extensoes.registro().nomes == ([] if desligadas else ["ouro"])


# ── ERROS ────────────────────────────────────────────────────────────────────

def test_extensao_sem_registrar_derruba_o_arranque(pasta_de_extensoes):
    _extensao(pasta_de_extensoes, "torta", "VALOR = 1\n")
    with pytest.raises(RuntimeError, match="'torta' não tem registrar"):
        extensoes.registro()


def test_extensao_que_nao_importa_derruba_o_arranque(pasta_de_extensoes):
    """Silently disappearing along with billing would be worse than not starting."""
    _extensao(pasta_de_extensoes, "quebrada", "import modulo_que_nao_existe\n")
    with pytest.raises(ModuleNotFoundError):
        extensoes.registro()


# ── MODELOS ──────────────────────────────────────────────────────────────────

def test_importar_modelos_importa_o_de_cada_extensao(pasta_de_extensoes):
    _extensao(pasta_de_extensoes, "ouro", REGISTRA_TUDO, {"modelos/__init__.py": "CARREGADO = True\n"})
    _extensao(pasta_de_extensoes, "sem_tabelas", "def registrar(registro):\n    pass\n")

    extensoes.importar_modelos()

    assert sys.modules[f"{extensoes.__name__}.ouro.modelos"].CARREGADO is True


def test_modelos_que_nao_importam_nao_somem_em_silencio(pasta_de_extensoes):
    """Only the absence of its OWN `modelos` is normal; a broken import inside it
    is an error."""
    _extensao(pasta_de_extensoes, "ouro", REGISTRA_TUDO, {"modelos/__init__.py": "import tabela_que_falta\n"})
    with pytest.raises(ModuleNotFoundError, match="tabela_que_falta"):
        extensoes.importar_modelos()


def test_o_schema_de_cada_extensao_vai_para_a_base_zero(pasta_de_extensoes, monkeypatch):
    """An extension's tables live in its `schema.sql`, which the alembic zero
    baseline runs after the core script — without importing the extension."""
    _extensao(pasta_de_extensoes, "ouro", "raise RuntimeError('não é para importar')\n",
              {"schema.sql": "CREATE TABLE ouro (id INT);\n"})
    _extensao(pasta_de_extensoes, "prata", "def registrar(registro):\n    pass\n")

    assert extensoes.esquemas() == [pasta_de_extensoes / "ouro" / "schema.sql"]

    monkeypatch.setenv("ATLANS_SEM_EXTENSOES", "1")
    assert extensoes.esquemas() == []


# ── CORE ─────────────────────────────────────────────────────────────────────

async def test_sem_extensao_o_teto_e_o_da_instalacao(registro_de_teste):
    from app.mcp import cotas
    from app.services import teto_do_assistente

    assert await teto_do_assistente.plano_e_teto("usr-1") == (None, cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA)
    assert await teto_do_assistente.teto_de("usr-1") == cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    assert teto_do_assistente.assinaturas_ativas() is False


async def test_com_extensao_quem_responde_e_ela(registro_de_teste):
    from app.services import teto_do_assistente

    vistos = []

    async def plano_e_teto(user_id, *, db=None, redis=None):
        vistos.append((user_id, db, redis))
        return "ouro", 7

    registro_de_teste.plano_e_teto = plano_e_teto
    assert await teto_do_assistente.plano_e_teto("usr-1", db="sessao", redis="pool") == ("ouro", 7)
    assert await teto_do_assistente.teto_de("usr-2") == 7
    assert vistos == [("usr-1", "sessao", "pool"), ("usr-2", None, None)]


def test_os_emails_do_nucleo_nao_veem_os_das_extensoes(registro_de_teste, monkeypatch, tmp_path):
    """The extensions' e-mail template folders go in AFTER the core's."""
    from jinja2 import TemplateNotFound

    from app.services import email_service

    (tmp_path / "so_da_extensao.html").write_text("<p>{{ nome }}</p>")
    monkeypatch.setattr(email_service, "_template_env", None)
    assert email_service._ambiente().get_template("verify_email.html")
    with pytest.raises(TemplateNotFound):
        email_service._ambiente().get_template("so_da_extensao.html")

    monkeypatch.setattr(email_service, "_template_env", None)
    registro_de_teste.templates.append(tmp_path)
    assert email_service._ambiente().get_template("so_da_extensao.html").render(nome="Ana") == "<p>Ana</p>"


# ── TETO ─────────────────────────────────────────────────────────────────────

def _teto_com(valor: str | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "ASSISTENTE_TETO_DE_TOKENS_POR_DIA"}
    if valor is not None:
        env["ASSISTENTE_TETO_DE_TOKENS_POR_DIA"] = valor
    return subprocess.run(
        [sys.executable, "-c", "from app.mcp import cotas; print(cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA)"],
        cwd=RAIZ, env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("valor, teto", [(None, "1500000"), ("", "1500000"), ("2000000", "2000000"), (" 250_000 ", "250000")])
def test_o_teto_da_instalacao_vem_do_ambiente(valor, teto):
    r = _teto_com(valor)
    assert r.returncode == 0, r.stderr[-1500:]
    assert r.stdout.strip() == teto


@pytest.mark.parametrize("valor", ["0", "-5", "muito"])
def test_teto_que_nao_e_positivo_impede_a_api_de_subir(valor):
    """Zero would lock every conversation after the first turn, without warning."""
    r = _teto_com(valor)
    assert r.returncode != 0
    assert "ASSISTENTE_TETO_DE_TOKENS_POR_DIA" in r.stderr
