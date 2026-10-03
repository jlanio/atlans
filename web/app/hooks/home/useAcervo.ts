"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import {
  normalizarArtefato, normalizarArquivoDoDrive, type ItemDoAcervo,
} from "@/app/components/home/artefatos/normalizar"

/** Which of the two sources went down while the other stayed up — degradation
 *  is per source, and each half needs its own notice (before, only Drive had one). */
export interface AvisosDoAcervo {
  artefatos: boolean
  drive: boolean
}

export interface UseAcervo {
  itens: ItemDoAcervo[]
  /** Only the FIRST load (the skeleton). A reload does not turn it back on. */
  carregando: boolean
  /** Reload in flight over the list already on screen — becomes `aria-busy`, not a skeleton. */
  atualizando: boolean
  /** An accepted load has already happened. The error block only takes over the list before that (§3). */
  jaCarregou: boolean
  /** Only when BOTH sources fail. */
  erro: string | null
  avisos: AvisosDoAcervo
  /** How many items the server says exist across both sources combined; `null`
   *  when one of them failed and they cannot be added up. */
  total: number | null
  recarregar: () => void
  /** Removes (optimistically) the item from the list after the backend confirms. */
  remover: (item: ItemDoAcervo) => Promise<boolean>
}

const LIMITE = 200

const SEM_AVISOS: AvisosDoAcervo = { artefatos: false, drive: false }

/**
 * The current workspace's collection: run artifacts + Drive files in the same
 * list (decision 8). Two ready-made endpoints, each with its own auth — the merge
 * happens on the client, via `Promise.allSettled`, so that the failure of ONE
 * source does not take down the other (Drive being down does not make the
 * artifacts vanish). Sorted by date, most recent first. With no active
 * workspace, an empty list.
 *
 * State precedence from §3 of the screen patterns: a reload that fails does NOT
 * erase what is already on screen. The list `set`s only happen when at least
 * one source responded; on total failure only `erro` is left, which the list
 * shows as an amber notice when there was already content and as a block only
 * on the first load.
 */
export function useAcervo(workspaceId: string | null | undefined): UseAcervo {
  const [itens, setItens] = useState<ItemDoAcervo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [jaCarregou, setJaCarregou] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [avisos, setAvisos] = useState<AvisosDoAcervo>(SEM_AVISOS)
  const [total, setTotal] = useState<number | null>(null)
  const geracao = useRef(0)
  // Mirrors `jaCarregou` so the callback can decide skeleton × `aria-busy`
  // without entering the dependencies (`recarregar` must be stable so the
  // effect does not re-fire on every load).
  const jaCarregouRef = useRef(false)

  const recarregar = useCallback(() => {
    if (!workspaceId) {
      setItens([]); setErro(null); setAvisos(SEM_AVISOS); setTotal(null)
      setCarregando(false); setAtualizando(false)
      return
    }
    const minha = ++geracao.current
    if (jaCarregouRef.current) setAtualizando(true)
    else setCarregando(true)
    Promise.allSettled([
      GisFlowService.getArtifacts({ workspace_id: workspaceId, limit: LIMITE }),
      GisFlowService.getDriveFiles({ workspace_id: workspaceId, page_size: LIMITE }),
    ]).then(([resArt, resDrive]) => {
      if (minha !== geracao.current) return
      const acervo: ItemDoAcervo[] = []
      let artOk = false
      let driveOk = false
      let totalArt = 0
      let totalDrive = 0
      if (resArt.status === "fulfilled" && resArt.value.success && resArt.value.data) {
        artOk = true
        totalArt = resArt.value.data.total ?? resArt.value.data.items.length
        for (const a of resArt.value.data.items) acervo.push(normalizarArtefato(a))
      }
      if (resDrive.status === "fulfilled" && resDrive.value.success && resDrive.value.data) {
        driveOk = true
        totalDrive = resDrive.value.data.total ?? resDrive.value.data.items.length
        for (const f of resDrive.value.data.items) acervo.push(normalizarArquivoDoDrive(f))
      }
      if (artOk || driveOk) {
        // Most recent first; undated last. `ordenadoEm` is the last content
        // write in Drive — the same order /drive shows.
        acervo.sort((x, y) => (y.ordenadoEm ?? "").localeCompare(x.ordenadoEm ?? ""))
        setItens(acervo)
        setErro(null)
        setTotal(artOk && driveOk ? totalArt + totalDrive : null)
        jaCarregouRef.current = true
        setJaCarregou(true)
      } else {
        // Total failure: keep the previous list (§3) and only signal the failure.
        setErro("Não foi possível carregar o acervo.")
      }
      setAvisos({ artefatos: !artOk && driveOk, drive: artOk && !driveOk })
      setCarregando(false)
      setAtualizando(false)
    })
  }, [workspaceId])

  // Switching workspaces is a NEW list: clear what was there and the skeleton
  // comes back. `recarregar` only changes identity when `workspaceId` changes,
  // so this effect does not fire on a manual reload (the "Tentar de novo" (try
  // again) button).
  useEffect(() => {
    jaCarregouRef.current = false
    setJaCarregou(false)
    setItens([])
    setTotal(null)
    recarregar()
  }, [recarregar])

  const remover = useCallback(async (item: ItemDoAcervo) => {
    const res = item.fonte === "artefato"
      ? await GisFlowService.deleteArtifact(item.id)
      : await GisFlowService.deleteDriveFile(item.id)
    if (res.success) {
      setItens((atual) => atual.filter((i) => i.chave !== item.chave))
      // The total comes from the server and feeds the "showing N of M": without
      // subtracting, the cutoff line would start lying right after a deletion.
      setTotal((t) => (t == null ? t : Math.max(0, t - 1)))
      return true
    }
    return false
  }, [])

  return { itens, carregando, atualizando, jaCarregou, erro, avisos, total, recarregar, remover }
}
