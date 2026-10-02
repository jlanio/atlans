/**
 * O layout raiz lê os fundos de mapa da instalação (MAPA_*) a cada pedido e os
 * entrega ao provider que o MapLibreMap consulta.
 *
 * Achado da revisão do lote D2: nenhum teste quebrava se o layout parasse de
 * montar o provider — o mapa cairia nas ruas do OpenStreetMap em silêncio. E o
 * valor tem de vir do ambiente em tempo de pedido, e não do build: a imagem do
 * web é a mesma para toda instalação.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { isValidElement, type ReactElement, type ReactNode } from "react"

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined }),
}))
vi.mock("@/app/fonts/inter", () => ({ inter: { variable: "font-inter" } }))
// O CSS do Tailwind não é o que se testa aqui, e processá-lo pede o PostCSS.
vi.mock("@/app/globals.css", () => ({}))

import RootLayout from "@/app/layout"
import { FundosDoMapaProvider } from "@/app/components/share/fundos-do-mapa"

function acharProvider(no: ReactNode): ReactElement<{ fundos: unknown }> | null {
  if (!isValidElement(no)) return null
  if (no.type === FundosDoMapaProvider) return no as ReactElement<{ fundos: unknown }>
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

describe("o layout raiz e os fundos de mapa", () => {
  it("passa ao provider os fundos lidos do ambiente no pedido", async () => {
    vi.stubEnv("MAPA_SATELITE_URL", "https://sat.example.org/{z}/{x}/{y}.jpg")
    vi.stubEnv("MAPA_SATELITE_CREDITO", "© Satélite de Exemplo")

    const arvore = await RootLayout({ children: <main /> })
    const provider = acharProvider(arvore)

    expect(provider).not.toBeNull()
    expect(provider!.props.fundos).toEqual({
      ruas: { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", credito: "© OpenStreetMap contributors" },
      satelite: { url: "https://sat.example.org/{z}/{x}/{y}.jpg", credito: "© Satélite de Exemplo" },
    })
  })

  it("sem MAPA_*, o provider recebe só as ruas", async () => {
    vi.stubEnv("MAPA_SATELITE_URL", "")
    vi.stubEnv("MAPA_HIBRIDO_URL", "")

    const provider = acharProvider(await RootLayout({ children: <main /> }))

    expect(provider!.props.fundos).toEqual({
      ruas: { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", credito: "© OpenStreetMap contributors" },
    })
  })
})
