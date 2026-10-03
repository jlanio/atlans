import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { IMySchedule, IArtifactItem, IConversationSummary, IDriveFile } from "@/service/types"

/**
 * The three lists of the Meus group (Chats, Agendamentos, Artefatos) in English and
 * Spanish: the language arrives through the `LanguageProvider`, as in the dashboard layout.
 * The hooks are the real ones, with the service doubled — so the microcopy the
 * HOOK chooses (the load failure, a toast's fallback) is also checked.
 *
 * Without a provider everything stays in Portuguese, byte for byte: each list's tests
 * check that, and the end of this file proves that the components
 * shared with the administration panel stay the same without the texts.
 */

const H = vi.hoisted(() => ({
  listarConversas: vi.fn(), renomearConversa: vi.fn(), apagarConversa: vi.fn(),
  getMySchedules: vi.fn(), updateSchedule: vi.fn(), getWorkflowById: vi.fn(), executeWorkflow: vi.fn(),
  getArtifacts: vi.fn(), getDriveFiles: vi.fn(), getDriveDownloadUrl: vi.fn(), getArtifactDownload: vi.fn(),
  deleteArtifact: vi.fn(), deleteDriveFile: vi.fn(),
  useWorkspace: vi.fn(),
  refresh: vi.fn(),
  toastSucesso: vi.fn(),
  toastErro: vi.fn(),
  rota: "/",
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    listarConversas: (...a: unknown[]) => H.listarConversas(...a),
    renomearConversa: (...a: unknown[]) => H.renomearConversa(...a),
    apagarConversa: (...a: unknown[]) => H.apagarConversa(...a),
    getMySchedules: (...a: unknown[]) => H.getMySchedules(...a),
    updateSchedule: (...a: unknown[]) => H.updateSchedule(...a),
    getWorkflowById: (...a: unknown[]) => H.getWorkflowById(...a),
    executeWorkflow: (...a: unknown[]) => H.executeWorkflow(...a),
    getArtifacts: (...a: unknown[]) => H.getArtifacts(...a),
    getDriveFiles: (...a: unknown[]) => H.getDriveFiles(...a),
    getDriveDownloadUrl: (...a: unknown[]) => H.getDriveDownloadUrl(...a),
    getArtifactDownload: (...a: unknown[]) => H.getArtifactDownload(...a),
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
vi.mock("@/context/ActiveRunsContext", () => ({ useActiveRuns: () => ({ refresh: H.refresh }) }))
// The route decides whether the screen follows the language (`ScopeByRoute`): only the Home is translated.
vi.mock("next/navigation", () => ({ usePathname: () => H.rota, useRouter: () => ({ push: vi.fn() }) }))
vi.mock("@/utils/createToast", () => ({
  createToast: {
    success: (...a: unknown[]) => H.toastSucesso(...a),
    error: (...a: unknown[]) => H.toastErro(...a),
  },
}))
// The parameters dialog belongs to the editor (not translated here) and the metadata belongs
// to the Drive: doubles, as in each list's tests.
vi.mock("@/app/components/workflow/execute-params-dialog", () => ({
  default: (props: { open: boolean }) => (props.open ? <div data-testid="exec-dialog" /> : null),
}))
vi.mock("@/app/components/drive/dialogs", () => ({
  MetadataDialog: (props: { open: boolean }) => (props.open ? <div data-testid="meta-dialog" /> : null),
}))
// Menu passthrough: without portal/pointer, the items stay in the DOM and clickable.
vi.mock("@/app/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children }: { children: React.ReactNode }) => <div data-testid="menu">{children}</div>,
  DropdownMenuItem: ({ children, onSelect, disabled }: { children: React.ReactNode; onSelect?: () => void; disabled?: boolean }) => (
    <button disabled={disabled} onClick={onSelect}>{children}</button>
  ),
}))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import { ScopeByRoute, LanguageProvider, useLanguage } from "@/context/IdiomaContext"
import type { Idioma } from "@/lib/idioma"
import { formatLocal } from "@/lib/dayjs"
import { ChatsLista } from "@/app/components/home/chats/lista"
import { AgendamentosLista } from "@/app/components/home/agendamentos/lista"
import { ArtefatosLista } from "@/app/components/home/artefatos/lista"
import { AvisoAmbar } from "@/app/components/shared/estados"
import { RetencaoHint } from "@/app/components/artifacts/badges"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { useHomeStore } from "@/app/stores/homeStore"

// ── Doubles ─────────────────────────────────────────────────────────────────

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = (status = 500, message?: string) => ({
  success: false, status, data: undefined, error: message ? { name: "AxiosError", message } : undefined,
})
const nunca = () => new Promise(() => {})

const conversa = (id: string, titulo: string): IConversationSummary => ({
  id, titulo, workflow_id: null, tokens_total: 0,
  created_at: "2026-09-10T12:00:00Z", updated_at: "2026-09-10T12:00:00Z",
})

const pagina = (itens: IMySchedule[], total = itens.length) => ok({ itens, total })
function ag(extra: Partial<IMySchedule> = {}): IMySchedule {
  return {
    job_id: "job-1", id_hash: "sch-1", active: true, strategy: "interval", interval: 6, unit: "hours",
    next_run_at: new Date(Date.now() + 3_600_000).toISOString(), last_run_at: null,
    retry_count: 0, workflow_id: "wf-1", workflow_name: "Fluxo A", flag_ative: true,
    workspace_id: "ws-1", origem: "usuario",
    ...extra,
  }
}

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

// 3.5 days ahead: the retention hint says "3 dias" (3 days) in any time zone.
const inThreeDays = () => new Date(Date.now() + 3.5 * 86_400_000).toISOString()

/** The usual collection: geojson, shapefile (inert), an ephemeral one and a Drive file. */
function defaultCollection() {
  H.getArtifacts.mockResolvedValue(ok({
    items: [
      artefato(),
      artefato({ id_hash: "art-shp", filename: "malha.zip", format: "shapefile" }),
      artefato({ id_hash: "art-efe", filename: "temporario.geojson", expires_at: inThreeDays() }),
    ],
    total: 700,
  }))
  H.getDriveFiles.mockResolvedValue(ok({ items: [arquivo()], total: 200 }))
}

const WS = { id_hash: "ws-1", name: "WS", description: null, owner_id: null, is_default: true, my_role: "operator" }
const LOCAL_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone
const OTHER_TIMEZONE = LOCAL_TIMEZONE === "America/La_Paz" ? "Europe/Lisbon" : "America/La_Paz"

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
  H.rota = "/"
  useHomeStore.setState({ conversaId: null, painel: "barra", anuncioDeConversa: null, pedidosDeCamada: [] })
  H.useWorkspace.mockReturnValue({ current: WS, workspaces: [WS] })
  H.listarConversas.mockResolvedValue(ok({
    itens: [conversa("c1", "Focos em Rondônia"), conversa("c2", "  ")],
    total: 300,
  }))
  H.getMySchedules.mockResolvedValue(pagina([ag()], 3))
  defaultCollection()
})

