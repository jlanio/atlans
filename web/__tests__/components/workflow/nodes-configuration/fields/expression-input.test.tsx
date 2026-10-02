import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent } from "@testing-library/react"
import { INodeContext } from "@/context/useFlowContext"

/**
 * Regressão: o dropdown de `{{$` sugeria o rótulo de exibição do nó e inseria
 * `{{$Caixa Delimitadora.bbox}}` — nome que não existe no contexto do executor,
 * que registra o nó como `ComputeBoundingBox` (flow/executor/core.py::
 * _resolve_alias exige identificador válido, senão usa o `name` da classe).
 *
 * O espaço também travava o próprio autocomplete: o gatilho varre
 * identificadores, então depois de inserir o rótulo o texto deixava de casar e
 * digitar "." nunca listava os campos de saída.
 */

// O componente lê o canvas de forma imperativa: tira uma fotografia do grafo
// quando o gatilho do autocomplete aparece, em vez de assinar `useNodes()` e
// recalcular as sugestões a cada quadro de arraste.
let nodesMock: INodeContext[] = []
let edgesMock: Array<{ id: string; source: string; target: string }> = []
vi.mock("@xyflow/react", () => ({
  useReactFlow: () => ({ getNodes: () => nodesMock, getEdges: () => edgesMock }),
}))

import ExpressionInput from "@/app/components/workflow/nodes-configuration/fields/expression-input"

type DadosNo = Partial<INodeContext["data"]> & { name: string }

function no(id: string, data: DadosNo): INodeContext {
  return { id, data } as unknown as INodeContext
}

// Campos de saída do catálogo (`saidas`) — é por eles que o autocomplete
// monta `$Alias.campo`.
const CAIXA = no("n1", {
  name: "ComputeBoundingBox",
  alias: "Caixa Delimitadora",
  saidas: [
    { name: "bbox", type: "array", description: "Extensão [minx, miny, maxx, maxy]" },
    { name: "crs", type: "string" },
  ],
} as unknown as DadosNo)

const DESTINO = no("n2", { name: "DataOutput", alias: "Saída", inputs: [] } as DadosNo)

/** Renderiza com o input controlado, como o formulário real faz. */
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
  nodesMock = [CAIXA, DESTINO]
  edgesMock = [{ id: "e1", source: "n1", target: "n2" }]
})

afterEach(cleanup)

describe("sugestões de alias", () => {
  it("sugere o alias do executor, não o rótulo com espaço", () => {
    const { digitar } = montar()

    digitar("{{$")

    // O que vai para o texto.
    expect(screen.getByText("ComputeBoundingBox")).toBeTruthy()
    // O rótulo do canvas continua visível, como descrição.
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
    // Mesmo `name` → mesma chave no contexto do executor.
    nodesMock = [
      no("n1", { name: "ComputeBoundingBox" } as DadosNo),
      no("n3", { name: "ComputeBoundingBox" } as DadosNo),
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
    // Ao salvar o modal, o alias digitado é promovido para data.alias — é ele
    // que chega ao banco e é o que o executor registra.
    nodesMock = [
      no("n1", {
        name: "ComputeBoundingBox",
        alias: "Caixa",
        properties: { alias: "Caixa" },
      } as unknown as DadosNo),
      DESTINO,
    ]
    const { onChange, digitar } = montar()

    digitar("{{$")
    fireEvent.mouseDown(screen.getByText("Caixa"))

    expect(onChange).toHaveBeenLastCalledWith("{{$Caixa")
  })

  it("lista os campos de nó NÃO conectado", () => {
    // Quem monta o fluxo de trás para frente digitava "{{$Alias." e não via
    // nada, sem pista de que conectar mudaria isso — mas os campos são
    // declarados pelo nó, não dependem da conexão.
    edgesMock = []
    const { digitar } = montar()

    digitar("{{$ComputeBoundingBox.")

    expect(screen.getByText("ComputeBoundingBox.bbox")).toBeTruthy()
    expect(screen.getByText("ComputeBoundingBox.crs")).toBeTruthy()
  })

  it("reserva vagas para aliases quando um nó tem muitos campos", () => {
    // Corte reto escondia TODOS os aliases atrás dos campos do primeiro nó.
    const muitosCampos = no("n1", {
      name: "NoGordo",
      saidas: Array.from({ length: 20 }, (_, i) => ({ name: `campo${i}` })),
    } as unknown as DadosNo)
    const outro = no("n3", { name: "SegundoNo" } as DadosNo)
    nodesMock = [muitosCampos, outro, DESTINO]
    edgesMock = [{ id: "e1", source: "n1", target: "n2" }]
    const { digitar } = montar()

    digitar("{{$")

    expect(screen.getByText("NoGordo")).toBeTruthy()
    // Sem a cota, este alias ficava fora das 12 primeiras entradas.
    expect(screen.getByText("SegundoNo")).toBeTruthy()
  })

  it("aceita alias acentuado no gatilho", () => {
    nodesMock = [no("n1", { name: "ComputeArea", alias: "Área" } as DadosNo), DESTINO]
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
    // `inputs` é um dict só — a chave `output` é a mesma para os dois.
    const comOutput = (id: string, nome: string) =>
      no(id, {
        name: nome,
        saidas: [{ name: "output", type: "geodataframe" }],
      } as unknown as DadosNo)
    nodesMock = [comOutput("n1", "ReadGeoJSON"), comOutput("n3", "ReadWFS"), DESTINO]
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
