/**
 * Entradas/Saídas panels with the data sample (docs/specs/node-data-panels.md §6):
 * source picker with every earlier node, Schema/Tabela/JSON views, drag payloads
 * and the empty states.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, fireEvent, within } from "@testing-library/react"

const edges: unknown[] = []
const nodes: unknown[] = []
vi.mock("@xyflow/react", () => ({
  useEdges: () => edges,
  useNodes: () => nodes,
}))
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "wf" }) }))
const exec: { statusWorkflow: unknown } = { statusWorkflow: null }
vi.mock("@/app/stores/workflowExecutionStore", () => ({
  useWorkflowExecutionStore: (sel: (s: typeof exec) => unknown) => sel(exec),
}))
vi.mock("@/app/stores/workflowCatalogStore", () => ({
  useWorkflowCatalogStore: (sel: (s: { pinnedNodes: unknown[] }) => unknown) => sel({ pinnedNodes: [] }),
}))

import InputInspector from "@/app/components/workflow/node-config-modal/input-inspector"
import OutputPreview from "@/app/components/workflow/node-config-modal/output-preview"
import { useNodeSamplesStore } from "@/app/stores/nodeSamplesStore"
import { alvoDoCampo, definirAlvo } from "@/app/components/workflow/node-config-modal/insercao"
import type { AmostraDoNo } from "@/types/amostra"
import type { INodeContext } from "@/context/useFlowContext"

const municipios: AmostraDoNo = {
  version: 1,
  outputs: {
    output: {
      kind: "table", rows_total: 144, crs: "EPSG:4674",
      columns: [
        { name: "nm_mun", type: "str" }, { name: "area_km2", type: "float" },
        { name: "geometry", type: "geometry:Polygon", geometry: true },
      ],
      rows: [["Abaetetuba", 1610.65, { type: "Polygon", vertices: 2841, wkt: "POLYGON ((-48.8 -1.7, …" }]],
      truncated: { rows: true, columns: false, cells: false },
    },
  },
}
const parametros: AmostraDoNo = {
  version: 1,
  outputs: { output: { kind: "json", value: { uf: "PA", buffer_m: 500 }, truncated: false } },
}

const no = (id: string, alias: string, name = "ReadGeoJSON") => ({ id, data: { name, alias, saidas: [{ name: "output" }] } })
const clip = { id: "clip", data: { name: "Clip", alias: "Recorte", saidas: [{ name: "output" }] } } as unknown as INodeContext

function arrastar(el: HTMLElement): string {
  let texto = ""
  fireEvent.dragStart(el, { dataTransfer: { setData: (_t: string, v: string) => { texto = v }, effectAllowed: "" } })
  return texto
}

beforeEach(() => {
  cleanup()
  edges.length = 0
  nodes.length = 0
  exec.statusWorkflow = null
  useNodeSamplesStore.getState().clear()
  definirAlvo(null)
  try { window.localStorage.clear() } catch { /* ignore */ }
  // par → mun → clip : Parametros is an earlier node, not wired to clip.
  nodes.push(no("par", "Parametros", "DataInput"), no("mun", "Municipios"), clip)
  edges.push(
    { id: "e1", source: "par", target: "mun", data: {} },
    { id: "e2", source: "mun", target: "clip", data: { from_key: "output" } },
  )
})

