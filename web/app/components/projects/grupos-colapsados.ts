/**
 * Which groups stay collapsed, from one visit to the next.
 *
 * It was plain `useState`: whoever collapsed the groups they do not use saw
 * everything open again on reload, and collapsed everything once more. In a
 * list with many groups, this state is exactly what makes the page usable.
 *
 * `localStorage` throws in a private window and with the quota full — and an
 * error when READING must not keep the page from opening. Every operation is
 * guarded, and failure is "no group collapsed", which is the usual initial state.
 *
 * The key is per workspace: collapsing a group in one workspace must not touch
 * the reading of another, where the ids do not even exist.
 */
const PREFIXO = "atlans:grupos-recolhidos"

export function chaveDosColapsados(workspaceId: string | null | undefined): string {
  return `${PREFIXO}:${workspaceId ?? "sem-workspace"}`
}

export function readCollapsed(chave: string): Set<string> {
  try {
    const cru = window.localStorage.getItem(chave)
    if (!cru) return new Set()
    const lista = JSON.parse(cru)
    // Content from another version, or edited by hand: better to start from scratch
    // than to let a `Set` with numbers inside reach `has()`.
    if (!Array.isArray(lista)) return new Set()
    return new Set(lista.filter((x): x is string => typeof x === "string"))
  } catch {
    return new Set()
  }
}

export function saveCollapsed(chave: string, recolhidos: Set<string>): void {
  try {
    window.localStorage.setItem(chave, JSON.stringify([...recolhidos]))
  } catch {
    // A display preference is not worth interrupting anything.
  }
}
