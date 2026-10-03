import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

const push = vi.fn()
// A single instance, as the App Router's `useRouter` actually returns.
const fakeRouter = { push, replace: vi.fn(), back: vi.fn(), forward: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() }
vi.mock("next/navigation", () => ({ useRouter: () => fakeRouter }))

import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"

/**
 * Double of `document.startViewTransition`: it stores the callback instead of
 * running it, so the test controls WHEN it's called and observes the returned
 * promise — that promise is precisely what was missing before.
 */
function dublarViewTransition() {
  const skipTransition = vi.fn()
  let executar: (() => void | Promise<void>) | null = null
  const startViewTransition = vi.fn((cb: () => void | Promise<void>) => {
    executar = cb
    return { skipTransition, ready: Promise.reject(new Error("abort")).catch(() => {}) }
  })
  Object.defineProperty(document, "startViewTransition", {
    value: startViewTransition, configurable: true, writable: true,
  })
  return { skipTransition, rodarCallback: () => (executar as unknown as () => Promise<void>)() }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
  window.history.replaceState({}, "", "/projects")
})

afterEach(() => {
  vi.useRealTimers()
  Reflect.deleteProperty(document, "startViewTransition")
})

describe("useViewTransitionRouter", () => {
  it("segura a transição até a rota comitar — e só então deixa animar", async () => {
    const { skipTransition, rodarCallback } = dublarViewTransition()
    const { result } = renderHook(() => useViewTransitionRouter())

    act(() => { result.current.push("/workflow/abc") })

    const espera = rodarCallback()
    let resolvida = false
    espera.then(() => { resolvida = true })

    // The App Router's `router.push` is asynchronous: the DOM is still the listing's.
    expect(push).toHaveBeenCalledWith("/workflow/abc")
    await act(async () => { await vi.advanceTimersByTimeAsync(48) })
    expect(resolvida).toBe(false)

    // Route commit — the App Router syncs the history on commit.
    window.history.pushState({}, "", "/workflow/abc")
    await act(async () => { await vi.advanceTimersByTimeAsync(32) })

    expect(resolvida).toBe(true)
    // There was a DOM swap: the animation is legitimate and must NOT be discarded.
    expect(skipTransition).not.toHaveBeenCalled()
  })

  it("descarta a animação quando a rota não comita dentro do teto", async () => {
    const { skipTransition, rodarCallback } = dublarViewTransition()
    const { result } = renderHook(() => useViewTransitionRouter())

    act(() => { result.current.push("/workflow/abc") })

    const espera = rodarCallback()
    let resolvida = false
    espera.then(() => { resolvida = true })

    // The editor route takes seconds (React Flow + Monaco, no prefetch).
    // Animating here would cross-fade two IDENTICAL snapshots: the whole page
    // flickered and slid 4px without changing screens. It's the bug this branch avoids.
    await act(async () => { await vi.advanceTimersByTimeAsync(400) })

    expect(resolvida).toBe(true)
    expect(skipTransition).toHaveBeenCalledTimes(1)
    // The navigation runs its course: only the animation is discarded.
    expect(push).toHaveBeenCalledWith("/workflow/abc")
  })

  it("devolve a mesma instância entre renders", () => {
    // The /projects callbacks have `[router]` as a dependency and go down to
    // memoized cards: a new object on every render reset `React.memo` and the
    // whole list re-rendered again on every search keystroke.
    const { result, rerender } = renderHook(() => useViewTransitionRouter())
    const primeiro = result.current
    rerender()
    expect(result.current).toBe(primeiro)
  })

  it("sem suporte a View Transitions, navega direto", () => {
    Reflect.deleteProperty(document, "startViewTransition")
    const { result } = renderHook(() => useViewTransitionRouter())

    act(() => { result.current.push("/workflow/abc") })

    expect(push).toHaveBeenCalledWith("/workflow/abc")
  })
})
