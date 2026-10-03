/**
 * `useArtifactsQuery` — what the hook guarantees to whoever receives it, beyond what the
 * screen shows (that is in tela-de-artefatos.test.tsx).
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import { QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { IArtifactItem } from "@/service/types"

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getArtifacts: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { criarClienteDeConsultas } from "@/lib/consultas"
import { PAGE_SIZE, useArtifactsQuery } from "@/app/(dashboard)/artifacts/use-artifacts-query"

const getArtifacts = vi.mocked(GisFlowService.getArtifacts)

function artefato(id: string): IArtifactItem {
  return {
    id_hash: id, workspace_id: "ws-a", workflow_id: null, workflow_name: "Bacias",
    run_id: `run-${id}`, node_id: null, output_key: "saida", filename: `${id}.geojson`,
    format: "geojson", size_bytes: 1, features: 1, protected: false, is_published: false,
    is_portal_active: false, is_pinned: false, executor_id: null,
    created_at: null, expires_at: null,
  }
}

function embrulho() {
  const cliente = criarClienteDeConsultas()
  return function Embrulho({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={cliente}>{children}</QueryClientProvider>
  }
}

beforeEach(() => {
  getArtifacts.mockReset()
  getArtifacts.mockImplementation(async (p = {}) => {
    const de = p.offset ?? 0
    const n = Math.max(0, Math.min(p.limit ?? PAGE_SIZE, 120 - de))
    const items = Array.from({ length: n }, (_, i) => artefato(`a${de + i}`))
    return { success: true, status: 200, data: { items, total: 120 } }
  })
})

describe("useArtifactsQuery", () => {
  it("loadMore e reload mantêm a identidade de uma página para a outra", async () => {
    // It is what `useExecucoes` solves with the offset in a ref, so the memoized
    // `TabelaExecucoes` does not re-render entirely on every page: a
    // handler changing identity defeats the memo exactly when the table
    // is largest.
    const { result } = renderHook(
      () => useArtifactsQuery({ kind: "execution", search: "", workspaceId: "ws-a", enabled: true }),
      { wrapper: embrulho() },
    )
    await waitFor(() => expect(result.current.items).toHaveLength(50))
    const { loadMore, reload } = result.current

    act(() => { result.current.loadMore() })
    await waitFor(() => expect(result.current.items).toHaveLength(100))

    expect(result.current.loadMore).toBe(loadMore)
    expect(result.current.reload).toBe(reload)
  })
})
