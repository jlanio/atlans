import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, waitFor, fireEvent, within } from "@testing-library/react"

// Admin screen "Piso de isolamento" (isolation floor, spec §4.5): only the platform
// administrator sets `no_pool`. Requiring asks for confirmation (it changes what runs where and
// can leave a workspace with no executor); releasing does not.

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { setWorkspaceIsolationFloor: vi.fn() },
}))
vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { IsolationFloorSection, hasNowhereToRun } from "@/app/components/admin/isolation-floor-section"
import type { IWorkspacePolicyAdmin } from "@/service/types"

const setFloor = vi.mocked(GisFlowService.setWorkspaceIsolationFloor)

function linha(extra: Partial<IWorkspacePolicyAdmin>): IWorkspacePolicyAdmin {
  return {
    id_hash: "ws-1", name: "Bacia", is_default: false, owner_id: "u-1", owner_username: "jl",
    mode: "dedicated_pool", isolation_floor: "none", fallback_terminal: "pool", effective_terminal: "pool",
    primary_count: 1, fallback_count: 0,
    ...extra,
  }
}

beforeEach(() => { cleanup(); vi.clearAllMocks() })

describe("piso de isolamento", () => {
  it("lista o modo e os níveis de cada workspace", () => {
    render(<IsolationFloorSection items={[linha({}), linha({ id_hash: "ws-2", name: "Defesa", mode: "isolated", isolation_floor: "no_pool", fallback_terminal: "fail", effective_terminal: "fail", primary_count: 2, fallback_count: 1 })]} onChanged={() => {}} />)
    expect(screen.getByText("Bacia")).toBeTruthy()
    expect(screen.getByText("Dedicado + pool")).toBeTruthy()
    expect(screen.getByText("2 principais · 1 reserva")).toBeTruthy()
    expect(screen.getByRole("switch", { name: "Exigir isolamento de Defesa" }).getAttribute("aria-checked")).toBe("true")
  })

  it("exigir pede confirmação e explica o que muda; só depois grava", async () => {
    setFloor.mockResolvedValue({ status: 200, success: true, data: { workspace_id: "ws-1", isolation_floor: "no_pool", fallback_terminal: "fail", terminal_forced_to_fail: true } })
    const onChanged = vi.fn()
    render(<IsolationFloorSection items={[linha({})]} onChanged={onChanged} />)

    fireEvent.click(screen.getByRole("switch", { name: "Exigir isolamento de Bacia" }))
    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText(/Exigir isolamento de «Bacia»/)).toBeTruthy()
    // Today it uses the pool as a last resort: that stops being true.
    expect(dialogo.textContent).toMatch(/deixa de valer/)
    expect(setFloor).not.toHaveBeenCalled()

    fireEvent.click(within(dialogo).getByRole("button", { name: "Exigir isolamento" }))
    await waitFor(() => expect(setFloor).toHaveBeenCalledWith("ws-1", "no_pool"))
    await waitFor(() => expect(onChanged).toHaveBeenCalled())
  })

  it("sem executor principal, o diálogo avisa que nada vai rodar", async () => {
    render(<IsolationFloorSection items={[linha({ mode: "pool", primary_count: 0, fallback_terminal: "fail", effective_terminal: "fail" })]} onChanged={() => {}} />)
    fireEvent.click(screen.getByRole("switch", { name: "Exigir isolamento de Bacia" }))
    const dialogo = await screen.findByRole("dialog")
    expect(dialogo.textContent).toMatch(/nada\s*roda/)
  })

  it("liberar não pede confirmação", async () => {
    setFloor.mockResolvedValue({ status: 200, success: true, data: { workspace_id: "ws-1", isolation_floor: "none", fallback_terminal: "fail", terminal_forced_to_fail: false } })
    render(<IsolationFloorSection items={[linha({ isolation_floor: "no_pool", mode: "isolated", effective_terminal: "fail" })]} onChanged={() => {}} />)
    fireEvent.click(screen.getByRole("switch", { name: "Exigir isolamento de Bacia" }))
    await waitFor(() => expect(setFloor).toHaveBeenCalledWith("ws-1", "none"))
    expect(screen.queryByRole("dialog")).toBeNull()
  })

  it("piso sem principal é o caso que vira pendência na visão geral", () => {
    expect(hasNowhereToRun(linha({ isolation_floor: "no_pool", primary_count: 0 }))).toBe(true)
    expect(hasNowhereToRun(linha({ isolation_floor: "no_pool", primary_count: 1 }))).toBe(false)
    expect(hasNowhereToRun(linha({ isolation_floor: "none", primary_count: 0 }))).toBe(false)
    render(<IsolationFloorSection items={[linha({ isolation_floor: "no_pool", mode: "isolated", primary_count: 0 })]} onChanged={() => {}} />)
    expect(screen.getByText(/sem executor principal: nada roda/)).toBeTruthy()
  })
})
