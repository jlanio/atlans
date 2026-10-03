"""
Read-only validation of the queries of the DatabaseQuery / DatabaseSpatialQuery nodes.

The previous version was a word denylist (`\\b(INSERT|...|DO|...)\\b`)
applied to the query text with comments removed by regex. That
was wrong in both directions:

- False positive: the denylist doesn't know what is code and what is text. Any
  Portuguese literal with "do" (`WHERE cidade = 'Rio do Sul'`, `LIKE '%do%'`),
  a column named `comment`, or an audit with
  `acao IN ('INSERT','UPDATE','DELETE')` was rejected as a forbidden command.
- False negative: the two comment regexes ran in sequence, blind to
  strings. A `--` inside a literal erased the rest of the query from validation,
  so `WHERE obs = 'a--b' ; DROP TABLE alvo` passed clean.

The approach here is the reverse: a single-pass scanner removes comments,
strings and quoted identifiers (`strip_sql_literals`), and the validation looks
at the SHAPE of the statement in what remains — it must start with SELECT/WITH, be a
single statement, and contain no writing CTE nor `INTO`. That way the user's text
is never mistaken for a command.

The effective defense remains `conn.transaction(readonly=True)` in the nodes
(SET TRANSACTION READ ONLY in Postgres) together with asyncpg's extended
protocol, which already rejects multiple statements. This module is defense in
depth — and, above all, an actionable error message for the user.
"""
import re

# Safety limits for queries
_MAX_QUERY_LENGTH = 20_000  # caracteres
_MAX_SUBQUERY_DEPTH = 25    # subqueries (SELECT inside SELECT)

# Opening of dollar-quoting: $$ or $tag$
_DOLLAR_TAG = re.compile(r"\$([A-Za-z_]\w*)?\$")

# The statement must be a read. Leading parentheses are valid:
# `(SELECT 1 UNION SELECT 2) ORDER BY 1`.
_LEADING_READ = re.compile(r"^\s*[(\s]*(WITH|SELECT|TABLE|VALUES)\b", re.IGNORECASE)

# Writing CTE — `WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d` starts
# with WITH and writes. On the already cleaned code, these words can only be
# commands: they are reserved in Postgres and can't be used as unquoted identifiers.
_WRITE_CTE = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE)\b", re.IGNORECASE)

# `SELECT ... INTO nova_tabela` creates a table. INTO is reserved — outside a string
# there is no legitimate use in a read node.
_SELECT_INTO = re.compile(r"\bINTO\b", re.IGNORECASE)

# Functions that escape the read-only transaction's scope: dblink/postgres_fdw
# open ANOTHER connection (the local READ ONLY doesn't apply there), and the
# file/large-object ones touch the server's filesystem. Denylist of FUNCTION NAME
# followed by `(` — unlike a loose word, this doesn't collide with Portuguese text.
_DANGEROUS_CALL = re.compile(
    r"\b(dblink\w*|pg_read_file|pg_read_binary_file|pg_write_file|pg_ls_dir"
    r"|pg_stat_file|lo_import|lo_export|pg_sleep\w*|pg_terminate_backend"
    r"|pg_cancel_backend|pg_reload_conf|pg_rotate_logfile)\s*\(",
    re.IGNORECASE,
)

_SELECT_TOKEN = re.compile(r"\bSELECT\b", re.IGNORECASE)
_TRAILING_SEMICOLONS = re.compile(r"[\s;]+$")


