// HTTP: relative URL — the browser sends to the same host/port,
// the /terra/* Route Handler proxies to API_INTERNA at runtime.
export const API_URL = "/terra"

// External URL of the API (without the /terra prefix), for use in code
// examples that will be run by external clients.
// Dev:  NEXT_PUBLIC_API_PORT=8000 → http://host:8000
// Prod: no NEXT_PUBLIC_API_PORT   → https?://host  (Traefik routes directly)
export function getExternalApiUrl(): string {
  if (typeof window === "undefined") return "http://localhost:8000"
  const proto   = window.location.protocol
  const host    = window.location.hostname
  const apiPort = process.env.NEXT_PUBLIC_API_PORT
  if (apiPort) return `${proto}//${host}:${apiPort}`
  const pagePort = window.location.port
  return pagePort ? `${proto}//${host}:${pagePort}` : `${proto}//${host}`
}

// WebSocket: computed at runtime from window.location.
// Dev:  NEXT_PUBLIC_API_PORT=8000 → ws://host:8000  (API exposed directly)
// Prod: no NEXT_PUBLIC_API_PORT   → wss://host      (Traefik routes /ws/*)
export function getWsUrl(): string {
  if (typeof window === "undefined") return "ws://localhost:8000"
  const proto   = window.location.protocol === "https:" ? "wss:" : "ws:"
  const host    = window.location.hostname
  // Security: warns if WebSocket is without TLS in production
  if (proto === "ws:" && process.env.NODE_ENV === "production") {
    console.warn("[SEGURANÇA] WebSocket sem TLS (ws://) detectado em produção. Use HTTPS para garantir wss://.")
  }
  const apiPort = process.env.NEXT_PUBLIC_API_PORT
  if (apiPort) return `${proto}//${host}:${apiPort}`
  const pagePort = window.location.port
  return pagePort ? `${proto}//${host}:${pagePort}` : `${proto}//${host}`
}
