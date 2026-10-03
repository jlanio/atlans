/**
 * Per-workflow column memory — the store that makes "Vistas na última
 * execução" survive F5, tab switches and clicks on Run.
 *
 * The important contract is FRESHNESS: a live write (`fresh: true`) is never
 * overwritten by the re-hydration of the persisted run, which may arrive
 * late over the network; and a node that completes WITHOUT publishing columns
 * becomes a TOMBSTONE (`porPorta: {}`, fresh) — keeping the old value would
 * assert columns the last execution did not produce, and deleting with no
 * memory let the late seeding resurrect them depending on network timing.
 */
import { describe, it, expect, beforeEach } from "vitest"
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore"

const zerar = () => useKnownColumnsStore.setState({ workflowId: null, porNo: new Map() })

const estado = () => useKnownColumnsStore.getState()

describe("useKnownColumnsStore", () => {
  beforeEach(zerar)

  it("escrita ao vivo grava por nó com fresh=true", () => {
    estado().aplicarDeExecucao("wf-a", "run-1", new Map([
      ["n1", { output: ["a", "b"] }],
    ]))
    expect(estado().workflowId).toBe("wf-a")
    expect(estado().porNo.get("n1")).toEqual({
      porPorta: { output: ["a", "b"] }, runId: "run-1", fresh: true,
    })
  })

  it("completed sem colunas vira LÁPIDE — nada a sugerir, mas com memória", () => {
    // A delete made the result depend on network timing: the late seeding
    // of the PREVIOUS run re-inserted the columns the live run had just
    // denied. The tombstone (fresh) is what the seed respects.
    estado().aplicarDeExecucao("wf-a", "run-1", new Map([["n1", { output: ["a"] }]]))
    estado().aplicarDeExecucao("wf-a", "run-2", new Map([["n1", null]]))
    expect(estado().porNo.get("n1")).toEqual({ porPorta: {}, runId: "run-2", fresh: true })
  })

  it("a semeadura atrasada NÃO ressuscita colunas que o run ao vivo negou", () => {
    estado().aplicarDeExecucao("wf-a", "run-2", new Map([["n1", null]]))
    estado().semearDoHistorico("wf-a", "run-1", { n1: { porPorta: { output: ["velha"] } } })
    expect(estado().porNo.get("n1")).toEqual({ porPorta: {}, runId: "run-2", fresh: true })
  })

  it("a semeadura do histórico entra com fresh=false e não pisa no ao vivo", () => {
    estado().aplicarDeExecucao("wf-a", "run-2", new Map([["n1", { output: ["novo"] }]]))
    estado().semearDoHistorico("wf-a", "run-1", {
      n1: { porPorta: { output: ["velho"] } },
      n2: { porPorta: { output: ["x"] } },
    })
    // n1 had already reported live (newer than any API response).
    expect(estado().porNo.get("n1")).toMatchObject({ porPorta: { output: ["novo"] }, fresh: true })
    // n2 only existed in the history.
    expect(estado().porNo.get("n2")).toEqual({
      porPorta: { output: ["x"] }, runId: "run-1", fresh: false, parciais: false,
    })
  })

  it("run ao vivo por cima da semeadura vira fresh=true", () => {
    estado().semearDoHistorico("wf-a", "run-1", { n1: { porPorta: { output: ["velho"] } } })
    estado().aplicarDeExecucao("wf-a", "run-2", new Map([["n1", { output: ["novo"] }]]))
    expect(estado().porNo.get("n1")).toMatchObject({ porPorta: { output: ["novo"] }, fresh: true })
  })

  it("preparar para OUTRO workflow limpa; para o MESMO, não toca em nada", () => {
    estado().aplicarDeExecucao("wf-a", "run-1", new Map([["n1", { output: ["a"] }]]))

    const antes = estado().porNo
    estado().prepararParaWorkflow("wf-a")
    // Same identity: reopening the same screen neither erases memory nor re-renders.
    expect(estado().porNo).toBe(antes)

    estado().prepararParaWorkflow("wf-b")
    expect(estado().porNo.size).toBe(0)
    expect(estado().workflowId).toBe("wf-b")
  })

  it("escrita atrasada de outro workflow não vaza para o atual", () => {
    // A duplicated workflow repeats the original's node ids — without the
    // per-workflow cut, A's columns would show up as suggestions in B.
    estado().aplicarDeExecucao("wf-a", "run-1", new Map([["n1", { output: ["deA"] }]]))
    estado().aplicarDeExecucao("wf-b", "run-9", new Map([["n2", { output: ["deB"] }]]))
    expect(estado().workflowId).toBe("wf-b")
    expect(estado().porNo.has("n1")).toBe(false)
    expect(estado().porNo.get("n2")).toMatchObject({ porPorta: { output: ["deB"] } })
  })

  it("semeadura atrasada de OUTRO workflow é ignorada", () => {
    // A live write may adopt the workflow (the event proves it is the one
    // running); an old API response proves nothing — accepting it would put
    // A's columns on B's screen.
    estado().aplicarDeExecucao("wf-b", "run-1", new Map([["n2", { output: ["deB"] }]]))
    estado().semearDoHistorico("wf-a", "run-9", { n1: { porPorta: { output: ["deA"] } } })
    expect(estado().workflowId).toBe("wf-b")
    expect(estado().porNo.has("n1")).toBe(false)
    expect(estado().porNo.get("n2")).toMatchObject({ porPorta: { output: ["deB"] } })
  })

  it("semeadura com a store virgem adota o workflow", () => {
    // Mounts outside the canvas (without the reset preparation) start with null.
    estado().semearDoHistorico("wf-a", "run-1", { n1: { porPorta: { output: ["a"] } } })
    expect(estado().workflowId).toBe("wf-a")
    expect(estado().porNo.get("n1")).toMatchObject({ fresh: false })
  })

  it("stat truncado semeia com a marca de lista parcial", () => {
    estado().semearDoHistorico("wf-a", "run-1", {
      n1: { porPorta: { output: ["a"] }, parciais: true },
    })
    expect(estado().porNo.get("n1")).toMatchObject({ parciais: true })
  })

  it("lote vazio não troca o Map (ninguém re-renderiza à toa)", () => {
    estado().aplicarDeExecucao("wf-a", "run-1", new Map([["n1", { output: ["a"] }]]))
    const antes = estado().porNo
    estado().aplicarDeExecucao("wf-a", "run-1", new Map())
    expect(estado().porNo).toBe(antes)
  })
})
