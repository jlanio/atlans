"use client"

import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { createToast } from "@/utils/createToast"
import type { IResponse } from "@/service/types"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import type { IWorkflowMetricsRow } from "@/service/types"
import { JANELA_EM_DIAS } from "./como-anda"

/**
 * Projects data (docs/specs/projects.md §3.3).
 *
 * Three calls go out together per workspace: listing, groups and metrics
 * (`/observability/metrics/workflows`, 30-day window). The first two are
 * mandatory — without them there is no shelf; the third is the "como anda"
 * column, and the list comes out complete without it, with a discreet notice.
 * No local cache: the listing is already lean and the backend keeps the
 * metrics for 45 s.
 */

export interface DadosDeProjetos {
  workflows: IWorkflow[]
  grupos: IWorkflowGroup[]
  /** By `workflow_hash`; null when the metrics failed (the column disappears). */
  metricas: Map<string, IWorkflowMetricsRow> | null
  /** First load of the workspace (skeleton). */
  carregando: boolean
  /** Subsequent reloads (the button spins, the list stays). */
  atualizando: boolean
  /** Listing or groups failed — error state with "Tentar de novo" (try again). */
  erro: string | null
  /** Only the metrics failed — discreet notice above the list. */
  metricasIndisponiveis: boolean
  /** Stamp (ms) of the last accepted response, for the "atualizado há X". */
  atualizadoEm: number | null
  /** "Atualizar" passes `force: true` to bypass the metrics cache on the backend. */
  recarregar: (opcoes?: { force?: boolean }) => void
  /** Optimistic mutations from `index` (activate, move, delete…); they accept a value or a function. */
  definirWorkflows: Dispatch<SetStateAction<IWorkflow[]>>
  definirGrupos: Dispatch<SetStateAction<IWorkflowGroup[]>>
}

/** The metrics refresh on their own at this pace while the tab is visible; the listing does not. */
export const INTERVALO_DAS_METRICAS_MS = 60_000

const ERRO_PADRAO = "Não foi possível carregar os projetos."

function mapaDeMetricas(linhas: IWorkflowMetricsRow[]): Map<string, IWorkflowMetricsRow> {
  return new Map(linhas.map(l => [l.workflow_hash, l]))
}

/** `allSettled` never rejects; neither does the service — but an unexpected `throw` must not bring down the screen. */
function resposta<T>(r: PromiseSettledResult<IResponse<T> | null>): IResponse<T> | null {
  return r.status === "fulfilled" ? r.value : null
}

function mensagemDe(...respostas: (IResponse<unknown> | null)[]): string {
  for (const r of respostas) {
    if (r?.error) return r.error.message ?? ERRO_PADRAO
  }
  return ERRO_PADRAO
}