/** A button that switches the language through the context, as Preferências does. */
function SwitchLanguage({ para }: { para: Idioma }) {
  const { escolher } = useLanguage()
  return <button type="button" onClick={() => escolher(para)}>trocar idioma</button>
}

function montar(idioma: Idioma, lista: React.ReactNode, trocarPara?: Idioma) {
  return render(
    <LanguageProvider inicial={{ idioma, detectado: idioma, escolhido: idioma }}>
      <SidebarProvider>{lista}</SidebarProvider>
      {trocarPara && <SwitchLanguage para={trocarPara} />}
    </LanguageProvider>,
  )
}

// The file name is drawn in two pieces; `data-nome` carries the whole one.
function nome(n: string): HTMLElement {
  const el = document.querySelector<HTMLElement>(`[data-nome="${n}"]`)
  if (!el) throw new Error(`Nenhum nome de arquivo "${n}" na tela`)
  return el
}
const findName = (n: string) => waitFor(() => nome(n))
const rowMenu = (i = 0) => screen.getAllByTestId("menu")[i]

// ── English ─────────────────────────────────────────────────────────────────

describe("em inglês — Chats", () => {
  it("a linha sem título, o menu e o rodapé do corte", async () => {
    montar("en", <ChatsLista />)
    expect(await screen.findByText("Focos em Rondônia")).toBeTruthy()
    expect(screen.getByText("Untitled")).toBeTruthy()
    expect(within(rowMenu()).getByText("Rename")).toBeTruthy()
    expect(within(rowMenu()).getByText("Delete")).toBeTruthy()
    expect(screen.getByText("showing 2 of 300")).toBeTruthy()
    expect(screen.getByText("Show more")).toBeTruthy()
  })

  it("o esqueleto da 1ª carga", () => {
    H.listarConversas.mockReturnValue(nunca())
    montar("en", <ChatsLista />)
    expect(screen.getByRole("status", { name: "Loading chats" })).toBeTruthy()
  })

  it("a falha da 1ª carga usa a microcopy do hook em inglês; vazio também", async () => {
    H.listarConversas.mockResolvedValue(falhou(500, "Erro inesperado."))
    montar("en", <ChatsLista />)
    expect(await screen.findByText("Couldn’t load chats.")).toBeTruthy()
    // The raw `detail` of a 500 does not reach the screen.
    expect(screen.queryByText("Erro inesperado.")).toBeNull()

    H.listarConversas.mockResolvedValue(ok({ itens: [], total: 0 }))
    fireEvent.click(screen.getByText("Try again"))
    expect(await screen.findByText("No chats yet.")).toBeTruthy()
  })

  it("renomear e apagar: os diálogos e o toast em inglês", async () => {
    H.apagarConversa.mockResolvedValue(falhou(500))
    montar("en", <ChatsLista />)
    await screen.findByText("Focos em Rondônia")

    fireEvent.click(within(rowMenu()).getByText("Rename"))
    const renomear = await screen.findByRole("dialog")
    expect(within(renomear).getByText("Rename chat")).toBeTruthy()
    expect(within(renomear).getByText("Choose a new title for this chat.")).toBeTruthy()
    expect(within(renomear).getByLabelText("Title")).toBeTruthy()
    expect(within(renomear).getByRole("button", { name: "Save" })).toBeTruthy()
    expect(within(renomear).getByRole("button", { name: "Close" })).toBeTruthy()
    fireEvent.click(within(renomear).getByRole("button", { name: "Cancel" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())

    fireEvent.click(within(rowMenu()).getByText("Delete"))
    const apagar = await screen.findByRole("dialog")
    expect(within(apagar).getByText("Delete chat")).toBeTruthy()
    expect(within(apagar).getByText(
      '"Focos em Rondônia" will be removed from the list. Its history stays on the server.',
    )).toBeTruthy()
    expect(within(apagar).getByRole("button", { name: "Cancel" })).toBeTruthy()
    expect(within(apagar).getByRole("button", { name: "Close" })).toBeTruthy()
    fireEvent.click(within(apagar).getByRole("button", { name: "Delete" }))
    // With no message from the server, the fallback is the hook's — in the language in use.
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith("Couldn’t delete the chat", "Try again."))
  })
})

describe("em inglês — Agendamentos", () => {
  it("o resumo de cada linha, o selo do assistente, o menu e o rodapé", async () => {
    H.getMySchedules.mockResolvedValue(pagina([
      ag(),
      ag({ job_id: "job-2", workflow_name: "Parado", flag_ative: false }),
      ag({
        job_id: "job-3", workflow_name: "Do assistente", origem: "assistente",
        strategy: "cron", cron_expression: "0 6 * * *", interval: null, unit: null, timezone: OTHER_TIMEZONE,
      }),
    ], 5))
    montar("en", <AgendamentosLista />)
    await screen.findByText("Fluxo A")
    expect(screen.getByText(/^every 6 h · (today|tomorrow), /)).toBeTruthy()
    expect(screen.getByText("paused — workflow inactive")).toBeTruthy()
    expect(screen.getByText(new RegExp(`^every day at 6:00\\sAM \\(${OTHER_TIMEZONE}\\) · `))).toBeTruthy()
    expect(screen.getByLabelText("Assistant workflow")).toBeTruthy()
    expect(screen.getAllByText("Pause")).toHaveLength(3)
    expect(screen.getAllByText("Run now")).toHaveLength(3)
    expect(screen.getByText("showing 3 of 5")).toBeTruthy()
    expect(screen.getByText("Show more")).toBeTruthy()
  })

  it("pausar e ativar avisam em inglês", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ active: false })], 1))
    H.updateSchedule.mockResolvedValue(ok({}))
    montar("en", <AgendamentosLista />)
    await screen.findByText("Fluxo A")
    // The reload that activating fires already brings the schedule as active.
    H.getMySchedules.mockResolvedValue(pagina([ag()], 1))
    fireEvent.click(screen.getByText("Activate"))
    await waitFor(() => expect(H.toastSucesso).toHaveBeenCalledWith("Schedule activated"))

    H.updateSchedule.mockResolvedValue(falhou(500))
    fireEvent.click(await screen.findByText("Pause"))
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith("Couldn’t update the schedule", "Try again."))
  })

  it("rodar agora: o toast de início e o da preparação que falha", async () => {
    H.getWorkflowById.mockResolvedValue(ok({ params_schema: {} }))
    H.executeWorkflow.mockResolvedValue(ok({}))
    montar("en", <AgendamentosLista />)
    await screen.findByText("Fluxo A")
    fireEvent.click(screen.getByText("Run now"))
    await waitFor(() => expect(H.toastSucesso).toHaveBeenCalledWith('Workflow "Fluxo A" started!'))

    H.getWorkflowById.mockResolvedValue(falhou(500))
    fireEvent.click(screen.getByText("Run now"))
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith(
      "Couldn’t prepare the run.", "Couldn’t read the workflow’s parameters. Try again.",
    ))
  })

  it("falha da 1ª carga, lista vazia e a recarga que falha", async () => {
    H.getMySchedules.mockResolvedValue(falhou(500, "Erro inesperado."))
    montar("en", <AgendamentosLista />)
    expect(await screen.findByText("Couldn’t load schedules.")).toBeTruthy()

    H.getMySchedules.mockResolvedValue(pagina([], 3))
    fireEvent.click(screen.getByText("Try again"))
    expect(await screen.findByText("No schedules.")).toBeTruthy()
    expect(screen.getByText("showing 0 of 3")).toBeTruthy()

    H.getMySchedules.mockResolvedValue(falhou(502, "Bad gateway"))
    fireEvent.click(screen.getByText("Show more"))
    const aviso = await screen.findByRole("status")
    expect(within(aviso).getByText("Couldn’t refresh schedules.")).toBeTruthy()
    expect(within(aviso).getByText("Try again")).toBeTruthy()
  })

  it("o esqueleto da 1ª carga", () => {
    H.getMySchedules.mockReturnValue(nunca())
    montar("en", <AgendamentosLista />)
    expect(screen.getByRole("status", { name: "Loading schedules" })).toBeTruthy()
  })
})

