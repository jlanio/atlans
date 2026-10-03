import { describe, it, expect, vi, afterEach } from "vitest"
import { cleanup, render, screen, within } from "@testing-library/react"
import type { IDriveFile } from "@/service/types"

/**
 * The pieces from outside the Home that the lists use — the content-on-executor
 * mark, the Drive metadata dialog and the download error — in the Home's
 * language. Without the texts they stay in the usual Portuguese (the Drive and the
 * Artifacts table do not pass them), and the dictionary's Portuguese is the SAME
 * text as their defaults.
 */
const H = vi.hoisted(() => ({ getArtifactDownload: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getArtifactDownload: (...a: unknown[]) => H.getArtifactDownload(...a) },
}))

import { LocalBadge, TEXTOS_DO_LOCAL_PT } from "@/app/components/local-badge"
import { MetadataDialog, TEXTOS_DOS_METADADOS_PT } from "@/app/components/drive/dialogs"
import { baixarArtefato, TEXTOS_DO_DOWNLOAD_PT } from "@/lib/baixar-artefato"
import { RETENCAO_EM_PORTUGUES } from "@/app/components/artifacts/badges"
import { TEXTOS_DO_RESULTADO_PT } from "@/app/components/drive/resultado-upload"
import { textosDe } from "@/app/components/home/i18n"
import { FORMATOS } from "@/app/components/home/i18n/formatos"
import { formatLocal } from "@/lib/dayjs"

afterEach(cleanup)

const arquivo: IDriveFile = {
  id_hash: "drv-1", workspace_id: "ws-1", original_name: "municipios.shp",
  extension: "shp", mime_type: null, size: 2048,
  uploaded_by: "u1", created_at: "2026-09-08T12:00:00Z", updated_at: null,
  content_written_at: null, content_location: "executor", content_executor_id: "exec-1234567890",
  spatial_metadata: {
    geometry_type: "Polygon", crs: "EPSG:4674", feature_count: 5570, columns: ["a", "b"],
    bbox: [-73.99, -33.75, -28.84, 5.27],
  },
}

describe("o português do dicionário é o dos componentes", () => {
  const pt = textosDe("pt-BR").listas.artefatos

  it("a marca do executor", () => {
    expect(pt.local.rotulo).toBe(TEXTOS_DO_LOCAL_PT.rotulo)
    for (const id of ["exec-1234567890", null, undefined]) {
      expect(pt.local.titulo(id)).toBe(TEXTOS_DO_LOCAL_PT.titulo(id))
    }
  })

  it("o diálogo de metadados e o download", () => {
    const { fechar, inteiro, dataEHora, ...frases } = TEXTOS_DOS_METADADOS_PT
    const { executor, ...resto } = frases
    const { executor: executorDoDicionario, ...restoDoDicionario } = pt.metadadosDialogo
    expect(restoDoDicionario).toEqual(resto)
    expect(executorDoDicionario("x")).toBe(executor("x"))
    expect(fechar).toBe(textosDe("pt-BR").comum.fechar)
    expect(inteiro(5570)).toBe(FORMATOS["pt-BR"].inteiro(5570))
    expect(dataEHora(arquivo.created_at)).toBe(FORMATOS["pt-BR"].dataEHora(arquivo.created_at))
    expect(pt.download).toEqual(TEXTOS_DO_DOWNLOAD_PT)
  })

  it("a dica de retenção, montada como a lista de Artefatos da Home a monta", () => {
    const r = pt.retencao
    const fmt = FORMATOS["pt-BR"]
    expect(r.expirado).toBe(RETENCAO_EM_PORTUGUES.expirado)
    expect(r.expiraHoje).toBe(RETENCAO_EM_PORTUGUES.expiraHoje)
    for (const dias of [1, 2, 3, 1500]) {
      expect(r.expiraEm(dias, fmt.inteiro(dias))).toBe(RETENCAO_EM_PORTUGUES.expiraEm(dias))
    }
    expect(r.removidoEm(fmt.dataEHora(arquivo.created_at))).toBe(RETENCAO_EM_PORTUGUES.removidoEm(arquivo.created_at))
  })

  it("o resultado do envio (o painel das recusas do Drive)", () => {
    const { enviados, falhas, ...resto } = textosDe("pt-BR").assistente.anexos.resultado
    const { enviados: enviadosPt, falhas: falhasPt, ...restoPt } = TEXTOS_DO_RESULTADO_PT
    expect(resto).toEqual(restoPt)
    for (const n of [0, 1, 2, 1500]) {
      expect(enviados(n)).toBe(enviadosPt(n))
      expect(falhas(n)).toBe(falhasPt(n))
    }
  })

  it("a data exata em português é o formatLocal de sempre", () => {
    expect(FORMATOS["pt-BR"].dataEHora(arquivo.created_at)).toBe(formatLocal(arquivo.created_at))
  })
})

