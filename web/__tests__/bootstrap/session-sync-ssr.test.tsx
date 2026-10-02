// @vitest-environment node
/**
 * SEG: o access_token do usuário não pode ser escrito no servidor.
 *
 * `setAuthToken` grava numa variável de MÓDULO do GisFlowService. No browser ela
 * é por-aba; no Node ela é por-PROCESSO, compartilhada por todas as requisições
 * em voo. Desde que o SessionProvider passou a receber a sessão resolvida no
 * servidor, o corpo de render do SessionSync roda no SSR já com o token real:
 * o render do usuário A gravava o token de A e o de B, concorrente, sobrescrevia
 * com o de B — vazamento de credencial entre usuários, legível pelo
 * interceptor do axios.
 *
 * Este teste roda em ambiente `node` de propósito: é a ausência de `window` que
 * caracteriza o SSR.
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
  // Com a sessão vinda do servidor, `useSession()` JÁ devolve dados no SSR.
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
