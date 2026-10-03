// @vitest-environment node
/**
 * SEC: the user's access_token must not be written on the server.
 *
 * `setAuthToken` writes to a MODULE variable of GisFlowService. In the browser it
 * is per tab; in Node it is per PROCESS, shared by all in-flight
 * requests. Since the SessionProvider started receiving the session resolved on the
 * server, SessionSync's render body runs in SSR already with the real token:
 * user A's render wrote A's token and B's, running concurrently, overwrote it
 * with B's — a credential leak between users, readable by the
 * axios interceptor.
 *
 * This test runs in a `node` environment on purpose: the absence of `window` is what
 * characterizes SSR.
 */
import { describe, it, expect, vi } from "vitest"
import type { ReactNode } from "react"
import { renderToString } from "react-dom/server"

const { setAuthToken } = vi.hoisted(() => ({ setAuthToken: vi.fn() }))

vi.mock("@/service/GisFlowService", () => ({
  setAuthToken,
}))
vi.mock("@/lib/sidebar-cache", () => ({ clearCachedHasAgents: vi.fn() }))
vi.mock("@/context/NotificationsContext", () => ({
  NotificationsProvider: ({ children }: { children?: ReactNode }) => children ?? null,
}))
vi.mock("@/app/components/command-palette", () => ({ default: () => null }))
vi.mock("next-auth/react", () => ({
  SessionProvider: ({ children }: { children?: ReactNode }) => children ?? null,
  signOut: vi.fn(),
  // With the session coming from the server, `useSession()` ALREADY returns data in SSR.
  useSession: () => ({
    data: { user: { id_hash: "u_A", access_token: "TOKEN-DO-USUARIO-A" } },
    status: "authenticated",
  }),
}))

import { SessionSync } from "@/app/components/providers"

describe("SessionSync no SSR", () => {
  it("não escreve o token no singleton de módulo", () => {
    expect(typeof window).toBe("undefined")
    renderToString(<SessionSync />)
    expect(setAuthToken).not.toHaveBeenCalled()
  })
})
