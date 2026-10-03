import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { IAgendamentoMeu } from "@/service/types"

/**
 * The "Meu → Agendamentos" panel: list (with paused ones + reason), pause/activate and
 * run now — triggers by role PER ITEM. The ⋯ menu is mocked as a passthrough
 * (no Radix portal/pointer), so the items are directly clickable.
 */

const H = vi.hoisted(() => ({
  getMySchedules: vi.fn(),
  updateSchedule: vi.fn(),
  getWorkflowById: vi.fn(),
  executeWorkflow: vi.fn(),
  useWorkspace: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getMySchedules: (...a: unknown[]) => H.getMySchedules(...a),
    updateSchedule: (...a: unknown[]) => H.updateSchedule(...a),
    getWorkflowById: (...a: unknown[]) => H.getWorkflowById(...a),
    executeWorkflow: (...a: unknown[]) => H.executeWorkflow(...a),
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
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: H.push }) }))
vi.mock("@/utils/createToast", () => ({ createToast: { success: vi.fn(), error: vi.fn() } }))
// The `className` passes through on purpose: it is through it that the theme test sees the
// `home-portal` the panel asks of the dialog.
vi.mock("@/app/components/workflow/execute-params-dialog", () => ({
  default: (props: { open: boolean; className?: string }) =>
    props.open ? <div data-testid="exec-dialog" className={props.className} /> : null,
}))
// Menu passthrough: without portal/pointer, the items stay in the DOM and clickable. The
// `className` PASSES THROUGH on purpose — it is through it that the theme (`home-portal`)
// and touch target (40px) tests see what the component asked for.
vi.mock("@/app/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="menu" className={className}>{children}</div>
  ),
  DropdownMenuItem: ({ children, onSelect, disabled, className }: { children: React.ReactNode; onSelect?: () => void; disabled?: boolean; className?: string }) => (
    <button disabled={disabled} onClick={onSelect} className={className}>{children}</button>
  ),
}))

import { SidebarProvider } from "@/app/components/ui/sidebar"
import { AgendamentosLista } from "@/app/components/home/agendamentos/lista"

const ok = <T,>(data: T) => ({ success: true, status: 200, data })

/** The envelope of `GET /me/schedules`: page + TOTAL (the same as Chats). */
const pagina = (itens: IAgendamentoMeu[], total = itens.length) => ok({ itens, total })

function ag(extra: Partial<IAgendamentoMeu> = {}): IAgendamentoMeu {
  return {
    job_id: "job-1", id_hash: "sch-1", active: true, strategy: "interval", interval: 6, unit: "hours",
    next_run_at: new Date(Date.now() + 3_600_000).toISOString(), last_run_at: null,
    retry_count: 0, workflow_id: "wf-1", workflow_name: "Fluxo A", flag_ative: true,
    workspace_id: "ws-op", origem: "usuario",
    ...extra,
  }
}

const WORKSPACES = [
  { id_hash: "ws-op", name: "Ops", description: null, owner_id: null, is_default: false, my_role: "operator" },
  { id_hash: "ws-view", name: "Leitura", description: null, owner_id: null, is_default: false, my_role: "viewer" },
]

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
  H.useWorkspace.mockReturnValue({ workspaces: WORKSPACES })
  H.getMySchedules.mockResolvedValue(pagina([ag()]))
})

function montar() {
  return render(
    <SidebarProvider>
      <AgendamentosLista />
    </SidebarProvider>,
  )
}

