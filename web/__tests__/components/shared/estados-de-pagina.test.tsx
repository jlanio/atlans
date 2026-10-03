/**
 * The state cards that lived inline in the pages (outside an `estados.tsx`):
 * the editor's first-load error (`/workflow/[id]`) and the portal's map with
 * no layers (`/share`). Same contract as the screens with their own module
 * (screen-patterns.md §3 and §5): the error announces itself with the message
 * and offers "Tentar de novo" (try again); the empty state keeps the usual text
 * and is not an alert.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "wf-1" }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

const getWorkflowById = vi.hoisted(() => vi.fn())
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: { getWorkflowById } }))

// The canvas is heavy (React Flow, Monaco) and isn't the subject here: the
// first-load error takes over the screen before it exists.
vi.mock("@/app/components/workflow", () => ({ default: () => <div data-testid="canvas" /> }))
vi.mock("@/context/useFlowContext", () => ({ FlowContextProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock("@xyflow/react", () => ({ ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
// React Flow's CSS would go through the app's PostCSS, which vitest doesn't load.
vi.mock("@xyflow/react/dist/style.css", () => ({}))

vi.mock("@/context/ThemeContext", () => ({ useTheme: () => ({ theme: "light", setTheme: () => {} }) }))
// With no layers the map doesn't even mount; the double just avoids loading MapLibre.
vi.mock("next/dynamic", () => ({ default: () => () => <div data-testid="mapa" /> }))

import WorkFlowCreatePage from "@/app/(dashboard)/workflow/[id]/page"
import WorkflowShareViewer from "@/app/components/share/WorkflowShareViewer"

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("editor (/workflow/[id]): erro de 1ª carga", () => {
  it("anuncia a falha com a mensagem do servidor, e «Tentar de novo» refaz a busca", async () => {
    getWorkflowById.mockResolvedValue({ success: false, status: 404, error: { message: "Workflow não encontrado." } })
    render(<WorkFlowCreatePage />)

    const alerta = await screen.findByRole("alert")
    expect(alerta).toHaveTextContent("Não foi possível carregar o workflow")
    expect(alerta).toHaveTextContent("Workflow não encontrado.")
    expect(alerta).toHaveClass("border-destructive/20")
    expect(screen.queryByTestId("canvas")).toBeNull()

    getWorkflowById.mockResolvedValue({ success: true, status: 200, data: { id: "wf-1" } })
    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar de novo" }))
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull())
    expect(getWorkflowById).toHaveBeenCalledTimes(2)
    expect(screen.getByTestId("canvas")).toBeInTheDocument()
  })
})

describe("portal (/share): mapa sem camadas", () => {
  it("o vazio canônico, rotulado pelo título, sem alerta", () => {
    render(<WorkflowShareViewer data={{ workflow_name: "Bacias", portal_access: "public", run_date: null, layers: [] }} />)
    const regiao = screen.getByRole("region", { name: "Nenhum dado disponível" })
    expect(regiao).toHaveTextContent("Execute o workflow com um nó PublishMap para ver dados aqui.")
    expect(screen.queryByRole("alert")).toBeNull()
    expect(screen.queryByTestId("mapa")).toBeNull()
  })
})
