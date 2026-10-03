import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { IAdminUser, IAdminUserListParams, IAdminUserListResponse } from "@/service/types"

/**
 * Admin › Users: every change of filter, page or search (debounced)
 * fires a new fetch, and the previous one stays in flight. Without a guard, whichever
 * RESOLVED last won: the response for an old filter arrived later
 * and overwrote the current filter's list — "Excluídos" (deleted) selected, and on screen
 * the suspended users.
 */

const svc = vi.hoisted(() => ({ getAdminUsers: vi.fn(), exportUsersCSV: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn(), loading: vi.fn() }))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { role: "admin", id_hash: "me" } }, status: "authenticated" }),
}))

import AdminUsersPage from "@/app/(dashboard)/admin/users/page"

function usuario(username: string, status: IAdminUser["status"]): IAdminUser {
  return {
    id_hash: `id-${username}`, username, email: `${username}@x.io`, status, role: "user", agent_quota: 0,
    workspace_id: null, last_login_at: null, suspended_at: null, deleted_at: null,
    created_at: "2026-01-01T00:00:00", updated_at: "2026-01-01T00:00:00",
  }
}

const pagina = (...items: IAdminUser[]): { success: true; status: 200; data: IAdminUserListResponse } =>
  ({ success: true, status: 200, data: { items, total: items.length, limit: 25, offset: 0 } })

/** Each fetch stays pending until the test resolves it — in whatever order it wants. */
let pendentes: { params: IAdminUserListParams; resolver: (r: unknown) => void }[] = []
function resolveForFilter(status: string | undefined, resposta: unknown) {
  const i = pendentes.findIndex(p => p.params.status === status)
  if (i < 0) throw new Error(`nenhuma busca pendente para status=${status}`)
  const [p] = pendentes.splice(i, 1)
  return act(async () => { p.resolver(resposta) })
}

beforeEach(() => {
  vi.clearAllMocks()
  pendentes = []
  svc.getAdminUsers.mockImplementation((params: IAdminUserListParams) =>
    new Promise(resolver => { pendentes.push({ params, resolver }) }))
})
afterEach(cleanup)

describe("Admin › Usuários — resposta de filtro antigo", () => {
  it("duas respostas fora de ordem: a tela fica com a do filtro ATUAL", async () => {
    render(<AdminUsersPage />)
    await waitFor(() => expect(svc.getAdminUsers).toHaveBeenCalledTimes(1))
    await resolveForFilter("active", pagina(usuario("ana", "active")))
    expect(await screen.findByText("ana")).toBeInTheDocument()

    // Two filter changes in a row: both fetches are in flight together.
    fireEvent.click(screen.getByRole("button", { name: "Suspensos" }))
    fireEvent.click(screen.getByRole("button", { name: "Excluídos" }))
    await waitFor(() => expect(pendentes.map(p => p.params.status)).toEqual(["suspended", "deleted"]))

    // The current filter's arrives first; the old filter's, afterward.
    await resolveForFilter("deleted", pagina(usuario("carla", "deleted")))
    await resolveForFilter("suspended", pagina(usuario("bruno", "suspended")))

    expect(screen.getByRole("button", { name: "Excluídos" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByText("carla")).toBeInTheDocument()
    expect(screen.queryByText("bruno")).toBeNull()
  })

  it("recarga que falha sobre a lista pronta mantém a lista e avisa por toast", async () => {
    render(<AdminUsersPage />)
    await waitFor(() => expect(svc.getAdminUsers).toHaveBeenCalledTimes(1))
    await resolveForFilter("active", pagina(usuario("ana", "active")))
    await screen.findByText("ana")

    fireEvent.click(screen.getByRole("button", { name: "Atualizar a lista de usuários" }))
    await waitFor(() => expect(pendentes).toHaveLength(1))
    await resolveForFilter("active", { success: false, status: 500, error: { name: "AxiosError", message: "boom" } })

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Não foi possível atualizar os usuários."))
    expect(screen.getByText("ana")).toBeInTheDocument()
    expect(screen.queryByText(/A listagem de contas não respondeu/)).toBeNull()
  })

  it("erro na 1ª carga: o cartão de erro, e sem toast", async () => {
    render(<AdminUsersPage />)
    await waitFor(() => expect(svc.getAdminUsers).toHaveBeenCalledTimes(1))
    await resolveForFilter("active", { success: false, status: 500, error: { name: "AxiosError", message: "boom" } })

    expect(await screen.findByText(/A listagem de contas não respondeu/)).toBeInTheDocument()
    expect(toast.error).not.toHaveBeenCalled()
  })
})
