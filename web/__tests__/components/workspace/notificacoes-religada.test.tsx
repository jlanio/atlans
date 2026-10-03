import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent, cleanup } from "@testing-library/react"

// "Notificações" section (webhook allowlist) mounted in the workspace panel.
//
// The whole vertical already existed and ran: the database column, the two
// endpoints, the mirrored Python test of the allowlist and — what matters most —
// enforcement in production. `run_result_consumer` BLOCKS the notification of a
// workflow whose host isn't on the allowlist, and the only record of that is a
// warning in the server log. Only the screen was missing: whoever configured a
// webhook and stopped receiving it had no way to see the allowlist or edit it.
//
// An audit classified the 430 LOC as dead code. The facts were right (zero
// render path) and the conclusion backwards: removing it would have destroyed
// the only interface of a rule that already blocks real traffic.

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getWorkspaceNotifications: vi.fn(),
    updateWorkspaceNotificationAllowlist: vi.fn(),
    getWorkspacePolicy: vi.fn().mockResolvedValue({
      status: 200, success: true,
      data: {
        workspace_id: "ws-a", mode: "pool", primary: [], fallback: [], fallback_terminal: "fail",
        effective_terminal: "fail", isolation_floor: "none", available_primary: 0, available_fallback: 0,
        pool: { total: 1, available: 1 }, policy_routing_enabled: true, target_executor_id: null,
      },
    }),
    getMyAgents: vi.fn().mockResolvedValue({ status: 200, success: true, data: [] }),
    listWorkspaceMembers: vi.fn().mockResolvedValue({ status: 200, success: true, data: [] }),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn() },
}))

// The sections load through `useFetchData`, which waits for the authenticated session.
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

const currentWorkspace = { id_hash: "ws-a", name: "A", my_role: "owner" }
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: currentWorkspace }),
  hasMinRole: () => true,
}))

import { GisFlowService } from "@/service/GisFlowService"
import { WorkspaceSettingsSheet } from "@/app/components/workspace/settings-sheet"

const getNotifs = vi.mocked(GisFlowService.getWorkspaceNotifications)

beforeEach(() => {
  cleanup()
  getNotifs.mockReset()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getNotifs.mockResolvedValue({
    status: 200, success: true,
    data: { allowlist: ["hooks.exemplo.com"], workflows: [] },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any)
})

function abrir() {
  return render(
    <WorkspaceSettingsSheet
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      workspace={currentWorkspace as any}
      currentUserId="u-1"
      onClose={() => {}}
    />,
  )
}

describe("painel do workspace — seção Notificações", () => {
  it("aparece na navegação", async () => {
    abrir()
    expect(await screen.findByRole("button", { name: /Notificações/i })).toBeTruthy()
  })

  it("carrega a allowlist do workspace ao abrir o painel", async () => {
    // The sections stay mounted and hidden on purpose (the component's comment
    // explains: it's what makes the rail's warnings worth anything), so the
    // fetch happens without needing a click.
    abrir()
    await waitFor(() => expect(getNotifs).toHaveBeenCalledWith("ws-a"))
  })

  it("mostra os hosts já configurados quando a seção é selecionada", async () => {
    abrir()
    fireEvent.click(await screen.findByRole("button", { name: /Notificações/i }))
    expect(await screen.findByText("hooks.exemplo.com")).toBeTruthy()
  })
})
