import { describe, it, expect } from "vitest"
import { Edge } from "@xyflow/react"
import { serializeEdge, resolveSourceHandle } from "@/app/components/workflow/utils/edge-persistence"
import { INodePortAPI } from "@/service/types"

/**
 * Regressão: ligar "Entrada de Dados" (2 portas) a "Salvar em PostGIS" funcionava
 * na sessão e sumia do canvas ao reabrir. `condition` era gravado para QUALQUER
 * handle nomeado, apagando o id da porta; no load virava sourceHandle="false",
 * handle inexistente, e o React Flow não conseguia ancorar a aresta.
 */

const port = (name: string): INodePortAPI => ({ name } as INodePortAPI)

// DataInput declara duas portas — o caso que quebrava.
const DATA_INPUT = [port("output"), port("metadata")]
// Conditional roteia por true/false.
const CONDITIONAL = [port("true"), port("false")]
// ReadGeoJSON tem porta única → handle anônimo.
const SINGLE = [port("output")]

function edge(partial: Partial<Edge>): Edge {
  return { id: "e1", source: "a", target: "b", ...partial } as Edge
}

/** Simula o ciclo completo: canvas → banco → canvas. */
function roundTrip(e: Edge, outputs: INodePortAPI[]): string | undefined {
  const saved = serializeEdge(e)
  return resolveSourceHandle(saved, new Map([[e.source, outputs]]))
}

describe("serializeEdge", () => {
  it("preserva o id da porta de um nó com múltiplas saídas", () => {
    const saved = serializeEdge(edge({ sourceHandle: "output", data: { from_key: "output" } }))

    expect(saved.source_handle).toBe("output")
    // O bug: "output" virava condition:false e o nome da porta se perdia.
    expect(saved.condition).toBeUndefined()
    expect(saved.from_key).toBe("output")
  })

  it("grava condition apenas para handles de roteamento", () => {
    expect(serializeEdge(edge({ sourceHandle: "true" })).condition).toBe(true)
    expect(serializeEdge(edge({ sourceHandle: "false" })).condition).toBe(false)
    expect(serializeEdge(edge({ sourceHandle: "metadata" })).condition).toBeUndefined()
  })

  it("não grava handle quando a porta é anônima (saída única)", () => {
    const saved = serializeEdge(edge({ sourceHandle: null, data: { from_key: "crs" } }))

    expect(saved.source_handle).toBeUndefined()
    expect(saved.condition).toBeUndefined()
    // from_key sobrevive: é o picker de chave, independente do handle.
    expect(saved.from_key).toBe("crs")
  })
})

/**
 * O par do conserto da porta ÚNICA (`handleDeEntrada`): com UMA porta o nó
 * renderiza um handle de entrada ANÔNIMO, então `buildEdges` resolve
 * `targetHandle` indefinido — mas o executor roteia pelo `to_key`. `serializeEdge`
 * TEM de gravar o `to_key` mesmo sem `targetHandle` (cai para `data.to_key`),
 * senão o conserto visual perderia o roteamento no banco. Esta é a garantia que
 * torna seguro NÃO ancorar a aresta pelo nome da porta única.
 *
 * Fecha o ciclo com `build-canvas.test.ts`: lá, uma porta + `to_key` →
 * `targetHandle` indefinido + `data.to_key` preservado; aqui, esse mesmo estado
 * volta ao banco como `to_key` intacto. A próxima abertura repete o passo e
 * desenha de novo — idempotente, sem a aresta sumir.
 */
describe("serializeEdge — `to_key` sobrevive sem targetHandle (porta única)", () => {
  it("targetHandle indefinido + data.to_key: grava o to_key do data", () => {
    const saved = serializeEdge(edge({ targetHandle: undefined, data: { to_key: "focos" } }))

    expect(saved.to_key).toBe("focos")
  })

  it("targetHandle nomeado (nó de 2+ portas): grava o próprio handle", () => {
    const saved = serializeEdge(edge({ targetHandle: "focos", data: { to_key: "focos" } }))

    expect(saved.to_key).toBe("focos")
  })

  it("sem targetHandle e sem to_key: não inventa chave", () => {
    const saved = serializeEdge(edge({ targetHandle: undefined, data: {} }))

    expect(saved.to_key).toBeUndefined()
  })
})

