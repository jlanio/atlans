import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, cleanup } from "@testing-library/react"
import DriveField from "@/app/components/workflow/nodes-configuration/fields/drive-field"
import { INodesPropertyAPI } from "@/service/types"

// O campo passou a consumir a listagem pelo GisFlowService (que envia
// page/page_size — sem isso o seletor só via os 50 primeiros arquivos do
// workspace). Mockamos o serviço, e não o axios: o módulo do serviço registra
// interceptors no import e um axios mockado por baixo não os tem.
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getDriveFiles: vi.fn() },
}))
import { GisFlowService } from "@/service/GisFlowService"
const getDriveFiles = vi.mocked(GisFlowService.getDriveFiles)

// Mock do WorkspaceContext
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

    // Simula troca de nó — agora as extensões são .csv
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

    // Rerender com mesma extensão — não deve fazer novo fetch
    rerender(
      <DriveField field={makeField({ drive_extensions: [".geojson"] })} setNodeField={vi.fn()} values={{ file_id: "f1" }} />
    )

    // Aguarda para garantir que nenhum novo fetch aconteça
    await new Promise(r => setTimeout(r, 50))
    expect(getDriveFiles).toHaveBeenCalledTimes(1)
  })

  it("com várias extensões, filtra no servidor — uma chamada por extensão", async () => {
    // O `ext` do backend aceita um valor só; filtrar no cliente sobre uma
    // página cortada era o que escondia arquivos do usuário.
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

    // O texto do estado vazio foi reescrito em 184e492 ("polish empty/loading
    // states") e este teste ficou para trás — a suíte Vitest não roda na CI,
    // então ninguém percebeu por ~3 meses. Casa com o trecho estável da frase,
    // não com a redação inteira.
    await waitFor(() => {
      expect(screen.getByText(/nenhum arquivo no drive/i)).toBeInTheDocument()
    })
  })
})
