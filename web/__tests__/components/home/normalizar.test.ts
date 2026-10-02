import { describe, it, expect } from "vitest"
import {
  normalizarArtefato, normalizarArquivoDoDrive, estadoDoAcervo,
} from "@/app/components/home/artefatos/normalizar"
import { textosDe } from "@/app/components/home/i18n"
import type { IArtifactItem, IDriveFile } from "@/service/types"

/**
 * O normalizador do acervo é puro: junta artefato e arquivo do Drive numa forma
 * só, decide a escada de estado (local > efêmero > permanente) e o "adicionável
 * ao globo". Testado sem montar nada.
 */

function artefato(extra: Partial<IArtifactItem> = {}): IArtifactItem {
  return {
    id_hash: "art-1", workspace_id: "ws-1", workflow_id: "wf-1", workflow_name: "Fluxo",
    run_id: "run-1", node_id: "n1", output_key: "out", filename: "saida.geojson",
    format: "geojson", size_bytes: 1234, features: 5,
    protected: false, is_published: false, is_portal_active: false, is_pinned: false,
    executor_id: null, content_location: "minio",
    created_at: "2026-09-10T12:00:00Z", expires_at: null,
    ...extra,
  }
}

function arquivo(extra: Partial<IDriveFile> = {}): IDriveFile {
  return {
    id_hash: "drv-1", workspace_id: "ws-1", original_name: "dados.geojson",
    extension: "geojson", mime_type: "application/geo+json", size: 999,
    uploaded_by: "u1", created_at: "2026-09-09T12:00:00Z", updated_at: null,
    content_written_at: null, content_location: "minio", content_executor_id: null,
    spatial_metadata: null,
    ...extra,
  }
}

describe("estadoDoAcervo", () => {
  it("permanente quando não expira e está na nuvem", () => {
    expect(estadoDoAcervo({ content_location: "minio", expires_at: null })).toBe("permanente")
  })
  it("efêmero quando tem expires_at", () => {
    expect(estadoDoAcervo({ content_location: "minio", expires_at: "2027-01-01T00:00:00Z" })).toBe("efemero")
  })
  it("local vence, mesmo com expires_at", () => {
    // A escada: local > efêmero. Um artefato no executor com prazo é LOCAL.
    expect(estadoDoAcervo({ content_location: "executor", expires_at: "2027-01-01T00:00:00Z" })).toBe("local")
  })
})

describe("normalizarArtefato", () => {
  it("geojson permanente é adicionável ao globo", () => {
    const i = normalizarArtefato(artefato())
    expect(i.fonte).toBe("artefato")
    expect(i.estado).toBe("permanente")
    expect(i.adicionavel).toBe(true)
    expect(i.chave).toBe("art:art-1")
    expect(i.formato).toBe("geojson")
  })

  it("geojson com prazo é efêmero e ainda adicionável", () => {
    const i = normalizarArtefato(artefato({ expires_at: "2027-01-01T00:00:00Z" }))
    expect(i.estado).toBe("efemero")
    expect(i.expiresAt).toBe("2027-01-01T00:00:00Z")
    expect(i.adicionavel).toBe(true)
  })

  it("artefato no executor é local e NÃO adicionável (sem bytes na nuvem)", () => {
    const i = normalizarArtefato(artefato({ content_location: "executor", executor_id: "exec-9" }))
    expect(i.estado).toBe("local")
    expect(i.adicionavel).toBe(false)
    expect(i.executorId).toBe("exec-9")
  })

  it("shapefile não publicado NÃO é adicionável, e diz por quê", () => {
    const i = normalizarArtefato(artefato({ format: "shapefile", filename: "s.zip" }))
    expect(i.adicionavel).toBe(false)
    expect(i.motivo).toBe("formatoSemPrevia")
  })

  it("publicado COM camada de portal é adicionável (vira MVT)", () => {
    const i = normalizarArtefato(artefato({ format: "json", is_published: true, is_portal_active: true }))
    expect(i.adicionavel).toBe(true)
    expect(i.motivo).toBeNull()
  })

  it("publicado SEM camada de portal NÃO é adicionável — o backend recusaria", () => {
    // `is_portal_active` é o casamento (is_published E o run tem PortalLayer)
    // que o endpoint da camada refaz: por `is_published` a lista prometia uma
    // prévia que voltaria "indisponível".
    const i = normalizarArtefato(artefato({ format: "json", is_published: true }))
    expect(i.adicionavel).toBe(false)
    expect(i.motivo).toBe("semCamadaNoPortal")
  })

  it.each(["png", "jpg", "jpeg", "pdf"])("a carta imagem (%s) NÃO é adicionável e o motivo manda baixar", (formato) => {
    const i = normalizarArtefato(artefato({ format: formato, filename: `carta.${formato}` }))
    expect(i.adicionavel).toBe(false)
    expect(i.motivo).toBe("cartaImagem")
    // A frase que a lista mostra para esse motivo.
    const frase = textosDe("pt-BR").listas.artefatos.semPrevia.cartaImagem
    expect(frase).toMatch(/carta imagem/)
    expect(frase).toMatch(/baixe/)
    // Nem "publique o mapa": publicar não poria uma imagem no globo.
    expect(frase).not.toMatch(/publique/)
  })

  it("o motivo do artefato local fala do executor, não do formato", () => {
    const i = normalizarArtefato(artefato({ content_location: "executor", executor_id: "e1" }))
    expect(i.motivo).toBe("executor")
  })
})

describe("normalizarArquivoDoDrive", () => {
  it("arquivo do Drive é permanente (sem expires_at) e NUNCA adicionável", () => {
    const i = normalizarArquivoDoDrive(arquivo())
    expect(i.fonte).toBe("drive")
    expect(i.estado).toBe("permanente")
    expect(i.expiresAt).toBeNull()
    expect(i.adicionavel).toBe(false) // Drive não vai ao globo na v1
    expect(i.motivo).toBe("drive")
    expect(i.chave).toBe("drv:drv-1")
    expect(i.nome).toBe("dados.geojson")
  })

  it("arquivo no executor é local nos dois tipos", () => {
    const i = normalizarArquivoDoDrive(arquivo({ content_location: "executor", content_executor_id: "exec-3" }))
    expect(i.estado).toBe("local")
    expect(i.executorId).toBe("exec-3")
  })

  it("ordena pela última escrita de conteúdo, não pela criação", () => {
    // O que /drive mostra no topo: um arquivo antigo sobrescrito hoje.
    const i = normalizarArquivoDoDrive(arquivo({ content_written_at: "2026-09-18T09:00:00Z" }))
    expect(i.ordenadoEm).toBe("2026-09-18T09:00:00Z")
  })

  it("sem content_written_at cai no created_at", () => {
    expect(normalizarArquivoDoDrive(arquivo()).ordenadoEm).toBe("2026-09-09T12:00:00Z")
  })
})
