import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"
import { INodeContext } from "@/context/useFlowContext"

/**
 * Regression: the `{{$` dropdown suggested the node's display label and inserted
 * `{{$Caixa Delimitadora.bbox}}` — a name that doesn't exist in the executor's
 * context, which registers the node as `ComputeBoundingBox` (flow/executor/core.py::
 * _resolve_alias requires a valid identifier, otherwise it uses the class's `name`).
 *
 * The space also jammed the autocomplete itself: the trigger scans
 * identifiers, so after inserting the label the text stopped matching and
 * typing "." never listed the output fields.
 */

// The component reads the canvas imperatively: it takes a snapshot of the graph
// when the autocomplete trigger appears, instead of subscribing to `useNodes()`
// and recomputing the suggestions on every drag frame.
let nodesMock: INodeContext[] = []
let edgesMock: Array<{ id: string; source: string; target: string }> = []
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ getNodes: () => nodesMock, getEdges: () => edgesMock }),
}))

import ExpressionInput from "@/app/components/workflow/nodes-configuration/fields/expression-input"

type NodeData = Partial<INodeContext["data"]> & { name: string }

function no(id: string, data: NodeData): INodeContext {
  return { id, data } as unknown as INodeContext
}

// Catalog output fields (`saidas`) — it's from them that the autocomplete
// builds `$Alias.campo`.
const BOUNDING_BOX = no("n1", {
  name: "ComputeBoundingBox",
  alias: "Caixa Delimitadora",
  saidas: [
    { name: "bbox", type: "array", description: "Extensão [minx, miny, maxx, maxy]" },
    { name: "crs", type: "string" },
  ],
} as unknown as NodeData)

const DESTINO = no("n2", { name: "DataOutput", alias: "Saída", inputs: [] } as NodeData)

/** Renders with the controlled input, as the real form does. */
function montar(inicial = "") {
  const onChange = vi.fn()
  let valor = inicial
  const { rerender } = render(
    <ExpressionInput value={valor} onChange={onChange} nodeFound={DESTINO} id="expr" />,
  )
  const input = screen.getByRole("textbox") as HTMLInputElement
  const digitar = (texto: string) => {
    valor = texto
    fireEvent.change(input, { target: { value: texto } })
    rerender(<ExpressionInput value={valor} onChange={onChange} nodeFound={DESTINO} id="expr" />)
  }
  return { onChange, input, digitar, valorAtual: () => valor }
}

beforeEach(() => {
  nodesMock = [BOUNDING_BOX, DESTINO]
  edgesMock = [{ id: "e1", source: "n1", target: "n2" }]
})

afterEach(cleanup)

