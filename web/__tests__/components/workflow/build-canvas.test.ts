/**
 * Montagem de um canvas a partir da definition persistida + catálogo.
 *
 * Isto vivia dentro do editor, lendo o closure e chamando `setNodes`/`setEdges`.
 * Saiu de lá para que o visualizador de sub-fluxo desenhe o grafo de OUTRO
 * workflow com as mesmas regras — e é a extração que estes testes protegem: o
 * `data` montado em dois lugares diverge, que é o defeito de sintoma bizarro
 * (funciona no nó novo, some ao recarregar) que `contratoDoNo` existe para
 * impedir.
 */
import { describe, it, expect } from "vitest"

import { buildEdges, buildNodes } from "@/app/components/workflow/utils/build-canvas"
import { INodesAPI } from "@/service/types"

const catalogo = [
  {
    name: "PythonScript",
    alias: "Script Python",
    description: "Roda um script",
    type: "action",
    properties: [
      { name: "code", label: "Código", type: "string", default: "" },
      { name: "ports", label: "Portas", type: "object", default: [] },
      // Campo que pede NOME DE COLUNA — carrega o marcador de sugestão.
      { name: "coluna", label: "Coluna", type: "string", default: "", suggest_columns: "*" },
    ],
    dynamic_inputs: true,
    outputs: [{ name: "output" }],
  },
  {
    name: "Conditional",
    alias: "Condicional",
    description: "Ramifica",
    type: "control",
    properties: [],
    outputs: [{ name: "result", type: "any" }],
    branches: true,
  },
  {
    // Duas saídas REAIS → handles nomeados (default-type desenha um por porta).
    // É o caso em que restaurar `source_handle` pelo nome faz sentido.
    name: "DataInput",
    alias: "Entrada de Dados",
    description: "Duas saídas nomeadas",
    type: "trigger",
    properties: [],
    outputs: [{ name: "output", port: true }, { name: "metadata", port: true }],
  },
] as unknown as INodesAPI[]

