/**
 * Sugestão de nomes de coluna, a partir da última execução.
 *
 * Antes, configurar um Join ou um filtro exigia adivinhar o nome da coluna —
 * ou executar, olhar o resultado, voltar e digitar. O executor passou a gravar
 * `output_columns` por saída, e estas funções dizem o que chega em cada porta
 * do nó que está sendo configurado.
 */
import { describe, it, expect } from "vitest"

import {
  colunasQueChegam,
  SEM_SUGESTAO,
  sugestaoParaNo,
  type ColunasConhecidasDoNo,
  type NoComColunas,
} from "@/app/components/workflow/utils/colunas-conhecidas"

const NOS: NoComColunas[] = [
  { id: "malha", output_columns: { output: ["cod", "nome", "geometry"] } },
  { id: "censo", output_columns: { result: ["cod", "populacao", "renda"] } },
  { id: "sem_run", output_columns: null },
]

describe("colunasQueChegam", () => {
  it("separa as colunas por porta de entrada", () => {
    // É a dúvida de quem configura um Join: o que é de A e o que é de B.
    const arestas = [
      { source: "malha", target: "join", data: { from_key: "output", to_key: "layerA" } },
      { source: "censo", target: "join", data: { from_key: "result", to_key: "layerB" } },
    ]
    expect(colunasQueChegam(arestas, NOS, "join")).toEqual({
      layerA: ["cod", "nome", "geometry"],
      layerB: ["cod", "populacao", "renda"],
    })
  })

  it("sem to_key, a porta é o próprio from_key", () => {
    const arestas = [{ source: "censo", target: "x", data: { from_key: "result" } }]
    expect(colunasQueChegam(arestas, NOS, "x")).toEqual({
      result: ["cod", "populacao", "renda"],
    })
  })

  it("sem from_key, o nó anterior espalha todas as saídas", () => {
    const arestas = [{ source: "censo", target: "x", data: {} }]
    expect(colunasQueChegam(arestas, NOS, "x")).toEqual({
      result: ["cod", "populacao", "renda"],
    })
  })

  it("duas arestas na mesma porta não repetem coluna", () => {
    const arestas = [
      { source: "malha", target: "x", data: { from_key: "output", to_key: "p" } },
      { source: "censo", target: "x", data: { from_key: "result", to_key: "p" } },
    ]
    expect(colunasQueChegam(arestas, NOS, "x").p).toEqual([
      "cod", "nome", "geometry", "populacao", "renda",
    ])
  })

  it("ignora arestas que não chegam neste nó", () => {
    const arestas = [{ source: "censo", target: "outro", data: { from_key: "result" } }]
    expect(colunasQueChegam(arestas, NOS, "x")).toEqual({})
  })

  it("nó que nunca executou não contribui", () => {
    // Nada de sugestão errada: sem execução, não há o que saber.
    const arestas = [{ source: "sem_run", target: "x", data: { from_key: "output" } }]
    expect(colunasQueChegam(arestas, NOS, "x")).toEqual({})
  })

  it("from_key que não existe na saída gravada não inventa porta", () => {
    const arestas = [{ source: "censo", target: "x", data: { from_key: "inexistente" } }]
    expect(colunasQueChegam(arestas, NOS, "x")).toEqual({})
  })

  it("nó de origem fora do canvas não quebra", () => {
    const arestas = [{ source: "fantasma", target: "x", data: { from_key: "output" } }]
    expect(colunasQueChegam(arestas, NOS, "x")).toEqual({})
  })
})

describe("sugestaoParaNo", () => {
  const porNo = new Map<string, ColunasConhecidasDoNo>([
    ["malha", { porPorta: { output: ["cod", "nome"] }, fresh: true }],
    ["censo", { porPorta: { result: ["cod", "renda"] }, fresh: false }],
  ])
  const arestas = [
    { source: "malha", target: "join", data: { from_key: "output", to_key: "layerA" } },
    { source: "censo", target: "join", data: { from_key: "result", to_key: "layerB" } },
  ]

  it("entrega por porta, o total e o frescor num pacote só", () => {
    expect(sugestaoParaNo(arestas, porNo, "join")).toEqual({
      porPorta: { layerA: ["cod", "nome"], layerB: ["cod", "renda"] },
      todas: ["cod", "nome", "renda"],
      // Um dos pais veio da re-hidratação: a lista inteira merece o aviso.
      desatualizadas: true,
      parciais: false,
    })
  })

  it("todos os pais ao vivo → sem aviso de frescor", () => {
    const soAoVivo = new Map([["malha", { porPorta: { output: ["cod"] }, fresh: true }]])
    expect(sugestaoParaNo(
      [{ source: "malha", target: "x", data: { from_key: "output" } }],
      soAoVivo, "x",
    )).toEqual({ porPorta: { output: ["cod"] }, todas: ["cod"], desatualizadas: false, parciais: false })
  })

  it("pai stale que NÃO contribui não dispara o aviso", () => {
    // O aviso fala das sugestões exibidas — um nó re-hidratado noutro canto do
    // grafo não torna esta lista desatualizada.
    expect(sugestaoParaNo(
      [{ source: "malha", target: "x", data: { from_key: "output" } }],
      porNo, "x",
    ).desatualizadas).toBe(false)
  })

  it("sem colunas conhecidas, o objeto estável de vazio", () => {
    expect(sugestaoParaNo(arestas, new Map(), "join")).toBe(SEM_SUGESTAO)
  })

  it("sem coluna nenhuma chegando, não há o que rotular", () => {
    // `desatualizadas` acompanha a LISTA: vazia, o aviso não tem referente.
    expect(sugestaoParaNo([], porNo, "join")).toEqual({
      porPorta: {}, todas: [], desatualizadas: false, parciais: false,
    })
  })

  it("pai com stat truncado marca a lista como parcial", () => {
    const comCorte = new Map([
      ["malha", { porPorta: { output: ["cod"] }, fresh: false, parciais: true }],
    ])
    expect(sugestaoParaNo(
      [{ source: "malha", target: "x", data: { from_key: "output" } }],
      comCorte, "x",
    )).toMatchObject({ parciais: true })
  })
})
