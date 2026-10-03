"""
Tests for validate_readonly_sql / strip_sql_literals (flow.utils.sql_guard).

The old validator was a word denylist over the raw query text. It rejected a
Portuguese literal containing "do" (`'Rio do Sul'`) as if it were the `DO`
command, and let `WHERE obs = 'a--b' ; DROP TABLE alvo` through because the
string's `--` ate the rest when "removing comments". Both classes of error are
covered here.
"""
from __future__ import annotations

import pytest

from flow.utils.sql_guard import (
    _MAX_QUERY_LENGTH,
    _MAX_SUBQUERY_DEPTH,
    strip_sql_literals,
    validate_readonly_sql,
)


class TestStripSqlLiterals:
    """The scanner must be a single pass — comments and strings delimit each other."""

    def test_line_comment_becomes_space(self):
        assert strip_sql_literals("SELECT 1 -- nota\nFROM t").split() == ["SELECT", "1", "FROM", "t"]

    def test_line_comment_at_end_without_newline(self):
        assert "nota" not in strip_sql_literals("SELECT 1 FROM t -- nota")

    def test_nested_block(self):
        # Postgres allows /* a /* b */ c */ — count depth, do not stop at the 1st */
        assert strip_sql_literals("SELECT /* a /* b */ c */ 1").split() == ["SELECT", "1"]

    def test_double_dash_inside_string_is_not_a_comment(self):
        codigo = strip_sql_literals("SELECT * FROM t WHERE obs = 'a--b' AND id = 1")
        assert "AND" in codigo and "id" in codigo

    def test_block_close_inside_line_comment_does_not_count(self):
        # The `*/` is inside the line comment: it closes no block.
        assert "carro" not in strip_sql_literals("SELECT 1 -- fim */ do carro\nFROM t")

    def test_doubled_quote_escapes(self):
        assert "b" not in strip_sql_literals("SELECT 'a''b' FROM t")

    def test_e_string_with_backslash(self):
        codigo = strip_sql_literals(r"SELECT * FROM t WHERE x = E'a\'--' AND y = 2")
        assert "AND" in codigo and "y" in codigo

    def test_quoted_identifier(self):
        assert "do" not in strip_sql_literals('SELECT t."do" FROM t')

    def test_dollar_quoting(self):
        assert "carro" not in strip_sql_literals("SELECT $$do carro$$ FROM t")

    def test_dollar_quoting_with_tag(self):
        assert "carro" not in strip_sql_literals("SELECT $tag$do carro$tag$ FROM t")

    @pytest.mark.parametrize("query, trecho", [
        ("SELECT 'aberta FROM t", "Aspas simples"),
        ('SELECT "aberta FROM t', "Aspas duplas"),
        ("SELECT 1 /* aberto FROM t", "bloco"),
        ("SELECT $$aberto FROM t", "Dollar-quoting"),
    ])
    def test_unterminated_construct_raises(self, query, trecho):
        # Silently consuming to the end would hide the rest of the query.
        with pytest.raises(ValueError, match=trecho):
            strip_sql_literals(query)


class TestLegitimateQueries:
    """Regression of the bug: user text must not become a command."""

    @pytest.mark.parametrize("query", [
        # the reported case — "do" in a comment and in text
        "-- teste do carro\nSELECT * FROM veiculos",
        "SELECT * FROM veiculos -- teste do carro",
        "SELECT * FROM municipios WHERE nome = 'Rio do Sul'",
        "SELECT * FROM veiculos WHERE modelo LIKE '%do%'",
        "SELECT * FROM clientes WHERE obs = 'documento do cliente'",
        # audit: the commands appear as DATA, not as a command
        "SELECT * FROM auditoria WHERE acao IN ('INSERT','UPDATE','DELETE')",
        "SELECT * FROM logs WHERE msg = 'DROP TABLE executado'",
        # identifiers that collide with the denylist
        "SELECT id, comment FROM posts",
        'SELECT t."do", t."set" FROM t',
        "SELECT $$do carro$$ AS obs",
        # SQL normal que precisa continuar passando
        "WITH x AS (SELECT 1) SELECT * FROM x",
        "SELECT ST_SetSRID(ST_MakePoint(1, 2), 4326) AS geom",
        "SELECT ST_AsBinary(geom) AS geom, nome FROM lotes WHERE area > :area",
        "(SELECT 1 UNION SELECT 2) ORDER BY 1",
        "SELECT * FROM t;",
        "  \n SELECT 1 \n ",
        "TABLE municipios",
        "VALUES (1), (2)",
    ])
    def test_passes(self, query):
        validate_readonly_sql(query)


