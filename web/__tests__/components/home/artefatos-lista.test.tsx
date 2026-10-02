import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { IArtifactItem, IDriveFile } from "@/service/types"

/**
 * O painel "Meu → Artefatos": merge de artefatos + Drive numa lista, degradação
 * por fonte, e o clique num geojson que ENFILEIRA um pedido de camada na store (o
 * HomeView é quem chama `camadaDoGlobo` depois — aqui só provamos o pedido).
 */

const H = vi.hoisted(() => ({
  getArtifacts: vi.fn(),
  getDriveFiles: vi.fn(),
  getDriveDownloadUrl: vi.fn(),
  deleteArtifact: vi.fn(),
  deleteDriveFile: vi.fn(),
  useWorkspace: vi.fn(),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getArtifacts: (...a: unknown[]) => H.getArtifacts(...a),
    getDriveFiles: (...a: unknown[]) => H.getDriveFiles(...a),
    getArtifactDownloadUrl: (id: string) => `http://dl/${id}`,
    getDriveDownloadUrl: (...a: unknown[]) => H.getDriveDownloadUrl(...a),
    deleteArtifact: (...a: unknown[]) => H.deleteArtifact(...a),
    deleteDriveFile: (...a: unknown[]) => H.deleteDriveFile(...a),
  },
}))
vi.mock("@/context/WorkspaceContext", () => {
  // Definido DENTRO da factory: `vi.mock` é içado acima dos consts do módulo.
  const ROLE_ORDER = ["viewer", "editor", "operator", "admin", "owner"]
  return {
    ROLE_ORDER,
    hasMinRole: (actual: string | null | undefined, minimum: string) => {
      if (!actual) return false
      const a = ROLE_ORDER.indexOf(actual)
      const m = ROLE_ORDER.indexOf(minimum)
      return a >= 0 && m >= 0 && a >= m
    },
    useWorkspace: () => H.useWorkspace(),
  }
})
vi.mock("@/utils/createToast", () => ({ createToast: { success: vi.fn(), error: vi.fn() } }))
vi.mock("@/app/components/workspace/workspace-switcher", () => ({ default: () => <div data-testid="ws-switcher" /> }))
// O `className` passa de propósito: é por ele que o teste de tema vê o
// `home-portal` que o painel pede ao diálogo.
vi.mock("@/app/components/drive/dialogs", () => ({
  MetadataDialog: (props: { open: boolean; className?: string }) =>
    props.open ? <div data-testid="meta-dialog" className={props.className} /> : null,
}))
// O `className` PASSA de propósito — é por ele que os testes de tema
// (`home-portal`) e de alvo de toque (40px) enxergam o que o componente pediu.
vi.mock("@/app/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="menu" className={className}>{children}</div>
  ),
  DropdownMenuItem: ({ children, onSelect, className }: { children: React.ReactNode; onSelect?: () => void; className?: string }) => (
    <button onClick={onSelect} className={className}>{children}</button>
  ),
}))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import { ArtefatosLista } from "@/app/components/home/artefatos/lista"
import { useHomeStore } from "@/app/stores/homeStore"

const ok = <T,>(data: T) => ({ success: true, status: 200, data })

function artefato(extra: Partial<IArtifactItem> = {}): IArtifactItem {
  return {
    id_hash: "art-geo", workspace_id: "ws-1", workflow_id: "wf-1", workflow_name: "Fluxo",
    run_id: "run-1", node_id: "n1", output_key: "out", filename: "saida.geojson",
    format: "geojson", size_bytes: 100, features: 3,
    protected: false, is_published: false, is_portal_active: false, is_pinned: false,
    executor_id: null, content_location: "minio",
    created_at: "2026-09-10T12:00:00Z", expires_at: null,
    ...extra,
  }
}

