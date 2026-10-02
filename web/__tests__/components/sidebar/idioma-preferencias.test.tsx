import { describe, it, expect, vi, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import Cookies from "js-cookie"

/**
 * O seletor de idioma das Preferências: Automático é uma opção de verdade (o
 * caminho de volta a seguir o navegador), cada idioma no próprio nome, a
 * escolha grava o cookie e a tela troca NA HORA, sem recarregar.
 */
vi.mock("@/context/ThemeContext", () => ({ useTheme: () => ({ theme: "dark", setTheme: vi.fn() }) }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { username: "fulana", email: "fulana@exemplo.com", role: "user" } }, status: "authenticated" }),
}))

import { UserPreferencesDialog } from "@/app/components/sidebar/user-preferences-dialog"
import { IdiomaProvider } from "@/context/IdiomaContext"
import type { IdiomaResolvido } from "@/lib/idioma"

afterEach(() => {
  cleanup()
  Cookies.remove("idioma")
})

const montar = (inicial: IdiomaResolvido) =>
  render(
    <IdiomaProvider inicial={inicial}>
      <UserPreferencesDialog open onOpenChange={() => {}} />
    </IdiomaProvider>,
  )

const opcao = (nome: RegExp) => screen.getByRole("button", { name: nome })

describe("Preferências — Idioma", () => {
  it("no automático: Automático marcado, com o idioma detectado à vista", () => {
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    expect(screen.getByText("Idioma")).toBeTruthy()
    expect(opcao(/Automático/).getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByText("Detectado: Português (Brasil)")).toBeTruthy()
    for (const nome of [/^Português \(Brasil\)$/, /^English$/, /^Español$/]) {
      expect(opcao(nome).getAttribute("aria-pressed")).toBe("false")
    }
  })

  it("cada idioma aparece no próprio nome, com o `lang` dele", () => {
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    expect(screen.getByText("English").getAttribute("lang")).toBe("en")
    expect(screen.getByText("Español").getAttribute("lang")).toBe("es")
  })

  it("escolher English grava o cookie e a tela troca na hora", () => {
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    fireEvent.click(opcao(/^English$/))

    expect(Cookies.get("idioma")).toBe("en")
    // O próprio diálogo já está em inglês — sem recarregar.
    expect(screen.getByText("Preferences")).toBeTruthy()
    expect(screen.getByText("Language")).toBeTruthy()
    expect(opcao(/^English$/).getAttribute("aria-pressed")).toBe("true")
    expect(opcao(/Automatic/).getAttribute("aria-pressed")).toBe("false")
  })

  it("a escolha fica para as próximas visitas: cookie de 365 dias, não de sessão", () => {
    // Pelo `document.cookie` não se lê a validade — só o valor. Sem `expires`
    // o cookie morreria ao fechar o navegador e a escolha se perderia.
    const set = vi.spyOn(Cookies, "set")
    montar({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null })
    fireEvent.click(opcao(/^Español$/))
    expect(set).toHaveBeenCalledWith("idioma", "es", { expires: 365, sameSite: "lax" })
    set.mockRestore()
  })

  it("Automático apaga o cookie e volta ao detectado", () => {
    Cookies.set("idioma", "es")
    montar({ idioma: "es", detectado: "en", escolhido: "es" })
    expect(screen.getByText("Preferencias")).toBeTruthy()

    fireEvent.click(opcao(/Automático/))
    expect(Cookies.get("idioma")).toBeUndefined()
    // Voltou ao detectado (inglês).
    expect(screen.getByText("Preferences")).toBeTruthy()
    expect(screen.getByText("Detected: English")).toBeTruthy()
  })

  it("um router.refresh traz a escolha do servidor (o cookie mudou noutra aba)", () => {
    const arvore = (inicial: IdiomaResolvido) => (
      <IdiomaProvider inicial={inicial}>
        <UserPreferencesDialog open onOpenChange={() => {}} />
      </IdiomaProvider>
    )
    const { rerender } = render(arvore({ idioma: "en", detectado: "pt-BR", escolhido: "en" }))
    expect(screen.getByText("Preferences")).toBeTruthy()

    // Noutra aba a pessoa voltou ao Automático; o layout resolve de novo e o
    // provider, que não remonta, recebe o `inicial` novo.
    rerender(arvore({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null }))
    expect(screen.getByText("Preferências")).toBeTruthy()
    expect(opcao(/Automático/).getAttribute("aria-pressed")).toBe("true")
    expect(opcao(/^English$/).getAttribute("aria-pressed")).toBe("false")

    // E o inverso: a escolha feita noutra aba chega aqui.
    rerender(arvore({ idioma: "es", detectado: "pt-BR", escolhido: "es" }))
    expect(screen.getByText("Preferencias")).toBeTruthy()
    expect(opcao(/^Español$/).getAttribute("aria-pressed")).toBe("true")
  })

  it("a escolha feita nesta aba sobrevive ao refresh que devolve o mesmo valor", () => {
    const arvore = (inicial: IdiomaResolvido) => (
      <IdiomaProvider inicial={inicial}>
        <UserPreferencesDialog open onOpenChange={() => {}} />
      </IdiomaProvider>
    )
    const { rerender } = render(arvore({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null }))
    fireEvent.click(opcao(/^English$/))
    // O refresh de antes da troca (o mesmo `inicial`) não desfaz a escolha…
    rerender(arvore({ idioma: "pt-BR", detectado: "pt-BR", escolhido: null }))
    expect(screen.getByText("Preferences")).toBeTruthy()
    // …e o de depois devolve o que ela gravou.
    rerender(arvore({ idioma: "en", detectado: "pt-BR", escolhido: "en" }))
    expect(screen.getByText("Preferences")).toBeTruthy()
    expect(opcao(/^English$/).getAttribute("aria-pressed")).toBe("true")
  })
})