describe("painel Entradas", () => {
  it("lista os pais primeiro e depois os outros nós anteriores", () => {
    render(<InputInspector nodeFound={clip} />)
    const select = screen.getByLabelText("De") as HTMLSelectElement
    const grupos = within(select).getAllByRole("group")
    expect(grupos.map(g => g.getAttribute("label"))).toEqual(["Ligados a este nó", "Outros nós anteriores"])
    expect(within(grupos[0]).getByText("Municipios")).toBeInTheDocument()
    expect(within(grupos[1]).getByText("Parametros")).toBeInTheDocument()
  })

  it("sem execução mostra o schema e pede para executar", () => {
    render(<InputInspector nodeFound={clip} />)
    expect(screen.getByRole("button", { name: "Schema" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByText(/Execute para ver as colunas/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    expect(screen.getByText("Ainda sem dados de execução")).toBeInTheDocument()
  })

  it("com amostra abre na Tabela, com total, CRS e geometria resumida", () => {
    useNodeSamplesStore.getState().beginRun("wf", "r1", true)
    useNodeSamplesStore.getState().apply("wf", "r1", "mun", municipios)
    render(<InputInspector nodeFound={clip} />)
    expect(screen.getByRole("button", { name: "Tabela" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByText("Abaetetuba")).toBeInTheDocument()
    expect(screen.getByText("Polygon · 2.841 vért.")).toBeInTheDocument()
    expect(screen.getByText("1 de 144 linhas")).toBeInTheDocument()
    expect(screen.getByText(/EPSG:4674/)).toBeInTheDocument()
    // Dragging a column header inserts the column name.
    expect(arrastar(screen.getByText("nm_mun").closest("th")!)).toBe("nm_mun")
  })

  it("no Schema, chave arrasta a expressão e coluna arrasta o nome", () => {
    useNodeSamplesStore.getState().apply("wf", "r1", "mun", municipios)
    render(<InputInspector nodeFound={clip} />)
    fireEvent.click(screen.getByRole("button", { name: "Schema" }))
    expect(arrastar(screen.getByText("output").closest("[draggable]") as HTMLElement)).toBe("{{ Municipios.output }}")
    expect(arrastar(screen.getByText("area_km2").closest("[draggable]") as HTMLElement)).toBe("area_km2")
    expect(screen.getByText("1.610,65")).toBeInTheDocument()  // example value
  })

  it("nó anterior não ligado é acessível por expressão; JSON arrasta o caminho", () => {
    useNodeSamplesStore.getState().apply("wf", "r1", "par", parametros)
    render(<InputInspector nodeFound={clip} />)
    fireEvent.change(screen.getByLabelText("De"), { target: { value: "par" } })
    expect(screen.getByText("não ligado diretamente")).toBeInTheDocument()
    // JSON output in Tabela → offers JSON.
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    fireEvent.click(screen.getByRole("button", { name: "Ver JSON" }))
    expect(arrastar(screen.getByText('"buffer_m"'))).toBe("{{ Parametros.output.buffer_m }}")
  })

  it("amostra da execução anterior aparece marcada", () => {
    useNodeSamplesStore.getState().beginRun("wf", "r1", true)
    useNodeSamplesStore.getState().apply("wf", "r1", "mun", municipios)
    useNodeSamplesStore.getState().beginRun("wf", "r2", true)
    render(<InputInspector nodeFound={clip} />)
    expect(screen.getByText("da execução anterior")).toBeInTheDocument()
  })

  it("admin desligou: diz isso em vez de pedir para executar", () => {
    useNodeSamplesStore.getState().beginRun("wf", "r1", false)
    exec.statusWorkflow = { status: "completed", nodes: [] }
    render(<InputInspector nodeFound={clip} />)
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    expect(screen.getByText("Amostras de dados desligadas")).toBeInTheDocument()
  })
})

describe("clique para inserir", () => {
  function campo(rotulo: string, valor = "") {
    const div = document.createElement("div")
    div.innerHTML = `<label for="c-${rotulo}">${rotulo}</label><input id="c-${rotulo}" value="${valor}">`
    document.body.appendChild(div)
    const input = div.querySelector("input") as HTMLInputElement
    const visto: string[] = []
    input.addEventListener("input", () => visto.push(input.value))
    return { input, visto }
  }

  it("com um campo selecionado, clicar numa coluna ou chave insere no cursor", () => {
    const { input, visto } = campo("Distância", "ab")
    input.setSelectionRange(1, 1)
    definirAlvo(alvoDoCampo(input))
    useNodeSamplesStore.getState().apply("wf", "r1", "mun", municipios)
    render(<InputInspector nodeFound={clip} />)
    expect(screen.getByText("“Distância”")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "nm_mun" }))
    expect(visto.at(-1)).toBe("anm_munb")
    fireEvent.click(screen.getByRole("button", { name: "Schema" }))
    input.value = ""
    fireEvent.click(screen.getByText("output"))
    expect(visto.at(-1)).toBe("{{ Municipios.output }}")
    input.parentElement!.remove()
  })

  it("sem campo selecionado, a dica explica como inserir", () => {
    render(<InputInspector nodeFound={clip} />)
    expect(screen.getByText(/Selecione um campo do formulário/)).toBeInTheDocument()
  })
})

describe("executar até este nó", () => {
  it("o painel vazio oferece o botão e chama a execução", () => {
    const executar = vi.fn()
    render(<InputInspector nodeFound={clip} onExecutarAteAqui={executar} />)
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    fireEvent.click(screen.getByRole("button", { name: "Executar até este nó" }))
    expect(executar).toHaveBeenCalledTimes(1)
  })

  it("executando, o botão fica desabilitado", () => {
    render(<OutputPreview nodeFound={clip} onExecutarAteAqui={() => {}} executando />)
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    expect(screen.getByRole("button", { name: "Executando…" })).toBeDisabled()
  })

  it("com as amostras desligadas pelo admin, não oferece o botão", () => {
    useNodeSamplesStore.getState().beginRun("wf", "r1", false)
    exec.statusWorkflow = { status: "completed", nodes: [] }
    render(<InputInspector nodeFound={clip} onExecutarAteAqui={() => {}} />)
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    expect(screen.queryByRole("button", { name: "Executar até este nó" })).toBeNull()
  })
})

describe("mapa e filtro de colunas", () => {
  const comMapa: AmostraDoNo = {
    version: 1,
    outputs: {
      output: {
        ...(municipios.outputs.output as object),
        map: { w: 1000, h: 800, features: [{ d: "M0 0 100 0 100 100Z", area: true }, { p: [500, 400] }] },
      } as AmostraDoNo["outputs"][string],
    },
  }

  it("Saídas com geometria oferece a visão Mapa", () => {
    useNodeSamplesStore.getState().apply("wf", "r1", "clip", comMapa)
    render(<OutputPreview nodeFound={clip} />)
    fireEvent.click(screen.getByRole("button", { name: "Mapa" }))
    const svg = screen.getByRole("img", { name: /Mapa das 2 feições/ })
    expect(svg.querySelectorAll("path")).toHaveLength(1)
    expect(svg.querySelectorAll("circle")).toHaveLength(1)
  })

  it("sem mapa na amostra, não há a visão Mapa", () => {
    useNodeSamplesStore.getState().apply("wf", "r1", "clip", municipios)
    render(<OutputPreview nodeFound={clip} />)
    expect(screen.queryByRole("button", { name: "Mapa" })).toBeNull()
  })

  it("muitas colunas: o filtro esconde as que não batem", () => {
    const larga: AmostraDoNo = {
      version: 1,
      outputs: {
        output: {
          kind: "table", rows_total: 1, truncated: { rows: false, columns: false, cells: false },
          columns: ["cd_mun", "nm_mun", "uf", "regiao", "area_km2", "pop", "densidade"].map(name => ({ name, type: "str" })),
          rows: [["1", "Belém", "PA", "Norte", "1059", "1300000", "1200"]],
        },
      },
    }
    useNodeSamplesStore.getState().apply("wf", "r1", "clip", larga)
    render(<OutputPreview nodeFound={clip} />)
    fireEvent.change(screen.getByPlaceholderText("Filtrar colunas"), { target: { value: "mun" } })
    expect(screen.getByText("cd_mun")).toBeInTheDocument()
    expect(screen.queryByText("regiao")).toBeNull()
    expect(screen.queryByText("PA")).toBeNull()
    expect(screen.getByText("Belém")).toBeInTheDocument()
  })
})

describe("painel Saídas", () => {
  it("mostra a amostra do próprio nó, sem arrasto", () => {
    useNodeSamplesStore.getState().apply("wf", "r1", "clip", municipios)
    render(<OutputPreview nodeFound={clip} />)
    expect(screen.getByText("Abaetetuba")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Schema" }))
    expect(screen.getByText("area_km2").closest("[draggable='true']")).toBeNull()
    expect(screen.getByText(/tabela · 144 linhas/)).toBeInTheDocument()
  })

  it("sem execução pede para executar", () => {
    render(<OutputPreview nodeFound={clip} />)
    fireEvent.click(screen.getByRole("button", { name: "Tabela" }))
    expect(screen.getByText("Execute o fluxo para ver os dados deste nó.")).toBeInTheDocument()
  })
})
