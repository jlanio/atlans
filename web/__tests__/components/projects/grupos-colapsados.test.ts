/**
 * Persistência de quais grupos ficam recolhidos.
 *
 * Era `useState` puro: quem recolhia os grupos que não usa via tudo aberto de
 * novo a cada visita. E `localStorage` lança em janela privada ou com a cota
 * cheia — um erro ao LER não pode impedir a página de abrir.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"

import {
  chaveDosColapsados,
  gravarColapsados,
  lerColapsados,
} from "@/app/components/projects/grupos-colapsados"

beforeEach(() => window.localStorage.clear())
afterEach(() => vi.restoreAllMocks())

describe("chaveDosColapsados", () => {
  it("separa por workspace", () => {
    expect(chaveDosColapsados("ws-1")).not.toBe(chaveDosColapsados("ws-2"))
  })

  it("workspace ausente tem chave própria, não a de outro", () => {
    // `undefined` na chave viraria a string "undefined" e colidiria com
    // qualquer outro estado sem workspace — aqui é explícito.
    expect(chaveDosColapsados(undefined)).toBe(chaveDosColapsados(null))
    expect(chaveDosColapsados(undefined)).not.toBe(chaveDosColapsados("ws-1"))
  })
})

describe("gravar e ler", () => {
  it("devolve o que foi gravado", () => {
    const chave = chaveDosColapsados("ws-1")
    gravarColapsados(chave, new Set(["a", "b"]))
    expect([...lerColapsados(chave)].sort()).toEqual(["a", "b"])
  })

  it("chave inexistente devolve conjunto vazio", () => {
    expect(lerColapsados(chaveDosColapsados("ws-novo")).size).toBe(0)
  })

  it("um workspace não lê o estado do outro", () => {
    gravarColapsados(chaveDosColapsados("ws-1"), new Set(["a"]))
    expect(lerColapsados(chaveDosColapsados("ws-2")).size).toBe(0)
  })
})

describe("conteúdo inesperado não derruba a página", () => {
  it("JSON inválido vira conjunto vazio", () => {
    const chave = chaveDosColapsados("ws-1")
    window.localStorage.setItem(chave, "{ isto não é json")
    expect(lerColapsados(chave).size).toBe(0)
  })

  it("JSON válido que não é lista vira conjunto vazio", () => {
    const chave = chaveDosColapsados("ws-1")
    window.localStorage.setItem(chave, '{"a":1}')
    expect(lerColapsados(chave).size).toBe(0)
  })

  it("descarta itens que não são texto", () => {
    // Um número dentro do Set nunca casaria com `has(id)`, e o grupo ficaria
    // recolhido para sempre sem que o clique resolvesse.
    const chave = chaveDosColapsados("ws-1")
    window.localStorage.setItem(chave, '["a", 3, null, "b"]')
    expect([...lerColapsados(chave)].sort()).toEqual(["a", "b"])
  })
})

describe("localStorage indisponível", () => {
  it("ler não lança", () => {
    vi.spyOn(window.localStorage.__proto__, "getItem").mockImplementation(() => {
      throw new Error("SecurityError")
    })
    expect(() => lerColapsados("x")).not.toThrow()
    expect(lerColapsados("x").size).toBe(0)
  })

  it("gravar não lança", () => {
    // Cota cheia: a preferência de exibição se perde, e nada mais.
    vi.spyOn(window.localStorage.__proto__, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError")
    })
    expect(() => gravarColapsados("x", new Set(["a"]))).not.toThrow()
  })
})
