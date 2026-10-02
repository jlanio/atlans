import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen, fireEvent, act } from "@testing-library/react"

/**
 * O ATALHO da paleta. Até aqui a paleta só tinha teste puro (`itensVisiveis`) —
 * o Ctrl+K, o toggle e o comportamento com a sessão carregando não tinham
 * cobertura nenhuma, e é justamente o atalho que vira o portão da Home.
 *
 * Molde: `shell-sidebar.test.tsx` (pathname mutável) + `home-sidebar.test.tsx`
 * (sessão mutável, inclusive `status: "loading"`).
 */
const ctx = vi.hoisted(() => ({
  pathname: "/" as string | null,
  papel: undefined as string | undefined,
  // ESTÁVEL entre renders, como o `useRouter` de verdade. Um objeto novo a cada
  // render trocaria a identidade do `loadItems` (`useCallback` com `router` nas
  // deps), que é dependência do efeito de abertura — e o efeito se realimentaria
  // num laço infinito que só existe no teste.
  router: { push: (..._a: unknown[]) => {} },
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ctx.router,
  usePathname: () => ctx.pathname,
}))
vi.mock("next-auth/react", () => ({
  useSession: () =>
    ctx.papel === undefined
      ? { data: null, status: "loading" }
      : { data: { user: { role: ctx.papel } }, status: "authenticated" },
}))

const servico = vi.hoisted(() => ({ getWorkflows: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getWorkflows: servico.getWorkflows },
}))
vi.mock("@/app/stores/workflowCatalogStore", () => ({
  useWorkflowCatalogStore: {
    getState: () => ({
      ensureCredentials: () => Promise.resolve([]),
      ensureNodesAPI: () => Promise.resolve([]),
    }),
  },
}))

import CommandPalette from "@/app/components/command-palette"

/** Ctrl+K como o navegador o entrega: no `window`, que é onde o listener mora. */
function ctrlK() {
  fireEvent.keyDown(window, { key: "k", ctrlKey: true })
}

const aberta = () => screen.queryByPlaceholderText(/Buscar workflows/i)

beforeEach(() => {
  cleanup()
  ctx.pathname = "/"
  ctx.papel = "user"
  servico.getWorkflows.mockReset()
  servico.getWorkflows.mockResolvedValue({ data: [] })
})

describe("Ctrl+K — o portão da Home", () => {
  it("na Home, quem não é admin não abre a paleta", () => {
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeNull()
  })

  it("e nem chega a buscar os fluxos", async () => {
    // O GET saía a cada Ctrl+K. Sem abrir, `loadItems` não roda.
    render(<CommandPalette />)
    act(() => ctrlK())
    await act(async () => {})
    expect(servico.getWorkflows).not.toHaveBeenCalled()
  })

  it("na Home, o admin abre normalmente", () => {
    ctx.papel = "admin"
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeTruthy()
  })

  it("fora da Home, quem não é admin abre normalmente", () => {
    ctx.pathname = "/projects"
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeTruthy()
  })

  it("sessão carregando na Home: não abre (falha FECHADA)", () => {
    // `data` nulo enquanto o `useSession` resolve. Errar para o lado de abrir
    // piscaria uma paleta que some no render seguinte.
    ctx.papel = undefined
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeNull()
  })

  it("Esc fecha mesmo quando o portão está fechado", () => {
    // Fechar nunca depende de regra: um Esc preso é pior que qualquer portão.
    ctx.pathname = "/projects"
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeTruthy()
    act(() => { fireEvent.keyDown(window, { key: "Escape" }) })
    expect(aberta()).toBeNull()
  })

  it("aberta fora da Home, chegar na Home a fecha", () => {
    // Navegação client-side para `/` com a paleta aberta.
    ctx.pathname = "/projects"
    const { rerender } = render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeTruthy()

    ctx.pathname = "/"
    act(() => { rerender(<CommandPalette />) })
    expect(aberta()).toBeNull()
  })
})
