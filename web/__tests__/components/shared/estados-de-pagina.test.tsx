/**
 * Os cartões de estado que moravam inline nas páginas (fora de um
 * `estados.tsx`): o erro de 1ª carga do editor (`/workflow/[id]`) e o mapa sem
 * camadas do portal (`/share`). Mesmo contrato das telas com módulo próprio
 * (screen-patterns.md §3 e §5): o erro anuncia com a mensagem e oferece "Tentar de
 * novo"; o vazio mantém o texto de sempre e não é alerta.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "wf-1" }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

const getWorkflowById = vi.hoisted(() => vi.fn())
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: { getWorkflowById } }))

// O canvas é pesado (React Flow, Monaco) e não é o objeto daqui: o erro de 1ª
// carga toma a tela antes dele existir.
vi.mock("@/app/components/workflow", () => ({ default: () => <div data-testid="canvas" /> }))
vi.mock("@/context/useFlowContext", () => ({ FlowContextProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
vi.mock("@xyflow/react", () => ({ ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <>{children}</> }))
// O CSS do React Flow passaria pelo PostCSS do app, que o vitest não carrega.
vi.mock("@xyflow/react/dist/style.css", () => ({}))

vi.mock("@/context/ThemeContext", () => ({ useTheme: () => ({ theme: "light", setTheme: () => {} }) }))
// Sem camadas o mapa nem monta; o dublê só evita carregar o MapLibre.
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
