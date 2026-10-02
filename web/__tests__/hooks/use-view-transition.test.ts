import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

const push = vi.fn()
// Instância única, como o `useRouter` do App Router de fato devolve.
const routerFalso = { push, replace: vi.fn(), back: vi.fn(), forward: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() }
vi.mock("next/navigation", () => ({ useRouter: () => routerFalso }))

import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"

/**
 * Dublê do `document.startViewTransition`: guarda o callback em vez de rodá-lo,
 * para o teste controlar QUANDO ele é chamado e observar a promessa devolvida —
 * é justamente essa promessa que faltava antes.
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

    // `router.push` do App Router é assíncrono: o DOM ainda é o da listagem.
    expect(push).toHaveBeenCalledWith("/workflow/abc")
    await act(async () => { await vi.advanceTimersByTimeAsync(48) })
    expect(resolvida).toBe(false)

    // Comite da rota — o App Router sincroniza o histórico no commit.
    window.history.pushState({}, "", "/workflow/abc")
    await act(async () => { await vi.advanceTimersByTimeAsync(32) })

    expect(resolvida).toBe(true)
    // Houve troca de DOM: a animação é legítima e NÃO pode ser descartada.
    expect(skipTransition).not.toHaveBeenCalled()
  })

  it("descarta a animação quando a rota não comita dentro do teto", async () => {
    const { skipTransition, rodarCallback } = dublarViewTransition()
    const { result } = renderHook(() => useViewTransitionRouter())

    act(() => { result.current.push("/workflow/abc") })

    const espera = rodarCallback()
    let resolvida = false
    espera.then(() => { resolvida = true })

    // A rota do editor leva segundos (React Flow + Monaco, sem prefetch).
    // Animar aqui cruzaria dois retratos IDÊNTICOS: a página inteira piscava e
    // deslizava 4px sem trocar de tela. É o bug que este ramo evita.
    await act(async () => { await vi.advanceTimersByTimeAsync(400) })

    expect(resolvida).toBe(true)
    expect(skipTransition).toHaveBeenCalledTimes(1)
    // A navegação segue seu curso: o que se descarta é só a animação.
    expect(push).toHaveBeenCalledWith("/workflow/abc")
  })

  it("devolve a mesma instância entre renders", () => {
    // Os callbacks de /projects têm `[router]` na dependência e descem para
    // cards memoizados: um objeto novo a cada render zerava o `React.memo` e a
    // lista inteira voltava a re-renderizar a cada tecla da busca.
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
