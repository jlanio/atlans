/**
 * Input ports: from the catalog or from the user.
 *
 * A `dynamic_inputs` node (Python Script) has its inputs declared by whoever
 * builds the workflow, in the `ports` property. The names become the connection
 * points on the canvas and, by extension, the edge's `to_key` — which is the
 * variable name inside the script.
 *
 * The test that matters most here is the NON-REGRESSION one: a node without
 * `ports` must keep an empty list, because that's what keeps the anonymous
 * connection point and the edges of existing workflows drawing as always.
 */
import { describe, it, expect } from "vitest"

import { contratoDoNo, inputHandle, lerPortas, portasDeEntrada, portasDeSaida, reconciliarPortas, reancorarArestasDoNo, NOME_DE_PORTA } from
  "@/app/components/workflow/utils/node-ports"

const CATALOGO = { inputs: [{ name: "layerA" }, { name: "layerB" }], dynamic_inputs: false }
const DINAMICO = { inputs: [], dynamic_inputs: true }

describe("lerPortas", () => {
  it("aceita lista", () => {
    expect(lerPortas(["a", "b"])).toEqual(["a", "b"])
  })

  it("aceita JSON em string", () => {
    // It's how the field writes: `setNodeField` only accepts string/number/boolean.
    expect(lerPortas('["a","b"]')).toEqual(["a", "b"])
  })

  it.each([undefined, null, "", "{}", "não é json", 42, {}])(
    "devolve lista vazia para %s", (bruto) => {
      expect(lerPortas(bruto)).toEqual([])
    })

  it("descarta entradas vazias e não-string", () => {
    expect(lerPortas(["a", "", "  ", 7, null, "b"])).toEqual(["a", "b"])
  })
})

describe("portasDeEntrada", () => {
  it("nó comum usa as portas do catálogo e ignora `ports`", () => {
    const r = portasDeEntrada(CATALOGO, { ports: ["x", "y"] })
    expect(r.map(p => p.name)).toEqual(["layerA", "layerB"])
  })

  it("nó dinâmico usa as portas do usuário", () => {
    const r = portasDeEntrada(DINAMICO, { ports: '["pontos","poligonos"]' })
    expect(r.map(p => p.name)).toEqual(["pontos", "poligonos"])
  })

  it("nó dinâmico SEM ports fica com lista vazia", () => {
    // The non-regression: an empty list keeps the anonymous connection point,
    // and the edges of existing workflows keep drawing. If this started
    // returning named ports, every already-saved Python Script would lose its
    // links on the canvas.
    expect(portasDeEntrada(DINAMICO, {})).toEqual([])
    expect(portasDeEntrada(DINAMICO, { ports: [] })).toEqual([])
    expect(portasDeEntrada(DINAMICO, undefined)).toEqual([])
  })

  it("nó desconhecido não quebra", () => {
    expect(portasDeEntrada(undefined, { ports: ["a"] })).toEqual([])
  })
})

describe("NOME_DE_PORTA", () => {
  it.each(["pontos", "layer_A", "_x", "a1"])("aceita %s", (nome) => {
    expect(NOME_DE_PORTA.test(nome)).toBe(true)
  })

  it.each(["com espaço", "acentuação", "1comeca_com_numero", "com-hifen", ""])(
    "recusa %s", (nome) => {
      // The name becomes a VARIABLE inside the Python script: an invalid character
      // would produce a SyntaxError in the middle of the user's code, far from the cause.
      expect(NOME_DE_PORTA.test(nome)).toBe(false)
    })
})

// ── The targetHandle guard ───────────────────────────────────────────────────

describe("targetHandle só é restaurado para porta que existe", () => {
  // n1: 2+ ports (named handles) · n2: 0 (anonymous) · n3: 1 (anonymous too).
  const portas = new Map([["n1", ["pontos", "poligonos"]], ["n2", []], ["n3", ["unica"]]])

  it("porta declarada (nó de 2+ portas) vira handle", () => {
    expect(inputHandle({ target: "n1", to_key: "pontos" }, portas)).toBe("pontos")
  })

  it("porta que não existe mais NÃO vira handle", () => {
    expect(inputHandle({ target: "n1", to_key: "removida" }, portas)).toBeUndefined()
  })

  it("nó sem portas declaradas NÃO vira handle", () => {
    expect(inputHandle({ target: "n2", to_key: "output" }, portas)).toBeUndefined()
  })

  it("porta ÚNICA NÃO vira handle: ancora no anônimo (espelha o `> 1` da renderização)", () => {
    // With a single port, default-type draws an ANONYMOUS HandleTarget (no id).
    // Returning "unica" would point the edge at a nonexistent handle and it would
    // disappear from the canvas while still executing. REGRESSION: removing the
    // `> 1` from handleDeEntrada brings back "unica" and breaks ONLY this test.
    expect(inputHandle({ target: "n3", to_key: "unica" }, portas)).toBeUndefined()
  })

  it("aresta sem to_key continua anônima", () => {
    expect(inputHandle({ target: "n1" }, portas)).toBeUndefined()
  })
})