describe("em inglês — Artefatos", () => {
  it("o menu, as dicas da linha, a retenção e o rodapé", async () => {
    montar("en", <ArtefatosLista />)
    await findName("saida.geojson")
    expect(screen.getAllByText("Show on the globe")).toHaveLength(2)
    expect(screen.getAllByText("Download")).toHaveLength(4)
    expect(screen.getAllByText("Metadata")).toHaveLength(1)
    expect(screen.getAllByText("Delete")).toHaveLength(4)

    expect(nome("saida.geojson").closest("button")!.getAttribute("title"))
      .toBe("saida.geojson · GEOJSON — show on the globe")
    // The inert row says why — in the `title` and in text for keyboard/touch.
    const inerte = nome("malha.zip").closest<HTMLElement>("div[title]")!
    const motivo = "no preview on the globe for this format — publish the map to show it"
    expect(inerte.getAttribute("title")).toBe(`malha.zip · SHAPEFILE — ${motivo}`)
    expect(within(inerte).getByText(motivo)).toBeTruthy()

    const dica = screen.getByText("expires in 3 days")
    // Month spelled out: "09/01/2026" would be read backward by an en-GB reader.
    expect(dica.getAttribute("title")).toMatch(/^Deleted automatically on [A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}\s[AP]M$/)
    expect(screen.getByText("showing 4 of 900")).toBeTruthy()
  })

  it("excluir: o diálogo e o toast em inglês", async () => {
    H.deleteArtifact.mockResolvedValue(falhou(500))
    montar("en", <ArtefatosLista />)
    await findName("saida.geojson")
    fireEvent.click(within(rowMenu(0)).getByText("Delete"))
    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText("Delete artifact")).toBeTruthy()
    expect(within(dialogo).getByText('"saida.geojson" will be deleted. This can’t be undone.')).toBeTruthy()
    expect(within(dialogo).getByRole("button", { name: "Cancel" })).toBeTruthy()
    fireEvent.click(within(dialogo).getByRole("button", { name: "Delete" }))
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith("Couldn’t delete", "Try again."))
  })

  it("o arquivo do Drive: excluir fala de arquivo, e baixar que falha avisa", async () => {
    H.getDriveDownloadUrl.mockResolvedValue(falhou(500))
    montar("en", <ArtefatosLista />)
    await findName("dados.csv")
    const menuDoDrive = rowMenu(3)
    fireEvent.click(within(menuDoDrive).getByText("Download"))
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith("Couldn’t download the file", "Try again."))

    fireEvent.click(within(menuDoDrive).getByText("Delete"))
    expect(within(await screen.findByRole("dialog")).getByText("Delete file")).toBeTruthy()
  })

  it("a degradação por fonte e a falha total", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [], total: 0 }))
    H.getDriveFiles.mockRejectedValue(new Error("drive fora do ar"))
    montar("en", <ArtefatosLista />)
    expect(await screen.findByText("No run artifacts — Drive couldn’t be read.")).toBeTruthy()
    const aviso = screen.getByRole("status")
    expect(within(aviso).getByText("Couldn’t list Drive files.")).toBeTruthy()
    expect(within(aviso).getByText("Try again")).toBeTruthy()

    cleanup()
    H.getArtifacts.mockRejectedValue(new Error("caiu"))
    montar("en", <ArtefatosLista />)
    expect(await screen.findByText("Couldn’t load artifacts and files.")).toBeTruthy()
    expect(screen.getByText("Try again")).toBeTruthy()
  })

  it("vazio, sem workspace e o esqueleto", async () => {
    H.getArtifacts.mockResolvedValue(ok({ items: [], total: 0 }))
    H.getDriveFiles.mockResolvedValue(ok({ items: [], total: 0 }))
    montar("en", <ArtefatosLista />)
    expect(await screen.findByText("No artifacts or files.")).toBeTruthy()

    cleanup()
    H.useWorkspace.mockReturnValue({ current: null, workspaces: [] })
    montar("en", <ArtefatosLista />)
    expect(await screen.findByText("No active workspace.")).toBeTruthy()

    cleanup()
    H.useWorkspace.mockReturnValue({ current: WS, workspaces: [WS] })
    H.getArtifacts.mockReturnValue(nunca())
    montar("en", <ArtefatosLista />)
    expect(screen.getByRole("status", { name: "Loading artifacts and files" })).toBeTruthy()
  })
})

