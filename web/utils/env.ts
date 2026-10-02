// HTTP: URL relativa — o browser envia para o mesmo host/porta,
// o Route Handler /terra/* faz o proxy para API_INTERNA em runtime.
export const API_URL = "/terra"

// URL externa da API (sem prefixo /terra), para uso em exemplos de código
// que serão executados por clientes externos.
// Dev:  NEXT_PUBLIC_API_PORT=8000 → http://host:8000
// Prod: sem NEXT_PUBLIC_API_PORT  → https?://host  (Traefik roteia diretamente)
export function getExternalApiUrl(): string {
  if (typeof window === "undefined") return "http://localhost:8000"
  const proto   = window.location.protocol
  const host    = window.location.hostname
  const apiPort = process.env.NEXT_PUBLIC_API_PORT
  if (apiPort) return `${proto}//${host}:${apiPort}`
  const pagePort = window.location.port
  return pagePort ? `${proto}//${host}:${pagePort}` : `${proto}//${host}`
}

// WebSocket: calculado em runtime a partir de window.location.
// Dev:  NEXT_PUBLIC_API_PORT=8000 → ws://host:8000  (API exposta diretamente)
// Prod: sem NEXT_PUBLIC_API_PORT  → wss://host      (Traefik roteia /ws/*)
export function getWsUrl(): string {
  if (typeof window === "undefined") return "ws://localhost:8000"
  const proto   = window.location.protocol === "https:" ? "wss:" : "ws:"
  const host    = window.location.hostname
  // Segurança: alerta se WebSocket sem TLS em produção
  if (proto === "ws:" && process.env.NODE_ENV === "production") {
    console.warn("[SEGURANÇA] WebSocket sem TLS (ws://) detectado em produção. Use HTTPS para garantir wss://.")
  }
  const apiPort = process.env.NEXT_PUBLIC_API_PORT
  if (apiPort) return `${proto}//${host}:${apiPort}`
  const pagePort = window.location.port
  return pagePort ? `${proto}//${host}:${pagePort}` : `${proto}//${host}`
}
