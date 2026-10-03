/**
 * Persistence of which groups stay collapsed.
 *
 * It was plain `useState`: someone who collapsed the groups they do not use saw everything open
 * again on every visit. And `localStorage` throws in a private window or with the quota
 * full — an error on READ must not keep the page from opening.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"

import {
  chaveDosColapsados,
  saveCollapsed,
  readCollapsed,
} from "@/app/components/projects/grupos-colapsados"

beforeEach(() => window.localStorage.clear())
afterEach(() => vi.restoreAllMocks())

describe("chaveDosColapsados", () => {
  it("separa por workspace", () => {
    expect(chaveDosColapsados("ws-1")).not.toBe(chaveDosColapsados("ws-2"))
  })

  it("workspace ausente tem chave própria, não a de outro", () => {
    // `undefined` in the key would become the string "undefined" and collide with
    // any other state without a workspace — here it is explicit.
    expect(chaveDosColapsados(undefined)).toBe(chaveDosColapsados(null))
    expect(chaveDosColapsados(undefined)).not.toBe(chaveDosColapsados("ws-1"))
  })
})

describe("gravar e ler", () => {
  it("devolve o que foi gravado", () => {
    const chave = chaveDosColapsados("ws-1")
    saveCollapsed(chave, new Set(["a", "b"]))
    expect([...readCollapsed(chave)].sort()).toEqual(["a", "b"])
  })

  it("chave inexistente devolve conjunto vazio", () => {
    expect(readCollapsed(chaveDosColapsados("ws-novo")).size).toBe(0)
  })

  it("um workspace não lê o estado do outro", () => {
    saveCollapsed(chaveDosColapsados("ws-1"), new Set(["a"]))
    expect(readCollapsed(chaveDosColapsados("ws-2")).size).toBe(0)
  })
})

describe("conteúdo inesperado não derruba a página", () => {
  it("JSON inválido vira conjunto vazio", () => {
    const chave = chaveDosColapsados("ws-1")
    window.localStorage.setItem(chave, "{ isto não é json")
    expect(readCollapsed(chave).size).toBe(0)
  })

  it("JSON válido que não é lista vira conjunto vazio", () => {
    const chave = chaveDosColapsados("ws-1")
    window.localStorage.setItem(chave, '{"a":1}')
    expect(readCollapsed(chave).size).toBe(0)
  })

  it("descarta itens que não são texto", () => {
    // A number inside the Set would never match `has(id)`, and the group would stay
    // collapsed forever without the click fixing it.
    const chave = chaveDosColapsados("ws-1")
    window.localStorage.setItem(chave, '["a", 3, null, "b"]')
    expect([...readCollapsed(chave)].sort()).toEqual(["a", "b"])
  })
})

describe("localStorage indisponível", () => {
  it("ler não lança", () => {
    vi.spyOn(window.localStorage.__proto__, "getItem").mockImplementation(() => {
      throw new Error("SecurityError")
    })
    expect(() => readCollapsed("x")).not.toThrow()
    expect(readCollapsed("x").size).toBe(0)
  })

  it("gravar não lança", () => {
    // Quota full: the display preference is lost, and nothing else.
    vi.spyOn(window.localStorage.__proto__, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError")
    })
    expect(() => saveCollapsed("x", new Set(["a"]))).not.toThrow()
  })
})
