/**
 * Contraparte de session-sync-ssr: no CLIENTE o token continua sendo escrito no
 * corpo do render, e não num efeito.
 *
 * Isso é o que evita a race com os effects dos componentes filhos, que disparam
 * chamadas à API no mesmo tick da hidratação e precisam do Authorization já
 * montado. O teste usa `renderToString` (que não executa efeitos) num ambiente
 * jsdom: se `setAuthToken` foi chamado, foi durante o render.
 */
import { describe, it, expect, vi } from "vitest"
import type { ReactNode } from "react"
import { renderToString } from "react-dom/server"

const { setAuthToken } = vi.hoisted(() => ({ setAuthToken: vi.fn() }))
const { sessionAtual } = vi.hoisted(() => ({
  sessionAtual: { valor: null as unknown },
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
  SessionProvider: ({ children }: { children?: ReactNode }) => children ?? null,
  signOut: vi.fn(),
  useSession: () => ({ data: sessionAtual.valor, status: "authenticated" }),
}))

import { SessionSync } from "@/app/components/providers"

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
