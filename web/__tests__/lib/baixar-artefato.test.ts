import { describe, it, expect, vi, beforeEach } from "vitest"

const servico = vi.hoisted(() => ({ getArtifactDownload: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

import { baixarArtefato } from "@/lib/baixar-artefato"

const abrir = vi.fn()
beforeEach(() => {
  servico.getArtifactDownload.mockReset()
  abrir.mockReset()
  vi.stubGlobal("open", abrir)
})

describe("baixarArtefato", () => {
  it("abre a URL PRÉ-ASSINADA, não o endpoint da plataforma", () => {
    // The endpoint returns `{download_url, filename}` as JSON: opening it in a tab
    // showed the JSON instead of downloading, and top-level navigation doesn't carry the Bearer.
    servico.getArtifactDownload.mockResolvedValue({
      success: true, status: 200, data: { download_url: "https://minio/a1.geojson?sig=x", filename: "a1.geojson" },
    })
    return baixarArtefato("a1").then((erro) => {
      expect(erro).toBeNull()
      expect(abrir).toHaveBeenCalledWith("https://minio/a1.geojson?sig=x", "_blank")
    })
  })

  it("409 é POLÍTICA, e a frase diz isso em vez de mandar tentar de novo", async () => {
    servico.getArtifactDownload.mockResolvedValue({ success: false, status: 409, error: { name: "AxiosError" } })
    expect(await baixarArtefato("a1")).toMatch(/permanece no executor/i)
    expect(abrir).not.toHaveBeenCalled()
  })

  it("outro erro devolve a mensagem do servidor", async () => {
    servico.getArtifactDownload.mockResolvedValue({
      success: false, status: 404, error: { name: "AxiosError", message: "Arquivo nao encontrado no storage." },
    })
    expect(await baixarArtefato("a1")).toBe("Arquivo nao encontrado no storage.")
  })

  it("sucesso sem download_url não abre aba nenhuma", async () => {
    servico.getArtifactDownload.mockResolvedValue({ success: true, status: 200, data: {} })
    expect(await baixarArtefato("a1")).toBeTruthy()
    expect(abrir).not.toHaveBeenCalled()
  })
})
