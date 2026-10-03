import { afterEach, expect, it, vi } from "vitest"
import { act, cleanup, render, screen } from "@testing-library/react"

// The real page; only the service, the session and what does not matter here are doubled.
const svc = vi.hoisted(() => ({
  getAgents: vi.fn(),
  getMyAgents: vi.fn(),
  getExecutorMetrics: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { role: "admin", id_hash: "me", agent_quota: 0 } }, status: "authenticated" }),
}))
vi.mock("@/app/hooks/useExecutorLocal", () => ({ useExecutorLocal: () => null }))
vi.mock("@/app/components/executores/dialogs", () => ({ CreateAgentDialog: () => null }))

import AgentsPage from "@/app/(dashboard)/executores/page"

afterEach(() => { cleanup(); vi.restoreAllMocks() })

const FALHA = { success: false, status: 500, error: { message: "fora do ar" } }

it("1ª carga em erro: o auto-refresh tenta de novo sem tirar o cartão da tela (um anúncio só)", async () => {
  // Each fetch stays pending until the test resolves it, like the real network:
  // it is in the middle of the fetch that the skeleton used to appear in place of the card.
  const pendentes: ((r: unknown) => void)[] = []
  svc.getAgents.mockImplementation(() => new Promise(r => { pendentes.push(r) }))
  svc.getExecutorMetrics.mockResolvedValue(FALHA)

  const intervalos: { fn: () => void; ms: number }[] = []
  const original = window.setInterval
  vi.spyOn(window, "setInterval").mockImplementation(((fn: () => void, ms: number) => {
    intervalos.push({ fn, ms })
    return original(() => {}, 1_000_000)
  }) as typeof window.setInterval)

  // Each inserted `role="alert"` node is a new announcement in the screen reader.
  let insercoes = 0
  const observador = new MutationObserver(mutacoes => {
    for (const m of mutacoes) for (const n of m.addedNodes) {
      if (n instanceof HTMLElement && (n.getAttribute("role") === "alert" || n.querySelector('[role="alert"]'))) insercoes++
    }
  })
  observador.observe(document.body, { childList: true, subtree: true })

  render(<AgentsPage />)
  await act(async () => { await Promise.resolve() })
  await act(async () => { pendentes.shift()!(FALHA) })
  const cartao = await screen.findByRole("alert")
  expect(cartao.textContent).toContain("Não foi possível carregar os executores")

  const tique = intervalos.find(i => i.ms === 15_000)!
  for (let k = 0; k < 3; k++) {
    await act(async () => { tique.fn() })
    // In flight: the same card, no skeleton.
    expect(screen.getByRole("alert")).toBe(cartao)
    expect(screen.queryByLabelText("Carregando os executores")).toBeNull()
    await act(async () => { pendentes.shift()!(FALHA) })
    expect(screen.getByRole("alert")).toBe(cartao)
  }
  expect(svc.getAgents).toHaveBeenCalledTimes(4)

  // Coming back to the tab is also a background reload.
  await act(async () => { document.dispatchEvent(new Event("visibilitychange")) })
  expect(screen.getByRole("alert")).toBe(cartao)
  await act(async () => { pendentes.shift()!(FALHA) })

  await new Promise(r => setTimeout(r, 0))
  observador.disconnect()
  expect(insercoes).toBe(1)

  // The server is back: the list takes the card's place, with no click.
  await act(async () => { tique.fn() })
  await act(async () => { pendentes.shift()!({ success: true, status: 200, data: [] }) })
  expect(screen.queryByRole("alert")).toBeNull()
})
