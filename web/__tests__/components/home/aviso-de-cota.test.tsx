import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import type { ExtensaoDoWeb } from "@/extensoes"

/**
 * O aviso de cota cheia, no núcleo.
 *
 * Ele diz o prazo REAL: o servidor manda `reabre_em_segundos`, o donut logo
 * abaixo já o usava, e «algumas horas» era a tela sabendo mais do que contava.
 *
 * E é o encaixe da oferta de uma extensão (`ofertaDaCota`): sem extensão, o
 * aviso é só o aviso; com uma, a oferta recebe o plano e se há o que vender. A
 * oferta dos planos tem testes na pasta da extensão.
 */

const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({ ...(await original<typeof import("@/extensoes")>()), EXTENSOES: registro.EXTENSOES }))

import { AvisoDeCotaCheia } from "@/app/components/home/assistente/aviso-de-cota"

const cota = (over = {}) => ({ gasto: 1_500_000, teto: 1_500_000, reabre_em_segundos: 22_320, ...over })

afterEach(() => { cleanup(); registro.EXTENSOES.length = 0 })

describe("a oferta é de uma extensão", () => {
  it("sem extensão, o aviso fica sozinho, sem botão", () => {
    render(<AvisoDeCotaCheia cota={cota()} plano="free" assinaturasAtivas />)

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
    render(<AvisoDeCotaCheia cota={cota()} plano="pro" assinaturasAtivas={false} />)

    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("oferta pro false")
  })

  it("uma oferta que quebra sai da tela; o aviso fica", () => {
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    registro.EXTENSOES.push({
      nome: "quebrada",
      ofertaDaCota: () => { throw new Error("defeito da extensão") },
    })
    render(<AvisoDeCotaCheia cota={cota()} plano="free" assinaturasAtivas />)

    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("Você usou a cota de hoje")
    expect(erro.mock.calls.some(c => String(c[0]).includes("«quebrada»"))).toBe(true)
    erro.mockRestore()
  })
})

describe("o aviso na tela", () => {
  it("diz o prazo REAL quando o servidor o manda", () => {
    render(<AvisoDeCotaCheia cota={cota({ reabre_em_segundos: 22_320 })} plano="free" assinaturasAtivas />)
    // 6 h 12 min. O donut logo abaixo já mostrava isto; o aviso dizia
    // «algumas horas» com o número na mão.
    expect(screen.getByTestId("aviso-de-cota").textContent).toMatch(/reabre em .*6/)
  })

  it("sem prazo conhecido, volta ao vago em vez de inventar", () => {
    render(<AvisoDeCotaCheia cota={cota({ reabre_em_segundos: null })} plano="free" assinaturasAtivas />)
    expect(screen.getByTestId("aviso-de-cota").textContent)
      .toContain("algumas horas depois da sua primeira conversa")
  })

  it("mostra o teto de quem está olhando, não um número fixo", () => {
    render(<AvisoDeCotaCheia cota={cota({ teto: 22_500_000 })} plano="pro" assinaturasAtivas />)
    expect(screen.getByTestId("aviso-de-cota").textContent).toContain("22.500.000")
  })
})
