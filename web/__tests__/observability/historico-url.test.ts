import { describe, it, expect } from "vitest"
import {
  DEFAULT_STATE, escreverEstado, filtrosAtivos, windowStart, lerEstado,
} from "@/app/components/observability/historico-url"

const sp = (s: string) => new URLSearchParams(s)

describe("lerEstado", () => {
  it("sem query string é o padrão: 30 dias, execuções, sem filtro", () => {
    expect(lerEstado(sp(""))).toEqual(DEFAULT_STATE)
  })
  it("lê tudo o que a página guarda", () => {
    expect(lerEstado(sp("periodo=7&visao=workflows&status=failed&workspace=ws1&workflow=wf1&executor=ex1&origem=schedule&assistente=1&q=timeout&execucao=run1")))
      .toEqual({
        periodo: 7, visao: "workflows", status: "failed", workspace: "ws1", workflow: "wf1", executor: "ex1",
        origem: "schedule", assistente: true, q: "timeout", execucao: "run1",
      })
  })
  it("valor inválido cai no padrão, não quebra a tela", () => {
    const e = lerEstado(sp("periodo=15&visao=x&status=weird&origem=cron"))
    expect(e.periodo).toBe(30)
    expect(e.visao).toBe("execucoes")
    expect(e.status).toBeNull()
    expect(e.origem).toBeNull()
  })
  it("assistente é o fluxo, origem é o disparo: os dois convivem na URL", () => {
    // `origem` is already the trigger's (`trigger_source`); the assistant chip
    // slices by WHO CREATED the workflow — hence its own name, and hence they can be combined.
    const e = lerEstado(sp("origem=manual&assistente=1"))
    expect([e.origem, e.assistente]).toEqual(["manual", true])
    expect(escreverEstado({ ...DEFAULT_STATE, origem: "manual", assistente: true }))
      .toBe("origem=manual&assistente=1")
    // Only "1" turns it on: anything else is the default (off), without breaking.
    expect(lerEstado(sp("assistente=sim")).assistente).toBe(false)
    expect(escreverEstado(DEFAULT_STATE)).toBe("")
  })
  it("origem=mcp (execução disparada por um agente) é um filtro válido", () => {
    expect(lerEstado(sp("origem=mcp")).origem).toBe("mcp")
    expect(escreverEstado({ ...DEFAULT_STATE, origem: "mcp" })).toBe("origem=mcp")
  })
  it("texto vazio ou só espaços é nulo; texto longo é cortado", () => {
    expect(lerEstado(sp("workspace=%20%20&q=%20")).workspace).toBeNull()
    expect(lerEstado(sp("q=%20")).q).toBe("")
    expect(lerEstado(sp(`q=${"a".repeat(300)}`)).q).toHaveLength(200)
  })
})

describe("escreverEstado", () => {
  it("não escreve os defaults", () => {
    expect(escreverEstado(DEFAULT_STATE)).toBe("")
  })
  it("ida e volta preserva o estado", () => {
    const estado = { ...DEFAULT_STATE, periodo: 90 as const, status: "running" as const, workflow: "wf1", q: " sicar ", execucao: "r1" }
    const qs = escreverEstado(estado)
    expect(qs).toBe("periodo=90&status=running&workflow=wf1&q=sicar&execucao=r1")
    expect(lerEstado(sp(qs))).toEqual({ ...estado, q: "sicar" })
  })
})

describe("derivados", () => {
  it("conta filtros ativos fora período, visão e execução aberta", () => {
    expect(filtrosAtivos(DEFAULT_STATE)).toBe(0)
    expect(filtrosAtivos({ ...DEFAULT_STATE, status: "failed", q: "x", execucao: "r", periodo: 7 })).toBe(2)
  })
  it("início da janela é N dias antes, em ISO UTC", () => {
    const agora = new Date("2026-09-06T19:43:00Z")
    expect(windowStart(7, agora)).toBe("2026-08-30T19:43:00.000Z")
    expect(windowStart(30, agora)).toBe("2026-08-07T19:43:00.000Z")
  })
})