export function useProjetosDados(opts: { intervaloDasMetricasMs?: number } = {}): DadosDeProjetos {
  const { intervaloDasMetricasMs = INTERVALO_DAS_METRICAS_MS } = opts
  const { current, loading: workspaceLoading } = useWorkspace()
  const workspaceId = current?.id_hash

  const [workflows, setWorkflows] = useState<IWorkflow[]>([])
  const [grupos, setGrupos] = useState<IWorkflowGroup[]>([])
  const [metricas, setMetricas] = useState<Map<string, IWorkflowMetricsRow> | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [metricasIndisponiveis, setMetricasIndisponiveis] = useState(false)
  const [atualizadoEm, setAtualizadoEm] = useState<number | null>(null)

  // Sequence stamp: switching workspaces twice in a row fires two loads, and
  // the slower one may respond last. Only the last load requested writes to
  // the screen.
  const seq = useRef(0)
  // Workspace whose data is ON SCREEN (`undefined` = never loaded). It is what
  // separates the skeleton (first load of this workspace) from "the button spins".
  const workspaceNaTela = useRef<string | null | undefined>(undefined)
  // `recarregar` reads the current workspace without changing identity on every
  // render (it goes down to the Atualizar button).
  const workspaceRef = useRef(workspaceId)
  workspaceRef.current = workspaceId

  // When "Atualizar" (force) wrote fresh metrics. A background tick that
  // started BEFORE that instant fetches the cached version (45 s) and, if it
  // arrives later, would overwrite the fresh with the stale — the two do not
  // change sequence (the tick does not bump `seq`). The tick checks this stamp
  // and gives up when a force has overtaken it.
  const forcadasEm = useRef(0)

  // Signature of the last accepted metrics response. The 60s tick rebuilds the
  // Map even when the payload is identical, and that identity change invalidates
  // the whole list's `useMemo`s (every row re-renders with nothing changed).
  // It only writes the state when the content actually changes.
  const assinaturaMetricas = useRef<string>("")

  const carregar = useCallback(async (alvo: string | undefined, force: boolean) => {
    const mine = ++seq.current
    const primeiraDesteWorkspace = workspaceNaTela.current !== (alvo ?? null)
    if (primeiraDesteWorkspace) setCarregando(true)
    else setAtualizando(true)

    const [rWorkflows, rGrupos, rMetricas] = await Promise.allSettled([
      // Including the assistant's: they are workflows like the others and the shelf
      // is where the person keeps track of what exists. The "Assistente" chip slices.
      GisFlowService.getWorkflows(alvo, { incluirDoAssistente: true }),
      GisFlowService.getWorkflowGroups(alvo),
      // Metrics always sliced by workspace (spec §2.3): without a workspace there
      // is nothing to slice by — and the list will come empty too.
      alvo ? GisFlowService.getWorkflowMetricsList(JANELA_EM_DIAS, force, { workspace_id: alvo }) : Promise.resolve(null),
    ])
    if (mine !== seq.current) return

    const listagem = resposta(rWorkflows)
    const gruposRes = resposta(rGrupos)
    const metricasRes = resposta(rMetricas)

    if (listagem?.data && gruposRes?.data) {
      setWorkflows(listagem.data)
      setGrupos(gruposRes.data)
      setErro(null)
      setAtualizadoEm(Date.now())
      workspaceNaTela.current = alvo ?? null
    } else {
      // What was already on screen stays (it belongs to whoever reloaded); whoever
      // switched workspaces sees the error block on top, because `erro` rules the screen.
      const mensagem = mensagemDe(listagem, gruposRes)
      setErro(mensagem)
      // With no accepted load, the error card takes over the screen and already
      // announces the failure (`role="alert"`); the toast would repeat the notice
      // to the screen reader. The toast is for a load that fails with a list
      // already on screen.
      if (workspaceNaTela.current !== undefined) createToast.error("Erro ao carregar projetos", mensagem)
    }

    if (!alvo) {
      assinaturaMetricas.current = ""
      setMetricas(new Map())
      setMetricasIndisponiveis(false)
    } else if (metricasRes?.data?.workflows) {
      if (force) forcadasEm.current = Date.now()
      // Aligns the signature so the first background tick does not re-set for nothing.
      assinaturaMetricas.current = JSON.stringify(metricasRes.data.workflows)
      setMetricas(mapaDeMetricas(metricasRes.data.workflows))
      setMetricasIndisponiveis(false)
    } else {
      // Null, and not the old map: on a workspace switch it would belong to
      // another shelf, and on a reload the spec asks for the list without the column.
      assinaturaMetricas.current = ""
      setMetricas(null)
      setMetricasIndisponiveis(true)
    }

    setCarregando(false)
    setAtualizando(false)
  }, [])

  // Reloads when switching workspaces, waiting for the context to resolve which
  // one it is — before that `current` is null and the call would bring everyone's list.
  useEffect(() => {
    if (workspaceLoading) return
    carregar(workspaceId, false)
  }, [workspaceLoading, workspaceId, carregar])

  // Only the metrics, without turning on `carregando`/`atualizando` — otherwise
  // the list would flicker every minute. It does not bump the sequence: a full
  // load requested in the middle wins.
  useEffect(() => {
    if (workspaceLoading || !workspaceId || intervaloDasMetricasMs <= 0) return
    let ultimo = Date.now()
    async function atualizarMetricas() {
      // The metrics annotate the list ON SCREEN. Without it (the 1st load failed, or
      // the new workspace's has not arrived yet), the tick has nothing to annotate,
      // and the stamp it writes took the error card off the screen: the screen
      // then said "first use" for a shelf that never even loaded.
      if (workspaceNaTela.current !== workspaceId) return
      const mine = seq.current
      const inicio = Date.now()
      ultimo = inicio
      const res = await GisFlowService.getWorkflowMetricsList(JANELA_EM_DIAS, false, { workspace_id: workspaceId })
      // Failed, arrived late (another load took over), or an "Atualizar" wrote
      // fresh data while this tick was fetching the cache: what was there stays;
      // the next tick tries again.
      if (mine !== seq.current || forcadasEm.current > inicio || !res.data?.workflows) return
      // Payload identical to the last accepted one: do not change the Map's identity,
      // so the whole list does not re-render every minute for no reason.
      const assinatura = JSON.stringify(res.data.workflows)
      if (assinatura === assinaturaMetricas.current) return
      assinaturaMetricas.current = assinatura
      setMetricas(mapaDeMetricas(res.data.workflows))
      setMetricasIndisponiveis(false)
      setAtualizadoEm(Date.now())
    }
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") atualizarMetricas()
    }, intervaloDasMetricasMs)
    // Returning to the tab after a long time away: refreshes right away instead of
    // waiting for the next tick — but not on every alt-tab.
    const onVisibility = () => {
      if (document.visibilityState === "visible" && Date.now() - ultimo >= intervaloDasMetricasMs) atualizarMetricas()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [workspaceLoading, workspaceId, intervaloDasMetricasMs])

  const recarregar = useCallback((opcoes: { force?: boolean } = {}) => {
    carregar(workspaceRef.current, opcoes.force ?? false)
  }, [carregar])

  return useMemo(() => ({
    workflows, grupos, metricas, carregando, atualizando, erro, metricasIndisponiveis, atualizadoEm,
    recarregar, definirWorkflows: setWorkflows, definirGrupos: setGrupos,
  }), [workflows, grupos, metricas, carregando, atualizando, erro, metricasIndisponiveis, atualizadoEm, recarregar])
}
