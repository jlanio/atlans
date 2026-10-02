/**
 * O snapshot da execução é único por janela, não um por consumidor.
 *
 * O painel de execução e o visualizador de sub-fluxo pedem a mesma linha do
 * tempo. Com um timer e uma reconstrução por hook, abrir o visualizador durante
 * um run dobrava o custo: `buildTimeline` percorre a lista inteira de eventos
 * (até 2000) e ordena os nós, oito vezes por segundo, na thread que anima o
 * canvas.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"

import { useRunSnapshot } from "@/app/components/workflow/run-panel/use-run-snapshot"
import { RunEvent, useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"

const T0 = 1_700_000_000_000

function evento(node: string, status: string): RunEvent {
  return { seq: 0, ts: T0, node, kind: "lifecycle", level: "info", status, raw: {} }
}

describe("useRunSnapshot", () => {
  beforeEach(() => {
    useWorkflowExecutionStore.getState().resetExecution()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("dois consumidores leem exatamente o mesmo objeto", () => {
    const a = renderHook(() => useRunSnapshot())
    const b = renderHook(() => useRunSnapshot())

    // Identidade, não igualdade: provar que a linha do tempo foi construída uma
    // vez só é o ponto de existir um snapshot compartilhado.
    expect(a.result.current).toBe(b.result.current)

    a.unmount()
    b.unmount()
  })

  it("assina a store uma única vez, com vários consumidores", () => {
    const subscribe = vi.spyOn(useWorkflowExecutionStore, "subscribe")

    const a = renderHook(() => useRunSnapshot())
    const b = renderHook(() => useRunSnapshot())
    const c = renderHook(() => useRunSnapshot())

    expect(subscribe).toHaveBeenCalledTimes(1)

    a.unmount()
    b.unmount()
    c.unmount()
  })

  it("o último a sair cancela a inscrição — e o próximo reabre", () => {
    const cancelar = vi.fn()
    const subscribe = vi
      .spyOn(useWorkflowExecutionStore, "subscribe")
      .mockReturnValue(cancelar)

    const a = renderHook(() => useRunSnapshot())
    const b = renderHook(() => useRunSnapshot())

    a.unmount()
    // Ainda há consumidor: manter a inscrição viva.
    expect(cancelar).not.toHaveBeenCalled()

    b.unmount()
    expect(cancelar).toHaveBeenCalledTimes(1)

    // Sem isto, reabrir o painel depois de fechado deixaria de receber eventos.
    const c = renderHook(() => useRunSnapshot())
    expect(subscribe).toHaveBeenCalledTimes(2)
    c.unmount()
  })

  it("o primeiro a chegar recolhe o que já existe, sem esperar a janela", () => {
    // Abrir o painel num run já carregado não pode mostrar tela vazia até o
    // próximo tique do agregador.
    act(() => {
      useWorkflowExecutionStore.getState().appendEvents([evento("a", "completed")])
    })

    const { result, unmount } = renderHook(() => useRunSnapshot())
    expect(result.current.events).toHaveLength(1)
    unmount()
  })

  it("propaga eventos novos para todos os consumidores", async () => {
    const a = renderHook(() => useRunSnapshot())
    const b = renderHook(() => useRunSnapshot())

    act(() => {
      useWorkflowExecutionStore.getState().appendEvents([evento("x", "started")])
    })

    await waitFor(() => expect(a.result.current.events).toHaveLength(1))
    expect(b.result.current).toBe(a.result.current)

    a.unmount()
    b.unmount()
  })
})
