import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IAdminUser, IExecutor } from "@/service/types"

/**
 * The action dialogs of Admin › Users and of Executors.
 *
 * The defect the duplication produced: the dialog's field called the SAME
 * function as the button on Enter, and that function didn't look at "loading" —
 * only the button, being `disabled`, was protected. Pressing Enter twice on a
 * slow action (or Enter and then the click) fired the call twice: two DELETEs,
 * two revocations, and in the batch revocation the quota→revoke sequence ran
 * twice.
 *
 * Here every action is SLOW (the promise only resolves when the test says so):
 * that is the window in which the second Enter used to arrive.
 */

const svc = vi.hoisted(() => ({
  suspendUser: vi.fn(),
  adminDeleteUser: vi.fn(),
  updateUserAgentQuota: vi.fn(),
  getUserAgentStats: vi.fn(),
  revokeAllUserAgents: vi.fn(),
  updateAgent: vi.fn(),
  revokeAgent: vi.fn(),
  deleteAgent: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn(), loading: vi.fn() }))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

// Menu passthrough (same double as chats-lista): without Radix's portal/pointer,
// the item becomes a button and its `onSelect` is what opens the dialog.
vi.mock("@/app/components/ui/dropdown-menu", () => ({
  DropdownMenuItem: ({ children, onSelect, className }: { children: React.ReactNode; onSelect?: (e: React.MouseEvent) => void; className?: string }) => (
    <button type="button" onClick={onSelect} className={className}>{children}</button>
  ),
}))

import {
  ChangeAgentQuotaDialog, DeleteUserDialog, SuspendUserDialog,
} from "@/app/components/admin/users/dialogs"
import {
  DeleteAgentDialog, EditAgentDialog, RevokeAgentDialog,
} from "@/app/components/executores/dialogs"

/** A call that only finishes when the test says so. */
function lenta<T>() {
  let resolver!: (valor: T) => void
  const promessa = new Promise<T>(res => { resolver = res })
  return { promessa, resolver }
}

const USUARIO: IAdminUser = {
  id_hash: "u-1", username: "fulano", email: "f@x.io", status: "active", role: "user",
  agent_quota: 3, workspace_id: null, last_login_at: null, suspended_at: null, deleted_at: null,
  created_at: "2026-01-01T00:00:00", updated_at: "2026-01-01T00:00:00",
}

const EXECUTOR: IExecutor = {
  id_hash: "ex-1", name: "geo-01", description: null, status: "active", executor_type: "dedicated",
  is_default: false, capabilities: [], max_concurrent_jobs: 1, max_queue_size: 10, executor_version: null,
  last_seen_at: null, created_at: "2026-01-01T00:00:00", created_by: "me", online: true, capacity: null,
  connected_at: null, system_info: null,
}

const enter = (el: HTMLElement) => fireEvent.keyDown(el, { key: "Enter", code: "Enter" })

beforeEach(() => {
  vi.clearAllMocks()
  svc.getUserAgentStats.mockResolvedValue({ success: true, status: 200, data: { created: 3 } })
})
afterEach(cleanup)

describe("Enter numa ação lenta chama o serviço UMA vez", () => {
  it("Excluir usuário: Enter, Enter e o clique viram um DELETE só", async () => {
    const acao = lenta<unknown>()
    svc.adminDeleteUser.mockReturnValue(acao.promessa)
    render(<DeleteUserDialog user={USUARIO} onCompleted={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Excluir/ }))
    const dialogo = await screen.findByRole("dialog")
    const campo = within(dialogo).getByPlaceholderText("fulano")
    fireEvent.change(campo, { target: { value: "fulano" } })

    enter(campo)
    enter(campo)
    fireEvent.click(within(dialogo).getByRole("button", { name: /Excluindo|Excluir/ }))

    expect(svc.adminDeleteUser).toHaveBeenCalledTimes(1)
    acao.resolver({ success: true, status: 200, data: null })
    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(svc.adminDeleteUser).toHaveBeenCalledTimes(1)
  })

  it("Cota de executores: Enter duas vezes grava a cota uma vez", async () => {
    const acao = lenta<unknown>()
    svc.updateUserAgentQuota.mockReturnValue(acao.promessa)
    render(<ChangeAgentQuotaDialog user={USUARIO} onCompleted={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Cota de executores/ }))
    const dialogo = await screen.findByRole("dialog")
    const campo = within(dialogo).getByLabelText("Limite de executores dedicados")
    fireEvent.change(campo, { target: { value: "5" } })

    enter(campo)
    enter(campo)

    expect(svc.updateUserAgentQuota).toHaveBeenCalledTimes(1)
    acao.resolver({ success: true, status: 200, data: {} })
    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(svc.updateUserAgentQuota).toHaveBeenCalledTimes(1)
  })

  it("Revogar todos: Enter duas vezes roda a sequência cota→revoke uma vez", async () => {
    const cota = lenta<unknown>()
    svc.updateUserAgentQuota.mockReturnValue(cota.promessa)
    svc.revokeAllUserAgents.mockResolvedValue({ success: true, status: 200, data: { revoked_count: 3, affected_workspaces: 1 } })
    render(<ChangeAgentQuotaDialog user={USUARIO} onCompleted={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Cota de executores/ }))
    const dialogo = await screen.findByRole("dialog")
    // Reducing below the 3 existing ones is what offers the batch revocation.
    await within(dialogo).findByText(/Atualmente possui/)
    fireEvent.change(within(dialogo).getByLabelText("Limite de executores dedicados"), { target: { value: "0" } })
    fireEvent.click(within(dialogo).getByRole("button", { name: /Revogar todos/ }))

    const revogar = await screen.findByRole("dialog", { name: /Revogar todos os executores/ })
    const campo = within(revogar).getByPlaceholderText("REVOGAR")
    fireEvent.change(campo, { target: { value: "REVOGAR" } })
    enter(campo)
    enter(campo)

    expect(svc.updateUserAgentQuota).toHaveBeenCalledTimes(1)
    cota.resolver({ success: true, status: 200, data: {} })
    await waitFor(() => expect(svc.revokeAllUserAgents).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(svc.updateUserAgentQuota).toHaveBeenCalledTimes(1)
    expect(svc.revokeAllUserAgents).toHaveBeenCalledTimes(1)
  })

  it("Editar executor: Enter duas vezes salva uma vez", async () => {
    const acao = lenta<unknown>()
    svc.updateAgent.mockReturnValue(acao.promessa)
    render(<EditAgentDialog executor={EXECUTOR} onUpdated={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Editar executor/ }))
    const dialogo = await screen.findByRole("dialog")
    const campo = within(dialogo).getByLabelText("Nome *")
    fireEvent.change(campo, { target: { value: "geo-01b" } })

    enter(campo)
    enter(campo)

    expect(svc.updateAgent).toHaveBeenCalledTimes(1)
    acao.resolver({ success: true, status: 200, data: { ...EXECUTOR, name: "geo-01b" } })
    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(svc.updateAgent).toHaveBeenCalledTimes(1)
  })

  it("Revogar executor: Enter duas vezes revoga uma vez", async () => {
    const acao = lenta<unknown>()
    svc.revokeAgent.mockReturnValue(acao.promessa)
    render(<RevokeAgentDialog executor={EXECUTOR} onRevoked={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Revogar executor/ }))
    const dialogo = await screen.findByRole("dialog")
    const campo = within(dialogo).getByPlaceholderText("geo-01")
    fireEvent.change(campo, { target: { value: "geo-01" } })

    enter(campo)
    enter(campo)

    expect(svc.revokeAgent).toHaveBeenCalledTimes(1)
    acao.resolver({ success: true, status: 204 })
    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(svc.revokeAgent).toHaveBeenCalledTimes(1)
  })
})

