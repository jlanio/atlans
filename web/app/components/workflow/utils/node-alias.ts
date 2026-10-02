/**
 * Alias de um nó como o EXECUTOR o registra no contexto Jinja.
 *
 * Espelha `_resolve_alias` em flow/executor/core.py: o alias customizado só
 * vale se for um identificador válido; caso contrário o executor cai no `name`
 * da classe do nó.
 *
 * Sem isso, o autocomplete sugeria o rótulo de exibição — "Caixa Delimitadora",
 * "Entrada de Dados" — que tem espaço e não é identificador. A expressão saía
 * apontando para um nome inexistente no contexto, e o próprio autocomplete
 * parava de reconhecer o texto que acabara de inserir (o regex de gatilho usa
 * \w, que não casa espaço), então o "." nunca listava os campos.
 */

/** Colidem com chaves fixas do contexto — ver RESERVED_ALIASES em flow/core/aliases.py. */
export const RESERVED_ALIASES: ReadonlySet<string> = new Set([
  "inputs", "nodes", "named", "now", "uuid", "env",
])

/**
 * Equivalente ao `str.isidentifier()` do Python — aceita identificadores
 * Unicode, então acento e ç valem. Exportado como fonte para quem precisa
 * compor um regex maior (o autocomplete varre `Alias.campo` no texto).
 */
export const IDENTIFIER_SOURCE = "[\\p{ID_Start}_][\\p{ID_Continue}]*"
const IDENTIFIER = new RegExp(`^${IDENTIFIER_SOURCE}$`, "u")

export function isValidAlias(alias: string | undefined | null): boolean {
  if (!alias) return false
  return IDENTIFIER.test(alias) && !RESERVED_ALIASES.has(alias)
}

/**
 * Nome pelo qual o nó é referenciável numa expressão (`$Alias.campo`).
 *
 * Réplica fiel de `_resolve_alias`, incluindo a semântica do `or` do Python:
 *
 *     custom = node_def.get("alias", "") or node_def["properties"].get("alias", "")
 *     return custom if custom.isidentifier() and custom not in RESERVADOS else node_def["name"]
 *
 * O `or` escolhe por VERACIDADE, não por validade — um `alias` preenchido mas
 * inutilizável (o rótulo do catálogo, "Caixa Delimitadora") faz o executor cair
 * direto no `name` da classe, sem sequer olhar `properties.alias`. Aproximar
 * isso por "o primeiro candidato válido" faria o autocomplete sugerir um nome
 * que o executor não registra — o bug que este módulo existe para evitar.
 *
 * Na prática `data.alias` já carrega o alias do usuário: o modal o promove ao
 * salvar. `properties.alias` cobre o nó cujo `alias` veio vazio do banco.
 */
export function resolveNodeAlias(data: {
  alias?: unknown
  name?: unknown
  properties?: { alias?: unknown } | null
}): string {
  const direto = typeof data?.alias === "string" ? data.alias : ""
  const emProps = typeof data?.properties?.alias === "string" ? data.properties.alias : ""
  const custom = direto || emProps
  if (isValidAlias(custom)) return custom
  return typeof data?.name === "string" ? data.name : ""
}
