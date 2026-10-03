import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import type { ComponentProps } from "react"
import type { ExtensaoDoWeb } from "@/extensoes"

/**
 * The user menu offers Theme, Settings and Log out — plus whatever the
 * extensions add (`itensDaConta`; the plans item is tested in the extension's
 * folder).
 *
 * "Tokens de acesso" (access tokens) stays OUT, by product decision (the page
 * /settings/tokens only opens for the system administrator, who reaches it
 * through the Ctrl+K palette or the URL; non-admins ask them for the token).
 *
 * No item here navigates: `proxy.ts:66` sends non-admins back to `/`, so a
 * route would be a dead end.
 */

const router = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => router }))

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { username: "fulana", email: "fulana@exemplo.com" } }, status: "authenticated" }),
  signOut: vi.fn(),
}))

vi.mock("@/context/ThemeContext", () => ({
  useTheme: () => ({ theme: "light", setTheme: vi.fn() }),
}))

const sidebar = vi.hoisted(() => ({ isMobile: false, setOpenMobile: vi.fn() }))
vi.mock("@/app/components/ui/sidebar", () => ({
  useSidebar: () => sidebar,
  // Only the real button matters here; `size` is a visual variant of the original.
  SidebarMenuButton: ({ children, size: _size, ...props }: ComponentProps<"button"> & { size?: string }) => (
    <button {...props}>{children}</button>
  ),
}))

// The `className` is captured: it's how the theme test sees the palette the
// menu passes on to Preferences.
vi.mock("@/app/components/sidebar/user-preferences-dialog", () => ({
  UserPreferencesDialog: (p: { className?: string }) => <div data-testid="prefs" data-classe={p.className ?? ""} />,
}))

// The core alone; one test hangs a fake extension on it.
const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({ ...(await original<typeof import("@/extensoes")>()), EXTENSOES: registro.EXTENSOES }))

import UserSidebar from "@/app/components/sidebar/user-sidebar"
import { SourceCodeProvider } from "@/app/components/share/codigo-fonte"
import { DropdownMenuItem } from "@/app/components/ui/dropdown-menu"
import { signOut } from "next-auth/react"

beforeEach(() => {
  vi.clearAllMocks()
  sidebar.isMobile = false
})
afterEach(() => { cleanup(); registro.EXTENSOES.length = 0 })

async function abrirMenu(props: ComponentProps<typeof UserSidebar> = {}) {
  render(<UserSidebar {...props} />)
  fireEvent.keyDown(screen.getByRole("button"), { key: "Enter" })
  return await screen.findByRole("menu")
}

describe("Menu do usuário — o que ele oferece", () => {
  it("oferece Tema, Configurações e Log out — e nada de tokens", async () => {
    const menu = await abrirMenu()
    expect(menu).toBeInTheDocument()
    const itens = screen.getAllByRole("menuitem").map(i => i.textContent?.trim())
    expect(itens).toEqual(["Tema claro", "Configurações", "Log out"])
    expect(screen.queryByRole("menuitem", { name: /tokens/i })).toBeNull()
  })

  it("uma extensão soma o item dela depois de Configurações, com a paleta do portal", async () => {
    registro.EXTENSOES.push({
      nome: "teste",
      itensDaConta: [({ portalClassName }) => (
        <DropdownMenuItem data-classe={portalClassName ?? ""}>Item da extensão</DropdownMenuItem>
      )],
    })
    await abrirMenu({ portalClassName: "home-portal" })

    const itens = screen.getAllByRole("menuitem").map(i => i.textContent?.trim())
    expect(itens).toEqual(["Tema claro", "Configurações", "Item da extensão", "Log out"])
    expect(screen.getByRole("menuitem", { name: "Item da extensão" }).getAttribute("data-classe"))
      .toBe("home-portal")
  })

  it("um item de extensão que quebra sai do menu; o resto fica", async () => {
    const erro = vi.spyOn(console, "error").mockImplementation(() => {})
    registro.EXTENSOES.push({
      nome: "quebrada",
      itensDaConta: [() => { throw new Error("defeito da extensão") }],
    })
    await abrirMenu()

    const itens = screen.getAllByRole("menuitem").map(i => i.textContent?.trim())
    expect(itens).toEqual(["Tema claro", "Configurações", "Log out"])
    expect(erro.mock.calls.some(c => String(c[0]).includes("«quebrada»"))).toBe(true)
    erro.mockRestore()
  })

  it("Log out cai na Home anônima, não no modal de entrada", async () => {
    // Home is public: opening the modal over someone who just logged out would be pushy.
    await abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: /Log out/i }))
    expect(vi.mocked(signOut)).toHaveBeenCalledWith({ callbackUrl: "/" })
  })

  it("Configurações abre o diálogo de Preferências em vez de trocar de rota", async () => {
    // One click per opening: the menu closes on select, and clicking in a row
    // on already-unmounted nodes wouldn't measure anything.
    await abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: /Configurações/i }))
    expect(router.push).not.toHaveBeenCalled()
    expect(sidebar.setOpenMobile).not.toHaveBeenCalled()
  })

  it("NENHUM item do menu navega", async () => {
    await abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: /Tema/i }))
    expect(router.push).not.toHaveBeenCalled()
  })

  it("com CODIGO_FONTE_URL, o código-fonte da instalação entra como link que abre fora (AGPL §13)", async () => {
    // It isn't a route of this application: it's an outbound <a>, in another
    // tab. Without the variable (the other tests), the item doesn't exist.
    render(
      <SourceCodeProvider url="https://codigo.example.org/fulana/atlans">
        <UserSidebar />
      </SourceCodeProvider>,
    )
    fireEvent.keyDown(screen.getByRole("button"), { key: "Enter" })
    await screen.findByRole("menu")

    const itens = screen.getAllByRole("menuitem").map(i => i.textContent?.trim())
    expect(itens).toEqual(["Tema claro", "Configurações", "Código-fonte", "Log out"])
    const link = screen.getByRole("menuitem", { name: /Código-fonte/i })
    expect(link.tagName).toBe("A")
    expect(link.getAttribute("href")).toBe("https://codigo.example.org/fulana/atlans")
    expect(link.getAttribute("target")).toBe("_blank")
    expect(router.push).not.toHaveBeenCalled()
  })
})

describe("Menu do usuário — a paleta dos portais", () => {
  // The menu and Preferences are portals in <body>, outside the tree of
  // whoever opened them: Home (always dark) passes `home-portal`, otherwise
  // they opened light on top of it. Without the prop, the behavior is the usual.
  it("repassa portalClassName ao menu e às Preferências", async () => {
    const menu = await abrirMenu({ portalClassName: "home-portal" })
    expect(menu.className).toContain("home-portal")
    expect(screen.getByTestId("prefs").getAttribute("data-classe")).toBe("home-portal")
  })

  it("sem a prop, nenhum dos dois ganha a paleta da Home", async () => {
    const menu = await abrirMenu()
    expect(menu.className).not.toContain("home-portal")
    expect(screen.getByTestId("prefs").getAttribute("data-classe")).toBe("")
  })
})
