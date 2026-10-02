/**
 * Endereço de um nó que executou dentro de um sub-fluxo.
 *
 * O executor prefixa o id do nó com o nó SubWorkflow que o chamou, e isso se
 * acumula a cada nível. O meta `subworkflow_parent_node` NÃO serve para descer:
 * cada nível o sobrescreve ao republicar, então ele sempre aponta para o nó do
 * canvas raiz. Quem carrega a cadeia inteira é o próprio id — é o que estes
 * testes fixam.
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
    // É este id — e não o endereço completo — que casa com a definition do
    // sub-fluxo carregada do backend.
    expect(idLocal("sA::sB::X")).toBe("X")
  })
})

describe("pertenceAoNivel", () => {
  it("aceita só os nós DIRETOS do nível", () => {
    expect(pertenceAoNivel("sA::X", ["sA"])).toBe(true)
    expect(pertenceAoNivel("sA::sB::X", ["sA", "sB"])).toBe(true)
  })

  it("recusa um nó de nível mais profundo, ainda que compartilhe o prefixo", () => {
    // Um `startsWith` diria que sim. Se disséssemos, o estado de um nó de C
    // seria pintado num nó de B que por acaso tem o mesmo id local.
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
