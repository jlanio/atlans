// web/app/components/home/artefatos/normalizar.ts
//
// The Home's unified collection: run artifacts and Drive files in the SAME list,
// distinguished ONLY by icon (decision 8). This module is PURE — it joins the
// backend's two shapes (`IArtifactItem`, `IDriveFile`) into a single
// `ItemDoAcervo` and decides the item's state. No React, no fetch: the state
// ladder and the "addable to the globe" can be tested without mounting anything.
//
// The reason an item doesn't go to the globe is decided HERE, as a key
// (`motivo`); the sentence belongs to the dictionary. The Home list translates
// by key at display time — the collection is stored in the hook, and switching
// language in Preferences must not leave the sentence in the old language.

import type { IArtifactItem, IDriveFile } from "@/service/types"
import { isLocalDoExecutor } from "@/app/components/local-badge"

export type FonteDoAcervo = "artefato" | "drive"

/** Why an item does NOT go to the globe — the keys of `listas.artefatos.semPrevia`. */
export type MotivoSemPrevia =
  | "executor"
  | "cartaImagem"
  | "semCamadaNoPortal"
  | "formatoSemPrevia"
  | "drive"

/**
 * The state that decides the icon (decision 8). Ladder, in this order:
 * - `local`: the content stayed on the executor and never went up to the cloud
 *   (no download, no preview) — applies to artifacts AND Drive files.
 * - `efemero`: has `expires_at` (artifacts only; the Drive is permanent).
 * - `permanente`: the rest (Drive, or an artifact without expiration).
 */
export type EstadoDoAcervo = "local" | "efemero" | "permanente"

export interface ItemDoAcervo {
  /** Unique key in the list (the source + the id — the two id spaces are disjoint
   *  in practice, but the prefix guarantees it). */
  chave: string
  id: string
  fonte: FonteDoAcervo
  nome: string
  /** geojson | json | csv | shapefile | ... (lowercase). */
  formato: string
  estado: EstadoDoAcervo
  /** Only when ephemeral (the Drive never has it). */
  expiresAt: string | null
  executorId: string | null
  /**
   * The date that SORTS the list — in the Drive it is the last CONTENT write, not
   * the row's creation. It is the same `coalesce` the server uses to sort
   * /drive: an eight-month-old `.gpkg` overwritten today by GeoSync needs to rise
   * to the top, and by `created_at` it sank among the old files — on two
   * screens with different orders for the same files.
   */
  ordenadoEm: string | null
  workspaceId: string | null
  /** Can go to the globe: only a geojson artifact or one with a live portal layer,
   *  and never local (`camadaDoGlobo` is an ARTIFACT endpoint — Drive files are
   *  not included in v1). */
  adicionavel: boolean
  /** Why it does NOT go to the globe — `null` when it does. It is by key that the
   *  list says the sentence in the current language. The reason is the only text
   *  the inert row has to offer, and "sem prévia no globo" alone described the
   *  most common case poorly (content parked on the executor). */
  motivo: MotivoSemPrevia | null
  driveFile?: IDriveFile
}

/** The state ladder, isolated for direct testing. */
export function estadoDoAcervo(
  item: { content_location?: string | null; expires_at?: string | null },
): EstadoDoAcervo {
  if (isLocalDoExecutor(item)) return "local"
  if (item.expires_at) return "efemero"
  return "permanente"
}

/**
 * An artifact can go to the globe when it is geojson OR has a live portal layer
 * (becomes MVT), and never when it is local (no bytes in the cloud to fetch).
 *
 * `is_published` alone is NOT enough: the layer endpoint matches the artifact to
 * a `PortalLayer` of that run and returns "indisponível" (unavailable) when it
 * doesn't find one (agente_camadas_router). `is_portal_active` is exactly that
 * match, already done on the server (`is_published` AND the run has a layer) —
 * offering "Exibir no globo" based on `is_published` promised a preview the
 * backend would refuse.
 *
 * Also returns the refusal reason's key: its sentence is the text the inert
 * row displays.
 */
const FORMATOS_DE_IMAGEM = new Set(["png", "jpg", "jpeg", "pdf"])

function previaDoArtefato(a: IArtifactItem): { adicionavel: boolean; motivo: MotivoSemPrevia | null } {
  if (isLocalDoExecutor(a)) return { adicionavel: false, motivo: "executor" }
  const formato = (a.format ?? "").toLowerCase()
  if (formato === "geojson") return { adicionavel: true, motivo: null }
  if (FORMATOS_DE_IMAGEM.has(formato)) {
    // The image map (CartaImagem node) is a file to download: not even publishing
    // it to the portal would put it on the globe, so the generic sentence
    // ("publique o mapa") would lie.
    return { adicionavel: false, motivo: "cartaImagem" }
  }
  if (a.is_portal_active) return { adicionavel: true, motivo: null }
  if (a.is_published) return { adicionavel: false, motivo: "semCamadaNoPortal" }
  return { adicionavel: false, motivo: "formatoSemPrevia" }
}

export function normalizarArtefato(a: IArtifactItem): ItemDoAcervo {
  const previa = previaDoArtefato(a)
  return {
    chave: `art:${a.id_hash}`,
    id: a.id_hash,
    fonte: "artefato",
    nome: a.filename,
    formato: (a.format ?? "").toLowerCase(),
    estado: estadoDoAcervo(a),
    expiresAt: a.expires_at,
    executorId: a.executor_id,
    // A run artifact is not overwritten: creation and sort order coincide.
    ordenadoEm: a.created_at,
    workspaceId: a.workspace_id,
    adicionavel: previa.adicionavel,
    motivo: previa.motivo,
  }
}

export function normalizarArquivoDoDrive(f: IDriveFile): ItemDoAcervo {
  return {
    chave: `drv:${f.id_hash}`,
    id: f.id_hash,
    fonte: "drive",
    nome: f.original_name,
    formato: (f.extension ?? "").toLowerCase(),
    estado: estadoDoAcervo(f), // Drive has no expires_at → local or permanent
    expiresAt: null,
    executorId: f.content_executor_id ?? null,
    // Sorts by the last content write, as the server sorts /drive.
    ordenadoEm: f.content_written_at ?? f.created_at,
    workspaceId: f.workspace_id,
    adicionavel: false, // a Drive file never goes to the globe in v1
    motivo: "drive",
    driveFile: f,
  }
}
