import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import type { ExtensaoDoWeb } from "@/extensoes"

/**
 * The full-quota warning, in the core.
 *
 * It states the REAL time: the server sends `reabre_em_segundos`, the donut right
 * below already used it, and "algumas horas" (a few hours) was the screen knowing more than it said.
 *
 * And it is the slot for an extension's offer (`ofertaDaCota`): without an extension, the
 * warning is just the warning; with one, the offer receives the plan and whether there is something to sell. The
 * plans' offer has tests in the extension's folder.
 */

const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({ ...(await original<typeof import("@/extensoes")>()), EXTENSOES: registro.EXTENSOES }))

import { QuotaFullNotice } from "@/app/components/home/assistente/aviso-de-cota"

const cota = (over = {}) => ({ gasto: 1_500_000, teto: 1_500_000, reabre_em_segundos: 22_320, ...over })

afterEach(() => { cleanup(); registro.EXTENSOES.length = 0 })

describe("a oferta é de uma extensão", () => {
  it("sem extensão, o aviso fica sozinho, sem botão", () => {
    render(<QuotaFullNotice cota={cota()} plano="free" assinaturasAtivas />)

    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("Você usou a cota de hoje")
    expect(screen.queryByRole("button")).toBeNull()
  })

  it("a oferta da extensão entra no aviso, com o plano e as assinaturas", () => {
    registro.EXTENSOES.push({
      nome: "teste",
      ofertaDaCota: ({ plano, assinaturasAtivas }) => (
        <button type="button">oferta {plano} {String(assinaturasAtivas)}</button>
      ),
    })
    render(<QuotaFullNotice cota={cota()} plano="pro" assinaturasAtivas={false} />)

    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("oferta pro false")
  })

  it("uma oferta que quebra sai da tela; o aviso fica", () => {
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    registro.EXTENSOES.push({
      nome: "quebrada",
      ofertaDaCota: () => { throw new Error("defeito da extensão") },
    })
    render(<QuotaFullNotice cota={cota()} plano="free" assinaturasAtivas />)

    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("Você usou a cota de hoje")
    expect(erro.mock.calls.some(c => String(c[0]).includes("«quebrada»"))).toBe(true)
    erro.mockRestore()
  })
})

describe("o aviso na tela", () => {
  it("diz o prazo REAL quando o servidor o manda", () => {
    render(<QuotaFullNotice cota={cota({ reabre_em_segundos: 22_320 })} plano="free" assinaturasAtivas />)
    // 6 h 12 min. The donut right below already showed this; the warning said
    // "algumas horas" with the number in hand.
    expect(screen.getByTestId("aviso-de-cota").textContent).toMatch(/reabre em .*6/)
  })

  it("sem prazo conhecido, volta ao vago em vez de inventar", () => {
    render(<QuotaFullNotice cota={cota({ reabre_em_segundos: null })} plano="free" assinaturasAtivas />)
    expect(screen.getByTestId("aviso-de-cota").textContent)
      .toContain("algumas horas depois da sua primeira conversa")
  })

  it("mostra o teto de quem está olhando, não um número fixo", () => {
    render(<QuotaFullNotice cota={cota({ teto: 22_500_000 })} plano="pro" assinaturasAtivas />)
    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("22.500.000")
  })
})
