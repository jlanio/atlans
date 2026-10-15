/**
 * Sub-workflow port editor, after ports became connection points.
 *
 * While `ports` was just an allowlist, touching it was harmless. Now each port
 * is a handle on the canvas: renaming or removing one with an edge attached
 * leaves the edge pointing to a point that no longer exists — it disappears
 * from the canvas, keeps executing, and with no line drawn you can't even
 * delete it. It's the same reason the Python Script port editor locks.
 *
 * The two editors lock on OPPOSITE sides, because their ports are handles on
 * opposite sides. SubWorkflowOutput's ports are input handles: the edges at
 * risk are the ones arriving at it. SubWorkflowInput's ports are OUTPUT handles
 * (`outputs_from_ports`): the edges at risk are the ones LEAVING it. This file
 * used to say "the input never locks", from when its ports were not handles;
 * counting only the arriving edges — always zero on a trigger — left its editor
 * open, and renaming `b` to `c` kept the `b` edge saved as `source_handle: b,
 * from_key: b`, drawn nowhere. After a reload it showed up on port `a`, still
 * asking for `b`, a key the node no longer produces.
 */
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { Edge, ReactFlowProvider } from "@xyflow/react"

import SubWorkflowPortsHelper from "@/app/components/workflow/nodes-configuration/sub-workflow-ports-helper"
import NodeConfigForm from "@/app/components/workflow/node-config-modal/node-config-form"
import { INodeContext } from "@/context/useFlowContext"

// The form's field registry pulls the code field in, and with it Monaco.
vi.mock("@monaco-editor/react", () => ({
  default: () => <div data-testid="monaco" />,
  Editor: () => <div data-testid="monaco" />,
  useMonaco: () => null,
  loader: { config: () => {} },
}))

afterEach(cleanup)

function montar(variant: "input" | "output", { entrada = 0, saida = 0 }: { entrada?: number; saida?: number } = {}) {
  return render(
    <SubWorkflowPortsHelper
      values={{ ports: JSON.stringify(["focos", "mapa"]) }}
      setNodeField={() => {}}
      hasUnsaved={false}
      variant={variant}
      conexoesDeEntrada={entrada}
      conexoesDeSaida={saida}
    />,
  )
}

const addButton = () => screen.getByRole("button", { name: /adicionar porta/i })

function esperarTravado() {
  expect(addButton()).toBeDisabled()
  for (const campo of screen.getAllByRole("textbox")) {
    expect(campo).toBeDisabled()
  }
  for (const remover of screen.getAllByTitle("Remover porta")) {
    expect(remover).toBeDisabled()
  }
}

describe("SubWorkflowPortsHelper — trava com arestas ligadas", () => {
  it("saída com aresta ligada bloqueia a edição", () => {
    montar("output", { entrada: 2 })
    esperarTravado()
  })

  it("o aviso diz quantas conexões impedem a edição", () => {
    montar("output", { entrada: 2 })
    expect(screen.getByText(/Há 2 conexões chegando a este nó/)).toBeInTheDocument()
  })

  it("uma conexão só é dita no singular", () => {
    montar("output", { entrada: 1 })
    expect(screen.getByText(/Há 1 conexão/)).toBeInTheDocument()
  })

  it("saída sem aresta continua editável", () => {
    montar("output")

    expect(addButton()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })

  it("entrada com aresta SAINDO bloqueia a edição — as portas dela são pontos de saída", () => {
    // The defect: renaming or removing a SubWorkflowInput port with an edge
    // leaving it stranded the edge on a handle that no longer exists.
    montar("input", { saida: 2 })

    esperarTravado()
    expect(screen.getByText(/Há 2 conexões saindo deste nó/)).toBeInTheDocument()
  })

  it("entrada sem aresta saindo continua editável, por mais que se conte chegando", () => {
    // SubWorkflowInput is a trigger: nothing arrives at it. What the old rule
    // ("the input never locks") got right is that an ARRIVING count must not
    // lock it — there the lock belongs to the edges that leave.
    montar("input", { entrada: 3 })

    expect(addButton()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })
})

/**
 * The count has to come from the form: it is the form that sees the canvas
 * edges. It only counted the arriving ones — on a trigger always zero — so even
 * a helper that knew its side would have stayed unlocked.
 */
describe("NodeConfigForm — conta as arestas do lado em que ficam as portas", () => {
  function noDe(name: "SubWorkflowInput" | "SubWorkflowOutput"): INodeContext {
    const entrada = name === "SubWorkflowInput"
    return {
      id: "no-1",
      position: { x: 0, y: 0 },
      data: {
        name,
        alias: name,
        description: "",
        type: entrada ? "trigger" : "output",
        properties: { ports: JSON.stringify(["a", "b"]) },
        fields: [{ name: "ports", label: "Portas", type: "object", default: [] }],
        inputs: entrada ? [] : [{ name: "a" }, { name: "b" }],
        outputs: entrada ? [{ name: "a" }, { name: "b" }] : [],
        outputs_from_ports: entrada,
        dynamic_inputs: !entrada,
      },
    } as unknown as INodeContext
  }

  function montarForm(name: "SubWorkflowInput" | "SubWorkflowOutput", arestas: Edge[]) {
    const no = noDe(name)
    return render(
      <ReactFlowProvider initialNodes={[no]} initialEdges={arestas}>
        <NodeConfigForm
          nodeFound={no}
          values={{ ports: JSON.stringify(["a", "b"]) }}
          setNodeField={() => {}}
          saveNodeConfig={() => {}}
          nodeName={name}
          requiresCredential={false}
        />
      </ReactFlowProvider>,
    )
  }

  it("SubWorkflowInput com uma aresta saindo da porta b trava o editor", () => {
    montarForm("SubWorkflowInput", [
      { id: "e1", source: "no-1", target: "buffer", sourceHandle: "b", data: { from_key: "b" } },
    ])

    esperarTravado()
    expect(screen.getByText(/Há 1 conexão saindo deste nó/)).toBeInTheDocument()
  })

  it("SubWorkflowOutput segue travando pelas arestas que chegam", () => {
    montarForm("SubWorkflowOutput", [
      { id: "e1", source: "buffer", target: "no-1", targetHandle: "a", data: { to_key: "a" } },
    ])

    esperarTravado()
    expect(screen.getByText(/Há 1 conexão chegando a este nó/)).toBeInTheDocument()
  })
})
