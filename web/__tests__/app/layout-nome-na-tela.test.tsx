/**
 * The root layout reads NOME_NA_TELA on each request and hands it to the provider that the
 * brand mark and the sign-in screen consult; the tab title comes from the same value. Without
 * the variable, "Atlans": the form with the domain belongs to the holder's install
 * (TRADEMARKS.md) and does not go into the code.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { isValidElement, type ReactElement, type ReactNode } from "react"

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined }),
}))
vi.mock("@/app/fonts/inter", () => ({ inter: { variable: "font-inter" } }))
vi.mock("@/app/globals.css", () => ({}))

import RootLayout, { generateMetadata } from "@/app/layout"
import { DisplayNameProvider } from "@/app/components/share/nome-na-tela"
import { readDisplayNameFromEnv } from "@/lib/nome-na-tela"

function findProvider(no: ReactNode): ReactElement<{ nome: string }> | null {
  if (!isValidElement(no)) return null
  if (no.type === DisplayNameProvider) return no as ReactElement<{ nome: string }>
  const filhos = (no.props as { children?: ReactNode }).children
  for (const filho of Array.isArray(filhos) ? filhos : [filhos]) {
    const achado = findProvider(filho)
    if (achado) return achado
  }
  return null
}

afterEach(() => {
  vi.unstubAllEnvs()
})

describe("o layout raiz e o nome na tela", () => {
  it("passa ao provider e ao título da aba o nome lido do ambiente no pedido", async () => {
    vi.stubEnv("NOME_NA_TELA", "  Geo   Exemplo ")

    const provider = findProvider(await RootLayout({ children: <main /> }))

    expect(provider).not.toBeNull()
    expect(provider!.props.nome).toBe("Geo Exemplo")
    expect((await generateMetadata()).title).toBe("Geo Exemplo")
  })

  it("sem NOME_NA_TELA, «Atlans» nos dois", async () => {
    vi.stubEnv("NOME_NA_TELA", "")

    const provider = findProvider(await RootLayout({ children: <main /> }))

    expect(provider!.props.nome).toBe("Atlans")
    expect((await generateMetadata()).title).toBe("Atlans")
  })

  it("um valor estranho volta ao padrão em vez de ir para a tela", () => {
    expect(readDisplayNameFromEnv({ NOME_NA_TELA: "Minha Instalação" })).toBe("Minha Instalação")
    expect(readDisplayNameFromEnv({ NOME_NA_TELA: "a".repeat(41) })).toBe("Atlans")
    expect(readDisplayNameFromEnv({ NOME_NA_TELA: "<b>x</b>" })).toBe("Atlans")
    // Spaces and line breaks become one space; a control character does not get through.
    expect(readDisplayNameFromEnv({ NOME_NA_TELA: "linha\nquebrada" })).toBe("linha quebrada")
    expect(readDisplayNameFromEnv({ NOME_NA_TELA: "nome\u0007ruim" })).toBe("Atlans")
    expect(readDisplayNameFromEnv({})).toBe("Atlans")
  })
})