class TestBlockedQueries:

    @pytest.mark.parametrize("query, trecho", [
        ("DROP TABLE alvo", "SELECT ou WITH"),
        ("DELETE FROM alvo", "SELECT ou WITH"),
        ("/* disfarce */ INSERT INTO t VALUES (1)", "SELECT ou WITH"),
        ("-- disfarce\nUPDATE t SET a = 1", "SELECT ou WITH"),
        ("DO $$ BEGIN PERFORM 1; END $$", "SELECT ou WITH"),
        ("COPY t TO '/tmp/x'", "SELECT ou WITH"),
        ("CREATE TABLE x (id int)", "SELECT ou WITH"),
        ("GRANT ALL ON t TO publico", "SELECT ou WITH"),
    ])
    def test_write_statement(self, query, trecho):
        with pytest.raises(ValueError, match=trecho):
            validate_readonly_sql(query)

    @pytest.mark.parametrize("query", [
        "SELECT 1; SELECT 2",
        "SELECT * FROM t; DROP TABLE alvo",
        # the old hole: the `--` inside the string erased the rest of the validation
        "SELECT * FROM t WHERE obs = 'a--b' ; DROP TABLE alvo",
    ])
    def test_multiple_statements(self, query):
        with pytest.raises(ValueError, match="mais de um comando"):
            validate_readonly_sql(query)

    def test_write_cte(self):
        # Starts with WITH and would pass the leading-statement test.
        with pytest.raises(ValueError, match="comando de escrita: 'DELETE'"):
            validate_readonly_sql("WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d")

    def test_select_into(self):
        with pytest.raises(ValueError, match="INTO"):
            validate_readonly_sql("SELECT * INTO nova FROM t")

    @pytest.mark.parametrize("query, nome", [
        ("SELECT dblink_exec('dbname=x', 'DELETE FROM t')", "dblink_exec"),
        ("SELECT pg_read_file('/etc/passwd')", "pg_read_file"),
        ("SELECT lo_export(1, '/tmp/x')", "lo_export"),
        ("SELECT pg_sleep(600)", "pg_sleep"),
    ])
    def test_dangerous_function(self, query, nome):
        # dblink opens ANOTHER connection — the local transaction's READ ONLY does not apply there.
        with pytest.raises(ValueError, match=nome):
            validate_readonly_sql(query)

    def test_dangerous_function_only_as_call(self):
        # The name as text is data, not a call: it must not block.
        validate_readonly_sql("SELECT * FROM logs WHERE fn = 'pg_read_file'")


class TestLimits:

    def test_character_limit(self):
        assert _MAX_QUERY_LENGTH == 20_000
        query = "SELECT " + ("a" * _MAX_QUERY_LENGTH)
        with pytest.raises(ValueError, match="20000 caracteres"):
            validate_readonly_sql(query)

    def test_large_query_within_the_limit_passes(self):
        query = "SELECT * FROM t WHERE nome IN (" + ",".join(f"'v{i}'" for i in range(2000)) + ")"
        assert 10_000 < len(query) <= _MAX_QUERY_LENGTH
        validate_readonly_sql(query)

    def test_too_many_selects(self):
        query = "SELECT " + " + ".join(f"(SELECT {i})" for i in range(_MAX_SUBQUERY_DEPTH + 5))
        with pytest.raises(ValueError, match="muito complexa"):
            validate_readonly_sql(query)

    def test_selects_in_comment_and_string_do_not_count(self):
        # Before, a SELECT inside a string counted toward the complexity limit.
        query = "SELECT " + " + ".join(f"'SELECT {i}'" for i in range(_MAX_SUBQUERY_DEPTH + 5))
        validate_readonly_sql(query)