describe("enquanto a ação roda, o diálogo não fecha", () => {
  it("Suspender: Esc, o X e o Cancelar ficam travados até a resposta", async () => {
    const acao = lenta<unknown>()
    svc.suspendUser.mockReturnValue(acao.promessa)
    render(<SuspendUserDialog user={USUARIO} onCompleted={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Suspender/ }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Suspender" }))

    fireEvent.keyDown(dialogo, { key: "Escape", code: "Escape" })
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    expect(within(dialogo).getByRole("button", { name: "Fechar" })).toBeDisabled()
    expect(within(dialogo).getByRole("button", { name: "Cancelar" })).toBeDisabled()

    acao.resolver({ success: true, status: 200, data: {} })
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
    expect(toast.success).toHaveBeenCalledWith("Usuário «fulano» suspenso.")
  })
})

describe("o 409 da política continua pedindo o «mesmo assim»", () => {
  const conflito = {
    success: false, status: 409,
    error: {
      name: "AxiosError", message: "conflito", code: "workspace_policy_conflict",
      workspaces: [{ workspace_id: "ws-1", workspace_name: "Bacia" }],
    },
  }

  it("revogar: o 409 vira o aviso na tela (sem toast) e a confirmação seguinte vai com force", async () => {
    svc.revokeAgent.mockResolvedValueOnce(conflito).mockResolvedValueOnce({ success: true, status: 204 })
    const onRevoked = vi.fn()
    render(<RevokeAgentDialog executor={EXECUTOR} onRevoked={onRevoked} />)

    fireEvent.click(screen.getByRole("button", { name: /Revogar executor/ }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.change(within(dialogo).getByPlaceholderText("geo-01"), { target: { value: "geo-01" } })
    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))

    const aviso = await within(dialogo).findByRole("alert")
    expect(aviso).toHaveTextContent("Bacia")
    expect(aviso).toHaveTextContent(/Ao revogar mesmo assim/)
    expect(toast.error).not.toHaveBeenCalled()
    expect(svc.revokeAgent).toHaveBeenLastCalledWith("ex-1", false)

    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar mesmo assim" }))
    await waitFor(() => expect(svc.revokeAgent).toHaveBeenLastCalledWith("ex-1", true))
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Executor revogado."))
    expect(onRevoked).toHaveBeenCalledTimes(1)
  })

  it("remover: mesmo fluxo, com o rótulo de remover", async () => {
    svc.deleteAgent.mockResolvedValueOnce(conflito).mockResolvedValueOnce({ success: true, status: 204 })
    const onDeleted = vi.fn()
    render(<DeleteAgentDialog executor={EXECUTOR} onDeleted={onDeleted} />)

    fireEvent.click(screen.getByRole("button", { name: /Remover executor/ }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Remover" }))

    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(/Ao remover mesmo assim/)
    expect(toast.error).not.toHaveBeenCalled()

    fireEvent.click(within(dialogo).getByRole("button", { name: "Remover mesmo assim" }))
    await waitFor(() => expect(svc.deleteAgent).toHaveBeenLastCalledWith("ex-1", true))
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Executor removido."))
    expect(onDeleted).toHaveBeenCalledTimes(1)
  })

  it("outro erro continua virando toast, com o título de sempre", async () => {
    svc.revokeAgent.mockResolvedValue({ success: false, status: 500, error: { name: "AxiosError", message: "boom" } })
    render(<RevokeAgentDialog executor={EXECUTOR} onRevoked={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /Revogar executor/ }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.change(within(dialogo).getByPlaceholderText("geo-01"), { target: { value: "geo-01" } })
    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Erro ao revogar executor", "boom"))
    expect(screen.getByRole("dialog")).toBeInTheDocument()
  })
})
