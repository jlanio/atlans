/**
 * Samples of each node's outputs for the node modal's panels
 * (docs/specs/node-data-panels.md §6.1): they survive the canvas reset, are
 * marked stale when a new run starts, and are scoped to one workflow.
 */
import { describe, it, expect, beforeEach } from "vitest"
import { useNodeSamplesStore, amostrasDosEventos, amostraDoEvento } from "@/app/stores/nodeSamplesStore"
import type { AmostraDoNo } from "@/types/amostra"
import { resumoDaAmostra } from "@/types/amostra"

const amostra = (n: number): AmostraDoNo => ({
  version: 1,
  outputs: {
    output: {
      kind: "table", rows_total: n, columns: [{ name: "a", type: "int" }], rows: [[1]],
      truncated: { rows: n > 1, columns: false, cells: false },
    },
  },
})

const st = () => useNodeSamplesStore.getState()

beforeEach(() => st().clear())

describe("nodeSamplesStore", () => {
  it("guarda a amostra de cada nó da execução atual", () => {
    st().beginRun("wf", "r1", true)
    st().apply("wf", "r1", "A", amostra(10))
    expect(st().byNode.A).toEqual({ sample: amostra(10), runId: "r1", stale: false })
    expect(st().disabledByAdmin).toBe(false)
  })

  it("nova execução marca as anteriores como antigas até o nó chegar de novo", () => {
    st().beginRun("wf", "r1", true)
    st().apply("wf", "r1", "A", amostra(10))
    st().apply("wf", "r1", "B", amostra(5))
    st().beginRun("wf", "r2", true)
    expect(st().byNode.A.stale).toBe(true)
    st().apply("wf", "r2", "A", amostra(11))
    expect(st().byNode.A).toEqual({ sample: amostra(11), runId: "r2", stale: false })
    expect(st().byNode.B.stale).toBe(true)
  })

  it("evento atrasado da execução anterior não sobrescreve a atual", () => {
    st().beginRun("wf", "r2", true)
    st().apply("wf", "r2", "A", amostra(2))
    st().apply("wf", "r1", "A", amostra(1))
    expect(st().byNode.A.sample).toEqual(amostra(2))
  })

  it("outro workflow começa vazio", () => {
    st().beginRun("wf", "r1", true)
    st().apply("wf", "r1", "A", amostra(1))
    st().beginRun("outro", "r9", true)
    expect(st().byNode).toEqual({})
    st().apply("wf", "r1", "A", amostra(1))
    expect(st().workflowId).toBe("wf")
    expect(Object.keys(st().byNode)).toEqual(["A"])
  })

  it("data_preview false na resposta = admin desligou", () => {
    st().beginRun("wf", "r1", false)
    expect(st().disabledByAdmin).toBe(true)
  })

  it("histórico semeia só quando nenhuma execução desta sessão é dona dos painéis", () => {
    st().seedFromHistory("wf", "r0", { A: amostra(3) })
    expect(st().byNode.A.runId).toBe("r0")
    st().beginRun("wf", "r1", true)
    st().seedFromHistory("wf", "r0", { A: amostra(4) })
    expect(st().byNode.A.sample).toEqual(amostra(3))
  })
})

describe("leitura dos eventos", () => {
  it("extrai a última amostra válida de cada nó", () => {
    const eventos = [
      { node: "A", status: "completed", extra: {} },
      { node: "A", status: "sample", extra: { output_sample: amostra(1) } },
      { node: "A", status: "sample", extra: { output_sample: amostra(2) } },
      // cut by the protocol reduction: no output_sample
      { node: "B", status: "sample", extra: { node_name: "x" } },
      { node: "C", status: "sample", extra: { output_sample: "lixo" } },
    ]
    expect(amostrasDosEventos(eventos)).toEqual({ A: amostra(2) })
    expect(amostraDoEvento({ status: "sample", extra: null })).toBeNull()
  })

  it("resume a amostra numa linha para o log bruto", () => {
    const s: AmostraDoNo = {
      version: 1,
      outputs: { ...amostra(1284).outputs, metadata: { kind: "json", value: {}, truncated: false } },
    }
    expect(resumoDaAmostra(s)).toBe("amostra: output (1 de 1.284 linhas), metadata (objeto)")
    expect(resumoDaAmostra(undefined)).toBe("amostra indisponível")
  })
})

describe("semear de várias execuções", () => {
  it("amostras de uma execução completa mais antiga, sob uma parcial, aparecem como anteriores", () => {
    useNodeSamplesStore.getState().clear()
    useNodeSamplesStore.getState().seedFromHistory(
      "wf", "parcial", { A: { version: 1, outputs: {} }, B: { version: 1, outputs: {} } }, { A: "parcial", B: "completa" },
    )
    const { byNode } = useNodeSamplesStore.getState()
    expect(byNode.A).toMatchObject({ runId: "parcial", stale: false })
    expect(byNode.B).toMatchObject({ runId: "completa", stale: true })
  })
})

