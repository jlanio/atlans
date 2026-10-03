import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { LinhaWorkflow, ehNovo, formatarHa, textoDeAutoria, type LinhaWorkflowProps } from "@/app/components/projects/linha-workflow"
import { derivarGatilho, resumirAgendamento } from "@/app/components/projects/gatilho"
import type { ComoAnda } from "@/app/components/projects/como-anda"
import type { IWorkflow, IWorkflowGroup, IWorkflowSchedule } from "@/service/types"

afterEach(cleanup)

const agora = new Date()
const haMin = (min: number) => new Date(agora.getTime() - min * 60_000).toISOString()
const haDias = (dias: number) => new Date(agora.getTime() - dias * 86_400_000).toISOString()

function wf(extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: "wf-1", flag_ative: true, name: "Consolidação de outorgas", description: "Une as outorgas da ANA e do IGAM",
    version: "1", priority: 0, definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u2",
    workspace_id: "ws-1", group_id: "g1", created_at: haDias(5), updated_at: haDias(2),
    created_by_username: "joao", updated_by_username: "maria", ...extra,
  }
}

const grupos: IWorkflowGroup[] = [
  { id: 1, id_hash: "g1", name: "Hidrologia", workflow_count: 3, created_at: "", updated_at: "" },
  { id: 2, id_hash: "g2", name: "Entregas de campo", workflow_count: 2, created_at: "", updated_at: "" },
]

// Tomorrow at 06:00 on the local clock: it is what "próxima amanhã, 06:00" expects.
const amanhaAsSeis = new Date(agora)
amanhaAsSeis.setDate(amanhaAsSeis.getDate() + 1)
amanhaAsSeis.setHours(6, 0, 0, 0)

const schedule: IWorkflowSchedule = {
  active: true, next_run_at: amanhaAsSeis.toISOString(), last_run_at: null,
  strategy: "cron", cron_expression: "0 6 * * *",
}

const concluida: ComoAnda = { tipo: "concluida", quando: "há 3 h", instante: 1, erro: null, total: 61, falhas: 3, mediana: 180 }
const executando: ComoAnda = { tipo: "executando", desde: "há 4 min", instante: 1, origem: "agendado", executor: "geo-01", tipica: 420 }

function props(extra: Partial<LinhaWorkflowProps> = {}): LinhaWorkflowProps {
  const workflow = extra.workflow ?? wf()
  return {
    workflow,
    gatilho: derivarGatilho(workflow),
    resumoDoAgendamento: resumirAgendamento(workflow.schedule, workflow.flag_ative, agora),
    comoAnda: concluida,
    grupos,
    canEdit: true, canExecute: true, canManage: false, podeMover: false,
    hasDnd: true, isDragging: false, executando: false, duplicando: false, runIdVivo: null,
    onOpen: vi.fn(), onPrefetch: vi.fn(), onRun: vi.fn(), onVerExecucao: vi.fn(), onAtivar: vi.fn(), onDesativar: vi.fn(),
    onConfigure: vi.fn(), onPortal: vi.fn(), onMove: vi.fn(), onDuplicate: vi.fn(), onDelete: vi.fn(), onViewRuns: vi.fn(),
    onAddToGroup: vi.fn(), onRemoveFromGroup: vi.fn(), onDragStart: vi.fn(), onDragEnd: vi.fn(),
    ...extra,
  }
}

function abrirMenu(nome = "Consolidação de outorgas") {
  fireEvent.keyDown(screen.getByRole("button", { name: `Mais ações de ${nome}` }), { key: "Enter" })
  return screen.getAllByRole("menuitem")
}

