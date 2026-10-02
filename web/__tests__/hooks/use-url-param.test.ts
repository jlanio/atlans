import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook } from "@testing-library/react"

// `cn`/`ndid`/`ndhid` são params EFÊMEROS de UI (modal de config, drawer de
// conexão). Escrevê-los com `push` empilhava uma entrada de histórico a cada
// abrir/fechar, e o Voltar do navegador reabria um modal já fechado. A URL é
// dublada por um `URLSearchParams` mutável; o teste observa quem foi chamado.
const url = { sp: new URLSearchParams(""), pathname: "/workflow/abc" }
const replace = vi.fn()
const push = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
}))

import { useUrlParam } from "@/app/hooks/useUrlParam"
import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams"

beforeEach(() => {
  replace.mockReset()
  push.mockReset()
  url.sp = new URLSearchParams("")
})
afterEach(() => vi.restoreAllMocks())

describe("useUrlParam — param efêmero usa replace, não push", () => {
  it("set grava com replace (nunca push)", () => {
    const { result } = renderHook(() => useUrlParam("cn"))
    act(() => result.current.set("n1"))
    expect(replace).toHaveBeenCalledTimes(1)
    expect(replace.mock.calls[0][0]).toContain("cn=n1")
    expect(push).not.toHaveBeenCalled()
  })

  it("remove tira o param com replace (nunca push)", () => {
    url.sp = new URLSearchParams("cn=n1")
    const { result } = renderHook(() => useUrlParam("cn"))
    act(() => result.current.remove())
    expect(replace).toHaveBeenCalledTimes(1)
    expect(replace.mock.calls[0][0]).not.toContain("cn=")
    expect(push).not.toHaveBeenCalled()
  })
})

describe("useLinkNodeParams — o drawer de conexão usa replace, não push", () => {
  // Este hook RE-IMPLEMENTA os writers de `ndid`/`ndhid` (não passa pelo
  // useUrlParam), então tinha o mesmo `push` a corrigir por conta própria.
  it("setLinkNodeParam grava ndid/ndhid com replace", () => {
    const { result } = renderHook(() => useLinkNodeParams())
    act(() => result.current.setLinkNodeParam("no-1", "h-2"))
    expect(replace).toHaveBeenCalledTimes(1)
    const u = replace.mock.calls[0][0] as string
    expect(u).toContain("ndid=no-1")
    expect(u).toContain("ndhid=h-2")
    expect(push).not.toHaveBeenCalled()
  })

  it("removeLinkNodeParam tira ndid/ndhid com replace", () => {
    url.sp = new URLSearchParams("ndid=no-1&ndhid=h-2")
    const { result } = renderHook(() => useLinkNodeParams())
    act(() => result.current.removeLinkNodeParam())
    expect(replace).toHaveBeenCalledTimes(1)
    const u = replace.mock.calls[0][0] as string
    expect(u).not.toContain("ndid=")
    expect(u).not.toContain("ndhid=")
    expect(push).not.toHaveBeenCalled()
  })
})
