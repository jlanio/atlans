import { describe, expect, it } from "vitest"
import {
  ESTADO_PADRAO, FILTROS, ORDENS, escreverEstado, filtrosAtivos, lerEstado,
} from "@/app/components/projects/projetos-url"

const sp = (s: string) => new URLSearchParams(s)

describe("lerEstado", () => {
  it("sem query string é o padrão: sem busca, Todos, por nome", () => {
    expect(lerEstado(sp(""))).toEqual(ESTADO_PADRAO)
    expect(ESTADO_PADRAO).toEqual({ q: "", filtro: "todos", ordem: "nome" })
  })

  it("lê busca, filtro e ordem", () => {
    expect(lerEstado(sp("q=outorga&filtro=falha&ordem=execucao")))
      .toEqual({ q: "outorga", filtro: "falha", ordem: "execucao" })
  })

  it("aceita todos os filtros e ordens válidos, inclusive os que só existem na URL", () => {
    for (const f of FILTROS) expect(lerEstado(sp(`filtro=${f}`)).filtro).toBe(f)
    for (const o of ORDENS) expect(lerEstado(sp(`ordem=${o}`)).ordem).toBe(o)
    expect(FILTROS).toContain("pausado")
    expect(FILTROS).toContain("nunca")
  })

  it("valor inválido cai no padrão, não quebra a tela", () => {
    const e = lerEstado(sp("filtro=weird&ordem=data"))
    expect(e.filtro).toBe("todos")
    expect(e.ordem).toBe("nome")
  })

  it("busca é aparada e cortada em 200 caracteres", () => {
    expect(lerEstado(sp("q=%20%20")).q).toBe("")
    expect(lerEstado(sp("q=%20sicar%20")).q).toBe("sicar")
    expect(lerEstado(sp(`q=${"a".repeat(300)}`)).q).toHaveLength(200)
  })
})

describe("escreverEstado", () => {
  it("não escreve os defaults", () => {
    expect(escreverEstado(ESTADO_PADRAO)).toBe("")
    expect(escreverEstado({ ...ESTADO_PADRAO, q: "   " })).toBe("")
  })

  it("escreve só o que difere do padrão", () => {
    expect(escreverEstado({ q: "", filtro: "agendados", ordem: "nome" })).toBe("filtro=agendados")
    expect(escreverEstado({ q: "", filtro: "todos", ordem: "alterado" })).toBe("ordem=alterado")
  })

  it("ida e volta preserva o estado", () => {
    const estado = { q: " bacia ", filtro: "pausado" as const, ordem: "execucao" as const }
    const qs = escreverEstado(estado)
    expect(qs).toBe("q=bacia&filtro=pausado&ordem=execucao")
    expect(lerEstado(sp(qs))).toEqual({ ...estado, q: "bacia" })
  })
})

describe("filtrosAtivos", () => {
  it("conta busca e chip; a ordenação não recorta a lista", () => {
    expect(filtrosAtivos(ESTADO_PADRAO)).toBe(0)
    expect(filtrosAtivos({ ...ESTADO_PADRAO, ordem: "alterado" })).toBe(0)
    expect(filtrosAtivos({ ...ESTADO_PADRAO, q: "x" })).toBe(1)
    expect(filtrosAtivos({ ...ESTADO_PADRAO, q: "x", filtro: "falha", ordem: "execucao" })).toBe(2)
  })
})