describe("LinhaWorkflow", () => {
  it("botão no nome abre o editor; a linha inteira também, sem role; hover aquece a rota", () => {
    const p = props()
    render(<LinhaWorkflow {...p} />)
    const nome = screen.getByRole("button", { name: "Abrir Consolidação de outorgas no editor" })
    const linha = nome.closest("[data-workflow]")!
    expect(linha).not.toHaveAttribute("role")
    fireEvent.click(nome)
    fireEvent.click(linha)
    expect(p.onOpen).toHaveBeenCalledTimes(2)
    expect(p.onOpen).toHaveBeenCalledWith("wf-1")
    fireEvent.pointerEnter(linha)
    expect(p.onPrefetch).toHaveBeenCalledWith("wf-1")
  })

  it("o que ele é: tile com o gatilho, descrição, metadados com agendamento e autoria", () => {
    const workflow = wf({ has_schedule_trigger: true, schedule })
    render(<LinhaWorkflow {...props({ workflow })} />)
    expect(screen.getByTitle("Agendado")).toBeInTheDocument()
    expect(screen.getByText("Une as outorgas da ANA e do IGAM")).toBeInTheDocument()
    // The trigger label shows up twice: in the tile (screen reader only) and in the metadata.
    const meta = screen.getByText("Agendado", { selector: ".text-foreground" }).closest("p")!
    expect(meta).toHaveTextContent("Agendado · todo dia às 06:00 · próxima amanhã, 06:00 · alterado há 2 d por maria")
    // "Como anda" beside it, and Executar on the right side.
    expect(screen.getByText("Concluída há 3 h")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Executar Consolidação de outorgas agora" })).toBeInTheDocument()
  })

  it("agendamento pausado por workflow inativo fica em âmbar; cron não reconhecido vai em code", () => {
    const workflow = wf({ flag_ative: false, has_schedule_trigger: true, schedule: { ...schedule, cron_expression: "5 4 * * 1,3" } })
    render(<LinhaWorkflow {...props({ workflow })} />)
    const pausa = screen.getByText("Agendamento pausado (workflow inativo)")
    expect(pausa.className).toContain("text-amber")
    expect(screen.getByText("5 4 * * 1,3").tagName).toBe("CODE")
    expect(screen.getByText("Inativo")).toBeInTheDocument()
  })

  it("selos: sub-fluxo, portal público/privado, novo", () => {
    const { rerender } = render(<LinhaWorkflow {...props({ workflow: wf({ is_subworkflow: true, has_publish_map: true, portal_access: "public", created_at: haMin(30), updated_at: haMin(30) }) })} />)
    expect(screen.getByText("Sub-fluxo")).toBeInTheDocument()
    expect(screen.getByText("Portal público")).toBeInTheDocument()
    expect(screen.getByText("Novo")).toBeInTheDocument()
    expect(screen.getByTitle("Chamado por outros workflows")).toBeInTheDocument()

    rerender(<LinhaWorkflow {...props({ workflow: wf({ has_publish_map: true, portal_access: "private" }) })} />)
    expect(screen.getByText("Portal privado")).toBeInTheDocument()
    rerender(<LinhaWorkflow {...props({ workflow: wf({ has_publish_map: true, portal_access: "disabled" }) })} />)
    expect(screen.queryByText(/Portal/)).toBeNull()
    expect(screen.queryByText("Novo")).toBeNull()
  })

  it("Executar chama onRun e trava enquanto prepara; no sub-fluxo fica apagado mas clicável", () => {
    const p = props()
    const { rerender } = render(<LinhaWorkflow {...p} />)
    const executar = screen.getByRole("button", { name: "Executar Consolidação de outorgas agora" })
    fireEvent.click(executar)
    expect(p.onRun).toHaveBeenCalledWith(p.workflow)
    expect(p.onOpen).not.toHaveBeenCalled()

    rerender(<LinhaWorkflow {...p} executando />)
    expect(screen.getByRole("button", { name: "Executar Consolidação de outorgas agora" })).toBeDisabled()

    const sub = props({ workflow: wf({ is_subworkflow: true }) })
    rerender(<LinhaWorkflow {...sub} />)
    const play = screen.getByRole("button", { name: "Executar Consolidação de outorgas agora" })
    expect(play.className).toContain("opacity-45")
    expect(play).toHaveAttribute("title", "Sub-fluxo: executar sozinho normalmente não faz o esperado")
    fireEvent.click(play)
    expect(sub.onRun).toHaveBeenCalledTimes(1)
  })

  it("Ativar só na linha inativa com permissão de editar", () => {
    const p = props({ workflow: wf({ flag_ative: false }) })
    const { rerender } = render(<LinhaWorkflow {...p} />)
    expect(screen.queryByRole("button", { name: /Executar/ })).toBeNull()
    fireEvent.click(screen.getByRole("button", { name: "Ativar Consolidação de outorgas" }))
    expect(p.onAtivar).toHaveBeenCalledWith(p.workflow)

    rerender(<LinhaWorkflow {...p} canEdit={false} />)
    expect(screen.queryByRole("button", { name: /Ativar/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /Executar/ })).toBeNull()

    rerender(<LinhaWorkflow {...props()} />)
    expect(screen.queryByRole("button", { name: /Ativar/ })).toBeNull()
  })

  it("Ver execução só com run vivo, e leva ao run", () => {
    const p = props({ comoAnda: executando, runIdVivo: "run-9" })
    const { rerender } = render(<LinhaWorkflow {...p} />)
    fireEvent.click(screen.getByRole("button", { name: "Ver execução de Consolidação de outorgas" }))
    expect(p.onVerExecucao).toHaveBeenCalledWith("run-9")
    expect(screen.queryByRole("button", { name: /Executar/ })).toBeNull()

    // Metrics say "rodando" (running) but the context does not have the run yet: with no id, the button stays Executar.
    rerender(<LinhaWorkflow {...p} runIdVivo={null} />)
    expect(screen.queryByRole("button", { name: /Ver execução/ })).toBeNull()
    expect(screen.getByRole("button", { name: /Executar/ })).toBeInTheDocument()
  })

  it("menu de quem edita: ordem fixa, com Desativar… na ativa e Ativar na inativa", () => {
    const p = props({ canManage: true, podeMover: true })
    const { rerender } = render(<LinhaWorkflow {...p} />)
    let itens = abrirMenu()
    expect(itens.map(i => i.textContent?.trim())).toEqual([
      "Abrir no editor", "Ver execuções", "Duplicar", "Configurar",
      "Mover para grupo", "Remover do grupo", "Mover para workspace",
      "Desativar…", "Excluir…",
    ])
    fireEvent.click(itens[8])
    expect(p.onDelete).toHaveBeenCalledWith("wf-1")
    expect(p.onOpen).not.toHaveBeenCalled()

    const inativo = props({ workflow: wf({ flag_ative: false, group_id: null, has_publish_map: true }) })
    rerender(<LinhaWorkflow {...inativo} />)
    itens = abrirMenu()
    expect(itens.map(i => i.textContent?.trim())).toEqual([
      "Abrir no editor", "Ver execuções", "Duplicar", "Configurar", "Configurar portal",
      "Mover para grupo", "Ativar", "Excluir…",
    ])
    fireEvent.click(itens[6])
    expect(inativo.onAtivar).toHaveBeenCalledWith(inativo.workflow)
  })

  it("Desativar… e Ver execuções sobem pelos callbacks certos", () => {
    const p = props()
    render(<LinhaWorkflow {...p} />)
    abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: "Desativar…" }))
    expect(p.onDesativar).toHaveBeenCalledWith(p.workflow)
    abrirMenu()
    fireEvent.click(screen.getByRole("menuitem", { name: "Ver execuções" }))
    expect(p.onViewRuns).toHaveBeenCalledWith("wf-1")
  })

  it("viewer: sem alça, sem Executar, e o menu reduzido a abrir e ver execuções", () => {
    const p = props({ canEdit: false, canExecute: false })
    const { container } = render(<LinhaWorkflow {...p} />)
    expect(container.querySelector("[title='Arraste para mover para um grupo']")).toBeNull()
    expect(container.firstElementChild).not.toHaveAttribute("draggable", "true")
    expect(screen.queryByRole("button", { name: /Executar/ })).toBeNull()
    const itens = abrirMenu()
    expect(itens.map(i => i.textContent?.trim())).toEqual(["Abrir no editor", "Ver execuções"])
    expect(within(itens[0].parentElement!).queryByRole("separator")).toBeNull()
  })

  it("alça e arrasto só com grupos e permissão", () => {
    const p = props()
    const { container, rerender } = render(<LinhaWorkflow {...p} />)
    expect(container.querySelector("[title='Arraste para mover para um grupo']")).not.toBeNull()
    fireEvent.dragStart(container.firstElementChild!)
    expect(p.onDragStart).toHaveBeenCalledWith("wf-1")
    rerender(<LinhaWorkflow {...p} hasDnd={false} />)
    expect(container.querySelector("[title='Arraste para mover para um grupo']")).toBeNull()
  })

  it("ponto do tile: verde ativo, cinza inativo, azul pulsando em execução", () => {
    const { container, rerender } = render(<LinhaWorkflow {...props()} />)
    // `.border-card` distinguishes the tile's dot from the green dot of "como anda".
    expect(container.querySelector(".border-card.bg-green-500")).not.toBeNull()
    rerender(<LinhaWorkflow {...props({ workflow: wf({ flag_ative: false }) })} />)
    expect(container.querySelector(".border-card.bg-green-500")).toBeNull()
    expect(container.querySelector(".border-card.bg-muted-foreground\\/40")).not.toBeNull()
    rerender(<LinhaWorkflow {...props({ comoAnda: executando })} />)
    expect(container.querySelector(".border-card.bg-blue-500 .motion-safe\\:animate-ping")).not.toBeNull()
  })
})

