/**
 * Memória de colunas por workflow — a store que faz "Vistas na última
 * execução" sobreviver a F5, troca de aba e cliques em Executar.
 *
 * O contrato importante é o de FRESCOR: escrita ao vivo (`fresh: true`) nunca
 * é sobrescrita pela re-hidratação do run persistido, que pode chegar
 * atrasada pela rede; e um nó que completa SEM publicar colunas vira LÁPIDE
 * (`porPorta: {}`, fresh) — manter o valor antigo afirmaria colunas que a
 * última execução não produziu, e apagar sem memória deixava a semeadura
 * atrasada ressuscitá-las conforme o timing da rede.
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
    // Um delete deixava o resultado depender do timing da rede: a semeadura
    // atrasada do run ANTERIOR re-inseria as colunas que o run ao vivo
    // acabou de negar. A lápide (fresh) é o que o seed respeita.
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
    // n1 já tinha dado ao vivo (mais novo que qualquer resposta de API).
    expect(estado().porNo.get("n1")).toMatchObject({ porPorta: { output: ["novo"] }, fresh: true })
    // n2 só existia no histórico.
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
    // Mesma identidade: reabrir a mesma tela não apaga memória nem re-renderiza.
    expect(estado().porNo).toBe(antes)

    estado().prepararParaWorkflow("wf-b")
    expect(estado().porNo.size).toBe(0)
    expect(estado().workflowId).toBe("wf-b")
  })

  it("escrita atrasada de outro workflow não vaza para o atual", () => {
    // Workflow duplicado repete os node ids do original — sem o corte por
    // workflow, as colunas de A apareceriam como sugestão em B.
    estado().aplicarDeExecucao("wf-a", "run-1", new Map([["n1", { output: ["deA"] }]]))
    estado().aplicarDeExecucao("wf-b", "run-9", new Map([["n2", { output: ["deB"] }]]))
    expect(estado().workflowId).toBe("wf-b")
    expect(estado().porNo.has("n1")).toBe(false)
    expect(estado().porNo.get("n2")).toMatchObject({ porPorta: { output: ["deB"] } })
  })

  it("semeadura atrasada de OUTRO workflow é ignorada", () => {
    // A escrita ao vivo pode adotar o workflow (o evento prova que é ele que
    // roda); uma resposta de API antiga não prova nada — aceitar colocaria as
    // colunas de A na tela de B.
    estado().aplicarDeExecucao("wf-b", "run-1", new Map([["n2", { output: ["deB"] }]]))
    estado().semearDoHistorico("wf-a", "run-9", { n1: { porPorta: { output: ["deA"] } } })
    expect(estado().workflowId).toBe("wf-b")
    expect(estado().porNo.has("n1")).toBe(false)
    expect(estado().porNo.get("n2")).toMatchObject({ porPorta: { output: ["deB"] } })
  })

  it("semeadura com a store virgem adota o workflow", () => {
    // Montagens fora do canvas (sem o preparo do reset) começam com null.
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
