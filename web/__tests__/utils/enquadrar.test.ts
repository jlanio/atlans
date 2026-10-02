/**
 * A regra de quando a câmera acompanha o fluxo sendo montado.
 *
 * O teste que dá razão a este arquivo é o do "cresceu pouco": sem folga, o
 * auto-layout reposicionando os nós por alguns pixels a cada passo dispararia
 * um reenquadramento novo a cada desenho — que é exatamente o salto de escala
 * que a regra existe para remover.
 */
import { describe, it, expect, afterEach, vi } from "vitest"

import {
  cabeNoEnquadrado,
  semMovimento,
  FOLGA_DO_ENQUADRAMENTO,
  type Caixa,
} from "@/app/components/workflow/utils/enquadrar"

const caixa = (x: number, y: number, width: number, height: number): Caixa =>
  ({ x, y, width, height })

describe("cabeNoEnquadrado", () => {
  it("sem quadro anterior, sempre precisa enquadrar", () => {
    // O primeiro desenho da conversa: não há o que comparar, e deixar a pessoa
    // olhando para uma tela parada enquanto o fluxo nasce fora dela é o defeito
    // que o enquadramento existe para evitar.
    expect(cabeNoEnquadrado(caixa(0, 0, 100, 100), null)).toBe(false)
  })

  it("a mesma caixa cabe — ninguém se mexe", () => {
    const c = caixa(10, 10, 200, 120)
    expect(cabeNoEnquadrado(c, c)).toBe(true)
  })

  // A folga vai EXPLÍCITA nestes, e não pela constante. Escrever
  // `FOLGA_DO_ENQUADRAMENTO - 1` parece mais robusto e é o contrário: o número
  // do teste passa a se mover junto com a constante, e zerar a constante deixa
  // de quebrar qualquer coisa. Medido — a mutação sobreviveu escrito assim.
  it("crescer menos que a folga não move a câmera", () => {
    // É o caso do auto-layout: os nós reposicionam por pouco a cada passo, e
    // sem isto cada passo viraria um reenquadramento.
    const antes = caixa(0, 0, 200, 200)
    expect(cabeNoEnquadrado(caixa(0, 0, 230, 230), antes, 40)).toBe(true)
  })

  it("crescer mais que a folga move a câmera", () => {
    const antes = caixa(0, 0, 200, 200)
    expect(cabeNoEnquadrado(caixa(0, 0, 250, 200), antes, 40)).toBe(false)
  })

  it("a folga padrão é útil nos dois extremos", () => {
    // Zero faria cada reposicionamento do auto-layout virar um
    // reenquadramento — o salto que a regra existe para remover. E grande
    // demais engoliria um nó inteiro entrando: os nós são espaçados de 180 em
    // 180 pelo layout, então a folga tem de ficar bem abaixo disso.
    expect(FOLGA_DO_ENQUADRAMENTO).toBeGreaterThan(0)
    expect(FOLGA_DO_ENQUADRAMENTO).toBeLessThan(90)
  })

  it("cada borda conta sozinha", () => {
    const antes = caixa(0, 0, 200, 200)
    const fora = 41
    // esquerda, topo, direita, baixo — um nó novo pode entrar por qualquer uma,
    // e uma comparação que só olhasse largura e altura perderia as duas
    // primeiras.
    expect(cabeNoEnquadrado(caixa(-fora, 0, 200, 200), antes)).toBe(false)
    expect(cabeNoEnquadrado(caixa(0, -fora, 200, 200), antes)).toBe(false)
    expect(cabeNoEnquadrado(caixa(0, 0, 200 + fora, 200), antes)).toBe(false)
    expect(cabeNoEnquadrado(caixa(0, 0, 200, 200 + fora), antes)).toBe(false)
  })

  it("o fluxo mudar de lugar move a câmera", () => {
    // Redesenho com geometria outra: a caixa tem o mesmo tamanho e não está
    // mais onde estava.
    expect(cabeNoEnquadrado(caixa(900, 900, 200, 200), caixa(0, 0, 200, 200))).toBe(false)
  })

  it("encolher não move a câmera", () => {
    // Um fluxo menor continua dentro do que já se vê; arrastar a câmera para
    // apertar o zoom seria movimento sem informação.
    expect(cabeNoEnquadrado(caixa(50, 50, 20, 20), caixa(0, 0, 200, 200))).toBe(true)
  })
})

describe("semMovimento", () => {
  afterEach(() => { vi.unstubAllGlobals() })

  it("respeita quem pediu menos movimento", () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })))
    expect(semMovimento()).toBe(true)
  })

  it("é falso quando ninguém pediu", () => {
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false })))
    expect(semMovimento()).toBe(false)
  })

  it("sem `matchMedia` não quebra — e não some com a animação", () => {
    // jsdom não implementa `matchMedia`, e o mesmo vale para o render do
    // servidor. Sem a guarda isto seria um TypeError no meio do desenho; e o
    // default tem de ser "há movimento", senão um ambiente sem a API desligaria
    // a animação para todo mundo.
    vi.stubGlobal("matchMedia", undefined)
    expect(semMovimento()).toBe(false)
  })
})
