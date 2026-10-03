import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { GrupoSecao, textoDaContagemDoGrupo, type GrupoSecaoProps } from "@/app/components/projects/grupo-secao"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"

afterEach(cleanup)

function wf(extra: Partial<IWorkflow> = {}): IWorkflow {
  return {
    id_hash: "wf", flag_ative: true, name: "Fluxo", description: "", version: "1", priority: 0,
    definition: { nodes: [], edges: [] }, created_by_id: "u1", updated_by_id: "u1", ...extra,
  }
}

const grupo: IWorkflowGroup = {
  id: 1, id_hash: "g1", name: "Hidrologia", description: "Rotinas diárias da bacia", workflow_count: 3, active_count: 2,
  created_at: "", updated_at: "",
}
const lista = [wf({ id_hash: "a", name: "Outorgas" }), wf({ id_hash: "b", name: "Cheias" }), wf({ id_hash: "c", name: "Nascentes" })]

function props(extra: Partial<GrupoSecaoProps> = {}): GrupoSecaoProps {
  return {
    grupo, workflows: lista, totalNoGrupo: 3, ativosNoGrupo: 2, recolhido: false, onToggle: vi.fn(),
    canEdit: true, podeArrastar: true, arrastandoEste: false, alvoDeReordenacao: false, recebendoWorkflow: false,
    nomeDoArrastado: null, onDragOver: vi.fn(), onDragLeave: vi.fn(), onDrop: vi.fn(),
    onDragStartGrupo: vi.fn(), onDragEndGrupo: vi.fn(), onRenomear: vi.fn(), onExcluir: vi.fn(),
    renderLinha: w => <span data-linha={w.id_hash}>{w.name}</span>,
    ...extra,
  }
}

describe("textoDaContagemDoGrupo", () => {
  it("plural, singular, vazio e o recorte do filtro", () => {
    expect(textoDaContagemDoGrupo(3, 2)).toBe("3 workflows · 2 ativos")
    expect(textoDaContagemDoGrupo(1, 1)).toBe("1 workflow · 1 ativo")
    expect(textoDaContagemDoGrupo(0, 0)).toBe("vazio")
    expect(textoDaContagemDoGrupo(3, 2, 1)).toBe("3 workflows · 2 ativos · 1 com este filtro")
    expect(textoDaContagemDoGrupo(3, 2, 3)).toBe("3 workflows · 2 ativos")
  })
})

