/**
 * The run snapshot is one per window, not one per consumer.
 *
 * The run panel and the sub-workflow viewer ask for the same timeline. With one
 * timer and one rebuild per hook, opening the viewer during a run doubled the
 * cost: `buildTimeline` walks the whole event list (up to 2,000) and sorts the
 * nodes, eight times per second, on the thread that animates the canvas.
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

    // Identity, not equality: proving the timeline was built only once is the
    // whole point of having a shared snapshot.
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
    // There's still a consumer: keep the subscription alive.
    expect(cancelar).not.toHaveBeenCalled()

    b.unmount()
    expect(cancelar).toHaveBeenCalledTimes(1)

    // Without this, reopening the panel after closing it would stop receiving events.
    const c = renderHook(() => useRunSnapshot())
    expect(subscribe).toHaveBeenCalledTimes(2)
    c.unmount()
  })

  it("o primeiro a chegar recolhe o que já existe, sem esperar a janela", () => {
    // Opening the panel on an already-loaded run must not show an empty screen
    // until the aggregator's next tick.
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
