"""
Validação read-only das queries dos nós DatabaseQuery / DatabaseSpatialQuery.

A versão anterior era uma denylist de palavras (`\\b(INSERT|...|DO|...)\\b`)
aplicada sobre o texto da query com os comentários removidos por regex. Isso
errava nos dois sentidos:

- Falso positivo: a denylist não sabe o que é código e o que é texto. Qualquer
  literal em português com "do" (`WHERE cidade = 'Rio do Sul'`, `LIKE '%do%'`),
  uma coluna chamada `comment`, ou uma auditoria com
  `acao IN ('INSERT','UPDATE','DELETE')` era rejeitada como comando proibido.
- Falso negativo: os dois regexes de comentário rodavam em sequência, cegos a
  strings. Um `--` dentro de um literal apagava o resto da query da validação,
  então `WHERE obs = 'a--b' ; DROP TABLE alvo` passava limpo.

A abordagem aqui é inversa: um scanner de um passe só remove comentários,
strings e identificadores quotados (`strip_sql_literals`), e a validação olha
para a FORMA do statement no que sobrou — deve começar com SELECT/WITH, ser um
único statement, não conter CTE de escrita nem `INTO`. Assim o texto do usuário
nunca é confundido com comando.

A defesa efetiva continua sendo `conn.transaction(readonly=True)` nos nós
(SET TRANSACTION READ ONLY no Postgres) somada ao protocolo estendido do
asyncpg, que já recusa múltiplos statements. Este módulo é defesa em
profundidade — e, principalmente, mensagem de erro acionável para o usuário.
"""
import re

# Limites de segurança para queries
_MAX_QUERY_LENGTH = 20_000  # caracteres
_MAX_SUBQUERY_DEPTH = 25    # subqueries (SELECT dentro de SELECT)

# Abertura de dollar-quoting: $$ ou $tag$
_DOLLAR_TAG = re.compile(r"\$([A-Za-z_]\w*)?\$")

# O statement precisa ser uma leitura. Parênteses à esquerda são válidos:
# `(SELECT 1 UNION SELECT 2) ORDER BY 1`.
_LEADING_READ = re.compile(r"^\s*[(\s]*(WITH|SELECT|TABLE|VALUES)\b", re.IGNORECASE)

# CTE de escrita — `WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d` começa
# com WITH e escreve. Sobre o código já limpo, essas palavras só podem ser
# comandos: são reservadas no Postgres, não servem de identificador sem aspas.
_WRITE_CTE = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE)\b", re.IGNORECASE)

# `SELECT ... INTO nova_tabela` cria tabela. INTO é reservada — fora de string
# não há uso legítimo num nó de leitura.
_SELECT_INTO = re.compile(r"\bINTO\b", re.IGNORECASE)

# Funções que escapam do escopo da transação read-only: dblink/postgres_fdw
# abrem OUTRA conexão (o READ ONLY local não vale lá), e as de arquivo/objeto
# grande tocam o filesystem do servidor. Denylist de NOME DE FUNÇÃO seguido de
# `(` — diferente de palavra solta, isso não colide com texto em português.
_DANGEROUS_CALL = re.compile(
    r"\b(dblink\w*|pg_read_file|pg_read_binary_file|pg_write_file|pg_ls_dir"
    r"|pg_stat_file|lo_import|lo_export|pg_sleep\w*|pg_terminate_backend"
    r"|pg_cancel_backend|pg_reload_conf|pg_rotate_logfile)\s*\(",
    re.IGNORECASE,
)

_SELECT_TOKEN = re.compile(r"\bSELECT\b", re.IGNORECASE)
_TRAILING_SEMICOLONS = re.compile(r"[\s;]+$")


def strip_sql_literals(sql: str) -> str:
    """Substitui comentários, strings e identificadores quotados por espaços.

    Passe único da esquerda para a direita — é o que garante que um `--` dentro
    de string não vire comentário e que um `*/` dentro de comentário de linha não
    feche um bloco.

    A saída tem o MESMO COMPRIMENTO da entrada, e cada caractere mascarado vira
    um espaço na posição em que estava. Isso é o que permite usar o resultado
    como mapa: quem precisa saber se uma posição do SQL original é código ou
    texto — o `prepare_query`, que não pode trocar `:nome` dentro de um literal —
    consulta o índice equivalente aqui. As checagens de forma abaixo não se
    importam com o comprimento; elas só olham a sequência de tokens que sobra.

    Levanta ValueError em construção não terminada (string, bloco ou
    dollar-quote sem fechamento): além de ser SQL inválido de qualquer forma,
    consumir até o fim do texto silenciosamente esconderia o resto da query da
    validação.
    """
    out: list[str] = []
    i, n = 0, len(sql)

    while i < n:
        c = sql[i]
        inicio = i

        # -- comentário de linha (vai até \n; sem \n no fim do arquivo é válido)
        if c == "-" and sql.startswith("--", i):
            quebra = sql.find("\n", i)
            i = n if quebra == -1 else quebra
            out.append(" " * (i - inicio))

        # /* bloco */ — o Postgres permite aninhamento, então contamos a profundidade
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

        # 'string' — aspa dobrada ('') escapa; com prefixo E'' o backslash também
        elif c == "'":
            escapa_barra = i > 0 and sql[i - 1] in "eE" and (i < 2 or not sql[i - 2].isalnum())
            i += 1
            fechou = False
            while i < n:
                if escapa_barra and sql[i] == "\\":
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
    """Garante que a query é uma leitura única. Levanta ValueError se não for."""
    if len(query) > _MAX_QUERY_LENGTH:
        raise ValueError(f"Query excede o limite de {_MAX_QUERY_LENGTH} caracteres.")

    codigo = strip_sql_literals(query)

    # Um `;` final (com espaços) é aceito; no meio significa mais de um statement.
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
