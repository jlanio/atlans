/**
 * Counterpart of session-sync-ssr: on the CLIENT the token is still written in the
 * render body, not in an effect.
 *
 * That is what avoids the race with the child components' effects, which fire
 * API calls in the same tick as hydration and need the Authorization already
 * set up. The test uses `renderToString` (which does not run effects) in a
 * jsdom environment: if `setAuthToken` was called, it was during render.
 */
import { describe, it, expect, vi } from "vitest"
import type { ReactNode } from "react"
import { renderToString } from "react-dom/server"

const { setAuthToken } = vi.hoisted(() => ({ setAuthToken: vi.fn() }))
const { sessionAtual, provedor } = vi.hoisted(() => ({
  sessionAtual: { valor: null as unknown },
  provedor: { props: null as Record<string, unknown> | null },
}))

vi.mock("@/service/GisFlowService", () => ({
  setAuthToken,
}))
vi.mock("@/lib/sidebar-cache", () => ({ clearCachedHasAgents: vi.fn() }))
vi.mock("@/context/NotificationsContext", () => ({
  NotificationsProvider: ({ children }: { children?: ReactNode }) => children ?? null,
}))
vi.mock("@/app/components/command-palette", () => ({ default: () => null }))
vi.mock("next-auth/react", () => ({
  SessionProvider: (props: { children?: ReactNode }) => {
    provedor.props = props
    return props.children ?? null
  },
  signOut: vi.fn(),
  useSession: () => ({ data: sessionAtual.valor, status: "authenticated" }),
}))

import Providers, { SessionSync } from "@/app/components/providers"

describe("SessionSync no cliente", () => {
  it("escreve o token durante o render, antes de qualquer efeito", () => {
    expect(typeof window).not.toBe("undefined")
    sessionAtual.valor = { user: { id_hash: "u_A", access_token: "TOKEN-A" } }
    setAuthToken.mockClear()

    renderToString(<SessionSync />)

    expect(setAuthToken).toHaveBeenCalledWith("TOKEN-A")
  })

  it("limpa o token quando não há sessão", () => {
    sessionAtual.valor = null
    setAuthToken.mockClear()

    renderToString(<SessionSync />)

    expect(setAuthToken).toHaveBeenCalledWith(null)
  })
})

describe("Providers: a sessão do cliente não envelhece numa aba com foco", () => {
  it("refaz a sessão periodicamente, em SEGUNDOS e bem abaixo do TTL do access token", () => {
    // Without a refetchInterval next-auth only refetches on visibilitychange: a
    // tab that kept focus held an expired token past the API's 30 min, and the
    // run WebSocket — which authenticates with that browser copy — got 4401.
    provedor.props = null
    renderToString(<Providers session={null}>{null}</Providers>)
    // Written by the SessionProvider double during the render above.
    const props = provedor.props as Record<string, unknown> | null

    const intervalo = props?.refetchInterval as number
    expect(intervalo).toBeGreaterThan(0)
    // next-auth multiplies by 1000: a value in ms would mean days.
    expect(intervalo * 1000).toBeLessThan(29 * 60 * 1000) // ACCESS_TTL_MS in auth.ts
    // The focus refetch stays on (next-auth's default).
    expect(props?.refetchOnWindowFocus).not.toBe(false)
  })
})
