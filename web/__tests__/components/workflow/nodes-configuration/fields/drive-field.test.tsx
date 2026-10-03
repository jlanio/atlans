import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, cleanup } from "@testing-library/react"
import DriveField from "@/app/components/workflow/nodes-configuration/fields/drive-field"
import { INodesPropertyAPI } from "@/service/types"

// The field now consumes the listing through GisFlowService (which sends
// page/page_size — without it the picker only saw the workspace's first 50
// files). We mock the service, not axios: the service module registers
// interceptors on import and a mocked axios underneath doesn't have them.
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getDriveFiles: vi.fn() },
}))
import { GisFlowService } from "@/service/GisFlowService"
const getDriveFiles = vi.mocked(GisFlowService.getDriveFiles)

// WorkspaceContext mock
const mockWorkspace = { id_hash: "ws-001", name: "Test", description: null, owner_id: null, is_default: true, my_role: "owner" }
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: mockWorkspace, canEdit: true }),
}))

function makeField(overrides: Partial<INodesPropertyAPI> = {}): INodesPropertyAPI {
  return {
    name: "file_id",
    type: "drive",
    default: "",
    description: "Arquivo do Drive",
    drive_extensions: [".geojson"],
    ...overrides,
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const resposta = (items: any[], total = items.length) =>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Promise.resolve({ status: 200, success: true, data: { items, total } } as any)

const geojson = [{ id_hash: "f1", original_name: "dados.geojson", extension: ".geojson", size: 100 }]
const csv     = [{ id_hash: "f2", original_name: "tabela.csv",    extension: ".csv",     size: 200 }]

describe("DriveField", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    cleanup()
  })

  it("busca arquivos ao montar, paginando no servidor", async () => {
    getDriveFiles.mockReturnValueOnce(resposta(geojson))

    render(<DriveField field={makeField()} setNodeField={vi.fn()} values={{}} />)

    await waitFor(() => {
      expect(getDriveFiles).toHaveBeenCalledTimes(1)
      expect(getDriveFiles).toHaveBeenCalledWith({
        workspace_id: "ws-001",
        ext: ".geojson",
        page: 1,
        page_size: 200,
      })
    })
  })

  it("refaz fetch quando drive_extensions muda (fix do bug)", async () => {
    getDriveFiles.mockReturnValueOnce(resposta(geojson))

    const { rerender } = render(
      <DriveField field={makeField({ drive_extensions: [".geojson"] })} setNodeField={vi.fn()} values={{}} />
    )

    await waitFor(() => {
      expect(getDriveFiles).toHaveBeenCalledTimes(1)
      expect(getDriveFiles).toHaveBeenCalledWith(expect.objectContaining({ ext: ".geojson" }))
    })

    // Simulates a node change — now the extensions are .csv
    getDriveFiles.mockReturnValueOnce(resposta(csv))

    rerender(
      <DriveField field={makeField({ drive_extensions: [".csv"] })} setNodeField={vi.fn()} values={{}} />
    )

    await waitFor(() => {
      expect(getDriveFiles).toHaveBeenCalledTimes(2)
      expect(getDriveFiles).toHaveBeenLastCalledWith(expect.objectContaining({ ext: ".csv" }))
    })
  })

  it("não refaz fetch quando mesma extensão é passada", async () => {
    getDriveFiles.mockReturnValueOnce(resposta(geojson))

    const { rerender } = render(
      <DriveField field={makeField({ drive_extensions: [".geojson"] })} setNodeField={vi.fn()} values={{}} />
    )

    await waitFor(() => {
      expect(getDriveFiles).toHaveBeenCalledTimes(1)
    })

    // Rerender with the same extension — must not make a new fetch
    rerender(
      <DriveField field={makeField({ drive_extensions: [".geojson"] })} setNodeField={vi.fn()} values={{ file_id: "f1" }} />
    )

    // Waits to make sure no new fetch happens
    await new Promise(r => setTimeout(r, 50))
    expect(getDriveFiles).toHaveBeenCalledTimes(1)
  })

  it("com várias extensões, filtra no servidor — uma chamada por extensão", async () => {
    // The backend's `ext` accepts a single value; filtering on the client over a
    // truncated page was what hid the user's files.
    getDriveFiles.mockReturnValueOnce(resposta(geojson)).mockReturnValueOnce(resposta(csv))

    render(
      <DriveField
        field={makeField({ drive_extensions: [".geojson", ".csv"] })}
        setNodeField={vi.fn()}
        values={{}}
      />
    )

    await waitFor(() => {
      expect(getDriveFiles).toHaveBeenCalledTimes(2)
    })
    expect(getDriveFiles).toHaveBeenCalledWith(expect.objectContaining({ ext: ".geojson" }))
    expect(getDriveFiles).toHaveBeenCalledWith(expect.objectContaining({ ext: ".csv" }))
  })

  it("exibe mensagem quando não há arquivos", async () => {
    getDriveFiles.mockReturnValueOnce(resposta([], 0))

    render(<DriveField field={makeField()} setNodeField={vi.fn()} values={{}} />)

    // The empty-state text was rewritten in 184e492 ("polish empty/loading
    // states") and this test was left behind — the Vitest suite doesn't run in
    // CI, so nobody noticed for ~3 months. It matches the stable part of the
    // sentence, not the whole wording.
    await waitFor(() => {
      expect(screen.getByText(/nenhum arquivo no drive/i)).toBeInTheDocument()
    })
  })
})
