/**
 * The Input box needs to state the name under which the data ARRIVES.
 *
 * For the Python Script the panel shows the variable name — it's the text that
 * gets dragged into the code. Before named ports that name was the PARENT's
 * output key, and it was right: that's how the executor named the input. With
 * ports, the rule became `to_key if to_key else from_key`, and the panel kept
 * telling people to use `output` when the variable was called `pontos` — it
 * went from missing information to giving wrong information.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

const edges: unknown[] = []
const nodes: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useEdges: () => edges,
  useNodes: () => nodes,
}))
vi.mock("@/app/stores/workflowExecutionStore", () => ({
  useWorkflowExecutionStore: () => undefined,
}))

import InputInspector from "@/app/components/workflow/node-config-modal/input-inspector"
import { INodeContext } from "@/context/useFlowContext"

const pai = {
  id: "pai",
  data: {
    name: "ReadGeoJSON", alias: "Leitor",
    saidas: [{ name: "output" }],
  },
}

function python(portas: string[]): INodeContext {
  return {
    id: "py",
    data: {
      name: "PythonScript",
      inputs: portas.map(name => ({ name })),
      properties: { ports: JSON.stringify(portas) },
    },
  } as unknown as INodeContext
}

beforeEach(() => {
  edges.length = 0
  nodes.length = 0
  nodes.push(pai)
  cleanup()
})

describe("nome da variável", () => {
  it("usa o nome da PORTA quando a aresta tem to_key", () => {
    edges.push({ id: "e", source: "pai", target: "py", data: { from_key: "output", to_key: "pontos" } })
    render(<InputInspector nodeFound={python(["pontos"])} />)

    // The parent's key stays visible as provenance…
    expect(screen.getByText("output")).toBeInTheDocument()
    // …but the name that goes into the script is the port's.
    expect(screen.getByText("pontos")).toBeInTheDocument()
  })

  it("sem to_key continua usando a chave do pai", () => {
    // Old workflow, no ports: the executor names by `from_key`, and the panel
    // needs to keep agreeing with it.
    edges.push({ id: "e", source: "pai", target: "py", data: { from_key: "output" } })
    render(<InputInspector nodeFound={python([])} />)

    expect(screen.getByText("output")).toBeInTheDocument()
    expect(screen.queryByText("pontos")).not.toBeInTheDocument()
  })
})

describe("portas configuradas aparecem antes de qualquer conexão", () => {
  it("lista as portas declaradas com nada ligado", () => {
    // Whoever just configured them had nowhere to check the names — and they're
    // what become the script's variables.
    render(<InputInspector nodeFound={python(["pontos", "poligonos"])} />)

    expect(screen.getByText("Entradas deste nó")).toBeInTheDocument()
    expect(screen.getByText("pontos")).toBeInTheDocument()
    expect(screen.getByText("poligonos")).toBeInTheDocument()
  })

  it("nó sem portas mantém só o aviso de vazio", () => {
    render(<InputInspector nodeFound={python([])} />)

    expect(screen.getByText(/Nenhuma entrada conectada/)).toBeInTheDocument()
    expect(screen.queryByText("Entradas deste nó")).not.toBeInTheDocument()
  })

  it("com uma porta ligada, a outra aparece como pendente", () => {
    // The parents list only shows the connected one; without this the missing
    // port stays invisible precisely to whoever still needs to connect it.
    edges.push({ id: "e", source: "pai", target: "py", data: { from_key: "output", to_key: "pontos" } })
    render(<InputInspector nodeFound={python(["pontos", "poligonos"])} />)

    expect(screen.getByText("Aguardando conexão")).toBeInTheDocument()
    expect(screen.getByText("poligonos")).toBeInTheDocument()
  })

  it("com todas ligadas, não sobra pendência", () => {
    edges.push({ id: "e1", source: "pai", target: "py", data: { from_key: "output", to_key: "pontos" } })
    render(<InputInspector nodeFound={python(["pontos"])} />)

    expect(screen.queryByText("Aguardando conexão")).not.toBeInTheDocument()
  })
})

// ── Findings from reviewing the change itself ───────────────────────────────

describe("mesmo pai alimentando duas portas", () => {
  it("mostra uma linha por aresta, não por chave", () => {
    // Both edges carry the same `from_key` (the parent has only one output).
    // Listing by key, the second port stayed invisible — precisely in the
    // scenario that named ports created.
    edges.push(
      { id: "e1", source: "pai", target: "py", data: { from_key: "output", to_key: "pontos" } },
      { id: "e2", source: "pai", target: "py", data: { from_key: "output", to_key: "poligonos" } },
    )
    render(<InputInspector nodeFound={python(["pontos", "poligonos"])} />)

    expect(screen.getByText("pontos")).toBeInTheDocument()
    expect(screen.getByText("poligonos")).toBeInTheDocument()
    expect(screen.queryByText("Aguardando conexão")).not.toBeInTheDocument()
  })

  it("aresta sem from_key ainda usa o to_key como nome", () => {
    // Parent with no declared outputs: the edge is born without `from_key` and
    // the executor spreads everything. `to_key`, when present, is still the arrival name.
    edges.push({ id: "e", source: "pai", target: "py", data: { to_key: "dados" } })
    render(<InputInspector nodeFound={python(["dados"])} />)

    expect(screen.getByText("dados")).toBeInTheDocument()
  })
})
