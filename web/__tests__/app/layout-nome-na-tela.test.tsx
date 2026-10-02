/**
 * O layout raiz lê NOME_NA_TELA a cada pedido e a entrega ao provider que a
 * marca e a tela de entrada consultam; o título da aba sai do mesmo valor. Sem
 * a variável, «Atlans»: a forma com o domínio é da instalação do titular
 * (TRADEMARKS.md) e não vai no código.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { isValidElement, type ReactElement, type ReactNode } from "react"

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined }),
}))
vi.mock("@/app/fonts/inter", () => ({ inter: { variable: "font-inter" } }))
vi.mock("@/app/globals.css", () => ({}))

import RootLayout, { generateMetadata } from "@/app/layout"
import { NomeNaTelaProvider } from "@/app/components/share/nome-na-tela"
import { lerNomeNaTelaDoAmbiente } from "@/lib/nome-na-tela"

function acharProvider(no: ReactNode): ReactElement<{ nome: string }> | null {
  if (!isValidElement(no)) return null
  if (no.type === NomeNaTelaProvider) return no as ReactElement<{ nome: string }>
  const filhos = (no.props as { children?: ReactNode }).children
  for (const filho of Array.isArray(filhos) ? filhos : [filhos]) {
    const achado = acharProvider(filho)
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

    const provider = acharProvider(await RootLayout({ children: <main /> }))

    expect(provider).not.toBeNull()
    expect(provider!.props.nome).toBe("Geo Exemplo")
    expect((await generateMetadata()).title).toBe("Geo Exemplo")
  })

  it("sem NOME_NA_TELA, «Atlans» nos dois", async () => {
    vi.stubEnv("NOME_NA_TELA", "")

    const provider = acharProvider(await RootLayout({ children: <main /> }))

    expect(provider!.props.nome).toBe("Atlans")
    expect((await generateMetadata()).title).toBe("Atlans")
  })

  it("um valor estranho volta ao padrão em vez de ir para a tela", () => {
    expect(lerNomeNaTelaDoAmbiente({ NOME_NA_TELA: "Minha Instalação" })).toBe("Minha Instalação")
    expect(lerNomeNaTelaDoAmbiente({ NOME_NA_TELA: "a".repeat(41) })).toBe("Atlans")
    expect(lerNomeNaTelaDoAmbiente({ NOME_NA_TELA: "<b>x</b>" })).toBe("Atlans")
    // Espaços e quebras de linha viram um espaço; um caractere de controle não passa.
    expect(lerNomeNaTelaDoAmbiente({ NOME_NA_TELA: "linha\nquebrada" })).toBe("linha quebrada")
    expect(lerNomeNaTelaDoAmbiente({ NOME_NA_TELA: "nome\u0007ruim" })).toBe("Atlans")
    expect(lerNomeNaTelaDoAmbiente({})).toBe("Atlans")
  })
})
