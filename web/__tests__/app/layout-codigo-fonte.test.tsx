/**
 * The root layout reads CODIGO_FONTE_URL on each request and hands it to the provider that
 * the sign-in screen and the account menu consult (AGPL §13: whoever uses the
 * install over the network finds its source code). Without the variable, the provider
 * receives null and no link shows up: the code carries no address at all.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { isValidElement, type ReactElement, type ReactNode } from "react"

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => undefined }),
}))
vi.mock("@/app/fonts/inter", () => ({ inter: { variable: "font-inter" } }))
vi.mock("@/app/globals.css", () => ({}))

import RootLayout from "@/app/layout"
import { CodigoFonteProvider } from "@/app/components/share/codigo-fonte"
import { lerCodigoFonteDoAmbiente } from "@/lib/codigo-fonte"

function acharProvider(no: ReactNode): ReactElement<{ url: string | null }> | null {
  if (!isValidElement(no)) return null
  if (no.type === CodigoFonteProvider) return no as ReactElement<{ url: string | null }>
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

describe("o layout raiz e o código-fonte da instalação", () => {
  it("passa ao provider a URL lida do ambiente no pedido", async () => {
    vi.stubEnv("CODIGO_FONTE_URL", " https://codigo.example.org/fulana/atlans ")

    const provider = acharProvider(await RootLayout({ children: <main /> }))

    expect(provider).not.toBeNull()
    expect(provider!.props.url).toBe("https://codigo.example.org/fulana/atlans")
  })

  it("sem CODIGO_FONTE_URL, o provider recebe null", async () => {
    vi.stubEnv("CODIGO_FONTE_URL", "")

    const provider = acharProvider(await RootLayout({ children: <main /> }))

    expect(provider!.props.url).toBeNull()
  })

  it("só aceita uma URL http(s): o resto vira null, sem link torto na tela", () => {
    expect(lerCodigoFonteDoAmbiente({ CODIGO_FONTE_URL: "https://codigo.example.org/x" })).toBe("https://codigo.example.org/x")
    expect(lerCodigoFonteDoAmbiente({ CODIGO_FONTE_URL: "codigo.example.org/x" })).toBeNull()
    expect(lerCodigoFonteDoAmbiente({ CODIGO_FONTE_URL: "javascript:alert(1)" })).toBeNull()
    expect(lerCodigoFonteDoAmbiente({ CODIGO_FONTE_URL: "https://x y" })).toBeNull()
    expect(lerCodigoFonteDoAmbiente({})).toBeNull()
  })
})
