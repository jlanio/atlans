/**
 * A service failure is not an empty list.
 *
 * `GisFlowService` NEVER rejects: a network drop, a 4xx and a 5xx come back
 * resolved, with `error` filled in and `data` undefined (service/http.ts). The
 * `try/catch` blocks around the calls were dead code, and whoever read only
 * `data` turned the failure into a false statement:
 *
 * - a run's log "expirou" (expired) when the network dropped (history-empty);
 * - "nenhuma execução registrada" (no run recorded) when the list never even
 *   arrived (history-empty and the recent runs popover);
 * - "nenhum artefato"/"nenhum arquivo no Drive" (no artifact / no file in
 *   Drive) in the node's pickers.
 *
 * In all of them, the failure now warns (a toast with the server's message, the
 * pattern of the editor's neighboring screens) and the "empty" spot says it
 * couldn't load.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "wf-1" }),
  useRouter: () => ({ push: vi.fn() }),
}))

const servico = vi.hoisted(() => ({
  getObservabilityRuns: vi.fn(),
  getRunEvents: vi.fn(),
  getWorkflowMetrics: vi.fn(),
  executeWorkflow: vi.fn(),
  getArtifacts: vi.fn(),
  getDriveFiles: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

const toast = vi.hoisted(() => ({
  error: vi.fn(), info: vi.fn(), success: vi.fn(), warning: vi.fn(), loading: vi.fn(),
}))
vi.mock("@/utils/createToast", () => ({ createToast: toast }))

vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-1" }, canExecute: true, canEdit: true }),
}))

import HistoryEmpty from "@/app/components/workflow/run-panel/history-empty"
import RecentRuns from "@/app/components/workflow/buttons/recent-runs"
import ArtifactField from "@/app/components/workflow/nodes-configuration/fields/artifact-field"
import DriveField from "@/app/components/workflow/nodes-configuration/fields/drive-field"
import type { INodesPropertyAPI } from "@/service/types"

/* eslint-disable @typescript-eslint/no-explicit-any */
const ok = (data: unknown) => ({ status: 200, success: true, data }) as any
/** What `resolveAxiosError` returns on a network drop (no response from the server). */
const falha = (message = "Erro inesperado.", status = 500) =>
  ({ status, success: false, error: { name: "AxiosError", message } }) as any
/* eslint-enable @typescript-eslint/no-explicit-any */

const RUN = {
  run_id: "run-1", workflow_id: "wf-1", status: "success",
  started_at: "2026-09-30T12:00:00", finished_at: "2026-09-30T12:00:05", duration_seconds: 5,
}

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("history-empty", () => {
  it("erro de rede ao abrir o log NÃO diz que o histórico expirou", async () => {
    servico.getObservabilityRuns.mockResolvedValue(ok({ total: 1, limit: 5, offset: 0, runs: [RUN] }))
    servico.getRunEvents.mockResolvedValue(falha("Erro inesperado."))

    render(<HistoryEmpty />)
    fireEvent.click(await screen.findByRole("button", { name: /5\.00s/ }))

    // Waits for ANY warning to come out, to then check which one it was.
    await waitFor(() => expect(toast.error.mock.calls.length + toast.info.mock.calls.length).toBeGreaterThan(0))
    // "Expirou" (expired) is the verdict for a response that ARRIVED empty — not for one
    // that never arrived.
    expect(toast.info).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar o log da execução", "Erro inesperado.")
  })

  it("o log vazio de verdade continua dizendo que expirou", async () => {
    servico.getObservabilityRuns.mockResolvedValue(ok({ total: 1, limit: 5, offset: 0, runs: [RUN] }))
    servico.getRunEvents.mockResolvedValue(ok({ run_id: "run-1", events: [], expired: true }))

    render(<HistoryEmpty />)
    fireEvent.click(await screen.findByRole("button", { name: /5\.00s/ }))

    await waitFor(() => expect(toast.info).toHaveBeenCalledWith(
      "Log indisponível", "O histórico desta execução expirou (mantido por 1 hora).",
    ))
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("a lista que falhou não diz 'Nenhuma execução registrada'", async () => {
    servico.getObservabilityRuns.mockResolvedValue(falha("Sessão expirada.", 401))

    render(<HistoryEmpty />)

    expect(await screen.findByText(/Não foi possível carregar as execuções/)).toBeInTheDocument()
    expect(screen.queryByText(/Nenhuma execução registrada/)).toBeNull()
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar execuções recentes", "Sessão expirada.")
  })
})

describe("execuções recentes (popover do editor)", () => {
  it("a lista que falhou não diz 'Nenhuma execução registrada ainda'", async () => {
    servico.getWorkflowMetrics.mockResolvedValue(falha("Erro inesperado."))

    render(<RecentRuns />)
    fireEvent.click(screen.getByTitle("Execuções recentes"))

    expect(await screen.findByText(/Não foi possível carregar as execuções/)).toBeInTheDocument()
    expect(screen.queryByText(/Nenhuma execução registrada/)).toBeNull()
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar execuções recentes", "Erro inesperado.")
  })

  it("sem execuções de verdade, o vazio continua o de sempre", async () => {
    servico.getWorkflowMetrics.mockResolvedValue(ok({ last_runs: [] }))

    render(<RecentRuns />)
    fireEvent.click(screen.getByTitle("Execuções recentes"))

    expect(await screen.findByText("Nenhuma execução registrada ainda.")).toBeInTheDocument()
    expect(toast.error).not.toHaveBeenCalled()
  })
})

describe("seletores do nó", () => {
  const campo = (over: Partial<INodesPropertyAPI> = {}) =>
    ({ name: "alvo", type: "string", default: "", description: "Alvo", ...over }) as INodesPropertyAPI

  it("artefatos: a falha não diz 'Nenhum artefato neste workspace'", async () => {
    servico.getArtifacts.mockResolvedValue(falha("Erro inesperado."))

    render(<ArtifactField field={campo()} values={{}} setNodeField={vi.fn()} />)

    expect(await screen.findByText(/Não foi possível carregar os artefatos/)).toBeInTheDocument()
    expect(screen.queryByText(/Nenhum artefato neste workspace/)).toBeNull()
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar artefatos", "Erro inesperado.")
  })

  it("Drive: a falha de UMA extensão não diz 'Nenhum arquivo no Drive' — e avisa uma vez só", async () => {
    // Two extensions, two calls: a list built only from the one that answered
    // would hide the other's files without saying anything.
    servico.getDriveFiles
      .mockResolvedValueOnce(ok({ items: [], total: 0 }))
      .mockResolvedValueOnce(falha("Erro inesperado."))

    render(
      <DriveField
        field={campo({ drive_extensions: [".geojson", ".csv"] })}
        values={{}}
        setNodeField={vi.fn()}
      />,
    )

    expect(await screen.findByText(/Não foi possível carregar os arquivos do Drive/)).toBeInTheDocument()
    expect(screen.queryByText(/Nenhum arquivo no Drive/)).toBeNull()
    expect(toast.error).toHaveBeenCalledTimes(1)
    expect(toast.error).toHaveBeenCalledWith("Erro ao carregar arquivos do Drive", "Erro inesperado.")
  })
})