describe("helpers da linha", () => {
  const ref = new Date("2026-09-07T12:00:00Z")

  it("formatarHa: relativo até um mês, data depois", () => {
    expect(formatarHa("2026-09-07T11:59:40Z", ref)).toBe("agora")
    expect(formatarHa("2026-09-07T11:15:00Z", ref)).toBe("há 45 min")
    expect(formatarHa("2026-09-07T05:00:00Z", ref)).toBe("há 7 h")
    expect(formatarHa("2026-09-05T10:00:00Z", ref)).toBe("há 2 d")
    expect(formatarHa("2026-07-01T10:00:00Z", ref)).toMatch(/^em 1 jul, \d{2}:\d{2}$/)
    expect(formatarHa(null, ref)).toBe("—")
  })

  it("textoDeAutoria: alterado × criado, com e sem nome, e nulo sem datas", () => {
    expect(textoDeAutoria({ created_at: "2026-09-02T10:00:00Z", updated_at: "2026-09-05T10:00:00Z", created_by_username: "joao", updated_by_username: "maria" }, ref)).toBe("alterado há 2 d por maria")
    expect(textoDeAutoria({ created_at: "2026-09-07T09:00:00Z", updated_at: "2026-09-07T09:00:00Z", created_by_username: "joao", updated_by_username: "joao" }, ref)).toBe("criado há 3 h por joao")
    expect(textoDeAutoria({ created_at: "2026-09-02T10:00:00Z", updated_at: "2026-09-05T10:00:00Z", created_by_username: null, updated_by_username: null }, ref)).toBe("alterado há 2 d")
    expect(textoDeAutoria({ created_at: "2026-09-02T10:00:00Z", updated_at: undefined, created_by_username: "joao" }, ref)).toBe("criado há 5 d por joao")
    expect(textoDeAutoria({}, ref)).toBeNull()
  })

  it("ehNovo: menos de 24 h desde a criação", () => {
    expect(ehNovo({ created_at: "2026-09-06T13:00:00Z" }, ref)).toBe(true)
    expect(ehNovo({ created_at: "2026-09-06T11:00:00Z" }, ref)).toBe(false)
    expect(ehNovo({}, ref)).toBe(false)
  })
})
