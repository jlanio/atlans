import { describe, it, expect, vi, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import Cookies from "js-cookie"

/**
 * The Preferences language picker: Automatic is a real option (the way back to
 * following the browser), each language in its own name, the choice writes the
 * cookie and the screen switches RIGHT AWAY, without reloading.
 */
vi.mock("@/context/ThemeContext", () => ({ useTheme: () => ({ theme: "dark", setTheme: vi.fn() }) }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { username: "fulana", email: "fulana@exemplo.com", role: "user" } }, status: "authenticated" }),
}))

import { UserPreferencesDialog } from "@/app/components/sidebar/user-preferences-dialog"
import { LanguageProvider } from "@/context/IdiomaContext"
import type { ResolvedLanguage } from "@/lib/idioma"

afterEach(() => {
  cleanup()
  Cookies.remove("idioma")
})

const montar = (inicial: ResolvedLanguage) =>
  render(
    <LanguageProvider inicial={inicial}>
      <UserPreferencesDialog open onOpenChange={() => {}} />
    </LanguageProvider>,
  )

const option = (nome: RegExp) => screen.getByRole("button", { name: nome })

describe("Preferências — Idioma", () => {
  it("no automático: Automático marcado, com o idioma detectado à vista", () => {
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    expect(screen.getByText("Idioma")).toBeTruthy()
    expect(option(/Automático/).getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByText("Detectado: Português (Brasil)")).toBeTruthy()
    for (const nome of [/^Português \(Brasil\)$/, /^English$/, /^Español$/]) {
      expect(option(nome).getAttribute("aria-pressed")).toBe("false")
    }
  })

  it("cada idioma aparece no próprio nome, com o `lang` dele", () => {
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    expect(screen.getByText("English").getAttribute("lang")).toBe("en")
    expect(screen.getByText("Español").getAttribute("lang")).toBe("es")
  })

  it("escolher English grava o cookie e a tela troca na hora", () => {
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    fireEvent.click(option(/^English$/))

    expect(Cookies.get("idioma")).toBe("en")
    // The dialog itself is already in English — without reloading.
    expect(screen.getByText("Preferences")).toBeTruthy()
    expect(screen.getByText("Language")).toBeTruthy()
    expect(option(/^English$/).getAttribute("aria-pressed")).toBe("true")
    expect(option(/Automatic/).getAttribute("aria-pressed")).toBe("false")
  })

  it("a escolha fica para as próximas visitas: cookie de 365 dias, não de sessão", () => {
    // `document.cookie` doesn't expose the expiry — only the value. Without
    // `expires` the cookie would die when the browser closed and the choice
    // would be lost.
    const set = vi.spyOn(Cookies, "set")
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    fireEvent.click(option(/^Español$/))
    expect(set).toHaveBeenCalledWith("idioma", "es", { expires: 365, sameSite: "lax" })
    set.mockRestore()
  })

  it("Automático apaga o cookie e volta ao detectado", () => {
    Cookies.set("idioma", "es")
    montar({ idioma: "es", detectado: "en", escolhido: "es" })
    expect(screen.getByText("Preferencias")).toBeTruthy()

    fireEvent.click(option(/Automático/))
    expect(Cookies.get("idioma")).toBeUndefined()
    // Back to the detected one (English).
    expect(screen.getByText("Preferences")).toBeTruthy()
    expect(screen.getByText("Detected: English")).toBeTruthy()
  })

  it("um router.refresh traz a escolha do servidor (o cookie mudou noutra aba)", () => {
    const arvore = (inicial: ResolvedLanguage) => (
      <LanguageProvider inicial={inicial}>
        <UserPreferencesDialog open onOpenChange={() => {}} />
      </LanguageProvider>
    )
    const { rerender } = render(arvore({ idioma: "en", detectado: "pt-BR", escolhido: "en" }))
    expect(screen.getByText("Preferences")).toBeTruthy()

    // In another tab the person went back to Automatic; the layout resolves
    // again and the provider, which doesn't remount, receives the new `inicial`.
    rerender(arvore({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null }))
    expect(screen.getByText("Preferências")).toBeTruthy()
    expect(option(/Automático/).getAttribute("aria-pressed")).toBe("true")
    expect(option(/^English$/).getAttribute("aria-pressed")).toBe("false")

    // E o inverso: a escolha feita noutra aba chega aqui.
    rerender(arvore({ idioma: "es", detectado: "pt-BR", escolhido: "es" }))
    expect(screen.getByText("Preferencias")).toBeTruthy()
    expect(option(/^Español$/).getAttribute("aria-pressed")).toBe("true")
  })

  it("a escolha feita nesta aba sobrevive ao refresh que devolve o mesmo valor", () => {
    const arvore = (inicial: ResolvedLanguage) => (
      <LanguageProvider inicial={inicial}>
        <UserPreferencesDialog open onOpenChange={() => {}} />
      </LanguageProvider>
    )
    const { rerender } = render(arvore({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null }))
    fireEvent.click(option(/^English$/))
    // The refresh from before the switch (the same `inicial`) doesn't undo the choice…
    rerender(arvore({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null }))
    expect(screen.getByText("Preferences")).toBeTruthy()
    // …and the one after returns what the person saved.
    rerender(arvore({ idioma: "en", detectado: "pt-BR", escolhido: "en" }))
    expect(screen.getByText("Preferences")).toBeTruthy()
    expect(option(/^English$/).getAttribute("aria-pressed")).toBe("true")
  })
})