// ── Espanhol ────────────────────────────────────────────────────────────────

describe("em espanhol — Chats", () => {
  it("a linha, o menu, o rodapé e os dois diálogos", async () => {
    H.apagarConversa.mockResolvedValue(falhou(500, "servidor fuera"))
    montar("es", <ChatsLista />)
    await screen.findByText("Focos em Rondônia")
    expect(screen.getByText("Sin título")).toBeTruthy()
    expect(screen.getByText("mostrando 2 de 300")).toBeTruthy()
    expect(screen.getByText("Ver más")).toBeTruthy()

    fireEvent.click(within(rowMenu()).getByText("Renombrar"))
    const renomear = await screen.findByRole("dialog")
    expect(within(renomear).getByText("Renombrar conversación")).toBeTruthy()
    expect(within(renomear).getByText("Elige un nuevo título para esta conversación.")).toBeTruthy()
    expect(within(renomear).getByLabelText("Título")).toBeTruthy()
    expect(within(renomear).getByRole("button", { name: "Guardar" })).toBeTruthy()
    expect(within(renomear).getByRole("button", { name: "Cerrar" })).toBeTruthy()
    fireEvent.click(within(renomear).getByRole("button", { name: "Cancelar" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())

    fireEvent.click(within(rowMenu()).getByText("Eliminar"))
    const apagar = await screen.findByRole("dialog")
    expect(within(apagar).getByText("Eliminar conversación")).toBeTruthy()
    expect(within(apagar).getByText(
      '"Focos em Rondônia" saldrá de la lista. El historial se queda en el servidor.',
    )).toBeTruthy()
    fireEvent.click(within(apagar).getByRole("button", { name: "Eliminar" }))
    // The server's message passes through as it came: what gets translated is the toast's title.
    await waitFor(() => expect(H.toastErro).toHaveBeenCalledWith("No se pudo eliminar la conversación", "servidor fuera"))
  })

  it("falha da 1ª carga e lista vazia", async () => {
    H.listarConversas.mockResolvedValue(falhou(503))
    montar("es", <ChatsLista />)
    expect(await screen.findByText("No se pudieron cargar las conversaciones.")).toBeTruthy()
    H.listarConversas.mockResolvedValue(ok({ itens: [], total: 0 }))
    fireEvent.click(screen.getByText("Intentar de nuevo"))
    expect(await screen.findByText("Aún no hay conversaciones.")).toBeTruthy()
  })
})

describe("em espanhol — Agendamentos", () => {
  it("o resumo, o menu, o rodapé e o toast de ativar", async () => {
    H.getMySchedules.mockResolvedValue(pagina([
      ag({ active: false }),
      ag({ job_id: "job-2", workflow_name: "Parado", flag_ative: false }),
      ag({
        job_id: "job-3", workflow_name: "Do assistente", origem: "assistente",
        strategy: "cron", cron_expression: "0 6 * * *", interval: null, unit: null, timezone: OTHER_TIMEZONE,
      }),
    ], 5))
    H.updateSchedule.mockResolvedValue(ok({}))
    montar("es", <AgendamentosLista />)
    await screen.findByText("Fluxo A")
    expect(screen.getAllByText("pausado")).toHaveLength(1)
    expect(screen.getByText("pausado — flujo inactivo")).toBeTruthy()
    expect(screen.getByText(new RegExp(`^todos los días a las 6:00 \\(${OTHER_TIMEZONE}\\) · `))).toBeTruthy()
    expect(screen.getByLabelText("Flujo del asistente")).toBeTruthy()
    expect(screen.getAllByText("Pausar")).toHaveLength(2)
    expect(screen.getAllByText("Ejecutar ahora")).toHaveLength(3)
    expect(screen.getByText("mostrando 3 de 5")).toBeTruthy()
    expect(screen.getByText("Ver más")).toBeTruthy()

    fireEvent.click(screen.getByText("Activar"))
    await waitFor(() => expect(H.toastSucesso).toHaveBeenCalledWith("Programación activada"))
  })

  it("o resumo de quem está ativo: cadência e próxima execução", async () => {
    montar("es", <AgendamentosLista />)
    await screen.findByText("Fluxo A")
    expect(screen.getByText(/^cada 6 h · (hoy|mañana), /)).toBeTruthy()
  })

  it("falha da 1ª carga e lista vazia", async () => {
    H.getMySchedules.mockResolvedValue(falhou(500))
    montar("es", <AgendamentosLista />)
    expect(await screen.findByText("No se pudieron cargar las programaciones.")).toBeTruthy()
    H.getMySchedules.mockResolvedValue(pagina([]))
    fireEvent.click(screen.getByText("Intentar de nuevo"))
    expect(await screen.findByText("No hay programaciones.")).toBeTruthy()
  })
})

describe("em espanhol — Artefatos", () => {
  it("o menu, a linha inerte, a retenção, o rodapé e a exclusão", async () => {
    montar("es", <ArtefatosLista />)
    await findName("saida.geojson")
    expect(screen.getAllByText("Mostrar en el globo")).toHaveLength(2)
    expect(screen.getAllByText("Descargar")).toHaveLength(4)
    expect(screen.getAllByText("Metadatos")).toHaveLength(1)
    expect(screen.getAllByText("Eliminar")).toHaveLength(4)

    const inerte = nome("malha.zip").closest<HTMLElement>("div[title]")!
    expect(within(inerte).getByText("formato sin vista previa en el globo — publica el mapa para mostrarlo")).toBeTruthy()

    const dica = screen.getByText("expira en 3 días")
    expect(dica.getAttribute("title")).toMatch(/^Eliminado automáticamente el \d{2}\/\d{2}\/\d{4}, \d{1,2}:\d{2}$/)
    expect(screen.getByText("mostrando 4 de 900")).toBeTruthy()

    fireEvent.click(within(rowMenu(0)).getByText("Eliminar"))
    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText("Eliminar artefacto")).toBeTruthy()
    expect(within(dialogo).getByText('"saida.geojson" se eliminará. Esta acción no se puede deshacer.')).toBeTruthy()
    expect(within(dialogo).getByRole("button", { name: "Cancelar" })).toBeTruthy()
    expect(within(dialogo).getByRole("button", { name: "Cerrar" })).toBeTruthy()
  })

  it("a falha do Drive e a falha total", async () => {
    H.getDriveFiles.mockRejectedValue(new Error("drive fora do ar"))
    montar("es", <ArtefatosLista />)
    await findName("saida.geojson")
    const aviso = screen.getByRole("status")
    expect(within(aviso).getByText("No se pudieron listar los archivos del Drive.")).toBeTruthy()
    expect(within(aviso).getByText("Intentar de nuevo")).toBeTruthy()

    cleanup()
    H.getArtifacts.mockRejectedValue(new Error("caiu"))
    montar("es", <ArtefatosLista />)
    expect(await screen.findByText("No se pudieron cargar los artefactos y archivos.")).toBeTruthy()
  })
})

// ── Switching language with the screen open ─────────────────────────────────

describe("trocar de idioma nas Preferências, com a lista na tela", () => {
  it("a falha que o hook guardou muda de idioma sem recarregar", async () => {
    // The hook keeps the failure's KEY, not the sentence: switching language does not
    // reload the list, and the old sentence would stay in the previous language.
    H.getMySchedules.mockResolvedValue(falhou(500))
    montar("en", <AgendamentosLista />, "es")
    expect(await screen.findByText("Couldn’t load schedules.")).toBeTruthy()
    fireEvent.click(screen.getByText("trocar idioma"))
    expect(await screen.findByText("No se pudieron cargar las programaciones.")).toBeTruthy()
    expect(screen.getByText("Intentar de nuevo")).toBeTruthy()
    expect(H.getMySchedules).toHaveBeenCalledTimes(1)
  })

  it("a falha das conversas também — o hook guarda a chave, não a frase", async () => {
    H.listarConversas.mockResolvedValue(falhou(500))
    montar("en", <ChatsLista />, "es")
    expect(await screen.findByText("Couldn’t load chats.")).toBeTruthy()
    fireEvent.click(screen.getByText("trocar idioma"))
    expect(await screen.findByText("No se pudieron cargar las conversaciones.")).toBeTruthy()
    expect(H.listarConversas).toHaveBeenCalledTimes(1)
  })

  it("o motivo da linha inerte também — o acervo guardado não é normalizado de novo", async () => {
    montar("en", <ArtefatosLista />, "es")
    await findName("malha.zip")
    expect(screen.getByText("no preview on the globe for this format — publish the map to show it")).toBeTruthy()
    fireEvent.click(screen.getByText("trocar idioma"))
    expect(await screen.findByText("formato sin vista previa en el globo — publica el mapa para mostrarlo")).toBeTruthy()
    expect(H.getArtifacts).toHaveBeenCalledTimes(1)
  })
})

describe("fora da Home, a lista fica inteira em português", () => {
  it("o resumo segue o idioma da TELA, como os textos — nunca meio a meio", async () => {
    H.rota = "/projects"
    H.getMySchedules.mockResolvedValue(pagina([
      ag({ strategy: "cron", cron_expression: "0 6 * * *", interval: null, unit: null }),
    ]))
    render(
      <LanguageProvider inicial={{ idioma: "en", detectado: "en", escolhido: "en" }}>
        <ScopeByRoute>
          <SidebarProvider><AgendamentosLista /></SidebarProvider>
        </ScopeByRoute>
      </LanguageProvider>,
    )
    await screen.findByText("Fluxo A")
    expect(screen.getByText(/^todo dia às 06:00 · /)).toBeTruthy()
    expect(screen.getByText("Pausar")).toBeTruthy()
  })
})

// ── The shared ones ─────────────────────────────────────────────────────────

describe("compartilhados com o painel de administração: sem os textos, o português de sempre", () => {
  it("AvisoAmbar", () => {
    render(<AvisoAmbar onTentar={() => {}}>Falhou.</AvisoAmbar>)
    expect(screen.getByRole("button", { name: "Tentar de novo" })).toBeTruthy()
  })

  it("DeleteDialog: sem `closeLabel`, o X continua 'Fechar'", () => {
    render(
      <Dialog open>
        <DeleteDialog title="Excluir x" description="d" onConfirm={() => {}} />
      </Dialog>,
    )
    const dialogo = screen.getByRole("dialog")
    expect(within(dialogo).getByRole("button", { name: "Fechar" })).toBeTruthy()
    expect(within(dialogo).getByRole("button", { name: "Cancelar" })).toBeTruthy()
    expect(within(dialogo).getByRole("button", { name: "Excluir" })).toBeTruthy()
  })

  it("RetencaoHint: as três frases e o title com o formatLocal", () => {
    const exp = inThreeDays()
    const { rerender } = render(<RetencaoHint expiresAt={exp} />)
    const dica = screen.getByText("expira em 3 dias")
    expect(dica.getAttribute("title")).toBe(`Removido automaticamente em ${formatLocal(exp)}`)

    rerender(<RetencaoHint expiresAt={new Date(Date.now() + 1.5 * 86_400_000).toISOString()} />)
    expect(screen.getByText("expira em 1 dia")).toBeTruthy()
    rerender(<RetencaoHint expiresAt={new Date(Date.now() + 3_600_000).toISOString()} />)
    expect(screen.getByText("expira hoje")).toBeTruthy()
    rerender(<RetencaoHint expiresAt={new Date(Date.now() - 3_600_000).toISOString()} />)
    expect(screen.getByText("expirado")).toBeTruthy()
  })

  it("a Home em português passa ao RetencaoHint exatamente o que ele diria sozinho", async () => {
    const exp = inThreeDays()
    H.getArtifacts.mockResolvedValue(ok({
      items: [artefato({ id_hash: "art-efe", filename: "temporario.geojson", expires_at: exp })],
      total: 1,
    }))
    // No provider: it is the Home in Portuguese, with the dictionary's texts.
    render(<SidebarProvider><ArtefatosLista /></SidebarProvider>)
    await findName("temporario.geojson")
    const naHome = screen.getByText("expira em 3 dias")

    const { container } = render(<RetencaoHint expiresAt={exp} />)
    const sozinho = container.querySelector("span")!
    expect(naHome.outerHTML).toBe(sozinho.outerHTML)
  })
})
