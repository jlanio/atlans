/**
 * Address of a node that executed inside a sub-workflow.
 *
 * The executor prefixes the node id with the SubWorkflow node that called it,
 * and this accumulates at each level. The `subworkflow_parent_node` meta is NOT
 * usable for descending: each level overwrites it when republishing, so it
 * always points to the root canvas's node. What carries the whole chain is the
 * id itself — that's what these tests pin down.
 */
import { describe, it, expect } from "vitest"

import {
  caminhoDeChamada, idLocal, pertenceAoNivel, segmentosDoRunNodeId,
} from "@/app/components/workflow/utils/subflow-path"

describe("endereço de um nó do run", () => {
  it("nó do próprio fluxo não tem caminho de chamada", () => {
    expect(caminhoDeChamada("abc")).toEqual([])
    expect(idLocal("abc")).toBe("abc")
    expect(segmentosDoRunNodeId("abc")).toEqual(["abc"])
  })

  it("um nível: separa o nó SubWorkflow do nó que rodou", () => {
    expect(caminhoDeChamada("sA::X")).toEqual(["sA"])
    expect(idLocal("sA::X")).toBe("X")
  })

  it("cadeia A→B→C: o id guarda os dois nós atravessados", () => {
    expect(caminhoDeChamada("sA::sB::X")).toEqual(["sA", "sB"])
    // It's this id — not the full address — that matches the sub-workflow
    // definition loaded from the backend.
    expect(idLocal("sA::sB::X")).toBe("X")
  })
})

describe("pertenceAoNivel", () => {
  it("aceita só os nós DIRETOS do nível", () => {
    expect(pertenceAoNivel("sA::X", ["sA"])).toBe(true)
    expect(pertenceAoNivel("sA::sB::X", ["sA", "sB"])).toBe(true)
  })

  it("recusa um nó de nível mais profundo, ainda que compartilhe o prefixo", () => {
    // A `startsWith` would say yes. If we said so, the state of a node in C
    // would be painted on a node in B that happens to have the same local id.
    expect(pertenceAoNivel("sA::sB::X", ["sA"])).toBe(false)
  })

  it("recusa um nó do fluxo raiz quando se está dentro de um sub-fluxo", () => {
    expect(pertenceAoNivel("X", ["sA"])).toBe(false)
  })

  it("na raiz, só os nós sem prefixo pertencem", () => {
    expect(pertenceAoNivel("X", [])).toBe(true)
    expect(pertenceAoNivel("sA::X", [])).toBe(false)
  })
})
