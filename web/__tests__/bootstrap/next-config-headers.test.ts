/**
 * The security headers come from next.config.ts's `headers()`, for EVERY
 * server response, and the CSP is BLOCKING. This test locks the shape of the
 * policy — especially what it allows from outside our build: the
 * Cloudflare Web Analytics beacon, which the edge injects into every HTML of the zone, and nothing
 * else. Monaco, which used to come from jsdelivr, is served from our own origin.
 */
import { describe, it, expect, vi, afterEach } from "vitest"

import nextConfig from "@/next.config"

async function cabecalhos(config = nextConfig) {
  const regras = (await config.headers?.()) ?? []
  expect(regras).toHaveLength(1)
  const [{ source, headers }] = regras
  const valor = (chave: string) => headers.find((h) => h.key === chave)?.value ?? ""
  return { source, valor }
}

function directives(csp: string): Map<string, string[]> {
  const mapa = new Map<string, string[]>()
  for (const parte of csp.split("; ")) {
    const [nome, ...fontes] = parte.split(" ")
    mapa.set(nome, fontes)
  }
  return mapa
}

describe("headers de segurança do next.config", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it("valem para toda resposta do servidor, não só para o que o middleware cobre", async () => {
    const { source } = await cabecalhos()
    expect(source).toBe("/(.*)")
  })

  it("a CSP bloqueia e continua relatando em /api/csp-report", async () => {
    const { valor } = await cabecalhos()
    // Just one: with both, the report-only one would be duplicate noise in the log.
    expect(valor("Content-Security-Policy-Report-Only")).toBe("")
    const csp = directives(valor("Content-Security-Policy"))
    expect(csp.get("report-uri")).toEqual(["/api/csp-report"])
    expect(csp.get("report-to")).toEqual(["csp"])
    expect(valor("Reporting-Endpoints")).toBe('csp="/api/csp-report"')
  })

  it("Permissions-Policy libera geolocalização só para a própria origem; câmera e microfone negados", async () => {
    const { valor } = await cabecalhos()
    const pp = valor("Permissions-Policy")
    // The Home locates the person on the globe — but only the site itself, never an
    // embedded third party. Empty `()` denies everyone; `(self)` allows the origin.
    expect(pp).toContain("geolocation=(self)")
    expect(pp).toContain("camera=()")
    expect(pp).toContain("microphone=()")
    // The pitfall: `geolocation=()` (empty) would forbid even the Home itself.
    expect(pp).not.toContain("geolocation=()")
  })

  it("script-src libera a origem e o beacon do Cloudflare — e nenhum CDN", async () => {
    const { valor } = await cabecalhos()
    const csp = directives(valor("Content-Security-Policy"))
    // Only the beacon host: the real URL is `.../beacon.min.js/v<hash>`, and a
    // path without a trailing slash in the CSP matches exactly. Any other host here is a
    // third-party script someone allowed without going through this test — the
    // Monaco from jsdelivr was the case, and now it comes from /monaco/vs.
    expect(csp.get("script-src")).toEqual(["'self'", "'unsafe-inline'", "https://static.cloudflareinsights.com"])
    // The Monaco and MapLibre workers start from `blob:`.
    expect(csp.get("worker-src")).toEqual(["'self'", "blob:"])
    // The beacon's POST (cloudflareinsights.com/cdn-cgi/rum) fits within `https:`.
    expect(csp.get("connect-src")).toEqual(["'self'", "https:", "wss:"])
    expect(csp.get("img-src")).toEqual(["'self'", "data:", "blob:", "https:"])
  })

  it("no `next dev` libera o que o dev usa fora da origem: eval do HMR, a API em outra porta e o MinIO http", async () => {
    vi.stubEnv("NODE_ENV", "development")
    vi.resetModules()
    const { default: configDev } = await import("@/next.config")
    const { valor } = await cabecalhos(configDev)
    const csp = directives(valor("Content-Security-Policy"))
    expect(csp.get("script-src")).toContain("'unsafe-eval'")
    // utils/env.ts: with NEXT_PUBLIC_API_PORT the WebSocket goes to ws://host:8000.
    expect(csp.get("connect-src")).toEqual(["'self'", "https:", "wss:", "http:", "ws:"])
    expect(csp.get("img-src")).toContain("http:")
    // Over HTTP Chrome does not deliver through the Reporting API and, with `report-to`
    // present, ignores `report-uri`: in dev only `report-uri` stays.
    expect(csp.get("report-to")).toBeUndefined()
    expect(csp.get("report-uri")).toEqual(["/api/csp-report"])
  })
})
