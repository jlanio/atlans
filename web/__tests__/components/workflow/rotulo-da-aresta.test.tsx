/**
 * The edge's badge and its delete button must never share the same spot.
 *
 * On hover the badge used to move up a line and the delete button showed up
 * exactly where the badge had been. The hover that precedes any click moved
 * the badge away from the cursor and put the delete button under it: in the
 * real editor, a click aimed at "a ▾" right after hovering it deleted the edge
 * (5 out of 5 tries, Chromium). And the hidden button stayed clickable — an
 * inline `pointerEvents: "all"` won over its `pointer-events-none` — so a click
 * on a badge that lets clicks through (true/false) also landed on it.
 *
 * jsdom does no layout: what is checked here is the geometry the component
 * declares and when the button can be clicked.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, cleanup } from "@testing-library/react"
import type { ReactNode } from "react"
import { createPortal } from "react-dom"
import type { EdgeProps } from "@xyflow/react"
import { Position } from "@xyflow/react"

const estado = vi.hoisted(() => ({
  triggerEdgeChanges: (() => {}) as (changes: unknown[]) => void,
  nodeData: {} as Record<string, unknown>,
  canvasReadOnly: false,
}))

vi.mock("@xyflow/react", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@xyflow/react")>()),
  // A portal into React Flow's own HTML layer, as in the editor — rendered inline
  // the badge would be created inside the <svg>, in the SVG namespace.
  EdgeLabelRenderer: ({ children }: { children: ReactNode }) => createPortal(children, document.body),
  useStoreApi: () => ({
    getState: () => ({
      edges: [{ id: "e1", source: "s1", target: "s2" }],
      nodeLookup: new Map([["s1", { data: estado.nodeData }]]),
      edgeLookup: new Map([["e1", { id: "e1", source: "s1", target: "s2", data: { from_key: "a" } }]]),
      triggerEdgeChanges: estado.triggerEdgeChanges,
    }),
  }),
}))
vi.mock("@/app/components/workflow/canvas-interaction", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/app/components/workflow/canvas-interaction")>()),
  useCanvasReadOnly: () => estado.canvasReadOnly,
}))

import CustomEdge from "@/app/components/workflow/custom-edges"
import { SubflowScope } from "@/app/components/workflow/subflow-viewer/scope"

// Python Script with two output variables: the badge is a key selector.
const DUAS_SAIDAS = { dynamic_output: true, properties: { output_vars: "a, b" }, outputs: [] }
// Conditional branch: the badge is plain text and lets clicks through.
const RAMO = { branches: true, outputs: [{ name: "true" }, { name: "false" }], saidas: [{ name: "result" }] }

function desenhar(data: Record<string, unknown>, sourceHandleId: string | null = null) {
  const props = {
    id: "e1", source: "s1", target: "s2",
    sourceX: 0, sourceY: 0, targetX: 300, targetY: 0,
    sourcePosition: Position.Right, targetPosition: Position.Left,
    sourceHandleId, data,
  } as unknown as EdgeProps
  return render(<svg><CustomEdge {...props} /></svg>)
}

const rotulo = () => document.querySelector<HTMLElement>('[data-role="edge-label"]')!
const lixeira = () => document.querySelector<HTMLElement>('[data-role="edge-delete"]')

beforeEach(() => {
  cleanup()
  estado.triggerEdgeChanges = vi.fn()
  estado.canvasReadOnly = false
  estado.nodeData = DUAS_SAIDAS
})

describe("rótulo da aresta e botão de excluir", () => {
  it("o rótulo não sai do lugar quando o mouse passa por ele", () => {
    desenhar({ from_key: "a" })
    const antes = rotulo().style.transform
    fireEvent.mouseEnter(rotulo())
    expect(rotulo().style.transform).toBe(antes)
  })

  it("com rótulo, o botão de excluir fica acima dele, não no mesmo ponto", () => {
    desenhar({ from_key: "a" })
    fireEvent.mouseEnter(rotulo())
    expect(lixeira()!.style.transform).toBe(`${rotulo().style.transform} translateY(-22px)`)
  })

  it("sem rótulo, o botão de excluir continua no meio da aresta", () => {
    estado.nodeData = {}
    desenhar({})
    expect(rotulo()).toBeNull()
    expect(lixeira()!.style.transform).not.toContain("translateY")
  })

  it("escondido, o botão de excluir não recebe clique", () => {
    desenhar({ from_key: "a" })
    expect(lixeira()!.className).toContain("pointer-events-none")
    expect(lixeira()!.style.pointerEvents).toBe("")
    expect(screen.getByTitle("Excluir conexão").className).not.toContain("pointer-events-auto")
  })

  it("visível (mouse sobre a aresta), passa a receber clique e exclui", () => {
    desenhar({ from_key: "a" })
    fireEvent.mouseEnter(rotulo())
    expect(lixeira()!.className).toContain("pointer-events-auto")
    fireEvent.click(screen.getByTitle("Excluir conexão"))
    expect(estado.triggerEdgeChanges).toHaveBeenCalledWith([{ id: "e1", type: "remove" }])
  })

  it("clicar no rótulo depois do hover abre a troca de saída e não exclui", () => {
    desenhar({ from_key: "a" })
    fireEvent.mouseEnter(rotulo())
    fireEvent.click(screen.getByTitle("Trocar a saída que passa por esta aresta"))
    expect(screen.getByRole("button", { name: /^b/ })).toBeInTheDocument()
    expect(estado.triggerEdgeChanges).not.toHaveBeenCalled()
  })

  it("rótulo de ramo (deixa o clique passar) não tem o botão de excluir por baixo", () => {
    estado.nodeData = RAMO
    desenhar({ from_key: "result" }, "true")
    expect(rotulo().className).toContain("pointer-events-none")
    expect(lixeira()!.style.transform).toContain("translateY(-22px)")
    expect(lixeira()!.className).toContain("pointer-events-none")
  })

  it("canvas somente leitura (celular) não oferece excluir", () => {
    estado.canvasReadOnly = true
    desenhar({ from_key: "a" })
    fireEvent.mouseEnter(rotulo())
    expect(lixeira()).toBeNull()
  })

  it("o visualizador de subfluxo não oferece excluir", () => {
    const props = {
      id: "e1", source: "s1", target: "s2",
      sourceX: 0, sourceY: 0, targetX: 300, targetY: 0,
      sourcePosition: Position.Right, targetPosition: Position.Left,
      sourceHandleId: null, data: { from_key: "a" },
    } as unknown as EdgeProps
    render(<SubflowScope estadoPorId={new Map()}><svg><CustomEdge {...props} /></svg></SubflowScope>)
    expect(lixeira()).toBeNull()
  })
})
