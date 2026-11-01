/**
 * `/workflow/[id]` loads the workflow on every id change without remounting:
 * /workflow/A → /workflow/B fires B's request while A's may still be in flight.
 * Whichever answered LAST used to win — a slow A landing after B put A's graph,
 * name and etag on the canvas under route B, and the next save (addressed by
 * the route id) wrote A over B. Only the latest load's answer is applied.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, render, screen } from "@testing-library/react"
import type { IWorkflow } from "@/service/types"

const rota = vi.hoisted(() => ({ id: "wf-a" }))
vi.mock("next/navigation", () => ({ useParams: () => ({ id: rota.id }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

const getWorkflowById = vi.hoisted(() => vi.fn())
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: { getWorkflowById } }))

// The canvas is not the subject: it only shows which workflow it was handed.
vi.mock("@/app/components/workflow", () => ({
  default: ({ workflow }: { workflow?: IWorkflow }) => <div data-testid="canvas">{workflow?.id_hash ?? "nenhum"}</div>,
}))
vi.mock("@/context/useFlowContext", () => ({ FlowContextProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock("@xyflow/react", () => ({ ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock("@xyflow/react/dist/style.css", () => ({}))

import WorkFlowPage from "@/app/(dashboard)/workflow/[id]/page"

type Resposta = { success: boolean; data?: Partial<IWorkflow>; error?: { message: string } }

/** One pending answer per requested id. */
function respostasAdiadas() {
  const pendentes = new Map<string, (r: Resposta) => void>()
  getWorkflowById.mockImplementation((id: string) => new Promise<Resposta>(r => { pendentes.set(id, r) }))
  return (id: string, r: Resposta) => act(async () => { pendentes.get(id)?.(r) })
}

const ok = (id_hash: string): Resposta => ({ success: true, data: { id_hash, name: id_hash } })

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  rota.id = "wf-a"
})

describe("/workflow/[id]: só a resposta do id atual entra", () => {
  it("A lenta chegando depois de B não hidrata A sob a rota de B", async () => {
    const responder = respostasAdiadas()
    const { rerender } = render(<WorkFlowPage />)

    rota.id = "wf-b"
    rerender(<WorkFlowPage />)
    expect(getWorkflowById.mock.calls.map(c => c[0])).toEqual(["wf-a", "wf-b"])

    await responder("wf-b", ok("wf-b"))
    expect(screen.getByTestId("canvas").textContent).toBe("wf-b")

    await responder("wf-a", ok("wf-a"))
    expect(screen.getByTestId("canvas").textContent).toBe("wf-b")
  })

  it("o erro de uma carga velha também não toma a tela", async () => {
    const responder = respostasAdiadas()
    const { rerender } = render(<WorkFlowPage />)
    rota.id = "wf-b"
    rerender(<WorkFlowPage />)

    await responder("wf-b", ok("wf-b"))
    await responder("wf-a", { success: false, error: { message: "sumiu" } })

    expect(screen.getByTestId("canvas").textContent).toBe("wf-b")
    expect(screen.queryByText("sumiu")).toBeNull()
  })
})
