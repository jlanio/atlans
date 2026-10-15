/**
 * After a conversation's first accepted drawing, the next ones apply by
 * themselves. The assistant builds on the SAVED workflow and never sees the
 * canvas's unsaved edits, so a connection drawn by hand in the meantime
 * vanished on the next drawing, with no one asked. A drawing that would drop
 * one now waits for the click, and says how many go.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, cleanup } from "@testing-library/react"

const canvas = vi.hoisted(() => ({
  nodes: [] as unknown[],
  edges: [] as unknown[],
}))

vi.mock("@xyflow/react", async (original) => ({
  ...(await original<Record<string, unknown>>()),
  useNodes: () => canvas.nodes,
  useEdges: () => canvas.edges,
}))

import ProposalCard from "@/app/components/workflow/assistente/cartao-proposta"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import type { WorkflowProposal } from "@/app/components/home/assistente/quadros"
import type { INodesAPI } from "@/service/types"

const catalogo = [
  {
    name: "DriveFile", alias: "Arquivo do Drive", description: "Lê", type: "trigger",
    properties: [{ name: "file_id", label: "Arquivo", type: "string", default: "" }],
    outputs: [{ name: "output" }],
  },
  {
    name: "Buffer", alias: "Buffer", description: "Buffer", type: "action",
    properties: [{ name: "distance", label: "Distância", type: "string", default: "" }],
    outputs: [{ name: "output" }],
  },
] as unknown as INodesAPI[]

const PROPOSTA: WorkflowProposal = {
  definicao: {
    nodes: [
      { id: "a", name: "DriveFile", type: "trigger", properties: { file_id: "mun.shp" }, position: { x: 0, y: 0 } },
      { id: "b", name: "Buffer", type: "action", properties: { distance: "500" }, position: { x: 0, y: 0 } },
      { id: "c", name: "Buffer", type: "action", properties: { distance: "900" }, position: { x: 0, y: 0 } },
    ],
    edges: [{ source: "a", target: "b" }, { source: "a", target: "c" }],
  },
  nos: 3, arestas: 2, desenhar: true, ok: true, erros: 0, avisos: 0,
}

const no = (id: string, name: string, properties: Record<string, string>) => ({
  id, position: { x: 0, y: 0 }, type: "DefaultIcon",
  data: { name, properties, alias: name, type: "action" },
})

beforeEach(() => {
  cleanup()
  useWorkflowCatalogStore.setState({ nodesAPI: catalogo })
  canvas.nodes = [
    no("a", "DriveFile", { file_id: "mun.shp" }),
    no("b", "Buffer", { distance: "500" }),
    no("c", "Buffer", { distance: "900" }),
  ]
})

describe("cartão da proposta com a conversa já liberada", () => {
  it("desenha sozinho quando não derruba nenhuma ligação", () => {
    canvas.edges = [{ id: "1", source: "a", target: "b" }, { id: "2", source: "a", target: "c" }]
    const onAplicar = vi.fn()
    render(<ProposalCard proposta={PROPOSTA} onAplicar={onAplicar} liberado onLiberar={() => {}} />)
    expect(onAplicar).toHaveBeenCalledTimes(1)
  })

  it("espera o clique quando uma ligação feita à mão sumiria", () => {
    // b→c was drawn on the canvas after the last save; the drawing does not have it.
    canvas.edges = [
      { id: "1", source: "a", target: "b" }, { id: "2", source: "a", target: "c" },
      { id: "3", source: "b", target: "c" },
    ]
    const onAplicar = vi.fn()
    render(<ProposalCard proposta={PROPOSTA} onAplicar={onAplicar} liberado onLiberar={() => {}} />)

    expect(onAplicar).not.toHaveBeenCalled()
    expect(screen.getByText(/1 ligação removida/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Desenhar no canvas/ }))
    expect(onAplicar).toHaveBeenCalledTimes(1)
    // Drawn: it says so and stops offering the button.
    expect(screen.getByText("Desenhado no canvas")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Desenhar no canvas/ })).toBeNull()
  })

  it("retido, não se desenha sozinho depois que o canvas muda", () => {
    // Held back by the hand-made b→c. The person then draws a NEWER card, whose
    // canvas no longer has b→c: recomputed against it, this older card found
    // nothing to remove and drew itself over the newer one.
    canvas.edges = [
      { id: "1", source: "a", target: "b" }, { id: "2", source: "a", target: "c" },
      { id: "3", source: "b", target: "c" },
    ]
    const onAplicar = vi.fn()
    const card = () => <ProposalCard proposta={PROPOSTA} onAplicar={onAplicar} liberado onLiberar={() => {}} />
    const { rerender } = render(card())
    expect(onAplicar).not.toHaveBeenCalled()

    canvas.edges = [{ id: "1", source: "a", target: "b" }, { id: "2", source: "a", target: "c" }]
    rerender(card())
    expect(onAplicar).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: /Desenhar no canvas/ })).toBeInTheDocument()
  })

  it("ligação que o próprio assistente desenhou não segura o desenho seguinte", () => {
    // b→c came from the conversation's previous drawing: the new one rewiring it
    // is the assistant changing its own work, not a connection made by hand.
    canvas.edges = [
      { id: "1", source: "a", target: "b" }, { id: "2", source: "a", target: "c" },
      { id: "3", source: "b", target: "c" },
    ]
    const onAplicar = vi.fn()
    render(<ProposalCard proposta={PROPOSTA} onAplicar={onAplicar} liberado onLiberar={() => {}}
      arestasDoAssistente={new Set(["1", "2", "3"])} />)
    expect(onAplicar).toHaveBeenCalledTimes(1)
  })
})
