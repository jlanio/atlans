/**
 * Port of `app/core/utils/allowlist.py` — keep the two in sync.
 *
 * It exists so the notifications screen can show the effect of an allowlist
 * WHILE it is being edited, before saving. Without it the user would only find
 * out which workflows they started blocking after saving — and the column
 * already fails silently enough.
 *
 * The backend remains the authority: what this function computes is a preview,
 * reconciled by the PUT response. `web/__tests__/lib/hostname-allowlist.test.ts`
 * mirrors the Python cases; if the rules there change, it breaks here.
 */

/**
 * Accepted patterns:
 *   - "exemplo.com"   → exact match
 *   - "*.exemplo.com" → any subdomain (a.exemplo.com, foo.bar.exemplo.com)
 *                       but NOT the bare domain (exemplo.com)
 *
 * Case-insensitive comparison.
 */
export function hostnameMatchesAllowlist(hostname: string, allowlist: string[]): boolean {
  const host = (hostname ?? "").toLowerCase().trim()
  if (!host) return false

  for (const raw of allowlist ?? []) {
    const pattern = (raw ?? "").toLowerCase().trim()
    if (!pattern) continue

    if (pattern.startsWith("*.")) {
      const suffix = pattern.slice(1) // ".exemplo.com"
      // `host !== suffix.slice(1)` is what excludes the bare domain: "*.exemplo.com"
      // covers the subdomains, not "exemplo.com".
      if (host.endsWith(suffix) && host !== suffix.slice(1)) return true
    } else if (host === pattern) {
      return true
    }
  }
  return false
}

/**
 * A host is allowed when the allowlist is empty.
 *
 * Mirrors the consumer's `if allowlist:`: without a list there is no additional
 * policy, and everything that passes the SSRF check is accepted. It is the
 * column's inverted semantics — applying `hostnameMatchesAllowlist` directly
 * would mark everything as blocked in the state where everything passes today.
 */
export function isHostAllowed(hostname: string, allowlist: string[]): boolean {
  if (!allowlist || allowlist.length === 0) return true
  return hostnameMatchesAllowlist(hostname, allowlist)
}

/**
 * Validates a pattern before it becomes a chip, with the same rules as
 * `_normalize_allowlist` in the backend. Returns the error message, or null.
 *
 * Duplicating the validation here is what makes mistakes cheap: pasting the
 * whole URL is the obvious slip, and discovering it only at the server's 400
 * costs a round-trip.
 */
export function validateAllowlistPattern(raw: string): string | null {
  const pattern = (raw ?? "").trim().toLowerCase()
  if (!pattern) return "Informe um host."

  if (pattern.includes("://") || pattern.includes("/") || pattern.includes("@") || pattern.includes(":")) {
    return "Informe apenas o host, sem protocolo, porta ou caminho (ex.: exemplo.com)."
  }
  if (pattern.includes("*") && !pattern.startsWith("*.")) {
    return "O curinga só vale no formato *.exemplo.com (subdomínios)."
  }
  if (pattern.startsWith("*.") && !pattern.slice(2).includes(".")) {
    return "Informe o domínio completo após o curinga (ex.: *.exemplo.com)."
  }
  if (!pattern.startsWith("*.") && !pattern.includes(".")) {
    return "Não parece um hostname válido (ex.: exemplo.com)."
  }
  return null
}