describe("round-trip canvas → banco → canvas", () => {
  it("DataInput: a porta escolhida volta ancorada", () => {
    expect(roundTrip(edge({ sourceHandle: "output", data: { from_key: "output" } }), DATA_INPUT))
      .toBe("output")
    expect(roundTrip(edge({ sourceHandle: "metadata", data: { from_key: "metadata" } }), DATA_INPUT))
      .toBe("metadata")
  })

  it("F9: trocar from_key sem sincronizar sourceHandle reancora na porta ERRADA", () => {
    // O bug do picker: só data.from_key mudava (para "metadata"), sourceHandle
    // ficava "output". No load, resolveSourceHandle segue o sourceHandle antigo.
    expect(roundTrip(edge({ sourceHandle: "output", data: { from_key: "metadata" } }), DATA_INPUT))
      .toBe("output")
    // escolherChave agora grava sourceHandle=from_key quando a chave é uma porta
    // declarada — a invariante sourceHandle==from_key que este round-trip exige.
    expect(roundTrip(edge({ sourceHandle: "metadata", data: { from_key: "metadata" } }), DATA_INPUT))
      .toBe("metadata")
  })

  it("Conditional: os ramos continuam corretos", () => {
    expect(roundTrip(edge({ sourceHandle: "true", data: { from_key: "output" } }), CONDITIONAL))
      .toBe("true")
    expect(roundTrip(edge({ sourceHandle: "false", data: { from_key: "output" } }), CONDITIONAL))
      .toBe("false")
  })

  it("saída única: segue anônima, sem inventar handle a partir do from_key", () => {
    // WFS declara 1 porta mas 4 chaves de dado — from_key="crs" não é handle.
    expect(roundTrip(edge({ sourceHandle: null, data: { from_key: "crs" } }), SINGLE))
      .toBeUndefined()
  })
})

describe("resolveSourceHandle — arestas salvas antes da correção", () => {
  it("recupera a porta a partir do from_key quando o nó tem várias saídas", () => {
    // Formato corrompido gravado pela versão antiga.
    const legado = { source: "a", target: "b", condition: false, from_key: "output" }

    expect(resolveSourceHandle(legado, new Map([["a", DATA_INPUT]]))).toBe("output")
  })

  it("não confunde condition legítimo de um nó condicional", () => {
    const ramo = { source: "a", target: "b", condition: false, from_key: "output" }

    // Mesmo payload, nó diferente: aqui `false` é ramo de verdade.
    expect(resolveSourceHandle(ramo, new Map([["a", CONDITIONAL]]))).toBe("false")
  })

  it("ignora from_key que não corresponde a uma porta declarada", () => {
    const legado = { source: "a", target: "b", condition: false, from_key: "feature_count" }

    expect(resolveSourceHandle(legado, new Map([["a", DATA_INPUT]]))).toBeUndefined()
  })

  it("não inventa handle para nó de saída única", () => {
    const legado = { source: "a", target: "b", from_key: "output" }

    expect(resolveSourceHandle(legado, new Map([["a", SINGLE]]))).toBeUndefined()
  })

  it("nó ausente do mapa não quebra a resolução", () => {
    const orfa = { source: "sumiu", target: "b", from_key: "output" }

    expect(resolveSourceHandle(orfa, new Map())).toBeUndefined()
  })
})

/**
 * Regressão: o picker do badge sincronizava o sourceHandle com QUALQUER
 * candidato (getCandidateKeys oferece todos os campos), gravando um source_handle
 * que não é handle nenhum. resolveSourceHandle o devolvia intacto e a aresta
 * ficava sem âncora — sumia do canvas e nem reabrindo voltava. Agora um handle
 * persistido que não corresponde a uma porta real é ignorado e a aresta se
 * recupera pelo from_key / handle anônimo.
 */
describe("resolveSourceHandle — handle fantasma (campo sem porta gravado)", () => {
  // ChangeDetector roteia por branches → nenhuma porta de dado nomeada.
  const STATIC_ONLY: INodePortAPI[] = []

  it("saída anônima: campo sem porta gravado como handle volta a anônimo", () => {
    const corrompida = { source: "a", target: "b", source_handle: "previous_hash", from_key: "previous_hash" }

    expect(resolveSourceHandle(corrompida, new Map([["a", STATIC_ONLY]]))).toBeUndefined()
  })

  it("nó multi-saída: handle fantasma cai na recuperação por from_key", () => {
    // source_handle inválido, mas from_key aponta uma porta real → reancora nela.
    const corrompida = { source: "a", target: "b", source_handle: "inexistente", from_key: "metadata" }

    expect(resolveSourceHandle(corrompida, new Map([["a", DATA_INPUT]]))).toBe("metadata")
  })

  it("saída única: handle fantasma volta a anônimo", () => {
    const corrompida = { source: "a", target: "b", source_handle: "crs", from_key: "crs" }

    expect(resolveSourceHandle(corrompida, new Map([["a", SINGLE]]))).toBeUndefined()
  })

  it("não afeta um handle nomeado LEGÍTIMO nem um ramo de roteamento", () => {
    expect(resolveSourceHandle(
      { source: "a", target: "b", source_handle: "metadata", from_key: "metadata" },
      new Map([["a", DATA_INPUT]]),
    )).toBe("metadata")
    expect(resolveSourceHandle(
      { source: "a", target: "b", source_handle: "true" },
      new Map([["a", CONDITIONAL]]),
    )).toBe("true")
  })
})