def strip_sql_literals(sql: str) -> str:
    """Replaces comments, strings and quoted identifiers with spaces.

    A single left-to-right pass — that is what guarantees that a `--` inside
    a string doesn't become a comment and that a `*/` inside a line comment
    doesn't close a block.

    The output has the SAME LENGTH as the input, and each masked character becomes
    a space at the position where it was. That is what allows using the result
    as a map: whoever needs to know whether a position in the original SQL is code
    or text — `prepare_query`, which must not replace `:nome` inside a literal —
    looks up the equivalent index here. The shape checks below don't care
    about length; they only look at the sequence of tokens that remains.

    Raises ValueError on an unterminated construct (string, block or
    dollar-quote without a closing): besides being invalid SQL anyway,
    silently consuming to the end of the text would hide the rest of the query
    from validation.
    """
    out: list[str] = []
    i, n = 0, len(sql)

    while i < n:
        c = sql[i]
        inicio = i

        # -- line comment (goes up to \n; without \n at end of file it is valid)
        if c == "-" and sql.startswith("--", i):
            quebra = sql.find("\n", i)
            i = n if quebra == -1 else quebra
            out.append(" " * (i - inicio))

        # /* block */ — Postgres allows nesting, so we count the depth
        elif c == "/" and sql.startswith("/*", i):
            profundidade, i = 1, i + 2
            while i < n and profundidade:
                if sql.startswith("/*", i):
                    profundidade, i = profundidade + 1, i + 2
                elif sql.startswith("*/", i):
                    profundidade, i = profundidade - 1, i + 2
                else:
                    i += 1
            if profundidade:
                raise ValueError("Comentário de bloco `/*` não fechado na query.")
            out.append(" " * (i - inicio))

        # 'string' — a doubled quote ('') escapes; with the E'' prefix the backslash does too
        elif c == "'":
            escapes_backslash = i > 0 and sql[i - 1] in "eE" and (i < 2 or not sql[i - 2].isalnum())
            i += 1
            fechou = False
            while i < n:
                if escapes_backslash and sql[i] == "\\":
                    i += 2
                    continue
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    fechou = True
                    break
                i += 1
            if not fechou:
                raise ValueError("Aspas simples não fechadas na query.")
            out.append(" " * (i - inicio))

        # "identificador" — aspa dobrada ("") escapa
        elif c == '"':
            i += 1
            fechou = False
            while i < n:
                if sql[i] == '"':
                    if i + 1 < n and sql[i + 1] == '"':
                        i += 2
                        continue
                    i += 1
                    fechou = True
                    break
                i += 1
            if not fechou:
                raise ValueError("Aspas duplas não fechadas na query.")
            out.append(" " * (i - inicio))

        # $$corpo$$ / $tag$corpo$tag$
        elif c == "$" and (m := _DOLLAR_TAG.match(sql, i)):
            tag = m.group(0)
            fim = sql.find(tag, m.end())
            if fim == -1:
                raise ValueError(f"Dollar-quoting `{tag}` não fechado na query.")
            i = fim + len(tag)
            out.append(" " * (i - inicio))

        else:
            out.append(c)
            i += 1

    return "".join(out)


def validate_readonly_sql(query: str) -> None:
    """Ensures the query is a single read. Raises ValueError if it is not."""
    if len(query) > _MAX_QUERY_LENGTH:
        raise ValueError(f"Query excede o limite de {_MAX_QUERY_LENGTH} caracteres.")

    codigo = strip_sql_literals(query)

    # A trailing `;` (with spaces) is accepted; in the middle it means more than one statement.
    if ";" in _TRAILING_SEMICOLONS.sub("", codigo):
        raise ValueError(
            "Query contém mais de um comando SQL (`;`). "
            "Este nó executa apenas uma consulta por vez."
        )

    if not _LEADING_READ.match(codigo):
        primeiro = next(iter(codigo.split()), "")
        achado = f" (começa com '{primeiro.upper()}')" if primeiro else ""
        raise ValueError(
            f"Apenas consultas de leitura são permitidas neste nó{achado}. "
            "A query deve começar com SELECT ou WITH."
        )

    if match := _WRITE_CTE.search(codigo):
        raise ValueError(
            f"Query contém comando de escrita: '{match.group().upper()}'. "
            "Apenas consultas de leitura são permitidas neste nó."
        )

    if _SELECT_INTO.search(codigo):
        raise ValueError(
            "Query contém 'INTO', que cria/grava tabela. "
            "Apenas consultas de leitura são permitidas neste nó."
        )

    if match := _DANGEROUS_CALL.search(codigo):
        nome = match.group(1)
        raise ValueError(f"Query chama a função '{nome}', não permitida neste nó.")

    select_count = len(_SELECT_TOKEN.findall(codigo))
    if select_count > _MAX_SUBQUERY_DEPTH:
        raise ValueError(
            f"Query muito complexa ({select_count} SELECTs, máximo: {_MAX_SUBQUERY_DEPTH})."
        )