// ── Findings from reviewing the change itself ───────────────────────────────

describe("nomes repetidos não viram pontos de conexão duplicados", () => {
  it("deduplica", () => {
    // Two handles with the same id leave React Flow not knowing which one the
    // edge touches, and the second input would overwrite the first in the
    // script — the defect ports exist to solve.
    const r = portasDeEntrada(DINAMICO, { ports: ["a", "b", "a"] })
    expect(r.map(p => p.name)).toEqual(["a", "b"])
  })

  it("preserva a ordem da primeira ocorrência", () => {
    const r = portasDeEntrada(DINAMICO, { ports: ["z", "a", "z", "m"] })
    expect(r.map(p => p.name)).toEqual(["z", "a", "m"])
  })
})

// ── The contract that goes into the instance's `data` ────────────────────────

describe("contratoDoNo", () => {
  const CAT = {
    inputs: [{ name: "layerA" }, { name: "layerB" }],
    outputs: [{ name: "result", type: "any" }],
    dynamic_inputs: false,
    dynamic_output: true,
  }

  it("leva TODOS os campos do catálogo que o canvas precisa", () => {
    // `data` was built field by field in two places, and a field forgotten in
    // one of them produced a defect with a bizarre symptom: works on the
    // freshly created node and disappears on reload. It happened with
    // `dynamic_inputs`, again with `dynamic_output` and again with `outputs_from_ports`.
    const c = contratoDoNo(CAT, {})
    expect(Object.keys(c).sort()).toEqual(
      ["branches", "dynamic_inputs", "dynamic_output", "inputs", "outputs", "outputs_from_ports", "saidas"],
    )
    expect(c.dynamic_output).toBe(true)
    expect(c.saidas).toBe(CAT.outputs)
  })

  it("as entradas saem derivadas, não copiadas do catálogo", () => {
    const dinamico = { ...CAT, inputs: [], dynamic_inputs: true }
    const c = contratoDoNo(dinamico, { ports: ["a", "b"] })
    expect(c.inputs.map(p => p.name)).toEqual(["a", "b"])
  })

  it("nó desconhecido não quebra", () => {
    const c = contratoDoNo(undefined, undefined)
    expect(c.inputs).toEqual([])
    expect(c.outputs).toEqual([])
  })

  it("as saídas do trigger saem derivadas de `ports`, não do catálogo", () => {
    // SubWorkflowInput: the declared ports become the OUTPUTS (from_key), so the
    // user chooses, via the edge, which key to pass along.
    const trigger = { outputs: [], outputs_from_ports: true }
    const c = contratoDoNo(trigger, { ports: '["focos","bbox"]' })
    expect(c.outputs.map(p => p.name)).toEqual(["focos", "bbox"])
    expect(c.outputs_from_ports).toBe(true)
  })
})

describe("portasDeSaida", () => {
  it("nó comum: só os campos com `port` viram pontos de conexão", () => {
    const cat = {
      outputs: [{ name: "output", port: true }, { name: "detalhe" }],
      outputs_from_ports: false,
    }
    expect(portasDeSaida(cat, { ports: ["ignorado"] }).map(p => p.name)).toEqual(["output"])
  })

  it("nó de ramo: os pontos de saída são true/false, não os campos", () => {
    const cat = { branches: true, outputs: [{ name: "result", port: true }] }
    expect(portasDeSaida(cat, {}).map(p => p.name)).toEqual(["true", "false"])
  })

  it("nenhum campo com `port`: ponto de saída anônimo (lista vazia)", () => {
    const cat = { outputs: [{ name: "output" }, { name: "stats" }] }
    expect(portasDeSaida(cat, {})).toEqual([])
  })

  it("outputs_from_ports: derivadas da propriedade `ports`", () => {
    const trigger = { outputs: [], outputs_from_ports: true }
    expect(portasDeSaida(trigger, { ports: ["focos", "bbox"] }).map(p => p.name))
      .toEqual(["focos", "bbox"])
  })

  it("sem portas declaradas → lista vazia (mantém o handle anônimo / espalhar)", () => {
    // NON-REGRESSION: 0/1 port preserves the legacy mode (edge without from_key).
    const trigger = { outputs: [], outputs_from_ports: true }
    expect(portasDeSaida(trigger, {})).toEqual([])
    expect(portasDeSaida(trigger, { ports: [] })).toEqual([])
  })

  it("remove nomes repetidos", () => {
    const trigger = { outputs: [], outputs_from_ports: true }
    expect(portasDeSaida(trigger, { ports: ["a", "b", "a"] }).map(p => p.name)).toEqual(["a", "b"])
  })
})

