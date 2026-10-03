import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook } from "@testing-library/react"

// `cn`/`ndid`/`ndhid` are EPHEMERAL UI params (config modal, connection
// drawer). Writing them with `push` stacked a history entry on every
// open/close, and the browser's Back reopened an already-closed modal. The URL
// is doubled by a mutable `URLSearchParams`; the test observes what was called.
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
  // This hook RE-IMPLEMENTS the `ndid`/`ndhid` writers (it doesn't go through
  // useUrlParam), so it had the same `push` to fix on its own.
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
