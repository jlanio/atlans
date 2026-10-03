/**
 * Local cache (sessionStorage) for the "this user has at least 1 accessible
 * executor" flag shown in the sidebar.
 *
 * Motivation:
 *   - Avoids flicker on F5: the component's initial state comes from the cache,
 *     not from a false placeholder that hides the menu until the fetch finishes.
 *   - Resilience to races / transient 401s: if the fetch fails, the cached
 *     value persists and the menu stays consistent until the next successful
 *     update (or the TTL expires).
 *
 * Security / privacy:
 *   - The cache stores ONLY a boolean + user_id + timestamp. No names,
 *     no executor IDs, no tokens.
 *   - It is keyed by the user_id in the payload — if the user logs out and
 *     another logs in on the same tab, the component detects the mismatch and
 *     discards it.
 *   - sessionStorage is per-origin, expires when the tab closes, and is not
 *     accessible to other sites.
 *   - A short TTL (1h) limits the mismatch window even in odd scenarios.
 *   - The backend remains the source of truth: the cache only decides whether
 *     the menu item appears; all real authorization happens in the endpoints.
 */

const KEY = "atlans:sidebar_has_agents"
const TTL_MS = 60 * 60 * 1000  // 1h

interface CacheEntry {
  value: boolean
  userId: string
  ts: number
}

export function readCachedHasAgents(): { value: boolean; userId: string | null } {
  if (typeof window === "undefined") return { value: false, userId: null }
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return { value: false, userId: null }
    const obj = JSON.parse(raw) as Partial<CacheEntry>
    if (typeof obj.value !== "boolean" || typeof obj.ts !== "number" || typeof obj.userId !== "string") {
      return { value: false, userId: null }
    }
    if (Date.now() - obj.ts > TTL_MS) return { value: false, userId: null }
    return { value: obj.value, userId: obj.userId }
  } catch {
    return { value: false, userId: null }
  }
}

export function writeCachedHasAgents(userId: string, value: boolean): void {
  if (typeof window === "undefined" || !userId) return
  try {
    const entry: CacheEntry = { value, userId, ts: Date.now() }
    sessionStorage.setItem(KEY, JSON.stringify(entry))
  } catch {
    // sessionStorage cheio / desabilitado — best-effort, ignora.
  }
}

export function clearCachedHasAgents(): void {
  if (typeof window === "undefined") return
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // best-effort
  }
}
