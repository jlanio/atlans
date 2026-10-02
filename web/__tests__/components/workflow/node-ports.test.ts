/**
 * Portas de entrada: do catálogo ou do usuário.
 *
 * Um nó de `dynamic_inputs` (Script Python) tem as entradas declaradas por quem
 * monta o fluxo, na propriedade `ports`. Os nomes viram os pontos de conexão no
 * canvas e, por tabela, o `to_key` da aresta — que é o nome da variável dentro
 * do script.
 *
 * O teste que mais importa aqui é o de NÃO-REGRESSÃO: um nó sem `ports` precisa
 * continuar com lista vazia, porque é isso que mantém o ponto de conexão
 * anônimo e as arestas dos fluxos que já existem desenhando como sempre.
 */
import { describe, it, expect } from "vitest"

import { contratoDoNo, handleDeEntrada, lerPortas, portasDeEntrada, portasDeSaida, reconciliarPortas, reancorarArestasDoNo, NOME_DE_PORTA } from
  "@/app/components/workflow/utils/node-ports"

const CATALOGO = { inputs: [{ name: "layerA" }, { name: "layerB" }], dynamic_inputs: false }
const DINAMICO = { inputs: [], dynamic_inputs: true }

describe("lerPortas", () => {
  it("aceita lista", () => {
    expect(lerPortas(["a", "b"])).toEqual(["a", "b"])
  })

  it("aceita JSON em string", () => {
    // É como o campo grava: `setNodeField` só aceita string/number/boolean.
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
    // A não-regressão: lista vazia mantém o ponto de conexão anônimo, e as
    // arestas dos fluxos existentes continuam desenhando. Se isto passasse a
    // devolver portas nomeadas, todo Script Python já salvo perderia as
    // ligações no canvas.
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
      // O nome vira VARIÁVEL dentro do script Python: um caractere inválido
      // produziria SyntaxError no meio do código do usuário, longe da causa.
      expect(NOME_DE_PORTA.test(nome)).toBe(false)
    })
})

// ── A guarda do targetHandle ────────────────────────────────────────────────

describe("targetHandle só é restaurado para porta que existe", () => {
  // n1: 2+ portas (handles nomeados) · n2: 0 (anônimo) · n3: 1 (anônimo também).
  const portas = new Map([["n1", ["pontos", "poligonos"]], ["n2", []], ["n3", ["unica"]]])

  it("porta declarada (nó de 2+ portas) vira handle", () => {
    expect(handleDeEntrada({ target: "n1", to_key: "pontos" }, portas)).toBe("pontos")
  })

  it("porta que não existe mais NÃO vira handle", () => {
    expect(handleDeEntrada({ target: "n1", to_key: "removida" }, portas)).toBeUndefined()
  })

  it("nó sem portas declaradas NÃO vira handle", () => {
    expect(handleDeEntrada({ target: "n2", to_key: "output" }, portas)).toBeUndefined()
  })

  it("porta ÚNICA NÃO vira handle: ancora no anônimo (espelha o `> 1` da renderização)", () => {
    // Com uma porta só, default-type desenha um HandleTarget ANÔNIMO (sem id).
    // Devolver "unica" apontaria a aresta para um handle inexistente e ela sumiria
    // do canvas continuando a executar. REGRESSÃO: tirar o `> 1` de handleDeEntrada
    // faz voltar a "unica" e derruba SÓ este teste.
    expect(handleDeEntrada({ target: "n3", to_key: "unica" }, portas)).toBeUndefined()
  })

  it("aresta sem to_key continua anônima", () => {
    expect(handleDeEntrada({ target: "n1" }, portas)).toBeUndefined()
  })
})

// ── Achados da revisão da própria mudança ───────────────────────────────────

describe("nomes repetidos não viram pontos de conexão duplicados", () => {
  it("deduplica", () => {
    // Dois handles com o mesmo id deixam o React Flow sem saber em qual a
    // aresta encosta, e a segunda entrada sobrescreveria a primeira no script
    // — o defeito que as portas existem para resolver.
    const r = portasDeEntrada(DINAMICO, { ports: ["a", "b", "a"] })
    expect(r.map(p => p.name)).toEqual(["a", "b"])
  })

  it("preserva a ordem da primeira ocorrência", () => {
    const r = portasDeEntrada(DINAMICO, { ports: ["z", "a", "z", "m"] })
    expect(r.map(p => p.name)).toEqual(["z", "a", "m"])
  })
})

// ── O contrato que vai para o `data` da instância ────────────────────────────

describe("contratoDoNo", () => {
  const CAT = {
    inputs: [{ name: "layerA" }, { name: "layerB" }],
    outputs: [{ name: "result", type: "any" }],
    dynamic_inputs: false,
    dynamic_output: true,
  }

  it("leva TODOS os campos do catálogo que o canvas precisa", () => {
    // O `data` era montado campo a campo em dois lugares, e um campo esquecido
    // num deles produzia um defeito de sintoma bizarro: funciona no nó
    // recém-criado e some ao recarregar. Aconteceu com `dynamic_inputs`, de
    // novo com `dynamic_output` e de novo com `outputs_from_ports`.
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
    // SubWorkflowInput: as portas declaradas viram as SAÍDAS (from_key), para o
    // usuário escolher, pela aresta, qual chave passar adiante.
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
    // NÃO-REGRESSÃO: 0/1 porta preserva o modo legado (edge sem from_key).
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
  // O bug: `buildEdges` roda antes das portas do contrato assíncrono chegarem,
  // então as arestas nascem com `targetHandle: undefined` e o React Flow prende
  // todas na primeira entrada. Quando as portas chegam, esta função devolve cada
  // aresta ao seu ponto pelo `to_key`/`from_key` que a `data` preservou.
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
    const jaAncorada = aresta({ target: "sub", targetHandle: "layerA", data: { to_key: "layerA" } })
    const orfa = aresta({ target: "sub", targetHandle: null, data: { to_key: "inexistente" } })
    const outroNo = aresta({ target: "outro", targetHandle: null, data: { to_key: "layerA" } })
    const edges = [jaAncorada, orfa, outroNo]
    expect(reancorarArestasDoNo(edges, "sub", ["layerA"], [])).toBe(edges)
  })

  it("entrada ÚNICA: NÃO re-ancora o targetHandle (fica anônimo)", () => {
    // Mesmo motivo de handleDeEntrada: com uma entrada só o handle é anônimo (sem
    // id). Re-ancorar pelo nome apontaria para um id inexistente e a aresta
    // sumiria. Nada muda → devolve o MESMO array. MUTAÇÃO: tirar o `inputs.length
    // > 1` seta "layerA" (e troca o array) e derruba SÓ este teste.
    const edges = [aresta({ target: "sub", targetHandle: null, data: { to_key: "layerA" } })]
    const r = reancorarArestasDoNo(edges, "sub", ["layerA"], [])
    expect(r[0].targetHandle).toBeNull()
    expect(r).toBe(edges)
  })

  it("saída ÚNICA: NÃO re-ancora o sourceHandle (fica anônimo)", () => {
    // Simétrico, no lado da saída. MUTAÇÃO: tirar o `outputs.length > 1` seta
    // "focos" e derruba SÓ este teste.
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
