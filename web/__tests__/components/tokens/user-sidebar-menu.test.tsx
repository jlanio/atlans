import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import type { ComponentProps } from "react"
import type { ExtensaoDoWeb } from "@/extensoes"

/**
 * O menu do usuário oferece Tema, Configurações e Log out — e o que as
 * extensões somarem (`itensDaConta`; o item dos planos tem teste na pasta da
 * extensão).
 *
 * «Tokens de acesso» continua FORA, por decisão de produto (a página
 * /settings/tokens só abre para o administrador do sistema, que chega a ela
 * pela paleta Ctrl+K ou pela URL; quem não é admin pede o token a ele).
 *
 * Nenhum item daqui navega: o `proxy.ts:66` devolve `/` a quem não é admin,
 * então uma rota seria um beco sem saída.
 */

const roteador = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => roteador }))

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
  // Só o botão de verdade importa aqui; `size` é uma variante visual do original.
  SidebarMenuButton: ({ children, size: _size, ...props }: ComponentProps<"button"> & { size?: string }) => (
    <button {...props}>{children}</button>
  ),
}))

// O `className` é capturado: é por ele que o teste de tema vê a paleta que o
// menu repassa às Preferências.
vi.mock("@/app/components/sidebar/user-preferences-dialog", () => ({
  UserPreferencesDialog: (p: { className?: string }) => <div data-testid="prefs" data-classe={p.className ?? ""} />,
}))

// O núcleo sozinho; um teste pendura uma extensão de mentira.
const registro = vi.hoisted(() => ({ EXTENSOES: [] as ExtensaoDoWeb[] }))
vi.mock("@/extensoes", async (original) => ({ ...(await original<typeof import("@/extensoes")>()), EXTENSOES: registro.EXTENSOES }))

import UserSidebar from "@/app/components/sidebar/user-sidebar"
import { CodigoFonteProvider } from "@/app/components/share/codigo-fonte"
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
    // A Home é pública: abrir o modal em cima de quem acabou de sair seria insistência.
    await abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: /Log out/i }))
    expect(vi.mocked(signOut)).toHaveBeenCalledWith({ callbackUrl: "/" })
  })

  it("Configurações abre o diálogo de Preferências em vez de trocar de rota", async () => {
    // Um clique por abertura: o menu fecha ao selecionar, e clicar em fila
    // sobre nós já desmontados não mediria nada.
    await abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: /Configurações/i }))
    expect(roteador.push).not.toHaveBeenCalled()
    expect(sidebar.setOpenMobile).not.toHaveBeenCalled()
  })

  it("NENHUM item do menu navega", async () => {
    await abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: /Tema/i }))
    expect(roteador.push).not.toHaveBeenCalled()
  })

  it("com CODIGO_FONTE_URL, o código-fonte da instalação entra como link que abre fora (AGPL §13)", async () => {
    // Não é rota desta aplicação: é um <a> para fora, em outra aba. Sem a
    // variável (os outros testes), o item não existe.
    render(
      <CodigoFonteProvider url="https://codigo.example.org/fulana/atlans">
        <UserSidebar />
      </CodigoFonteProvider>,
    )
    fireEvent.keyDown(screen.getByRole("button"), { key: "Enter" })
    await screen.findByRole("menu")

    const itens = screen.getAllByRole("menuitem").map(i => i.textContent?.trim())
    expect(itens).toEqual(["Tema claro", "Configurações", "Código-fonte", "Log out"])
    const link = screen.getByRole("menuitem", { name: /Código-fonte/i })
    expect(link.tagName).toBe("A")
    expect(link.getAttribute("href")).toBe("https://codigo.example.org/fulana/atlans")
    expect(link.getAttribute("target")).toBe("_blank")
    expect(roteador.push).not.toHaveBeenCalled()
  })
})

describe("Menu do usuário — a paleta dos portais", () => {
  // O menu e as Preferências são portais no <body>, fora da árvore de quem os
  // abriu: a Home (sempre escura) passa `home-portal`, senão abriam claros por
  // cima dela. Sem a prop, o comportamento é o de sempre.
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
