import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent, cleanup } from "@testing-library/react"

vi.mock("next-auth/react", () => ({ useSession: () => ({ data: { user: { access_token: "t" } }, status: "authenticated" }) }))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getDriveFiles: vi.fn() },
}))

// Switchable workspace — the header selector switches the context WITHOUT remounting the
// page, which is the reason the page/filter state survives the switch.
const currentWorkspace = { current: { id_hash: "ws-a", name: "A" } }
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: currentWorkspace.current, canEdit: true }),
}))

import { GisFlowService } from "@/service/GisFlowService"
import DrivePage from "@/app/(dashboard)/drive/page"

const getDriveFiles = vi.mocked(GisFlowService.getDriveFiles)

function arquivo(id: string, workspaceId: string) {
  return {
    id_hash: id, workspace_id: workspaceId, original_name: `${id}.csv`,
    extension: "csv", mime_type: "text/csv", size: 10, uploaded_by: null,
    created_at: "2026-08-28T12:00:00", updated_at: null, content_written_at: null,
    storage: "minio", executor_id: null,
  }
}

/** Responds according to the requested workspace: A has 300 files, B has 20. */
function responder() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getDriveFiles.mockImplementation(((params: any) => {
    const total = params.workspace_id === "ws-a" ? 300 : 20
    const pagina = params.page ?? 1
    const cabem  = Math.max(0, Math.min(50, total - (pagina - 1) * 50))
    const items  = Array.from({ length: cabem }, (_, i) =>
      arquivo(`${params.workspace_id}-p${pagina}-${i}`, params.workspace_id))
    return Promise.resolve({ status: 200, success: true, data: { items, total } })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  }) as any)
}

const lastCall = () => getDriveFiles.mock.calls.at(-1)![0]

beforeEach(() => { getDriveFiles.mockReset(); responder(); cleanup() })

describe("Drive — troca de workspace", () => {
  it("volta para a primeira página em vez de deixar o usuário numa lista vazia", async () => {
    currentWorkspace.current = { id_hash: "ws-a", name: "A" }
    const { rerender } = render(<DrivePage />)

    await waitFor(() => expect(getDriveFiles).toHaveBeenCalled())
    await screen.findByText("1 / 6")

    // Advances to page 4 of workspace A.
    for (const alvo of ["2 / 6", "3 / 6", "4 / 6"]) {
      const anterior = screen.getByText(alvo.replace(/^(\d)/, m => String(Number(m) - 1)))
      const proximo  = anterior.parentElement!.querySelectorAll("button")[1]
      fireEvent.click(proximo)
      await screen.findByText(alvo)
    }
    await waitFor(() => expect(lastCall().page).toBe(4))

    // Switch workspace in the selector: no remount, only the context changes.
    currentWorkspace.current = { id_hash: "ws-b", name: "B" }
    rerender(<DrivePage />)

    // The bug: the fetch went out with `workspace_id=B&page=4`, B only has 20 files, the
    // response came back empty and the pagination footer was not even mounted
    // (`total > PAGE_SIZE` is false with 20) — no control to get out of there.
    await waitFor(() => expect(lastCall().workspace_id).toBe("ws-b"))
    await waitFor(() => expect(lastCall().page).toBe(1))
    expect(getDriveFiles.mock.calls.every(([p]) => !(p.workspace_id === "ws-b" && (p.page ?? 1) > 1))).toBe(true)
  })
})
