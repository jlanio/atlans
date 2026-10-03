"use client"
import { useEffect, useReducer, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflow } from "@/service/types"

/**
 * Cache by hash, at module level (and not in a component ref): going down and
 * back via the breadcrumb remounts the viewer, and without this every step would
 * redo the same fetch. A sub-workflow is read often and edited rarely — and the
 * reload button provides the way out for the rare case.
 *
 * Ceiling because the session is long and a definition is not small: without it,
 * visiting many sub-workflows holds all of them in memory until the page reloads.
 * Evicts the oldest, which in a drill-down is the level already left behind.
 */
const cache = new Map<string, IWorkflow>()
const MAX_EM_CACHE = 12

function guardar(hash: string, workflow: IWorkflow) {
  if (cache.size >= MAX_EM_CACHE) {
    const maisAntigo = cache.keys().next().value
    if (maisAntigo !== undefined) cache.delete(maisAntigo)
  }
  cache.set(hash, workflow)
}

export interface SubflowDefinition {
  workflow: IWorkflow | null
  carregando: boolean
  erro: string | null
  recarregar(): void
}

/**
 * Loads a sub-workflow's workflow by hash.
 *
 * `workflow` is read from the cache on render, and not kept in state: kept, it
 * survived the level change and the viewer drew the PREVIOUS level's graph
 * while the new one loaded — made worse by the caveats, which, comparing the
 * new level's events against the old graph, flagged every node as "no longer
 * in the graph". Reading from the cache, either the right graph is already
 * there, or there is no graph — and the screen shows that it is loading.
 *
 * No new endpoint: `GET /workflows/{hash}` already returns the definition, and
 * its authorization covers the case — a sub-workflow can only be called from
 * within the parent's workspace (validate_subworkflow_references_against_db), so
 * whoever reaches the parent reaches the child.
 */
export function useSubflowDefinition(workflowHash: string | null): SubflowDefinition {
  // Only to repaint when the fetch populates the cache — the data itself comes from the Map.
  const [, repintar] = useReducer((n: number) => n + 1, 0)
  const [versao, setVersao] = useState(0)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const workflow = workflowHash ? cache.get(workflowHash) ?? null : null

  useEffect(() => {
    if (!workflowHash || cache.has(workflowHash)) {
      setCarregando(false)
      setErro(null)
      return
    }

    let cancelado = false
    setCarregando(true)
    setErro(null)

    GisFlowService.getWorkflowById(workflowHash).then(res => {
      if (cancelado) return
      setCarregando(false)
      if (res?.error || !res?.data) {
        setErro(res?.error?.message ?? "Não foi possível carregar o sub-fluxo.")
        return
      }
      guardar(workflowHash, res.data)
      repintar()
    })

    return () => { cancelado = true }
  }, [workflowHash, versao])

  return {
    workflow,
    carregando,
    erro,
    recarregar: () => {
      if (workflowHash) cache.delete(workflowHash)
      setVersao(v => v + 1)
    },
  }
}
