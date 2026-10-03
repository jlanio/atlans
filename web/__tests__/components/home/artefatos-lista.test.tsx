import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { IArtifactItem, IDriveFile } from "@/service/types"

/**
 * The "Meu → Artefatos" panel: merge of artifacts + Drive into one list, degradation
 * per source, and the click on a geojson that QUEUES a layer request in the store (the
 * HomeView is what calls `camadaDoGlobo` afterward — here we only prove the request).
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
  // Defined INSIDE the factory: `vi.mock` is hoisted above the module's consts.
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
// The `className` passes through on purpose: it is through it that the theme test sees the
// `home-portal` the panel asks of the dialog.
vi.mock("@/app/components/drive/dialogs", () => ({
  MetadataDialog: (props: { open: boolean; className?: string }) =>
    props.open ? <div data-testid="meta-dialog" className={props.className} /> : null,
}))
// The `className` PASSES THROUGH on purpose — it is through it that the theme
// (`home-portal`) and touch target (40px) tests see what the component asked for.
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

// The file name is drawn in TWO pieces (the ellipsis falls in the middle, so the
// end — the version and the extension — is not eaten in a narrow bar), so matching
// the whole text in a single element finds nothing. `data-nome` carries the
// full name precisely for this.
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
    // The owner's decision: the scope switch left here and comes back later, somewhere
    // else in the shell. The `WorkspaceSwitcher` double stays registered ON
    // PURPOSE: if someone puts it back in the panel, `ws-switcher` shows up and
    // this test fails. Without the double, the assertion would pass by accident.
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
    // It is in a large workspace that a source's failure vanishes without anyone noticing: the
    // body becomes a virtual list and the warning lived INSIDE the short branch.
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
    // 1st load with the Drive down: the artifacts come in and the amber warning offers the
    // "Tentar de novo" (try again) that fires the reload.
    H.getArtifacts.mockResolvedValue(ok({ items: [artefato()], total: 1 }))
    H.getDriveFiles.mockRejectedValue(new Error("drive fora do ar"))
    montar()
    await acharNome("saida.geojson")

    // Now BOTH sources go down: the list has to stay on screen (§3).
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
    // Portaled to <body>, the menu sits OUTSIDE the `.home dark` tree: without
    // `home-portal` it opens light over the near-black Home.
    expect(screen.getByTestId("menu").className).toContain("home-portal")
    // D5: the 40px rule applies to the ITEMS, not just the trigger.
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
    // Both dialogs are shared across the app and are born without a palette: the Home
    // passes `home-portal`, otherwise they opened white over #050505.
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

    // Only the geojson offers "Exibir no globo" (show on globe; the shapefile cannot be added).
    expect(screen.getAllByText("Exibir no globo")).toHaveLength(1)

    // Clicking the geojson queues the request — via the store, not by calling camadaDoGlobo.
    fireEvent.click(nome("saida.geojson"))
    const fila = useHomeStore.getState().pedidosDeCamada
    expect(fila.map((p) => p.artifactId)).toContain("art-geo")
    expect(fila.map((p) => p.artifactId)).not.toContain("art-shp")
  })
})
