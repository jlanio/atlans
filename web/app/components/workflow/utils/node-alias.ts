/**
 * A node's alias as the EXECUTOR registers it in the Jinja context.
 *
 * Mirrors `_resolve_alias` in flow/executor/core.py: the custom alias only
 * counts if it is a valid identifier; otherwise the executor falls back to the
 * node class's `name`.
 *
 * Without this, the autocomplete suggested the display label — "Caixa
 * Delimitadora", "Entrada de Dados" — which has spaces and is not an
 * identifier. The expression ended up pointing at a name that does not exist
 * in the context, and the autocomplete itself stopped recognizing the text it
 * had just inserted (the trigger regex uses \w, which does not match a space),
 * so "." never listed the fields.
 */

/** These collide with fixed context keys — see RESERVED_ALIASES in flow/core/aliases.py. */
export const RESERVED_ALIASES: ReadonlySet<string> = new Set([
  "inputs", "nodes", "named", "now", "uuid", "env",
])

/**
 * Equivalent to Python's `str.isidentifier()` — accepts Unicode identifiers,
 * so accents and ç are fine. Exported as a source for anyone who needs to
 * compose a larger regex (the autocomplete scans `Alias.campo` in the text).
 */
export const IDENTIFIER_SOURCE = "[\\p{ID_Start}_][\\p{ID_Continue}]*"
const IDENTIFIER = new RegExp(`^${IDENTIFIER_SOURCE}$`, "u")

export function isValidAlias(alias: string | undefined | null): boolean {
  if (!alias) return false
  return IDENTIFIER.test(alias) && !RESERVED_ALIASES.has(alias)
}

/**
 * Name by which the node can be referenced in an expression (`$Alias.campo`).
 *
 * A faithful replica of `_resolve_alias`, including the semantics of Python's `or`:
 *
 *     custom = node_def.get("alias", "") or node_def["properties"].get("alias", "")
 *     return custom if custom.isidentifier() and custom not in RESERVADOS else node_def["name"]
 *
 * The `or` chooses by TRUTHINESS, not validity — an `alias` that is filled but
 * unusable (the catalog label, "Caixa Delimitadora") makes the executor fall
 * straight to the class `name`, without even looking at `properties.alias`.
 * Approximating that as "the first valid candidate" would make the autocomplete
 * suggest a name the executor does not register — the bug this module exists
 * to prevent.
 *
 * In practice `data.alias` already carries the user's alias: the modal promotes
 * it on save. `properties.alias` covers the node whose `alias` came empty from
 * the database.
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