describe("GrupoSecao", () => {
  it("cabeçalho: nome, contagem do grupo inteiro, descrição, e o corpo com uma linha por workflow", () => {
    render(<GrupoSecao {...props()} />)
    expect(screen.getByRole("region", { name: "Hidrologia" })).toBeInTheDocument()
    expect(screen.getByText("3 workflows · 2 ativos")).toBeInTheDocument()
    expect(screen.getByText("Rotinas diárias da bacia")).toBeInTheDocument()
    expect(screen.getAllByRole("listitem").map(li => li.textContent)).toEqual(["Outorgas", "Cheias", "Nascentes"])
  })

  it("recolher: aria-expanded e o corpo fica escondido mas presente (aria-controls válido)", () => {
    const p = props()
    const { rerender } = render(<GrupoSecao {...p} />)
    const botao = screen.getByRole("button", { name: /^Hidrologia/ })
    expect(botao).toHaveAttribute("aria-expanded", "true")
    expect(botao).toHaveAttribute("aria-controls", "grupo-g1-corpo")
    const corpo = document.getElementById("grupo-g1-corpo")
    expect(corpo).not.toBeNull()
    expect(corpo).not.toHaveAttribute("hidden")
    fireEvent.click(botao)
    expect(p.onToggle).toHaveBeenCalledWith("g1")

    rerender(<GrupoSecao {...p} recolhido />)
    expect(screen.getByRole("button", { name: /^Hidrologia/ })).toHaveAttribute("aria-expanded", "false")
    // The body stays in the DOM (the button references it via aria-controls), just
    // hidden; the rows are not mounted when collapsed.
    const corpoRecolhido = document.getElementById("grupo-g1-corpo")
    expect(corpoRecolhido).not.toBeNull()
    expect(corpoRecolhido).toHaveAttribute("hidden")
    expect(screen.queryByText("Outorgas")).toBeNull()
  })

  it("com filtro ativo a contagem ganha o recorte", () => {
    render(<GrupoSecao {...props({ workflows: [lista[0]] })} />)
    expect(screen.getByText("3 workflows · 2 ativos · 1 com este filtro")).toBeInTheDocument()
  })

  it("vazio: convite para quem edita, frase neutra para quem só vê", () => {
    const { rerender } = render(<GrupoSecao {...props({ workflows: [], totalNoGrupo: 0, ativosNoGrupo: 0 })} />)
    expect(screen.getByText("vazio")).toBeInTheDocument()
    expect(screen.getByText("Nenhum workflow aqui. Arraste um para cá ou use «Mover para grupo» no menu do workflow.")).toBeInTheDocument()
    rerender(<GrupoSecao {...props({ workflows: [], totalNoGrupo: 0, ativosNoGrupo: 0, canEdit: false })} />)
    expect(screen.getByText("Nenhum workflow neste grupo.")).toBeInTheDocument()
  })

  it("estados de arrasto: receber workflow, reordenar e o próprio arrastado", () => {
    const { container, rerender } = render(<GrupoSecao {...props({ recebendoWorkflow: true, nomeDoArrastado: "Recorte por município" })} />)
    const secao = container.firstElementChild!
    expect(secao.className).toContain("border-primary")
    expect(screen.getByText("Solte para mover «Recorte por município» para Hidrologia")).toBeInTheDocument()

    rerender(<GrupoSecao {...props({ alvoDeReordenacao: true })} />)
    expect(secao.className).toContain("border-dashed")
    expect(screen.getByText("Soltar aqui move o grupo para esta posição")).toBeInTheDocument()

    rerender(<GrupoSecao {...props({ arrastandoEste: true })} />)
    expect(secao.className).toContain("opacity-40")
  })

  it("a alça arrasta o grupo e só existe quando pode arrastar", () => {
    const p = props()
    const { rerender } = render(<GrupoSecao {...p} />)
    const alca = screen.getByTitle("Arraste para reordenar os grupos")
    fireEvent.dragStart(alca)
    expect(p.onDragStartGrupo).toHaveBeenCalledWith("g1")
    fireEvent.dragEnd(alca)
    expect(p.onDragEndGrupo).toHaveBeenCalledTimes(1)
    rerender(<GrupoSecao {...p} podeArrastar={false} />)
    expect(screen.queryByTitle("Arraste para reordenar os grupos")).toBeNull()
  })

  it("os eventos de soltar sobem pela seção", () => {
    const p = props()
    const { container } = render(<GrupoSecao {...p} />)
    fireEvent.dragOver(container.firstElementChild!)
    fireEvent.drop(container.firstElementChild!)
    expect(p.onDragOver).toHaveBeenCalledTimes(1)
    expect(p.onDrop).toHaveBeenCalledTimes(1)
  })

  it("menu do grupo: Renomear e Excluir, só para quem edita", () => {
    const p = props()
    const { rerender } = render(<GrupoSecao {...p} />)
    fireEvent.keyDown(screen.getByRole("button", { name: "Ações do grupo Hidrologia" }), { key: "Enter" })
    const itens = screen.getAllByRole("menuitem")
    expect(itens.map(i => i.textContent?.trim())).toEqual(["Renomear grupo", "Excluir grupo"])
    fireEvent.click(itens[1])
    expect(p.onExcluir).toHaveBeenCalledWith(grupo)

    rerender(<GrupoSecao {...p} canEdit={false} />)
    expect(screen.queryByRole("button", { name: "Ações do grupo Hidrologia" })).toBeNull()
  })

  it("children substitui as linhas montadas por renderLinha", () => {
    render(<GrupoSecao {...props({ renderLinha: undefined })}><p>corpo pronto</p></GrupoSecao>)
    expect(screen.getByText("corpo pronto")).toBeInTheDocument()
    expect(screen.queryByRole("listitem")).toBeNull()
  })
})
