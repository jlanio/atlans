import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

// The artifacts table download: the SAFE variant fetches the presigned URL
// through `getArtifactDownload` (Bearer → respects `protected`) and NAVIGATES to
// it, without pulling the whole file into an in-memory blob (the synchronous
// `revokeObjectURL` aborted large downloads on Firefox/Safari).
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

function renderTable(it: IArtifactItem) {
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
    renderTable(item())

    fireEvent.click(screen.getByRole("button", { name: /Download/ }))

    await waitFor(() =>
      expect(window.open).toHaveBeenCalledWith("https://s3/presigned?sig=x", "_blank"),
    )
    // The safe variant doesn't pull the whole file into a blob (the PR's bug).
    expect(fetch).not.toHaveBeenCalled()
    // And it respects the Bearer: it went through getArtifactDownload, not the public endpoint.
    expect(getArtifactDownload).toHaveBeenCalledWith("a1")
  })
})