describe("em inglês", () => {
  const en = textosDe("en").listas.artefatos

  it("a marca do executor: o nome para o leitor de tela e o title", () => {
    render(<LocalBadge executorId="exec-1234567890" textos={en.local} />)
    const marca = screen.getByRole("img", { name: "Content only on the executor" })
    expect(marca.getAttribute("title")).toContain("executor exec-123…")
    expect(marca.getAttribute("title")).toContain("never uploaded to the cloud")
  })

  it("o diálogo de metadados: rótulos, números, o aviso do executor e o fechar", () => {
    render(
      <MetadataDialog
        file={arquivo}
        open
        onClose={() => {}}
        textos={{ ...en.metadadosDialogo, fechar: "Close", inteiro: FORMATOS.en.inteiro, dataEHora: FORMATOS.en.dataEHora }}
      />,
    )
    const dialogo = screen.getByRole("dialog")
    expect(within(dialogo).getByText("File metadata")).toBeTruthy()
    for (const rotulo of ["Extension", "Size", "Uploaded", "Geometry", "Features", "Columns", "Extent"]) {
      expect(within(dialogo).getByText(rotulo)).toBeTruthy()
    }
    expect(within(dialogo).getByText("5,570")).toBeTruthy()
    expect(within(dialogo).getByText("The content isn’t in the cloud.")).toBeTruthy()
    expect(within(dialogo).getByText("executor exec-1234567890")).toBeTruthy()
    // The X and the footer button.
    expect(within(dialogo).getAllByRole("button", { name: "Close" })).toHaveLength(2)
    expect(dialogo.textContent).not.toContain("Metadados")
  })

  it("o erro do download: o 409 e a falha sem mensagem no idioma; a do servidor como veio", async () => {
    H.getArtifactDownload.mockResolvedValueOnce({ success: false, status: 409 })
    expect(await baixarArtefato("a1", en.download)).toBe("This file stays on the executor and can’t be downloaded from here.")
    H.getArtifactDownload.mockResolvedValueOnce({ success: false, status: 500 })
    expect(await baixarArtefato("a1", en.download)).toBe("Try again.")
    H.getArtifactDownload.mockResolvedValueOnce({ success: false, status: 500, error: { message: "Falha no MinIO." } })
    expect(await baixarArtefato("a1", en.download)).toBe("Falha no MinIO.")
  })
})

describe("sem os textos (o Drive e a tabela de Artefatos), o português de sempre", () => {
  it("o diálogo de metadados", () => {
    render(<MetadataDialog file={arquivo} open onClose={() => {}} />)
    const dialogo = screen.getByRole("dialog")
    expect(within(dialogo).getByText("Metadados do arquivo")).toBeTruthy()
    expect(within(dialogo).getByText("Feições")).toBeTruthy()
    expect(within(dialogo).getByText("5.570")).toBeTruthy()
    expect(within(dialogo).getAllByText("Extensão")).toHaveLength(2)
    expect(within(dialogo).getByText(formatLocal(arquivo.created_at))).toBeTruthy()
    expect(within(dialogo).getAllByRole("button", { name: "Fechar" })).toHaveLength(2)
  })

  it("o download", async () => {
    H.getArtifactDownload.mockResolvedValueOnce({ success: false, status: 409 })
    expect(await baixarArtefato("a1")).toBe("Este arquivo permanece no executor e não pode ser baixado daqui.")
  })
})
