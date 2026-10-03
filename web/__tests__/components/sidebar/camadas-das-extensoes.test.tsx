import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import type { ExtensaoDoWeb } from "@/extensoes"

/**
 * The extensions' layers in the shell (`SidebarRoot`): each one is mounted
 * once, and one that breaks while rendering leaves the screen on its own — the
 * shell and the others stay.
 */

const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({
  ...(await original<typeof import("@/extensoes")>()),
  EXTENSOES: registro.EXTENSOES,
}))

import { ExtensionLayers } from "@/app/components/sidebar/camadas-das-extensoes"

afterEach(() => { cleanup(); registro.EXTENSOES.length = 0; vi.restoreAllMocks() })

function Crash(): never {
  throw new Error("defeito da extensão")
}

describe("as camadas das extensões", () => {
  it("sem extensão, nada", () => {
    const { container } = render(<ExtensionLayers />)
    expect(container.innerHTML).toBe("")
  })

  it("monta as camadas de cada extensão, uma vez", () => {
    registro.EXTENSOES.push(
      { nome: "a", camadas: [() => <p>camada a1</p>, () => <p>camada a2</p>] },
      { nome: "b", camadas: [() => <p>camada b</p>] },
    )
    render(<ExtensionLayers />)
    expect(screen.getAllByText(/^camada /).map(e => e.textContent)).toEqual(["camada a1", "camada a2", "camada b"])
  })

  it("uma camada que quebra sai da tela; as outras ficam", () => {
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    registro.EXTENSOES.push(
      { nome: "quebrada", camadas: [Crash] },
      { nome: "boa", camadas: [() => <p>camada boa</p>] },
    )
    render(<ExtensionLayers />)

    expect(screen.getByText("camada boa")).toBeTruthy()
    expect(erro.mock.calls.some(c => String(c[0]).includes("«quebrada»"))).toBe(true)
  })
})