describe("AgendamentosLista", () => {
  it("a linha NÃO leva ao editor — a Home é a única página de quem não é admin", async () => {
    // The `next/navigation` mock stays registered ON PURPOSE: if someone
    // puts `router.push` back on the row, `H.push` starts being called and this
    // test fails. Without the double, the "did not navigate" assertion would pass by accident.
    montar()
    const nome = await screen.findByText("Fluxo A")

    // It is not a button: a `<button>` with no action would promise a click that does not
    // happen, and the screen reader would still announce it as actionable.
    expect(nome.closest("button")).toBeNull()

    fireEvent.click(nome)
    expect(H.push).not.toHaveBeenCalled()
  })

  it("mostra um pausado com o motivo da pausa", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ workflow_name: "Parado", flag_ative: false })]))
    montar()
    expect(await screen.findByText("Parado")).toBeTruthy()
    expect(screen.getByText(/workflow inativo/)).toBeTruthy()
  })

  it("ativar chama updateSchedule(wf, job, {active:true})", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ active: false })]))
    H.updateSchedule.mockResolvedValue(ok({}))
    montar()
    await screen.findByText("Fluxo A")
    fireEvent.click(screen.getByText("Ativar"))
    await waitFor(() =>
      expect(H.updateSchedule).toHaveBeenCalledWith("wf-1", "job-1", { active: true }),
    )
  })

  it("recarga que falha depois de pausar NÃO apaga os agendamentos", async () => {
    // The §3 scenario: the secondary reload the action itself fires fails and
    // used to take the 12 rows away, replacing them with an error line.
    H.updateSchedule.mockResolvedValue(ok({}))
    montar()
    await screen.findByText("Fluxo A")
    H.getMySchedules.mockResolvedValue({ success: false, status: 502, error: { name: "AxiosError", message: "Bad gateway" } })
    fireEvent.click(screen.getByText("Pausar"))
    await waitFor(() =>
      expect(screen.getByText(/Não foi possível atualizar os agendamentos/)).toBeTruthy(),
    )
    expect(screen.getByText("Fluxo A")).toBeTruthy()
  })

  it("erro de 1ª carga usa a microcopy da casa e oferece 'Tentar de novo'", async () => {
    H.getMySchedules.mockResolvedValue({ success: false, status: 500, error: { name: "AxiosError", message: "Erro inesperado." } })
    montar()
    // The raw `detail` of a 500 does not reach the screen.
    expect(await screen.findByText("Não foi possível carregar os agendamentos.")).toBeTruthy()
    expect(screen.queryByText("Erro inesperado.")).toBeNull()

    H.getMySchedules.mockResolvedValue(pagina([ag()]))
    fireEvent.click(screen.getByText("Tentar de novo"))
    expect(await screen.findByText("Fluxo A")).toBeTruthy()
  })

  // The schedule WITH A TIME: it is the time that the time zone qualifies ("todo dia às 06:00").
  const comHora = { strategy: "cron" as const, cron_expression: "0 6 * * *", interval: null, unit: null }
  // The schedule WITHOUT A TIME: a cadence is the same in any time zone.
  const semHora = { strategy: "cron" as const, cron_expression: "*/30 * * * *", interval: null, unit: null }
  const FUSO_LOCAL = Intl.DateTimeFormat().resolvedOptions().timeZone
  const OUTRO_FUSO = FUSO_LOCAL === "America/La_Paz" ? "Europe/Lisbon" : "America/La_Paz"

  it("mostra o fuso do agendamento quando ele difere do do navegador", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ ...comHora, timezone: OUTRO_FUSO })]))
    montar()
    await screen.findByText("Fluxo A")
    expect(screen.getByText(new RegExp(`todo dia às 06:00 \\(${OUTRO_FUSO}\\)`))).toBeTruthy()
  })

  it("não nomeia o fuso quando é o mesmo do navegador", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ ...comHora, timezone: FUSO_LOCAL })]))
    montar()
    await screen.findByText("Fluxo A")
    expect(screen.queryByText(new RegExp(`\\(${FUSO_LOCAL}\\)`))).toBeNull()
  })

  it("não gruda o fuso numa descrição SEM hora (cadência)", async () => {
    // "a cada 30 min (America/La_Paz)" means nothing: the time zone only
    // qualifies a time of day, not a cadence.
    H.getMySchedules.mockResolvedValue(pagina([ag({ ...semHora, timezone: OUTRO_FUSO })]))
    montar()
    expect(await screen.findByText(/a cada 30 min/)).toBeTruthy()
    expect(screen.queryByText(new RegExp(`\\(${OUTRO_FUSO}\\)`))).toBeNull()
  })

  it("não gruda o fuso num cron que a tela não soube traduzir", async () => {
    H.getMySchedules.mockResolvedValue(pagina([
      ag({ strategy: "cron", cron_expression: "7 3 */2 * 1", interval: null, unit: null, timezone: OUTRO_FUSO }),
    ]))
    montar()
    await screen.findByText("Fluxo A")
    expect(screen.queryByText(new RegExp(`\\(${OUTRO_FUSO}\\)`))).toBeNull()
  })

  it("diz quantos agendamentos o servidor tem e o 'Ver mais' traz a página seguinte", async () => {
    // The server ceiling truncated silently: 200 rows on screen and nothing saying
    // there were more.
    H.getMySchedules.mockResolvedValue(pagina([ag()], 3))
    montar()
    await screen.findByText("Fluxo A")
    expect(screen.getByText(/mostrando 1 de 3/)).toBeTruthy()

    H.getMySchedules.mockResolvedValue(pagina(
      [ag({ job_id: "job-2", workflow_id: "wf-2", workflow_name: "Fluxo B" })],
      3,
    ))
    fireEvent.click(screen.getByText("Ver mais"))
    expect(await screen.findByText("Fluxo B")).toBeTruthy()
    // The second page is requested starting from what is already on screen.
    expect(H.getMySchedules).toHaveBeenLastCalledWith(200, 1)
    expect(screen.getByText("Fluxo A")).toBeTruthy()
  })

  it("não oferece 'Ver mais' quando a página é o total", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag()], 1))
    montar()
    await screen.findByText("Fluxo A")
    expect(screen.queryByText("Ver mais")).toBeNull()
  })

  it("com a lista VAZIA o rodapé continua na tela — e a falha ali tem onde avisar", async () => {
    // The empty-list branch exited via `return` BEFORE the footer: the "Ver mais" that
    // would bring the rest disappeared, and a failed reload had nowhere to show up.
    H.getMySchedules.mockResolvedValue(pagina([], 3))
    montar()
    expect(await screen.findByText("Nenhum agendamento.")).toBeTruthy()
    expect(screen.getByText(/mostrando 0 de 3/)).toBeTruthy()

    H.getMySchedules.mockResolvedValue({ success: false, status: 502, error: { name: "AxiosError", message: "Bad gateway" } })
    fireEvent.click(screen.getByText("Ver mais"))
    expect(await screen.findByText(/Não foi possível atualizar os agendamentos/)).toBeTruthy()
    expect(screen.getByText("Nenhum agendamento.")).toBeTruthy()
  })

  it("o menu herda a paleta da Home e seus itens têm alvo de 40px", async () => {
    montar()
    await screen.findByText("Fluxo A")
    // Portaled to <body>, the menu sits OUTSIDE the `.home dark` tree: without
    // `home-portal` it opens light over the near-black Home.
    expect(screen.getByTestId("menu").className).toContain("home-portal")
    // D5: the 40px rule applies to the ITEMS, not just the trigger.
    for (const rotulo of ["Pausar", "Rodar agora"]) {
      expect(screen.getByText(rotulo).closest("button")?.className).toContain("max-md:min-h-10")
    }
  })

  it("dois cliques em Pausar soltam um PUT só", async () => {
    // The PUT stays in flight on purpose: it is in that window that the second click landed.
    const adiado: { resolver: ((v: unknown) => void) | null } = { resolver: null }
    H.updateSchedule.mockReturnValue(new Promise((r) => { adiado.resolver = r }))
    montar()
    await screen.findByText("Fluxo A")
    fireEvent.click(screen.getByText("Pausar"))
    fireEvent.click(screen.getByText("Ativar")) // the row has already gone optimistic
    expect(H.updateSchedule).toHaveBeenCalledTimes(1)
    adiado.resolver?.(ok({}))
  })

  it("viewer não vê ações (pausar/ativar/rodar)", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ workspace_id: "ws-view" })]))
    montar()
    await screen.findByText("Fluxo A")
    expect(screen.queryByText("Rodar agora")).toBeNull()
    expect(screen.queryByText("Pausar")).toBeNull()
    expect(screen.queryByLabelText(/Ações de/)).toBeNull()
  })

  it("a linha: o principal ocupa o espaço e o ⋯ é irmão no flex — nunca por cima do texto", async () => {
    // It was an `absolute` ⋯ with `pr-7` reserved by hand: ZERO slack on desktop and,
    // on the phone (40px ⋯), 16px of text under the button.
    montar()
    const nome = await screen.findByText("Fluxo A")
    const principal = nome.closest("div[title]")!
    for (const c of ["min-w-0", "flex-1"]) expect(principal.className).toContain(c)
    expect(principal.className).not.toMatch(/\bpr-7\b/)

    const gatilho = screen.getByRole("button", { name: 'Ações de "Fluxo A"' })
    const linha = principal.closest('[data-slot="linha-do-meu"]')!
    expect(gatilho.closest('[data-slot="linha-do-meu"]')).toBe(linha)
    expect(linha.className).toContain("flex")
    expect(gatilho.className).not.toMatch(/\babsolute\b/)
  })

  it("a segunda linha truncada leva o texto inteiro no title", async () => {
    H.getMySchedules.mockResolvedValue(pagina([ag({ workflow_name: "Parado", flag_ative: false })]))
    montar()
    await screen.findByText("Parado")
    const resumo = screen.getByText(/workflow inativo/)
    expect(resumo.className).toContain("truncate")
    expect(resumo.getAttribute("title")).toBe(resumo.textContent)
  })

  it("Rodar agora com parâmetros abre o diálogo na paleta da Home", async () => {
    H.getWorkflowById.mockResolvedValue(ok({ params_schema: { area: { type: "string", required: true } } }))
    montar()
    await screen.findByText("Fluxo A")
    fireEvent.click(screen.getByText("Rodar agora"))
    expect((await screen.findByTestId("exec-dialog")).className).toContain("home-portal")
  })

  it("rodar agora abre o diálogo quando há params_schema", async () => {
    H.getWorkflowById.mockResolvedValue(ok({ params_schema: { area: { type: "string", required: true } } }))
    montar()
    await screen.findByText("Fluxo A")
    fireEvent.click(screen.getByText("Rodar agora"))
    expect(await screen.findByTestId("exec-dialog")).toBeTruthy()
    expect(H.executeWorkflow).not.toHaveBeenCalled()
  })

  it("rodar agora dispara direto quando não há params_schema", async () => {
    H.getWorkflowById.mockResolvedValue(ok({ params_schema: {} }))
    H.executeWorkflow.mockResolvedValue(ok({}))
    montar()
    await screen.findByText("Fluxo A")
    fireEvent.click(screen.getByText("Rodar agora"))
    await waitFor(() => expect(H.executeWorkflow).toHaveBeenCalledWith("wf-1", {}, false))
    expect(screen.queryByTestId("exec-dialog")).toBeNull()
  })
})
