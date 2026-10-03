/**
 * Masking of SQL literals — port of the scanner in `flow/utils/sql_guard.py`.
 *
 * It exists to answer a single question: is a position in the SQL code or text?
 * What needs this in the editor is `:placeholders` detection — without it,
 * `WHERE obs = 'urgente:revisar'` made the panel offer a `:revisar` parameter
 * that does not exist, and the backend rejected the whole query.
 *
 * The output has the SAME LENGTH as the input: each character of a comment,
 * string or quoted identifier becomes a space at the position where it was.
 * Kept paired with the Python version — if one of them changes, the other
 * changes along with it.
 */

/** Dollar-quoting opener: `$$` or `$tag$`. */
const DOLLAR_TAG = /^\$([A-Za-z_]\w*)?\$/

export function mascararLiteraisSql(sql: string): string {
  const out: string[] = []
  const n = sql.length
  let i = 0

  const branco = (de: number, ate: number) => " ".repeat(ate - de)

  while (i < n) {
    const inicio = i
    const c = sql[i]

    // -- line comment
    if (c === "-" && sql.startsWith("--", i)) {
      const quebra = sql.indexOf("\n", i)
      i = quebra === -1 ? n : quebra
      out.push(branco(inicio, i))
      continue
    }

    // /* bloco */ — o Postgres permite aninhamento
    if (c === "/" && sql.startsWith("/*", i)) {
      let profundidade = 1
      i += 2
      while (i < n && profundidade > 0) {
        if (sql.startsWith("/*", i)) { profundidade++; i += 2 }
        else if (sql.startsWith("*/", i)) { profundidade--; i += 2 }
        else i++
      }
      // Unclosed block: the rest is a comment. Unlike the backend, here it is not
      // an error — the user is still typing, and the editor cannot blow up on
      // every keystroke in the middle of a `/*`.
      out.push(branco(inicio, i))
      continue
    }

    // 'string' — a doubled quote ('') escapes; with the E'' prefix, backslash does too
    if (c === "'") {
      const anterior = sql[i - 1]
      const escapaBarra =
        (anterior === "e" || anterior === "E") &&
        (i < 2 || !/[0-9A-Za-z]/.test(sql[i - 2]))
      i++
      while (i < n) {
        if (escapaBarra && sql[i] === "\\") { i += 2; continue }
        if (sql[i] === "'") {
          if (sql[i + 1] === "'") { i += 2; continue }
          i++
          break
        }
        i++
      }
      out.push(branco(inicio, i))
      continue
    }

    // "identificador" — aspa dobrada ("") escapa
    if (c === '"') {
      i++
      while (i < n) {
        if (sql[i] === '"') {
          if (sql[i + 1] === '"') { i += 2; continue }
          i++
          break
        }
        i++
      }
      out.push(branco(inicio, i))
      continue
    }

    // $$corpo$$ / $tag$corpo$tag$
    if (c === "$") {
      const m = DOLLAR_TAG.exec(sql.slice(i))
      if (m) {
        const tag = m[0]
        const fim = sql.indexOf(tag, i + tag.length)
        i = fim === -1 ? n : fim + tag.length
        out.push(branco(inicio, i))
        continue
      }
    }

    out.push(c)
    i++
  }

  return out.join("")
}

/** Regex for the `:nome` placeholder — the same as the backend's. */
const PLACEHOLDER = /(?<!:):([A-Za-z_]\w*)\b/g

/**
 * Unique names of the query's `:placeholders`, in order of appearance, ignoring
 * those inside a string or comment.
 */
export function extrairPlaceholders(sql: string): string[] {
  const nomes: string[] = []
  for (const m of mascararLiteraisSql(sql).matchAll(PLACEHOLDER)) {
    if (!nomes.includes(m[1])) nomes.push(m[1])
  }
  return nomes
}
