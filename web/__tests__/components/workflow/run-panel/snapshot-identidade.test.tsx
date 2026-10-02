/**
 * O snapshot não pode realocar tudo a cada janela.
 *
 * `buildTimeline` é pura e cria um `NodeRun` novo para cada nó a cada chamada.
 * Como as linhas do painel são memoizadas por identidade de prop, isso fazia
 * TODAS elas re-renderizarem oito vezes por segundo mesmo quando um único nó
 * mudava. E, com o painel recolhido, essa reconstrução acontecia para ninguém:
 * a barra de 34px só precisa de contagens e status.
 */
import { describe, it, expect, beforeEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"

import { useRunSnapshot } from "@/app/components/workflow/run-panel/use-run-snapshot"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

const T0 = 1_700_000_000_000

function no(id: string, status: INodeStatusWorkFlow["status"]) {
  return { id, status, position: { x: 0, y: 0 }, data: { alias: `Nó ${id}` } } as INodeStatusWorkFlow
}

function evento(node: string, status: string, atMs = 0): RunEvent {
  return { seq: 0, ts: T0 + atMs, node, kind: "lifecycle", level: "info", status, raw: {} }
}

describe("useRunSnapshot — identidade e custo", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
  })

  it("preserva a instância das linhas que não mudaram entre janelas", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle"), no("b", "idle")])
    store.appendEvents([evento("a", "started")])

    const { result, unmount } = renderHook(() => useRunSnapshot(true))
    await waitFor(() => expect(result.current.timeline.nodes).toHaveLength(2))
    const linhaB = result.current.timeline.nodes.find(n => n.nodeId === "b")!

    act(() => {
      useWorkflowExecutionStore.getState().appendEvents([evento("a", "completed", 500)])
    })
    await waitFor(() => {
      expect(result.current.timeline.nodes.find(n => n.nodeId === "a")!.status).toBe("completed")
    })

    // "b" não foi tocado por nenhum evento: a linha dele tem de ser o MESMO
    // objeto, senão o `memo` do NodeRow não segura nada.
    expect(result.current.timeline.nodes.find(n => n.nodeId === "b")).toBe(linhaB)
    unmount()
  })

  it("com a barra recolhida não monta a linha do tempo por evento", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle")])
    store.appendEvents([
      evento("a", "started"),
      { seq: 0, ts: T0 + 10, node: "a", kind: "stdout", level: "info", status: "log", lines: ["oi"], raw: {} },
    ])

    const { result, unmount } = renderHook(() => useRunSnapshot(false))
    // O resumo continua respondendo "o que está acontecendo": contagens e
    // status vêm do estado por nó do canvas, sem percorrer os eventos.
    expect(result.current.timeline.counts.total).toBe(1)
    expect(result.current.timeline.workflow.status).toBe("running")
    // Prints são detalhe do painel aberto — ninguém os desenha com ele fechado.
    expect(result.current.timeline.totalPrints).toBe(0)
    unmount()
  })

  it("abrir o painel passa a entregar a linha do tempo completa", async () => {
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([no("a", "idle")])
    store.appendEvents([
      evento("a", "started"),
      { seq: 0, ts: T0 + 10, node: "a", kind: "stdout", level: "info", status: "log", lines: ["oi"], raw: {} },
    ])

    const { result, rerender, unmount } = renderHook(
      ({ aberto }: { aberto: boolean }) => useRunSnapshot(aberto),
      { initialProps: { aberto: false } },
    )
    expect(result.current.timeline.totalPrints).toBe(0)

    rerender({ aberto: true })
    await waitFor(() => expect(result.current.timeline.totalPrints).toBe(1))
    unmount()
  })
})
