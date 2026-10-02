/**
 * Os headers de segurança saem do `headers()` do next.config.ts, para TODA
 * resposta do servidor, e a CSP é BLOQUEANTE. Este teste tranca a forma da
 * política — em especial o que ela libera de fora do nosso build: o beacon do
 * Cloudflare Web Analytics, que a borda injeta em todo HTML da zona, e nada
 * mais. O Monaco, que vinha do jsdelivr, é servido da própria origem.
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

function diretivas(csp: string): Map<string, string[]> {
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
    // Uma só: com as duas, a de relatório seria ruído duplicado no log.
    expect(valor("Content-Security-Policy-Report-Only")).toBe("")
    const csp = diretivas(valor("Content-Security-Policy"))
    expect(csp.get("report-uri")).toEqual(["/api/csp-report"])
    expect(csp.get("report-to")).toEqual(["csp"])
    expect(valor("Reporting-Endpoints")).toBe('csp="/api/csp-report"')
  })

  it("Permissions-Policy libera geolocalização só para a própria origem; câmera e microfone negados", async () => {
    const { valor } = await cabecalhos()
    const pp = valor("Permissions-Policy")
    // A Home localiza a pessoa no globo — mas só o próprio site, nunca um
    // terceiro embutido. `()` vazio nega para todos; `(self)` libera a origem.
    expect(pp).toContain("geolocation=(self)")
    expect(pp).toContain("camera=()")
    expect(pp).toContain("microphone=()")
    // A armadilha: `geolocation=()` (vazio) proibiria até a própria Home.
    expect(pp).not.toContain("geolocation=()")
  })

  it("script-src libera a origem e o beacon do Cloudflare — e nenhum CDN", async () => {
    const { valor } = await cabecalhos()
    const csp = diretivas(valor("Content-Security-Policy"))
    // Só o host do beacon: a URL real é `.../beacon.min.js/v<hash>`, e um
    // caminho sem barra final na CSP casa exato. Qualquer outro host aqui é
    // script de terceiro que alguém liberou sem passar por este teste — o
    // Monaco do jsdelivr era o caso, e agora vem de /monaco/vs.
    expect(csp.get("script-src")).toEqual(["'self'", "'unsafe-inline'", "https://static.cloudflareinsights.com"])
    // Os workers do Monaco e do MapLibre sobem de `blob:`.
    expect(csp.get("worker-src")).toEqual(["'self'", "blob:"])
    // O POST do beacon (cloudflareinsights.com/cdn-cgi/rum) cabe no `https:`.
    expect(csp.get("connect-src")).toEqual(["'self'", "https:", "wss:"])
    expect(csp.get("img-src")).toEqual(["'self'", "data:", "blob:", "https:"])
  })

  it("no `next dev` libera o que o dev usa fora da origem: eval do HMR, a API em outra porta e o MinIO http", async () => {
    vi.stubEnv("NODE_ENV", "development")
    vi.resetModules()
    const { default: configDev } = await import("@/next.config")
    const { valor } = await cabecalhos(configDev)
    const csp = diretivas(valor("Content-Security-Policy"))
    expect(csp.get("script-src")).toContain("'unsafe-eval'")
    // utils/env.ts: com NEXT_PUBLIC_API_PORT o WebSocket vai a ws://host:8000.
    expect(csp.get("connect-src")).toEqual(["'self'", "https:", "wss:", "http:", "ws:"])
    expect(csp.get("img-src")).toContain("http:")
    // Em HTTP o Chrome não entrega pelo Reporting API e, com `report-to`
    // presente, ignora o `report-uri`: no dev só o `report-uri` fica.
    expect(csp.get("report-to")).toBeUndefined()
    expect(csp.get("report-uri")).toEqual(["/api/csp-report"])
  })
})
