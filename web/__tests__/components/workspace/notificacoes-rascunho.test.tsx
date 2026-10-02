import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

/**
 * Seção «Notificações»: o «Atualizar» traz a allowlist e os workflows atuais,
 * mas NÃO apaga em silêncio uma edição em andamento. Sem edição, o rascunho
 * acompanha o que o servidor devolveu; com edição, ele sobrevive à recarga.
 */

const svc = vi.hoisted(() => ({ getWorkspaceNotifications: vi.fn(), updateWorkspaceNotificationAllowlist: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))
vi.mock("@/utils/createToast", () => ({ createToast: { success: vi.fn(), error: vi.fn() } }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

import { NotificationsSection } from "@/app/components/workspace/settings-sheet/notifications-section"

const resposta = (allowlist: string[]) => ({ success: true, status: 200, data: { allowlist, workflows: [] } })

beforeEach(() => vi.clearAllMocks())
afterEach(cleanup)

describe("Notificações — o rascunho e o Atualizar", () => {
  it("sem edição, o Atualizar traz a allowlist nova para o rascunho", async () => {
    svc.getWorkspaceNotifications.mockResolvedValueOnce(resposta(["a.exemplo.com"])).mockResolvedValueOnce(resposta(["b.exemplo.com"]))
    render(<NotificationsSection workspaceId="ws-a" canManage />)
    expect(await screen.findByText("a.exemplo.com")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Atualizar allowlist" }))
    expect(await screen.findByText("b.exemplo.com")).toBeInTheDocument()
    expect(screen.queryByText("a.exemplo.com")).toBeNull()
    expect(screen.queryByText("Alterações não salvas")).toBeNull()
  })

  it("com edição em andamento, o rascunho sobrevive ao Atualizar", async () => {
    svc.getWorkspaceNotifications.mockResolvedValue(resposta(["a.exemplo.com"]))
    render(<NotificationsSection workspaceId="ws-a" canManage />)
    await screen.findByText("a.exemplo.com")

    const campo = screen.getByRole("textbox", { name: "Adicionar host" })
    fireEvent.change(campo, { target: { value: "c.exemplo.com" } })
    fireEvent.keyDown(campo, { key: "Enter" })
    expect(await screen.findByText("Alterações não salvas")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Atualizar allowlist" }))
    await waitFor(() => expect(svc.getWorkspaceNotifications).toHaveBeenCalledTimes(2))
    expect(await screen.findByText("c.exemplo.com")).toBeInTheDocument()
    expect(screen.getByText("a.exemplo.com")).toBeInTheDocument()
    expect(screen.getByText("Alterações não salvas")).toBeInTheDocument()
  })
})
