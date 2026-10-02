/**
 * Reordenar grupos arrastando um sobre o outro.
 *
 * A armadilha é o índice: depois de remover o item da posição de origem, tudo
 * o que estava à frente andou uma casa para trás, e reutilizar o índice do alvo
 * calculado ANTES da remoção insere no lugar errado — o item cai uma posição
 * além, e a ordem gravada não é a que a pessoa viu ao soltar.
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
    // Identidade, não igualdade: é o que permite a quem chama pular a gravação
    // no servidor sem comparar item a item.
    expect(moverGrupo(LISTA, "b", "b")).toBe(LISTA)
  })

  it("id de origem fora da lista devolve a mesma", () => {
    expect(moverGrupo(LISTA, "z", "b")).toBe(LISTA)
  })

  it("id de alvo fora da lista devolve a mesma", () => {
    expect(moverGrupo(LISTA, "a", "z")).toBe(LISTA)
  })
})
