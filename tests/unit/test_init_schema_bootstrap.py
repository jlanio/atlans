# tests/unit/test_init_schema_bootstrap.py
"""`scripts/init_schema.sql` tem de ser "DROP ALL + CREATE ALL" de verdade.

O script carimba `alembic_version` na head, entao `alembic upgrade head` nunca
mais executa nada num banco criado por ele: tudo o que faltar aqui fica faltando
para sempre, sem correcao possivel via alembic. Foi assim que
`user_executor_assignments` sumiu (500 na primeira atribuicao de executor) e que
`audit_events` nasceu sem tabela.

E o inverso tambem quebra: uma tabela no CREATE mas fora do bloco de DROP faz o
reset de um banco existente abortar no meio (com ON_ERROR_STOP, depois de tudo
ja ter sido dropado) ou preservar silenciosamente os dados antigos.

As tabelas de uma extensao (`app/extensoes`) moram no `schema.sql` dela, que a
base zero roda depois do script do nucleo: o banco e a soma dos dois, e e a
soma que se compara com os models. Sem a extensao, nem o model nem o SQL dela
estao aqui, e o nucleo tem de fechar sozinho.
"""
import importlib
import pkgutil
import re
from pathlib import Path

import pytest

import app.models
from app.extensoes import esquemas
from app.models.base import Base

# `app.models.__init__` importa so parte dos modulos; para comparar com o script
# o metadata precisa estar COMPLETO — senao o teste passa justamente quando um
# model novo foi esquecido, que e o caso que ele existe para pegar.
for _mod in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{_mod.name}")

RAIZ = Path(__file__).resolve().parents[2]
SQL_DO_NUCLEO = (RAIZ / "scripts" / "init_schema.sql").read_text(encoding="utf-8")
SQL_DAS_EXTENSOES = [p.read_text(encoding="utf-8") for p in esquemas()]
SQL = "\n".join([SQL_DO_NUCLEO, *SQL_DAS_EXTENSOES])

# `alembic_version` e criada pelo script mas nao e um model.
_SO_DO_SCRIPT = {"alembic_version"}

_CRIADAS = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", SQL))
_DROPADAS = set(re.findall(r"DROP TABLE IF EXISTS (\w+) CASCADE", SQL))
_TABELAS_DOS_MODELS = set(Base.metadata.tables)

# Palavras que abrem uma restricao, nao uma coluna, dentro do CREATE TABLE.
_NAO_E_COLUNA = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "EXCLUDE", "LIKE"}


def _colunas_do_script() -> dict:
    """Colunas declaradas em cada `CREATE TABLE` do script.

    Comparar so NOMES DE TABELA deixa passar o caso mais comum de divergencia
    entre os tres caminhos de bootstrap: uma COLUNA nova. `workflows.origem`
    entrou por migracao e por model; se tivesse ficado de fora do script, um
    banco criado por ele nasceria sem a coluna — e, como o script ja carimba a
    head do alembic, nenhum `upgrade` posterior a criaria.
    """
    blocos = re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\((.*?)\n\);", SQL, re.S)
    fora = {}
    for nome, corpo in blocos:
        colunas = set()
        for linha in corpo.splitlines():
            linha = re.sub(r"--.*$", "", linha).strip()
            if not linha:
                continue
            token = linha.split()[0].strip('",').strip('"')
            if not re.fullmatch(r"\w+", token or "") or token.upper() in _NAO_E_COLUNA:
                continue
            colunas.add(token.lower())
        fora[nome] = colunas
    return fora


_COLUNAS_DO_SCRIPT = _colunas_do_script()


def test_todo_model_tem_create_no_script():
    assert not (_TABELAS_DOS_MODELS - _CRIADAS)


def test_toda_tabela_criada_tem_o_drop_correspondente():
    assert not (_CRIADAS - _DROPADAS)


def test_o_script_nao_cria_tabela_que_nao_e_de_nenhum_model():
    assert not (_CRIADAS - _TABELAS_DOS_MODELS - _SO_DO_SCRIPT)


def _criadas(sql: str) -> set[str]:
    return set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", sql))


# As tabelas dos models que moram numa extensão.
_TABELAS_DE_EXTENSAO = {
    m.local_table.name for m in Base.registry.mappers
    if m.class_.__module__.startswith("app.extensoes.")
}