describe("sugestões de alias", () => {
  it("sugere o alias do executor, não o rótulo com espaço", () => {
    const { digitar } = montar()

    digitar("{{$")

    // What goes into the text.
    expect(screen.getByText("ComputeBoundingBox")).toBeTruthy()
    // The canvas label stays visible, as a description.
    expect(screen.getByText("Caixa Delimitadora")).toBeTruthy()
  })

  it("insere o alias válido ao escolher a sugestão", () => {
    const { onChange, digitar } = montar()

    digitar("{{$")
    fireEvent.mouseDown(screen.getByText("ComputeBoundingBox"))

    expect(onChange).toHaveBeenLastCalledWith("{{$ComputeBoundingBox")
  })

  it("encontra o nó pelo nome que aparece no canvas", () => {
    const { digitar } = montar()

    digitar("{{$Caixa")

    expect(screen.getByText("ComputeBoundingBox")).toBeTruthy()
  })

  it("lista os campos de saída depois do ponto", () => {
    const { digitar } = montar()

    digitar("{{$ComputeBoundingBox.")

    expect(screen.getByText("ComputeBoundingBox.bbox")).toBeTruthy()
    expect(screen.getByText("ComputeBoundingBox.crs")).toBeTruthy()
  })

  it("filtra os campos conforme o usuário digita após o ponto", () => {
    const { digitar } = montar()

    digitar("{{$ComputeBoundingBox.bb")

    expect(screen.getByText("ComputeBoundingBox.bbox")).toBeTruthy()
    expect(screen.queryByText("ComputeBoundingBox.crs")).toBeNull()
  })

  it("insere alias e campo de uma vez", () => {
    const { onChange, digitar } = montar()

    digitar("{{$ComputeBoundingBox.")
    fireEvent.mouseDown(screen.getByText("ComputeBoundingBox.bbox"))

    expect(onChange).toHaveBeenLastCalledWith("{{$ComputeBoundingBox.bbox")
  })

  it("dois nós sem alias próprio aparecem uma vez só", () => {
    // Same `name` → same key in the executor's context.
    nodesMock = [
      no("n1", { name: "ComputeBoundingBox" } as NodeData),
      no("n3", { name: "ComputeBoundingBox" } as NodeData),
      DESTINO,
    ]
    edgesMock = [
      { id: "e1", source: "n1", target: "n2" },
      { id: "e2", source: "n3", target: "n2" },
    ]
    const { digitar } = montar()

    digitar("{{$")

    expect(screen.getAllByText("ComputeBoundingBox")).toHaveLength(1)
  })

  it("usa o alias que o usuário configurou", () => {
    // When the modal is saved, the typed alias is promoted to data.alias — it's
    // what reaches the database and what the executor registers.
    nodesMock = [
      no("n1", {
        name: "ComputeBoundingBox",
        alias: "Caixa",
        properties: { alias: "Caixa" },
      } as unknown as NodeData),
      DESTINO,
    ]
    const { onChange, digitar } = montar()

    digitar("{{$")
    fireEvent.mouseDown(screen.getByText("Caixa"))

    expect(onChange).toHaveBeenLastCalledWith("{{$Caixa")
  })

  it("lista os campos de nó NÃO conectado", () => {
    // Someone building the workflow back to front typed "{{$Alias." and saw
    // nothing, with no hint that connecting would change that — but the fields
    // are declared by the node, they don't depend on the connection.
    edgesMock = []
    const { digitar } = montar()

    digitar("{{$ComputeBoundingBox.")

    expect(screen.getByText("ComputeBoundingBox.bbox")).toBeTruthy()
    expect(screen.getByText("ComputeBoundingBox.crs")).toBeTruthy()
  })

  it("reserva vagas para aliases quando um nó tem muitos campos", () => {
    // A straight cut hid ALL the aliases behind the first node's fields.
    const manyFields = no("n1", {
      name: "NoGordo",
      saidas: Array.from({ length: 20 }, (_, i) => ({ name: `campo${i}` })),
    } as unknown as NodeData)
    const outro = no("n3", { name: "SegundoNo" } as NodeData)
    nodesMock = [manyFields, outro, DESTINO]
    edgesMock = [{ id: "e1", source: "n1", target: "n2" }]
    const { digitar } = montar()

    digitar("{{$")

    expect(screen.getByText("NoGordo")).toBeTruthy()
    // Without the quota, this alias was left out of the first 12 entries.
    expect(screen.getByText("SegundoNo")).toBeTruthy()
  })

  it("aceita alias acentuado no gatilho", () => {
    nodesMock = [no("n1", { name: "ComputeArea", alias: "Área" } as NodeData), DESTINO]
    const { digitar } = montar()

    digitar("{{$Áre")

    expect(screen.getByText("Área")).toBeTruthy()
  })
})

describe("sugestões de inputs", () => {
  it("lista os campos do pai em {{ inputs.", () => {
    const { digitar } = montar()

    digitar("{{ inputs.")

    expect(screen.getByText("bbox")).toBeTruthy()
    expect(screen.getByText("crs")).toBeTruthy()
  })

  it("filtrar mantém os campos que casam", () => {
    const { digitar } = montar()

    expect(() => digitar("{{ inputs.bb")).not.toThrow()
    expect(screen.getByText("bbox")).toBeTruthy()
  })

  it("campo declarado por dois pais aparece uma vez, marcado", () => {
    // `inputs` is a single dict — the `output` key is the same for both.
    const withOutput = (id: string, nome: string) =>
      no(id, {
        name: nome,
        saidas: [{ name: "output", type: "geodataframe" }],
      } as unknown as NodeData)
    nodesMock = [withOutput("n1", "ReadGeoJSON"), withOutput("n3", "ReadWFS"), DESTINO]
    edgesMock = [
      { id: "e1", source: "n1", target: "n2" },
      { id: "e2", source: "n3", target: "n2" },
    ]
    const { digitar } = montar()

    digitar("{{ inputs.")

    expect(screen.getAllByText("output")).toHaveLength(1)
    expect(screen.getByText("output — vem de mais de um nó")).toBeTruthy()
  })
})