describe("reconciliarPortas", () => {
  it("traz data.outputs do trigger em dia com `ports`", () => {
    const nos = [{ data: { outputs_from_ports: true, properties: { ports: '["focos","bbox"]' }, outputs: [] as { name: string }[] } }]
    const r = reconciliarPortas(nos)
    expect(r[0].data.outputs?.map(p => p.name)).toEqual(["focos", "bbox"])
  })

  it("traz data.inputs dos nós de entradas dinâmicas (não regride)", () => {
    const nos = [{ data: { dynamic_inputs: true, properties: { ports: ["a", "b"] }, inputs: [] as { name: string }[] } }]
    const r = reconciliarPortas(nos)
    expect(r[0].data.inputs?.map(p => p.name)).toEqual(["a", "b"])
  })

  it("devolve o MESMO array quando nada muda (proteção anti-laço)", () => {
    const nos = [{ data: { outputs_from_ports: true, properties: { ports: ["x"] }, outputs: [{ name: "x" }] } }]
    expect(reconciliarPortas(nos)).toBe(nos)
  })
})

describe("reancorarArestasDoNo", () => {
  // The bug: `buildEdges` runs before the async contract's ports arrive, so
  // the edges are born with `targetHandle: undefined` and React Flow pins them
  // all to the first input. When the ports arrive, this function returns each
  // edge to its point via the `to_key`/`from_key` that `data` preserved.
  const aresta = (over: Record<string, unknown>) => ({
    source: "src", target: "sub", sourceHandle: null, targetHandle: null,
    data: {}, ...over,
  })

  it("re-ancora o targetHandle pelo to_key quando a porta de entrada passa a existir", () => {
    const edges = [
      aresta({ target: "sub", targetHandle: null, data: { to_key: "layerA" } }),
      aresta({ target: "sub", targetHandle: null, data: { to_key: "layerB" } }),
    ]
    const r = reancorarArestasDoNo(edges, "sub", ["layerA", "layerB"], [])
    expect(r.map(e => e.targetHandle)).toEqual(["layerA", "layerB"])
  })

  it("re-ancora o sourceHandle pelo from_key nas saídas do nó", () => {
    const edges = [aresta({ source: "sub", target: "dst", sourceHandle: null, data: { from_key: "focos" } })]
    const r = reancorarArestasDoNo(edges, "sub", [], ["focos", "bbox"])
    expect(r[0].sourceHandle).toBe("focos")
  })

  it("não mexe em aresta já ancorada nem em to_key sem porta correspondente", () => {
    const alreadyAnchored = aresta({ target: "sub", targetHandle: "layerA", data: { to_key: "layerA" } })
    const orfa = aresta({ target: "sub", targetHandle: null, data: { to_key: "inexistente" } })
    const otherNode = aresta({ target: "outro", targetHandle: null, data: { to_key: "layerA" } })
    const edges = [alreadyAnchored, orfa, otherNode]
    expect(reancorarArestasDoNo(edges, "sub", ["layerA"], [])).toBe(edges)
  })

  it("entrada ÚNICA: NÃO re-ancora o targetHandle (fica anônimo)", () => {
    // Same reason as inputHandle: with a single input the handle is anonymous
    // (no id). Re-anchoring by name would point at a nonexistent id and the edge
    // would disappear. Nothing changes → returns the SAME array. MUTATION: removing
    // the `inputs.length > 1` sets "layerA" (and swaps the array) and breaks ONLY this test.
    const edges = [aresta({ target: "sub", targetHandle: null, data: { to_key: "layerA" } })]
    const r = reancorarArestasDoNo(edges, "sub", ["layerA"], [])
    expect(r[0].targetHandle).toBeNull()
    expect(r).toBe(edges)
  })

  it("saída ÚNICA: NÃO re-ancora o sourceHandle (fica anônimo)", () => {
    // Symmetric, on the output side. MUTATION: removing the `outputs.length > 1`
    // sets "focos" and breaks ONLY this test.
    const edges = [aresta({ source: "sub", target: "dst", sourceHandle: null, data: { from_key: "focos" } })]
    const r = reancorarArestasDoNo(edges, "sub", [], ["focos"])
    expect(r[0].sourceHandle).toBeNull()
    expect(r).toBe(edges)
  })

  it("devolve o MESMO array quando nada muda (proteção anti-laço)", () => {
    const edges = [aresta({ target: "sub", targetHandle: "layerA", data: { to_key: "layerA" } })]
    expect(reancorarArestasDoNo(edges, "sub", ["layerA"], [])).toBe(edges)
  })
})