function arquivo(extra: Partial<IDriveFile> = {}): IDriveFile {
  return {
    id_hash: "drv-1", workspace_id: "ws-1", original_name: "dados.csv",
    extension: "csv", mime_type: "text/csv", size: 42,
    uploaded_by: "u1", created_at: "2026-09-08T12:00:00Z", updated_at: null,
    content_written_at: null, content_location: "minio", content_executor_id: null,
    spatial_metadata: null,
    ...extra,
  }
}

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (q: string) => ({
      matches: false, media: q, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  })
})

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  useHomeStore.setState({ pedidosDeCamada: [] })
  H.useWorkspace.mockReturnValue({
    current: { id_hash: "ws-1", name: "WS", description: null, owner_id: null, is_default: true, my_role: "editor" },
    workspaces: [{ id_hash: "ws-1", name: "WS", description: null, owner_id: null, is_default: true, my_role: "editor" }],
  })
})

function montar() {
  return render(
    <SidebarProvider>
      <ArtefatosLista />
    </SidebarProvider>,
  )
}

// O nome do arquivo é desenhado em DOIS pedaços (a elipse cai no meio, para o
// fim — a versão e a extensão — não ser comido em barra estreita), então casar
// o texto inteiro num elemento só não acha nada. `data-nome` carrega o nome
// íntegro justamente para isto.
function nome(n: string): HTMLElement {
  const el = document.querySelector<HTMLElement>(`[data-nome="${n}"]`)
  if (!el) throw new Error(`Nenhum nome de arquivo "${n}" na tela`)
  return el
}
const acharNome = (n: string) => waitFor(() => nome(n))