describe("buildNodes", () => {
  it("resolve o schema do catálogo e preserva os valores salvos", () => {
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: { code: "print(1)" }, position: { x: 10, y: 20 }, type: "action" }] },
      catalogo,
    )

    expect(no.id).toBe("a")
    expect(no.data.properties.code).toBe("print(1)")
    expect(no.data.description).toBe("Roda um script")
    expect(no.position).toEqual({ x: 10, y: 20 })
  })

  it("campo ausente na definition nasce com o default do catálogo", () => {
    // É o que permite acrescentar uma propriedade ao schema sem migrar os
    // workflows já salvos.
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" }] },
      catalogo,
    )
    expect(no.data.properties.code).toBe("")
  })

  it("preserva `suggest_columns` na projeção dos campos", () => {
    // A regressão clássica desta projeção: o nó recém-arrastado sugeria
    // colunas (o drawer copia o objeto inteiro do catálogo) e o MESMO nó,
    // salvo e recarregado, nunca mais — a whitelist descartava o marcador e
    // `sugerirColunas()` devolvia [] para sempre.
    const [no] = buildNodes(
      { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" }] },
      catalogo,
    )
    const campo = no.data.fields.find(f => f.name === "coluna")
    expect(campo?.suggest_columns).toBe("*")
  })

  it("entradas dinâmicas viram pontos de conexão a partir de `ports`", () => {
    const [no] = buildNodes(
      {
        nodes: [{
          id: "a",
          name: "PythonScript",
          properties: { ports: JSON.stringify(["focos", "bbox"]) },
          position: { x: 0, y: 0 },
          type: "action",
        }],
      },
      catalogo,
    )
    expect(no.data.inputs).toEqual([{ name: "focos" }, { name: "bbox" }])
  })

  it("sem catálogo não monta nada — o schema não teria de onde vir", () => {
    const definition = { nodes: [{ id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" }] }
    expect(buildNodes(definition, [])).toEqual([])
    expect(buildNodes(definition, undefined)).toEqual([])
  })

  it("definition sem nós devolve lista vazia, e não undefined", () => {
    // O editor passa o retorno direto ao `setNodes`; um undefined aqui virava
    // canvas quebrado em vez de canvas vazio.
    expect(buildNodes(undefined, catalogo)).toEqual([])
    expect(buildNodes({}, catalogo)).toEqual([])
  })
})

describe("buildEdges", () => {
  it("restaura o handle de origem persistido (porta nomeada de nó multi-saída)", () => {
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "DataInput", properties: {}, position: { x: 0, y: 0 }, type: "trigger" },
        { id: "b", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
      ] },
      catalogo,
    )
    const [aresta] = buildEdges(
      { edges: [{ source: "a", target: "b", source_handle: "output", from_key: "output" }] },
      nodes,
    )
    expect(aresta.sourceHandle).toBe("output")
    expect(aresta.data).toEqual({ from_key: "output" })
    expect(aresta.type).toBe("custom")
  })

  it("saída anônima: source_handle fantasma (bug do picker) volta a anônimo", () => {
    // PythonScript (action) desenha um handle ANÔNIMO — "output" não é handle
    // nomeado. O seletor antigo gravava esse nome mesmo assim e a aresta sumia;
    // agora ela volta ao canvas ancorada no handle anônimo (sourceHandle nulo).
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
        { id: "b", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
      ] },
      catalogo,
    )
    const [aresta] = buildEdges(
      { edges: [{ source: "a", target: "b", source_handle: "output", from_key: "output" }] },
      nodes,
    )
    expect(aresta.sourceHandle).toBeUndefined()
    expect(aresta.data).toEqual({ from_key: "output" })
  })

  it("ramo de condicional só vira handle quando o nó tem as portas true/false", () => {
    const nodes = buildNodes(
      { nodes: [
        { id: "c", name: "Conditional", properties: {}, position: { x: 0, y: 0 }, type: "control" },
        { id: "b", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
      ] },
      catalogo,
    )
    const [aresta] = buildEdges({ edges: [{ source: "c", target: "b", condition: true }] }, nodes)
    expect(aresta.sourceHandle).toBe("true")
  })

  it("porta ÚNICA: a aresta ancora no handle anônimo, não no nome da porta", () => {
    // Com UMA porta, `default-type` desenha um HandleTarget ANÔNIMO (sem id) — o
    // handle nomeado só existe com 2+ portas. Devolver "focos" apontaria a aresta
    // para um id inexistente: o React Flow não a desenha, ela some do canvas
    // continuando a executar, e sem linha não há como apagá-la. `targetHandle`
    // fica indefinido (ancora no anônimo) e o `to_key` sobrevive em `data`, então
    // o executor ainda roteia pela chave.
    //
    // REGRESSÃO deste conserto: tirar o `> 1` de `handleDeEntrada` faz o
    // `targetHandle` voltar a "focos" e derruba SÓ este teste.
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
        {
          id: "b",
          name: "PythonScript",
          properties: { ports: JSON.stringify(["focos"]) },
          position: { x: 0, y: 0 },
          type: "action",
        },
      ] },
      catalogo,
    )

    const [aresta] = buildEdges({ edges: [{ source: "a", target: "b", to_key: "focos" }] }, nodes)
    expect(aresta.targetHandle).toBeUndefined()
    // A chave de dado permanece: o executor ainda roteia; some só a âncora visual.
    expect(aresta.data).toEqual({ to_key: "focos" })
  })

  it("2+ portas: `to_key` vira o handle nomeado que existe; fora da lista fica órfã", () => {
    // Com 2+ portas, `default-type` desenha um HandleTarget por porta (id = nome),
    // então ancorar pelo nome é legítimo — o ponto de conexão existe.
    const nodes = buildNodes(
      { nodes: [
        { id: "a", name: "PythonScript", properties: {}, position: { x: 0, y: 0 }, type: "action" },
        {
          id: "b",
          name: "PythonScript",
          properties: { ports: JSON.stringify(["focos", "alertas"]) },
          position: { x: 0, y: 0 },
          type: "action",
        },
      ] },
      catalogo,
    )

    const [declarada] = buildEdges({ edges: [{ source: "a", target: "b", to_key: "focos" }] }, nodes)
    expect(declarada.targetHandle).toBe("focos")

    const [orfa] = buildEdges({ edges: [{ source: "a", target: "b", to_key: "inexistente" }] }, nodes)
    expect(orfa.targetHandle).toBeUndefined()
    // A chave de dado permanece: quem se perderia é só a âncora visual.
    expect(orfa.data).toEqual({ to_key: "inexistente" })
  })

  it("definition sem arestas devolve lista vazia", () => {
    expect(buildEdges(undefined, [])).toEqual([])
    expect(buildEdges({}, [])).toEqual([])
  })
})
