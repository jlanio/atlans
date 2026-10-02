// @vitest-environment node
/**
 * O coletor de relatos da CSP é público (o navegador posta sem sessão). Dois
 * limites: um LOTE do Reporting API — até um minuto de relatos, cada um com a
 * política inteira (~900 bytes) — tem de caber, e um corpo gigante sem
 * Content-Length (chunked) não pode ser bufferizado inteiro antes da recusa.
 */
import { describe, it, expect, vi, afterEach } from "vitest"

import { POST } from "@/app/api/csp-report/route"

afterEach(() => vi.restoreAllMocks())

const POLITICA = "default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; " +
  "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; ".repeat(6)

function relato(i: number) {
  return {
    type: "csp-violation",
    age: 10,
    url: "https://atlans.example.org/workflow/x",
    user_agent: "Mozilla/5.0",
    body: {
      documentURL: "https://atlans.example.org/workflow/x",
      effectiveDirective: "script-src-elem",
      blockedURL: `https://cdn.exemplo/${i}.js`,
      originalPolicy: POLITICA,
      disposition: "enforce",
      statusCode: 200,
    },
  }
}

describe("POST /api/csp-report", () => {
  it("aceita o lote de um minuto do Chrome (bem acima de 16 KB) e loga no máximo 20", async () => {
    const aviso = vi.spyOn(console, "warn").mockImplementation(() => {})
    const corpo = JSON.stringify(Array.from({ length: 25 }, (_, i) => relato(i)))
    expect(corpo.length).toBeGreaterThan(16 * 1024)

    const resp = await POST(new Request("http://x/api/csp-report", {
      method: "POST", body: corpo, headers: { "content-type": "application/reports+json" },
    }))

    expect(resp.status).toBe(204)
    expect(aviso).toHaveBeenCalledTimes(20)
    expect(String(aviso.mock.calls[0][1])).toContain('"disposicao":"enforce"')
  })

  it("recusa pelo Content-Length sem ler o corpo", async () => {
    const resp = await POST(new Request("http://x/api/csp-report", {
      method: "POST", body: "{}", headers: { "content-length": String(10 * 1024 * 1024) },
    }))
    expect(resp.status).toBe(413)
  })

  it("corpo sem Content-Length: para de ler no teto e cancela o resto", async () => {
    let lidos = 0
    let cancelado = false
    const pedaco = new Uint8Array(64 * 1024)
    const fluxo = new ReadableStream<Uint8Array>({
      pull(ctrl) {
        lidos += pedaco.byteLength
        ctrl.enqueue(pedaco)   // infinito: sem o teto, ninguém terminaria
      },
      cancel() { cancelado = true },
    })

    const resp = await POST(new Request("http://x/api/csp-report", {
      method: "POST", body: fluxo, duplex: "half",
    } as RequestInit))

    expect(resp.status).toBe(413)
    expect(cancelado).toBe(true)
    expect(lidos).toBeLessThanOrEqual(512 * 1024)
  })

  it("JSON inválido é 400", async () => {
    const resp = await POST(new Request("http://x/api/csp-report", { method: "POST", body: "{nao" }))
    expect(resp.status).toBe(400)
  })
})
