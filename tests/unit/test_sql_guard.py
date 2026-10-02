"""
Testes de validate_readonly_sql / strip_sql_literals (flow.utils.sql_guard).

O validador antigo era uma denylist de palavras sobre o texto cru da query.
Rejeitava literal em português com "do" (`'Rio do Sul'`) como se fosse o comando
`DO`, e deixava passar `WHERE obs = 'a--b' ; DROP TABLE alvo` porque o `--` da
string comia o resto na hora de "remover comentários". As duas classes de erro
estão cobertas aqui.
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
    """O scanner precisa ser um passe único — comentário e string se delimitam."""

    def test_comentario_de_linha_vira_espaco(self):
        assert strip_sql_literals("SELECT 1 -- nota\nFROM t").split() == ["SELECT", "1", "FROM", "t"]

    def test_comentario_de_linha_no_fim_sem_quebra(self):
        assert "nota" not in strip_sql_literals("SELECT 1 FROM t -- nota")

    def test_bloco_aninhado(self):
        # Postgres permite /* a /* b */ c */ — contar profundidade, não parar no 1o */
        assert strip_sql_literals("SELECT /* a /* b */ c */ 1").split() == ["SELECT", "1"]

    def test_traco_duplo_dentro_de_string_nao_e_comentario(self):
        codigo = strip_sql_literals("SELECT * FROM t WHERE obs = 'a--b' AND id = 1")
        assert "AND" in codigo and "id" in codigo

    def test_fecha_bloco_dentro_de_comentario_de_linha_nao_conta(self):
        # O `*/` está dentro do comentário de linha: não fecha bloco nenhum.
        assert "carro" not in strip_sql_literals("SELECT 1 -- fim */ do carro\nFROM t")

    def test_aspa_dobrada_escapa(self):
        assert "b" not in strip_sql_literals("SELECT 'a''b' FROM t")

    def test_string_e_com_backslash(self):
        codigo = strip_sql_literals(r"SELECT * FROM t WHERE x = E'a\'--' AND y = 2")
        assert "AND" in codigo and "y" in codigo

    def test_identificador_quotado(self):
        assert "do" not in strip_sql_literals('SELECT t."do" FROM t')

    def test_dollar_quoting(self):
        assert "carro" not in strip_sql_literals("SELECT $$do carro$$ FROM t")

    def test_dollar_quoting_com_tag(self):
        assert "carro" not in strip_sql_literals("SELECT $tag$do carro$tag$ FROM t")

    @pytest.mark.parametrize("query, trecho", [
        ("SELECT 'aberta FROM t", "Aspas simples"),
        ('SELECT "aberta FROM t', "Aspas duplas"),
        ("SELECT 1 /* aberto FROM t", "bloco"),
        ("SELECT $$aberto FROM t", "Dollar-quoting"),
    ])
    def test_construcao_nao_terminada_levanta(self, query, trecho):
        # Consumir até o fim silenciosamente esconderia o resto da query.
        with pytest.raises(ValueError, match=trecho):
            strip_sql_literals(query)


class TestQueriesLegitimas:
    """Regressão do bug: texto do usuário não pode virar comando."""

    @pytest.mark.parametrize("query", [
        # o caso relatado — "do" em comentário e em texto
        "-- teste do carro\nSELECT * FROM veiculos",
        "SELECT * FROM veiculos -- teste do carro",
        "SELECT * FROM municipios WHERE nome = 'Rio do Sul'",
        "SELECT * FROM veiculos WHERE modelo LIKE '%do%'",
        "SELECT * FROM clientes WHERE obs = 'documento do cliente'",
        # auditoria: os comandos aparecem como DADO, não como comando
        "SELECT * FROM auditoria WHERE acao IN ('INSERT','UPDATE','DELETE')",
        "SELECT * FROM logs WHERE msg = 'DROP TABLE executado'",
        # identificadores que colidiam com a denylist
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
    def test_passa(self, query):
        validate_readonly_sql(query)


class TestQueriesBloqueadas:

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
    def test_statement_de_escrita(self, query, trecho):
        with pytest.raises(ValueError, match=trecho):
            validate_readonly_sql(query)

    @pytest.mark.parametrize("query", [
        "SELECT 1; SELECT 2",
        "SELECT * FROM t; DROP TABLE alvo",
        # o furo antigo: o `--` dentro da string apagava o resto da validação
        "SELECT * FROM t WHERE obs = 'a--b' ; DROP TABLE alvo",
    ])
    def test_multiplos_statements(self, query):
        with pytest.raises(ValueError, match="mais de um comando"):
            validate_readonly_sql(query)

    def test_cte_de_escrita(self):
        # Começa com WITH e passaria no teste de statement inicial.
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
    def test_funcao_perigosa(self, query, nome):
        # dblink abre OUTRA conexão — o READ ONLY da transação local não vale lá.
        with pytest.raises(ValueError, match=nome):
            validate_readonly_sql(query)

    def test_funcao_perigosa_so_como_chamada(self):
        # O nome como texto é dado, não chamada: não pode bloquear.
        validate_readonly_sql("SELECT * FROM logs WHERE fn = 'pg_read_file'")


class TestLimites:

    def test_limite_de_caracteres(self):
        assert _MAX_QUERY_LENGTH == 20_000
        query = "SELECT " + ("a" * _MAX_QUERY_LENGTH)
        with pytest.raises(ValueError, match="20000 caracteres"):
            validate_readonly_sql(query)

    def test_query_grande_dentro_do_limite_passa(self):
        query = "SELECT * FROM t WHERE nome IN (" + ",".join(f"'v{i}'" for i in range(2000)) + ")"
        assert 10_000 < len(query) <= _MAX_QUERY_LENGTH
        validate_readonly_sql(query)

    def test_excesso_de_selects(self):
        query = "SELECT " + " + ".join(f"(SELECT {i})" for i in range(_MAX_SUBQUERY_DEPTH + 5))
        with pytest.raises(ValueError, match="muito complexa"):
            validate_readonly_sql(query)

    def test_selects_em_comentario_e_string_nao_contam(self):
        # Antes o SELECT dentro de string contava para o limite de complexidade.
        query = "SELECT " + " + ".join(f"'SELECT {i}'" for i in range(_MAX_SUBQUERY_DEPTH + 5))
        validate_readonly_sql(query)
