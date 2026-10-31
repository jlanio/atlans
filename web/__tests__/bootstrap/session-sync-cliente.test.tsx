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

describe("Providers: a sessão do cliente não vira anônima por um fetch que falhou", () => {
  it("não refaz a sessão por intervalo (um poll que falha deixa a aba anônima)", () => {
    // In next-auth 5 one failed /api/auth/session sets the session to null and
    // stops refetching. The run socket fetches its own fresh token before a
    // reconnect, so no periodic poll is needed.
    provedor.props = null
    renderToString(<Providers session={null}>{null}</Providers>)
    // Written by the SessionProvider double during the render above.
    const props = provedor.props as Record<string, unknown> | null

    expect(props?.refetchInterval).toBeUndefined()
    // The focus refetch stays on (next-auth's default).
    expect(props?.refetchOnWindowFocus).not.toBe(false)
  })
})
