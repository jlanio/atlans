import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, render, screen, fireEvent, act } from "@testing-library/react"

/**
 * The palette SHORTCUT. Until now the palette only had a pure test (`itensVisiveis`) —
 * Ctrl+K, the toggle and the behavior while the session is loading had no
 * coverage at all, and it is precisely the shortcut that becomes the Home's gate.
 *
 * Template: `shell-sidebar.test.tsx` (mutable pathname) + `home-sidebar.test.tsx`
 * (mutable session, including `status: "loading"`).
 */
const ctx = vi.hoisted(() => ({
  pathname: "/" as string | null,
  papel: undefined as string | undefined,
  // STABLE across renders, like the real `useRouter`. A new object on every
  // render would change the identity of `loadItems` (`useCallback` with `router` in its
  // deps), which is a dependency of the open effect — and the effect would feed itself
  // in an infinite loop that only exists in the test.
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

/** Ctrl+K as the browser delivers it: on `window`, which is where the listener lives. */
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
    // The GET went out on every Ctrl+K. Without opening, `loadItems` does not run.
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
    // `data` is null while `useSession` resolves. Erring on the side of opening
    // would flash a palette that disappears on the next render.
    ctx.papel = undefined
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeNull()
  })

  it("Esc fecha mesmo quando o portão está fechado", () => {
    // Closing never depends on a rule: a stuck Esc is worse than any gate.
    ctx.pathname = "/projects"
    render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeTruthy()
    act(() => { fireEvent.keyDown(window, { key: "Escape" }) })
    expect(aberta()).toBeNull()
  })

  it("aberta fora da Home, chegar na Home a fecha", () => {
    // Client-side navigation to `/` with the palette open.
    ctx.pathname = "/projects"
    const { rerender } = render(<CommandPalette />)
    act(() => ctrlK())
    expect(aberta()).toBeTruthy()

    ctx.pathname = "/"
    act(() => { rerender(<CommandPalette />) })
    expect(aberta()).toBeNull()
  })
})
