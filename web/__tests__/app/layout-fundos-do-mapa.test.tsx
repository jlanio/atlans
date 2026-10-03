/**
 * The root layout reads the install's map backgrounds (MAPA_*) on each request and
 * hands them to the provider that MapLibreMap consults.
 *
 * Finding from the batch D2 review: no test broke if the layout stopped
 * mounting the provider — the map would silently fall back to OpenStreetMap streets. And the
 * value has to come from the environment at request time, not from the build: the web
 * image is the same for every install.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { isValidElement, type ReactElement, type ReactNode } from "react"

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined }),
}))
vi.mock("@/app/fonts/inter", () => ({ inter: { variable: "font-inter" } }))
// Tailwind's CSS is not what is tested here, and processing it requires PostCSS.
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
