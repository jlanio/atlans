import { describe, expect, it } from "vitest"
import {
  ESCOPO_PADRAO, PERIODO_PADRAO, escreverEstado, lerEscopo, type EstadoDoEscopo,
} from "@/app/components/dashboard/dashboard-url"

const sp = (s: string) => new URLSearchParams(s)

describe("lerEscopo", () => {
  it("sem query string é o padrão: workspace ativo", () => {
    expect(lerEscopo(sp(""))).toBe("ativo")
    expect(ESCOPO_PADRAO).toBe("ativo")
  })

  it("só `escopo=todos` vira 'todos'", () => {
    expect(lerEscopo(sp("escopo=todos"))).toBe("todos")
  })

  it("qualquer outro valor cai em 'ativo', sem quebrar a tela", () => {
    expect(lerEscopo(sp("escopo=ativo"))).toBe("ativo")
    expect(lerEscopo(sp("escopo=global"))).toBe("ativo")
    expect(lerEscopo(sp("escopo="))).toBe("ativo")
    expect(lerEscopo(sp("outro=todos"))).toBe("ativo")
  })
})

describe("escreverEstado", () => {
  it("omite o escopo padrão para deixar a URL limpa", () => {
    expect(escreverEstado({ escopo: "ativo", periodo: PERIODO_PADRAO })).toBe("")
  })

  it("escreve 'todos'", () => {
    expect(escreverEstado({ escopo: "todos", periodo: PERIODO_PADRAO })).toBe("escopo=todos")
  })

  it("ida e volta preserva o escopo", () => {
    for (const e of ["ativo", "todos"] as EstadoDoEscopo[]) {
      expect(lerEscopo(sp(escreverEstado({ escopo: e, periodo: PERIODO_PADRAO })))).toBe(e)
    }
  })
})
