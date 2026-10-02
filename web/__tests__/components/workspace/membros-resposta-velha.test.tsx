import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, render, screen, waitFor } from "@testing-library/react"
import type { IWorkspaceMember } from "@/service/types"

/**
 * Seção «Membros» do painel do workspace: trocar o workspace com a lista do
 * anterior ainda em voo. Sem guarda, a resposta que chegasse por último
 * vencia — os membros do workspace ANTERIOR sob o nome do atual.
 */

const svc = vi.hoisted(() => ({ listWorkspaceMembers: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))
vi.mock("@/utils/createToast", () => ({ createToast: { success: vi.fn(), error: vi.fn() } }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

import { MembersSection } from "@/app/components/workspace/settings-sheet/members-section"

const membro = (username: string): IWorkspaceMember =>
  ({ user_id: `u-${username}`, username, email: `${username}@x.io`, role: "editor", joined_at: "2026-01-01T00:00:00" })

let pendentes: { ws: string; resolver: (r: unknown) => void }[] = []
function resolver(ws: string, membros: IWorkspaceMember[]) {
  const i = pendentes.findIndex(p => p.ws === ws)
  const [p] = pendentes.splice(i, 1)
  return act(async () => { p.resolver({ success: true, status: 200, data: membros }) })
}

beforeEach(() => {
  vi.clearAllMocks()
  pendentes = []
  svc.listWorkspaceMembers.mockImplementation((ws: string) => new Promise(r => { pendentes.push({ ws, resolver: r }) }))
})
afterEach(cleanup)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const workspace = (id_hash: string) => ({ id_hash, name: id_hash.toUpperCase() }) as any

describe("Membros — resposta do workspace anterior", () => {
  it("fora de ordem, a lista fica com a do workspace ATUAL", async () => {
    const { rerender } = render(<MembersSection workspace={workspace("ws-a")} canManage currentUserId="me" />)
    await waitFor(() => expect(pendentes.map(p => p.ws)).toEqual(["ws-a"]))

    rerender(<MembersSection workspace={workspace("ws-b")} canManage currentUserId="me" />)
    await waitFor(() => expect(pendentes.map(p => p.ws)).toEqual(["ws-a", "ws-b"]))

    await resolver("ws-b", [membro("beto")])
    await resolver("ws-a", [membro("alice")])

    expect(await screen.findByText("beto")).toBeInTheDocument()
    expect(screen.queryByText("alice")).toBeNull()
  })
})
