import { describe, it, expect } from "vitest"
import { Edge } from "@xyflow/react"
import { serializeEdge, resolveSourceHandle } from "@/app/components/workflow/utils/edge-persistence"
import { INodePortAPI } from "@/service/types"

/**
 * Regression: connecting "Entrada de Dados" (2 ports) to "Salvar em PostGIS"
 * worked in the session and disappeared from the canvas on reopening. `condition`
 * was written for ANY named handle, erasing the port id; on load it became
 * sourceHandle="false", a nonexistent handle, and React Flow couldn't anchor the edge.
 */

const port = (name: string): INodePortAPI => ({ name } as INodePortAPI)

// DataInput declara duas portas — o caso que quebrava.
const DATA_INPUT = [port("output"), port("metadata")]
// Conditional routes by true/false.
const CONDITIONAL = [port("true"), port("false")]
// ReadGeoJSON has a single port → anonymous handle.
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
    // The bug: "output" became condition:false and the port name was lost.
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
    // from_key survives: it's the key picker, independent of the handle.
    expect(saved.from_key).toBe("crs")
  })
})

/**
 * The counterpart of the SINGLE-port fix (`handleDeEntrada`): with ONE port the
 * node renders an ANONYMOUS input handle, so `buildEdges` resolves `targetHandle`
 * as undefined — but the executor routes by `to_key`. `serializeEdge` MUST write
 * `to_key` even without `targetHandle` (it falls back to `data.to_key`),
 * otherwise the visual fix would lose the routing in the database. This is the
 * guarantee that makes it safe NOT to anchor the edge by the single port's name.
 *
 * It closes the loop with `build-canvas.test.ts`: there, one port + `to_key` →
 * undefined `targetHandle` + preserved `data.to_key`; here, that same state
 * goes back to the database as an intact `to_key`. The next opening repeats the
 * step and draws again — idempotent, without the edge disappearing.
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
    // The picker bug: only data.from_key changed (to "metadata"), sourceHandle
    // stayed "output". On load, resolveSourceHandle follows the old sourceHandle.
    expect(roundTrip(edge({ sourceHandle: "output", data: { from_key: "metadata" } }), DATA_INPUT))
      .toBe("output")
    // escolherChave now writes sourceHandle=from_key when the key is a declared
    // port — the sourceHandle==from_key invariant that this round-trip requires.
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
    // WFS declares 1 port but 4 data keys — from_key="crs" is not a handle.
    expect(roundTrip(edge({ sourceHandle: null, data: { from_key: "crs" } }), SINGLE))
      .toBeUndefined()
  })
})

describe("resolveSourceHandle — arestas salvas antes da correção", () => {
  it("recupera a porta a partir do from_key quando o nó tem várias saídas", () => {
    // Corrupted format written by the old version.
    const legado = { source: "a", target: "b", condition: false, from_key: "output" }

    expect(resolveSourceHandle(legado, new Map([["a", DATA_INPUT]]))).toBe("output")
  })

  it("não confunde condition legítimo de um nó condicional", () => {
    const ramo = { source: "a", target: "b", condition: false, from_key: "output" }

    // Same payload, different node: here `false` is a real branch.
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
 * Regression: the badge picker synced the sourceHandle with ANY candidate
 * (getCandidateKeys offers every field), writing a source_handle that isn't a
 * handle at all. resolveSourceHandle returned it intact and the edge was left
 * without an anchor — it disappeared from the canvas and didn't come back even
 * on reopening. Now a persisted handle that doesn't match a real port is ignored
 * and the edge recovers through from_key / the anonymous handle.
 */
describe("resolveSourceHandle — handle fantasma (campo sem porta gravado)", () => {
  // ChangeDetector routes by branches → no named data port.
  const STATIC_ONLY: INodePortAPI[] = []

  it("saída anônima: campo sem porta gravado como handle volta a anônimo", () => {
    const corrompida = { source: "a", target: "b", source_handle: "previous_hash", from_key: "previous_hash" }

    expect(resolveSourceHandle(corrompida, new Map([["a", STATIC_ONLY]]))).toBeUndefined()
  })

  it("nó multi-saída: handle fantasma cai na recuperação por from_key", () => {
    // Invalid source_handle, but from_key points to a real port → re-anchors on it.
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
