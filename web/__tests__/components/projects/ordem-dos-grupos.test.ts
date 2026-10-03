/**
 * Reordering groups by dragging one over another.
 *
 * The pitfall is the index: after removing the item from its source position, everything
 * that was ahead moved back one slot, and reusing the target index
 * computed BEFORE the removal inserts in the wrong place — the item lands one position
 * further, and the saved order is not the one the person saw on dropping.
 */
import { describe, it, expect } from "vitest"

import { moverGrupo } from "@/app/components/projects/ordem-dos-grupos"

const LISTA = ["a", "b", "c", "d"]

describe("moverGrupo", () => {
  it("para baixo: o arrastado assume a posição do alvo", () => {
    expect(moverGrupo(LISTA, "a", "c")).toEqual(["b", "c", "a", "d"])
  })

  it("para cima: o arrastado assume a posição do alvo", () => {
    expect(moverGrupo(LISTA, "d", "b")).toEqual(["a", "d", "b", "c"])
  })

  it("soltar no último manda para o fim", () => {
    expect(moverGrupo(LISTA, "a", "d")).toEqual(["b", "c", "d", "a"])
  })

  it("soltar no primeiro manda para o começo", () => {
    expect(moverGrupo(LISTA, "c", "a")).toEqual(["c", "a", "b", "d"])
  })

  it("vizinhos trocam de lugar", () => {
    expect(moverGrupo(LISTA, "b", "c")).toEqual(["a", "c", "b", "d"])
  })

  it("não perde nem duplica nenhum grupo", () => {
    const saida = moverGrupo(LISTA, "b", "d")
    expect([...saida].sort()).toEqual([...LISTA].sort())
  })

  it("não muta a lista recebida", () => {
    const original = [...LISTA]
    moverGrupo(LISTA, "a", "c")
    expect(LISTA).toEqual(original)
  })
})

describe("quando não há o que mover", () => {
  it("soltar sobre si mesmo devolve a MESMA lista", () => {
    // Identity, not equality: it is what lets the caller skip saving
    // to the server without comparing item by item.
    expect(moverGrupo(LISTA, "b", "b")).toBe(LISTA)
  })

  it("id de origem fora da lista devolve a mesma", () => {
    expect(moverGrupo(LISTA, "z", "b")).toBe(LISTA)
  })

  it("id de alvo fora da lista devolve a mesma", () => {
    expect(moverGrupo(LISTA, "a", "z")).toBe(LISTA)
  })
})
