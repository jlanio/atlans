import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

// O download da tabela de artefatos: a variante SEGURA busca a URL pré-assinada
// pelo `getArtifactDownload` (Bearer → respeita `protected`) e NAVEGA até ela,
// sem puxar o arquivo inteiro para um blob em memória (o `revokeObjectURL`
// síncrono abortava downloads grandes no Firefox/Safari).
const getArtifactDownload = vi.fn()
const getArtifactDownloadUrl = vi.fn((..._a: unknown[]) => "https://plataforma/artifacts/a1/download")
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getArtifactDownload: (...a: unknown[]) => getArtifactDownload(...a),
    getArtifactDownloadUrl: (...a: unknown[]) => getArtifactDownloadUrl(...a),
  },
}))

import { ArtifactTable } from "@/app/components/artifacts/tabela"
import type { IArtifactItem } from "@/service/types"

const item = (over: Partial<IArtifactItem> = {}): IArtifactItem =>
  ({
    id_hash: "a1", filename: "focos.geojson", workflow_name: "WF", run_id: "run123456",
    output_key: "focos", format: "geojson", executor_id: null, is_pinned: false,
    protected: false, features: 10, size_bytes: 1234, created_at: "2026-09-20T00:00:00Z",
    expires_at: null, content_location: "minio", is_published: false, is_portal_active: false,
    ...over,
  }) as unknown as IArtifactItem

beforeEach(() => {
  getArtifactDownload.mockReset()
  getArtifactDownloadUrl.mockReset().mockReturnValue("https://plataforma/artifacts/a1/download")
  vi.stubGlobal("open", vi.fn())
  vi.stubGlobal("fetch", vi.fn())
})

function renderTabela(it: IArtifactItem) {
  return render(
    <ArtifactTable
      items={[it]}
      tab="execution"
      selected={new Set()}
      isOwner
      onToggle={() => {}}
      onToggleAll={() => {}}
    />,
  )
}

describe("download de artefato — navega para a URL pré-assinada, sem blob", () => {
  it("clicar Download abre a URL pré-assinada (via getArtifactDownload) e NÃO bufferiza em fetch", async () => {
    getArtifactDownload.mockResolvedValue({
      error: null,
      data: { download_url: "https://s3/presigned?sig=x", filename: "focos.geojson" },
    })
    renderTabela(item())

    fireEvent.click(screen.getByRole("button", { name: /Download/ }))

    await waitFor(() =>
      expect(window.open).toHaveBeenCalledWith("https://s3/presigned?sig=x", "_blank"),
    )
    // A variante segura não puxa o arquivo inteiro para um blob (o bug do PR).
    expect(fetch).not.toHaveBeenCalled()
    // E respeita o Bearer: passou pelo getArtifactDownload, não pelo endpoint público.
    expect(getArtifactDownload).toHaveBeenCalledWith("a1")
  })
})
