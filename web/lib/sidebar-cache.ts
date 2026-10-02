/**
 * Cache local (sessionStorage) para o flag "este usuário tem ao menos 1 executor
 * acessível" exibido na sidebar.
 *
 * Motivação:
 *   - Evita flicker no F5: estado inicial do componente sai do cache, não de
 *     um false placeholder que esconde o menu até o fetch terminar.
 *   - Resiliência a race / 401 transitório: se o fetch falhar, o valor
 *     cacheado persiste e o menu permanece consistente até a próxima
 *     atualização bem-sucedida (ou expiração do TTL).
 *
 * Segurança / privacidade:
 *   - O cache armazena APENAS um boolean + user_id + timestamp. Sem nomes,
 *     sem IDs de executor, sem tokens.
 *   - É keyed pelo user_id no payload — se o usuário fizer logout e outro
 *     logar na mesma aba, o componente detecta a divergência e descarta.
 *   - sessionStorage é por-origem, expira ao fechar a aba, não acessível a
 *     outros sites.
 *   - TTL curto (1h) limita janela de divergência mesmo em cenários estranhos.
 *   - Backend continua sendo a source-of-truth: o cache só decide se o item de
 *     menu aparece; toda autorização real acontece nos endpoints.
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
