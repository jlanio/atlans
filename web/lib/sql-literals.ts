/**
 * Mascaramento de literais SQL — porta do scanner de `flow/utils/sql_guard.py`.
 *
 * Existe para responder uma pergunta só: uma posição do SQL é código ou texto?
 * Quem precisa disso no editor é a detecção de `:placeholders` — sem ela,
 * `WHERE obs = 'urgente:revisar'` fazia o painel oferecer um parâmetro
 * `:revisar` que não existe, e o backend recusava a consulta inteira.
 *
 * A saída tem o MESMO COMPRIMENTO da entrada: cada caractere de comentário,
 * string ou identificador entre aspas vira um espaço na posição em que estava.
 * Mantido em par com a versão Python — se um dos dois mudar, o outro muda junto.
 */

/** Abertura de dollar-quoting: `$$` ou `$tag$`. */
const DOLLAR_TAG = /^\$([A-Za-z_]\w*)?\$/

export function mascararLiteraisSql(sql: string): string {
  const out: string[] = []
  const n = sql.length
  let i = 0

  const branco = (de: number, ate: number) => " ".repeat(ate - de)

  while (i < n) {
    const inicio = i
    const c = sql[i]

    // -- comentário de linha
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
      // Bloco não fechado: o resto é comentário. Diferente do backend, aqui não
      // é erro — o usuário ainda está digitando, e o editor não pode explodir a
      // cada tecla no meio de um `/*`.
      out.push(branco(inicio, i))
      continue
    }

    // 'string' — aspa dobrada ('') escapa; com prefixo E'' o backslash também
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

/** Regex de placeholder `:nome` — a mesma do backend. */
const PLACEHOLDER = /(?<!:):([A-Za-z_]\w*)\b/g

/**
 * Nomes únicos dos `:placeholders` da query, em ordem de aparição, ignorando os
 * que estão dentro de string ou comentário.
 */
export function extrairPlaceholders(sql: string): string[] {
  const nomes: string[] = []
  for (const m of mascararLiteraisSql(sql).matchAll(PLACEHOLDER)) {
    if (!nomes.includes(m[1])) nomes.push(m[1])
  }
  return nomes
}
