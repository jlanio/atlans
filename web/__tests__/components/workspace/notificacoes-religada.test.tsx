import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent, cleanup } from "@testing-library/react"

// Seção "Notificações" (allowlist de webhooks) montada no painel do workspace.
//
// A vertical inteira já existia e rodava: a coluna no banco, os dois endpoints,
// o teste Python espelhado da allowlist e — o que mais importa — o enforcement
// em produção. `run_result_consumer` BLOQUEIA a notificação de um workflow cujo
// host não está na allowlist, e o único registro disso é um warning no log do
// servidor. Faltava só a tela: quem configurava um webhook e parava de recebê-lo
// não tinha como ver a allowlist nem editá-la.
//
// Uma auditoria classificou os 430 LOC como código morto. Os fatos estavam
// certos (zero caminho de render) e a conclusão invertida: remover teria
// destruído a única interface de uma regra que já bloqueia tráfego real.

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

// As seções carregam pelo `useFetchData`, que espera a sessão autenticada.
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

const workspaceAtual = { id_hash: "ws-a", name: "A", my_role: "owner" }
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: workspaceAtual }),
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
      workspace={workspaceAtual as any}
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
    // As seções ficam montadas e ocultas de propósito (o comentário do
    // componente explica: é o que faz os avisos da rail valerem alguma coisa),
    // então a busca acontece sem precisar clicar.
    abrir()
    await waitFor(() => expect(getNotifs).toHaveBeenCalledWith("ws-a"))
  })

  it("mostra os hosts já configurados quando a seção é selecionada", async () => {
    abrir()
    fireEvent.click(await screen.findByRole("button", { name: /Notificações/i }))
    expect(await screen.findByText("hooks.exemplo.com")).toBeTruthy()
  })
})
