"""Base zero: o banco nasce pronto.

Colapsa a cadeia de 53 migracoes numa revisao inicial unica (F3 da
simplificacao — docs/specs/simplification.md, A9/N3; premissa dada pelo dono:
nada esta em producao de verdade, nao ha banco legado a preservar).

O corpo NAO mora aqui: e o proprio `scripts/init_schema.sql`, lido e executado
na hora. E o mesmo arquivo que os testes de convergencia ja prendem aos models
(tests/unit/test_init_schema_bootstrap.py), entao alembic, psql e testes
enxergam UMA fonte de verdade — a divergencia entre "o que a cadeia constroi"
e "o que o script constroi", que a convergencia vigiava, deixa de poder
existir. Depois dele vem o `schema.sql` de cada extensao presente
(`app/extensoes`, ver `esquemas()`): as tabelas que so existem com ela.

O filtro tira do script, antes de executar, apenas os comandos sobre
`alembic_version` (DROP/CREATE/INSERT): dentro do alembic quem gerencia essa
tabela e o proprio alembic; o INSERT do arquivo existe para o caminho psql e
aqui viraria linha duplicada. Os DROPs das tabelas de aplicacao FICAM — num
banco vazio sao no-op, e e o que mantem o texto identico ao do reset manual.

Banco EXISTENTE (carimbado numa revisao da cadeia antiga): o schema nao muda —
o squash produz o mesmo DDL que a cadeia produzia. Rode uma vez:

    alembic stamp --purge 9ed006ca1660

ou resete do zero com `psql -f scripts/init_schema.sql` (o proprio script
carimba esta revisao).
"""
import re
from pathlib import Path

import sqlalchemy as sa
from alembic import context, op

revision = "9ed006ca1660"  # pragma: allowlist secret
down_revision = None
branch_labels = None
depends_on = None

_RAIZ = Path(__file__).resolve().parents[2]


def _sql_sem_alembic_version(sql: str) -> str:
    """O script pronto para o `op.execute`.

    Dois cortes, nenhum deles mudando o efeito num banco vazio:
    - os comandos sobre `alembic_version` (motivo no docstring do modulo);
    - as linhas que sao SO comentario: `op.execute` passa o texto por
      `sqlalchemy.text()`, que le `:palavra` como bind — e a secao comentada
      de GRANTs usa `:app_user` como variavel do psql. Sem este corte, o
      upgrade falha pedindo valor para um parametro que so existe num
      comentario. No caminho psql o arquivo segue integro, comentarios e tudo.
    """
    sql = re.sub(r"^DROP TABLE IF EXISTS alembic_version CASCADE;[^\n]*$", "", sql, flags=re.M)
    sql = re.sub(r"^CREATE TABLE alembic_version \(.*?\);[^\n]*$", "", sql, flags=re.M | re.S)
    sql = re.sub(r"^INSERT INTO alembic_version[^\n]*$", "", sql, flags=re.M)
    sql = re.sub(r"^\s*--[^\n]*$", "", sql, flags=re.M)
    # Nenhum comando executavel pode sobrar mirando a tabela do alembic, e
    # nenhum falso bind do psql pode chegar ao text().
    sobras = re.search(r"^\s*(DROP|CREATE|INSERT)[^\n]*alembic_version", sql, flags=re.M | re.I)
    assert not sobras, f"filtro deixou passar: {sobras.group(0)!r}"
    assert ":app_user" not in sql
    return sql


# O preâmbulo do script offline (--sql): reproduz a guarda do modo online do
# lado de quem EXECUTA. `alembic_version` pode ainda não existir no ponto em
# que o preâmbulo roda (a criação dela pelo alembic varia com o modo), por isso
# o EXECUTE dinâmico: presente e carimbada -> segue; presente e vazia, ou
# ausente, com tabelas da aplicação no banco -> aborta antes do DROP ALL.
_GUARDA_OFFLINE = """
DO $guarda_base_zero$
DECLARE
    carimbos bigint;
BEGIN
    IF to_regclass('public.users') IS NULL THEN
        RETURN; -- banco vazio: o caminho legítimo
    END IF;
    IF to_regclass('public.alembic_version') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM alembic_version' INTO carimbos;
        IF carimbos > 0 THEN
            RETURN; -- carimbado: o alembic online nem teria chegado aqui
        END IF;
    END IF;
    RAISE EXCEPTION 'base zero: este banco tem tabelas da aplicacao e nenhum carimbo — o corpo e DROP ALL + CREATE ALL. Cadeia antiga? alembic stamp --purge 9ed006ca1660. Reset intencional? psql -f scripts/init_schema.sql.';
END
$guarda_base_zero$;
"""


def upgrade() -> None:
    # Guarda do único caminho destrutivo que a base zero abriria: um banco COM
    # tabelas da aplicação e SEM carimbo (alembic_version vazia ou ausente).
    # Só nesse estado o alembic decide "nada aplicado" e chega aqui — e o corpo
    # é DROP ALL + CREATE ALL. Um banco da cadeia antiga nunca chega (o carimbo
    # desconhecido derruba o alembic antes, sem tocar em nada); um banco vazio
    # passa.
    #
    # No modo offline (--sql) não há banco para inspecionar NA GERAÇÃO — mas o
    # script gerado é executável e roda longe dos olhos do alembic. Então a
    # MESMA guarda vai como preâmbulo do próprio script (um DO que aborta em
    # banco populado sem carimbo), em vez de confiar que ninguém o aplica às
    # cegas. Gerar continua sempre funcionando; é a EXECUÇÃO que se recusa.
    if context.is_offline_mode():
        op.execute(_GUARDA_OFFLINE)
    else:
        tem_users = op.get_bind().execute(
            sa.text("SELECT to_regclass('public.users') IS NOT NULL")
        ).scalar()
        if tem_users:
            raise RuntimeError(
                "Este banco ja tem tabelas da aplicacao, mas nenhum carimbo do "
                "alembic — executar a base zero aqui APAGARIA os dados (o corpo "
                "dela e DROP ALL + CREATE ALL). Se e um banco da cadeia antiga: "
                "alembic stamp --purge 9ed006ca1660. Se o reset e intencional: "
                "psql -f scripts/init_schema.sql."
            )

    caminho = _RAIZ / "scripts" / "init_schema.sql"
    op.execute(_sql_sem_alembic_version(caminho.read_text(encoding="utf-8")))

    # As tabelas de cada extensao presente, depois das do nucleo e com o mesmo
    # filtro. Sem extensao (a distribuicao livre), nada.
    from app.extensoes import esquemas

    for esquema in esquemas():
        op.execute(_sql_sem_alembic_version(esquema.read_text(encoding="utf-8")))


def downgrade() -> None:
    raise RuntimeError(
        "A base zero nao tem downgrade: abaixo dela nao existe estado. "
        "Para descartar o banco, rode scripts/init_schema.sql (DROP ALL + CREATE ALL)."
    )