def test_tabela_de_extensao_nao_mora_no_script_do_nucleo():
    """Sem a extensão (a distribuição livre), uma tabela dela no script do núcleo
    seria uma tabela sem model, criada em toda instalação. Ela mora no
    `schema.sql` da extensão, com o DROP junto."""
    assert not (_criadas(SQL_DO_NUCLEO) & _TABELAS_DE_EXTENSAO)
    das_extensoes = set().union(set(), *(_criadas(sql) for sql in SQL_DAS_EXTENSOES))
    assert _TABELAS_DE_EXTENSAO <= das_extensoes


@pytest.mark.parametrize(
    "tabela",
    ["user_executor_assignments", "audit_events", "executor_enrollment_otp"],
)
def test_tabelas_que_ja_faltaram(tabela):
    """Regressoes nominais: as tres que ja quebraram um bootstrap."""
    assert tabela in _CRIADAS and tabela in _DROPADAS


def test_toda_coluna_de_model_existe_no_script():
    """O buraco que o teste por NOME DE TABELA nao via: coluna nova no model e
    na migracao, mas esquecida no script — banco novo nasce sem ela, para sempre."""
    faltando = {}
    for tabela, obj in Base.metadata.tables.items():
        no_script = _COLUNAS_DO_SCRIPT.get(tabela)
        if no_script is None:
            continue  # ausencia da TABELA ja e coberta por outro teste
        ausentes = {c.name.lower() for c in obj.columns} - no_script
        if ausentes:
            faltando[tabela] = sorted(ausentes)
    assert not faltando, f"colunas no model e fora do init_schema.sql: {faltando}"


@pytest.mark.parametrize(
    ("tabela", "coluna"),
    [("workflows", "origem"), ("users", "agent_quota"), ("workflow_runs", "trigger_source")],
)
def test_colunas_que_o_teste_por_nome_deixava_passar(tabela, coluna):
    """Regressoes nominais de COLUNA — o analogo do teste de tabelas acima."""
    assert coluna in _COLUNAS_DO_SCRIPT[tabela]


def test_nenhum_indice_aponta_para_tabela_inexistente():
    """`ix_otp_unused` era criado sobre `agent_enrollment_otp`, nome anterior ao
    rename de 20260716_0001 — o script inteiro estourava na secao 2."""
    alvos = set(re.findall(r"CREATE (?:UNIQUE )?INDEX \w+ ON (\w+)", SQL))
    assert not (alvos - _CRIADAS)


def test_carimbo_do_alembic_e_a_head_real():
    """Um carimbo posterior ao conteudo do script e exatamente o bug que ele ja
    teve: alembic considera aplicado o que nunca rodou."""
    carimbo = re.search(r"INSERT INTO alembic_version \(version_num\) VALUES \('(\w+)'\)", SQL)
    assert carimbo

    versoes = RAIZ / "alembic" / "versions"
    revisoes, down = set(), set()
    for arquivo in versoes.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        # A anotacao de tipo varia entre migracoes (`: str`, `: Union[str, None]`,
        # nenhuma); casar so `: str` deixava quase todo `down_revision` de fora,
        # e "heads" virava o conjunto de TODAS as revisoes — qualquer carimbo
        # antigo passava.
        for m in re.finditer(r'^revision(?::[^=\n]+)?\s*=\s*"(\w+)"', texto, re.M):
            revisoes.add(m.group(1))
        for m in re.finditer(r'^down_revision(?::[^=\n]+)?\s*=\s*"(\w+)"', texto, re.M):
            down.add(m.group(1))

    heads = revisoes - down
    assert len(heads) == 1, f"a cadeia de migracoes tem mais de uma head: {sorted(heads)}"
    assert carimbo.group(1) in heads


def test_system_config_updated_at_e_not_null():
    """O squash perdeu o NOT NULL que a cadeia antiga criava — e o model exige.

    `docs`/a própria migração prometem "o mesmo DDL que a cadeia produzia"; um
    banco novo nascia com `system_config.updated_at` anulável enquanto o model
    declara `nullable=False`. Regressão da revisão adversarial de 2026-09-24 —
    presa aqui coluna a coluna até a convergência de NULABILIDADE inteira valer.
    """
    import re as _re

    bloco = _re.search(r"CREATE TABLE system_config \((.*?)\);", SQL, _re.S)
    assert bloco, "CREATE TABLE system_config sumiu do init_schema.sql"
    assert _re.search(r"updated_at\s+TIMESTAMP\s+DEFAULT\s+now\(\)\s+NOT\s+NULL", bloco.group(1)), (
        "system_config.updated_at precisa de NOT NULL (o model tem nullable=False)"
    )
