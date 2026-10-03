"use client"

// web/app/hooks/home/useAnexos.ts
//
// Files dropped on the Home, on their way to the workspace Drive.
//
// **Why this exists.** The `/drive` screen has always had the upload zone,
// but the middleware sends anyone who does not administer the system back to
// `/` (`web/proxy.ts`), so in practice a regular user never reached an
// upload field. The Home is their only page — and the house rule sends every
// visual flow into it.
//
// **The filters are the same, and it is the server that applies them.**
// Allowed extension, dangerous inner extension (`notas.sh.csv`), size ceiling
// in MB, empty file and workspace role all live in the backend
// (`drive_service.py`, `drive_router.py`), apply to any upload path and are
// not rewritten here: this hook sends the file and translates the rejection
// with the SAME `classifyUploadError` as the `/drive` screen — by the code the
// server sends, not by the sentence. Two copies of the rule would diverge —
// and the wrong one would be the client's, which is the one the person reads.
//
// The only thing judged BEFORE sending is the workspace role, because it is
// already on the client (`useWorkspace().canEdit`, the mirror of the `editor`
// role that Drive requires): uploading a whole file to reap a 403 that could
// have been predicted wastes the network of the person on the other end.

import { useCallback } from "react"

import { classifyUploadError } from "@/app/components/drive/resultado-upload"
import { useHomeStore, type Anexo } from "@/app/stores/homeStore"
import { GisFlowService } from "@/service/GisFlowService"
import { useTexts } from "@/app/components/home/i18n"

/** How many files a single gesture can bring. Beyond that it is a mistake. */
export const MAX_PER_GESTURE = 10

// Sequence of chip ids. **MODULE-level, not a `useRef`**: the attachments live
// in the store (persists), but a `useRef` resets when HomeView unmounts and
// remounts (the admin leaves `/` and comes back). If an `anexo-0` were left in
// the store, the next gesture would create another `anexo-0` — a duplicate
// React key and an `atualizarAnexo` that would match BOTH rows. A module
// counter is monotonic for the life of the tab, so it never collides.
let _sequence = 0

export interface UseAttachments {
  /** Receives what was dropped (or chosen in the picker) and takes it to Drive. */
  receber: (arquivos: File[]) => void
}

export function useAnexos({
  workspaceId,
  podeEnviar,
  anonimo,
  aoExigirLogin,
  aoAvisar,
}: {
  /** The Home's active workspace. `null` while the list has not arrived. */
  workspaceId: string | null
  /** `canEdit` of the active workspace: the mirror of the `editor` role that Drive requires. */
  podeEnviar: boolean
  /** Without a session the Home opens anonymous — dragging asks for sign-in. */
  anonimo: boolean
  aoExigirLogin: () => void
  /** Rejections that never even become a chip (no workspace, no role, large batch). */
  aoAvisar: (titulo: string, detalhe?: string) => void
}): UseAttachments {
  // Store actions only: this hook does not READ the attachments (the bar and
  // the panel draw them), so it does not subscribe to them — that way it does
  // not re-render the Home on every byte of progress.
  const adicionarAnexos = useHomeStore((s) => s.adicionarAnexos)
  const atualizarAnexo = useHomeStore((s) => s.atualizarAnexo)
  const t = useTexts().assistente.anexos

  const receber = useCallback((arquivos: File[]) => {
    if (arquivos.length === 0) return

    if (anonimo) {
      aoExigirLogin()
      return
    }
    if (!workspaceId) {
      aoAvisar(t.semWorkspace, t.semWorkspaceDica)
      return
    }
    if (!podeEnviar) {
      aoAvisar(t.semPapel, t.semPapelDica)
      return
    }

    const lote = arquivos.slice(0, MAX_PER_GESTURE)
    if (arquivos.length > lote.length) {
      aoAvisar(t.lote(MAX_PER_GESTURE), t.loteDica(arquivos.length))
    }

    // The id cannot come from the name: dropping the same file twice is legitimate
    // (the person fixed the content and dropped it again) and the two rows must
    // exist separately.
    const novos: Anexo[] = lote.map((arquivo) => ({
      id: `anexo-${_sequence++}`,
      nome: arquivo.name,
      bytes: arquivo.size,
      estado: "enviando",
    }))
    adicionarAnexos(novos)

    // Serially, as the `/drive` screen always did: in parallel, ten large files
    // compete for the same bandwidth and all take longer — and the server
    // accumulates each body in the worker's memory while reading.
    void (async () => {
      for (let i = 0; i < lote.length; i++) {
        const arquivo = lote[i]
        const { id } = novos[i]
        const res = await GisFlowService.uploadDriveFile(workspaceId, arquivo)
        if (res.error) {
          atualizarAnexo(id, {
            estado: "recusado",
            motivo: res.error.message ?? t.naoEnviou(arquivo.name),
            tipo: classifyUploadError(res.status, res.error.code),
          })
        } else {
          atualizarAnexo(id, { estado: "pronto" })
        }
      }
    })()
  }, [anonimo, workspaceId, podeEnviar, aoExigirLogin, aoAvisar, adicionarAnexos, atualizarAnexo, t])

  return { receber }
}