describe("ArtefatosLista", () => {
  it("junta artefatos e arquivos do Drive na mesma lista", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [arquivo()], total: 1 }))
    montar()
    expect(await acharNome("saida.geojson")).toBeTruthy()
    expect(nome("dados.csv")).toBeTruthy()
  })

  it("NÃO oferece troca de workspace — o painel segue o workspace da pessoa", async () => {
    // Decisão do dono: a troca de escopo saiu daqui e volta depois, em outro
    // lugar da casca. O dublê do `WorkspaceSwitcher` continua registrado DE
    // PROPÓSITO: se alguém o recolocar no painel, o `ws-switcher` aparece e
    // este teste cai. Sem o dublê, a asserção passaria por acidente.
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [], total: 0 }))
    montar()
    await acharNome("saida.geojson")

    expect(screen.queryByTestId("ws-switcher")).toBeNull()
    expect(screen.queryByText("Escopo")).toBeNull()
  })

  it("a falha do Drive não derruba os artefatos (degradação por fonte)", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockRejectedValue(new Error("drive fora do ar"))
    montar()
    expect(await acharNome("saida.geojson")).toBeTruthy()
    expect(screen.getByText(/Não foi possível listar o Drive/)).toBeTruthy()
  })

  it("o aviso do Drive sobrevive à lista virtual (>150 itens)", async () => {
    // É no workspace grande que a falha de uma fonte some sem ninguém notar: o
    // corpo vira lista virtual e o aviso morava DENTRO do ramo curto.
    const muitos = Array.from({ length: 180 }, (_, i) =>
      artefato({ id_hash: `art-${i}`, filename: `saida-${i}.geojson` }),
    )
    H.getArtifacts.mockResolvedValue(ok({ items: muitos, total: 180 }))
    H.getDriveFiles.mockRejectedValue(new Error("drive fora do ar"))
    montar()
    expect(await screen.findByText(/Não foi possível listar o Drive/)).toBeTruthy()
  })

  it("a falha SÓ dos artefatos também avisa (degradação simétrica)", async () => {
    H.getArtifacts.mockRejectedValue(new Error("artifacts 500"))
    H.getDriveFiles.mockResolvedValue(ok({ items: [arquivo()], total: 1 }))
    montar()
    expect(await acharNome("dados.csv")).toBeTruthy()
    expect(screen.getByText(/Não foi possível listar os artefatos/)).toBeTruthy()
  })

  it("recarga que falha NÃO apaga a lista já carregada — só avisa", async () => {
    // 1ª carga com o Drive fora: os artefatos entram e o aviso âmbar dá o
    // "Tentar de novo" que dispara a recarga.
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockRejectedValue(new Error("drive fora do ar"))
    montar()
    await acharNome("saida.geojson")

    // Agora as DUAS fontes caem: a lista tem de continuar na tela (§3).
    H.getArtifacts.mockRejectedValue(new Error("caiu"))
    fireEvent.click(screen.getAllByText("Tentar de novo")[0])
    await waitFor(() => expect(screen.getByText(/Não foi possível atualizar o acervo/)).toBeTruthy())
    expect(nome("saida.geojson")).toBeTruthy()
  })

  it("erro de 1ª carga oferece 'Tentar de novo' e microcopy da casa", async () => {
    H.getArtifacts.mockRejectedValue(new Error("boom"))
    H.getDriveFiles.mockRejectedValue(new Error("boom"))
    montar()
    expect(await screen.findByText("Não foi possível carregar o acervo.")).toBeTruthy()
    expect(screen.getByText("Tentar de novo")).toBeTruthy()
  })

  it("diz quantos itens o servidor tem quando a lista vem cortada", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 700 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [arquivo()], total: 200 }))
    montar()
    await acharNome("saida.geojson")
    expect(screen.getByText(/mostrando 2 de 900/)).toBeTruthy()
  })

  it("o menu herda a paleta da Home e seus itens têm alvo de 40px", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [], total: 0 }))
    montar()
    await acharNome("saida.geojson")
    // Portado para o <body>, o menu fica FORA da árvore `.home dark`: sem
    // `home-portal` ele abre claro sobre a Home quase preta.
    expect(screen.getByTestId("menu").className).toContain("home-portal")
    // D5: a regra dos 40px vale para os ITENS, não só para o gatilho.
    for (const rotulo of ["Exibir no globo", "Baixar", "Excluir"]) {
      expect(screen.getByText(rotulo).closest("button")?.className).toContain("max-md:min-h-10")
    }
  })

  it("a linha: o principal ocupa o espaço e o ⋯ é irmão no flex", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [], total: 0 }))
    montar()
    const botao = (await acharNome("saida.geojson")).closest("button")!
    for (const c of ["min-w-0", "flex-1"]) expect(botao.className).toContain(c)
    const gatilho = screen.getByRole("button", { name: 'Ações de "saida.geojson"' })
    expect(gatilho.closest('[data-slot="linha-do-meu"]')).toBe(botao.closest('[data-slot="linha-do-meu"]'))
    expect(gatilho.className).not.toMatch(/\babsolute\b/)
  })

  it("Metadados de um arquivo do Drive e Excluir abrem na paleta da Home", async () => {
    // Os dois diálogos são compartilhados pelo app e nascem sem paleta: a Home
    // passa `home-portal`, senão abriam brancos sobre #050505.
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [arquivo()], total: 1 }))
    montar()
    fireEvent.click(await acharNome("dados.csv"))
    expect((await screen.findByTestId("meta-dialog")).className).toContain("home-portal")

    fireEvent.click(screen.getAllByText("Excluir")[0])
    const dialogo = await screen.findByRole("dialog")
    expect(dialogo.className).toContain("home-portal")
  })

  it("clicar num geojson enfileira o pedido de camada; shapefile não é exibível", async () => {
    H.getArtifacts.mockResolvedValue(ok({
      items: [artefato(), artefato({ id_hash: "art-shp", filename: "malha.zip", format: "shapefile" })],
      total: 2,
    }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [], total: 0 }))
    montar()
    await acharNome("saida.geojson")

    // Só o geojson oferece "Exibir no globo" (o shapefile não é adicionável).
    expect(screen.getAllByText("Exibir no globo")).toHaveLength(1)

    // Clicar no geojson enfileira o pedido — via store, não chamando camadaDoGlobo.
    fireEvent.click(nome("saida.geojson"))
    const fila = useHomeStore.getState().pedidosDeCamada
    expect(fila.map((p) => p.artifactId)).toContain("art-geo")
    expect(fila.map((p) => p.artifactId)).not.toContain("art-shp")
  })
})
