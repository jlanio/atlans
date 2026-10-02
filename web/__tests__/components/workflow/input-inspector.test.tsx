/**
 * A caixa de Entrada precisa dizer o nome com que o dado CHEGA.
 *
 * Para o Script Python o painel mostra o nome da variável — é o texto que se
 * arrasta para dentro do código. Antes das portas nomeadas esse nome era a
 * chave de saída do PAI, e estava certo: era assim que o executor batizava a
 * entrada. Com portas, a regra passou a ser `to_key if to_key else from_key`, e
 * o painel ficou instruindo a usar `output` quando a variável se chamava
 * `pontos` — deixou de faltar informação e passou a dar informação errada.
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

    // A chave do pai continua visível como procedência…
    expect(screen.getByText("output")).toBeInTheDocument()
    // …mas o nome que se leva para o script é o da porta.
    expect(screen.getByText("pontos")).toBeInTheDocument()
  })

  it("sem to_key continua usando a chave do pai", () => {
    // Fluxo antigo, sem portas: o executor batiza pelo `from_key`, e o painel
    // precisa continuar concordando com ele.
    edges.push({ id: "e", source: "pai", target: "py", data: { from_key: "output" } })
    render(<InputInspector nodeFound={python([])} />)

    expect(screen.getByText("output")).toBeInTheDocument()
    expect(screen.queryByText("pontos")).not.toBeInTheDocument()
  })
})

describe("portas configuradas aparecem antes de qualquer conexão", () => {
  it("lista as portas declaradas com nada ligado", () => {
    // Quem acabou de configurá-las não tinha onde conferir os nomes — e são
    // eles que viram as variáveis do script.
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
    // A lista de pais só mostra a que está ligada; sem isto a porta que falta
    // fica invisível justamente para quem ainda precisa ligá-la.
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

// ── Achados da revisão da própria mudança ───────────────────────────────────

describe("mesmo pai alimentando duas portas", () => {
  it("mostra uma linha por aresta, não por chave", () => {
    // As duas arestas carregam o mesmo `from_key` (o pai só tem uma saída).
    // Listando por chave, a segunda porta ficava invisível — justamente no
    // cenário que as portas nomeadas criaram.
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
    // Pai sem saídas declaradas: a aresta nasce sem `from_key` e o executor
    // espalha tudo. O `to_key`, quando existe, continua sendo o nome de chegada.
    edges.push({ id: "e", source: "pai", target: "py", data: { to_key: "dados" } })
    render(<InputInspector nodeFound={python(["dados"])} />)

    expect(screen.getByText("dados")).toBeInTheDocument()
  })
})
