"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService, IExecutor } from "@/service/GisFlowService"
import type { IWorkspacePolicy } from "@/service/types"
import { createToast } from "@/utils/createToast"
import type { Workspace } from "@/context/WorkspaceContext"

/** <Select> value for "platform pool" — the backend represents it as null. */
export const POOL = "__default__"

/**
 * The "target" the quick picker represents, read from the policy.
 *
 * Follows what routing READS: with the flag on, the primary tier; with it off,
 * the legacy pointer — which is what decides where the run goes until the
 * switchover. Showing the tier while the server routes by the pointer would be
 * claiming a destination the next run will not have.
 */
export function alvoDaPolitica(p: IWorkspacePolicy): string | null {
  return p.policy_routing_enabled
    ? (p.primary[0]?.id_hash ?? null)
    : (p.target_executor_id ?? null)
}

/**
 * Executor of each workspace in the list, for the quick switch on the card itself.
 *
 * Lives here, and not inside the card, for three reasons: `getMyAgents` is ONE
 * call for the whole screen; the switch needs a rollback; and "couldn't read"
 * must NOT become "platform pool" — the card would be lying about where that
 * workspace's runs go.
 */
export function useWorkspaceExecutors(workspaces: Workspace[]) {
  const [executores, setExecutores] = useState<IExecutor[]>([])
  const [alvos, setAlvos] = useState<Record<string, string | null>>({})
  /** Full policy per workspace — tiers, terminal, floor and health. */
  const [politicas, setPoliticas] = useState<Record<string, IWorkspacePolicy>>({})
  /** Workspaces whose executor read failed — "don't know" state, neither pool nor target. */
  const [desconhecidos, setDesconhecidos] = useState<Set<string>>(new Set())
  /** Failure listing MY executors: without it, every target would look "removed". */
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState<Set<string>>(new Set())

  // Only the list of ids goes into the dependency: the `workspaces` array is
  // recreated on every context reload and would fire the fetch in a loop.
  const ids = workspaces.map(w => w.id_hash).join(",")

  // Load epoch: only serves for "a NEWER load beats an older one".
  // A `trocar` does NOT touch this — invalidating the whole epoch would discard
  // a concurrent general reload entirely (all the OTHER workspaces lost the
  // fresh data).
  const epocaRef = useRef(0)
  // Ids with a write in flight — preserved by any concurrent reload.
  const emVooRef = useRef<Set<string>>(new Set())
  // Monotonic clock for ordering writes. Each `carregar` keeps the stamp of when
  // it STARTED; each authoritative `trocar` stamps the workspace when leaving
  // "in flight". An old load, when merging, preserves the workspace whose write
  // stamp is newer than its start — protects the switch without throwing away
  // the rest.
  const relogioRef = useRef(0)
  const escritoEmRef = useRef<Record<string, number>>({})

  const carregar = useCallback(async () => {
    const lista = ids ? ids.split(",") : []
    if (lista.length === 0) {
      setExecutores([]); setAlvos({}); setPoliticas({}); setDesconhecidos(new Set()); setErro(null)
      return
    }
    const minha = ++epocaRef.current
    const inicio = ++relogioRef.current   // start stamp of this load
    // One read per workspace: the policy brings along the legacy pointer
    // (`target_executor_id`), so the executor does not need its own read.
    const [meus, ...respostas] = await Promise.all([
      GisFlowService.getMyAgents(),
      ...lista.map(id => GisFlowService.getWorkspacePolicy(id)),
    ])
    if (minha !== epocaRef.current) return

    if (meus.error) {
      setErro(meus.error.message ?? "Não foi possível carregar seus executores.")
    } else {
      setErro(null)
      // Keeps even revoked/inactive: that is how you detect a removed executor
      // that is still pointed at as the workspace's target.
      setExecutores(meus.data ?? [])
    }

    const mapa: Record<string, string | null> = {}
    const lidas: Record<string, IWorkspacePolicy> = {}
    const falhas = new Set<string>()
    lista.forEach((id, i) => {
      const r = respostas[i]
      if (r.error || !r.data) falhas.add(id)
      else { mapa[id] = alvoDaPolitica(r.data); lidas[id] = r.data }
    })
    // A workspace is preserved (not overwritten by this load) when it has a
    // write IN FLIGHT or an authoritative `trocar` write newer than the start
    // of this load — the snapshot here predates it.
    const preservar = (id: string) =>
      emVooRef.current.has(id) || (escritoEmRef.current[id] ?? 0) > inicio
    // Merges (does not replace): a partial reload cannot erase what was already
    // known, and a switch's value (in flight or just written) takes precedence.
    setAlvos(prev => {
      const merged = { ...prev, ...mapa }
      for (const id of Object.keys(merged)) if (preservar(id) && id in prev) merged[id] = prev[id]
      return merged
    })
    setPoliticas(prev => {
      const merged = { ...prev, ...lidas }
      for (const id of Object.keys(merged)) if (preservar(id) && id in prev) merged[id] = prev[id]
      return merged
    })
    // A protected workspace does not become "unknown" because of a read failure
    // in this stale load: its authoritative value was just written.
    setDesconhecidos(new Set([...falhas].filter(id => !preservar(id))))
  }, [ids])

  useEffect(() => { carregar() }, [carregar])

  // The previous value comes from a ref: between the click and the response the
  // map has already been rewritten by the optimistic update.
  const alvosRef = useRef<Record<string, string | null>>({})
  useEffect(() => { alvosRef.current = alvos }, [alvos])
  const desconhecidosRef = useRef<Set<string>>(new Set())
  useEffect(() => { desconhecidosRef.current = desconhecidos }, [desconhecidos])

  // Executor name for the toast — the list is already on screen.
  const executoresRef = useRef<IExecutor[]>([])
  useEffect(() => { executoresRef.current = executores }, [executores])

  const trocar = useCallback(async (workspaceId: string, valor: string, nomeDoWorkspace?: string) => {
    if (emVooRef.current.has(workspaceId)) return
    const agentId = valor === POOL ? null : valor
    const anterior = alvosRef.current[workspaceId] ?? null
    // If this workspace's read had FAILED, "previous" is `null` — which on screen
    // means "platform pool". Without restoring the unknown state, a failing
    // switch makes the card claim pool, the same lie the "don't know" state
    // exists to avoid.
    const eraDesconhecido = desconhecidosRef.current.has(workspaceId)

    // A set, and not a single id: switching two cards in sequence cleared the
    // wrong card's spinner and re-enabled a Select still in flight.
    emVooRef.current.add(workspaceId)
    setSalvando(s => new Set(s).add(workspaceId))
    setAlvos(prev => ({ ...prev, [workspaceId]: agentId }))
    setDesconhecidos(prev => {
      if (!prev.has(workspaceId)) return prev
      const s = new Set(prev); s.delete(workspaceId); return s
    })

    const res = await GisFlowService.setWorkspaceAgent(workspaceId, agentId)

    if (res.error) {
      emVooRef.current.delete(workspaceId)
      setSalvando(s => { const n = new Set(s); n.delete(workspaceId); return n })
      setAlvos(prev => ({ ...prev, [workspaceId]: anterior }))
      if (eraDesconhecido) setDesconhecidos(prev => new Set(prev).add(workspaceId))
      createToast.error("Erro ao trocar o executor", res.error.message)
      return
    }
    // The legacy endpoint writes both sides (pointer and primary tier), but
    // returns only the pointer: this workspace's policy — tiers, mode, health —
    // is re-read so the badge and the panel sentence are not left with the old
    // version. Still "in flight" during the re-read: a concurrent general reload
    // must not overwrite the switch with a snapshot that predates it.
    const pol = await GisFlowService.getWorkspacePolicy(workspaceId)
    // Protects this write against a general reload that started BEFORE and has
    // not responded yet (it carries a snapshot from before this switch). Instead
    // of invalidating the whole epoch — which discarded that reload's result
    // for ALL workspaces —, it stamps ONLY this one on the clock and only then
    // leaves "in flight": the old load, when merging, sees stamp > its start and
    // preserves this workspace, without losing the fresh data of the others.
    escritoEmRef.current[workspaceId] = ++relogioRef.current
    emVooRef.current.delete(workspaceId)
    setSalvando(s => { const n = new Set(s); n.delete(workspaceId); return n })
    if (!pol.error && pol.data) {
      const lida = pol.data
      setPoliticas(prev => ({ ...prev, [workspaceId]: lida }))
      setAlvos(prev => ({ ...prev, [workspaceId]: alvoDaPolitica(lida) }))
    }
    // The toast states the RESULT: where this workspace now runs.
    const quem = nomeDoWorkspace ? `«${nomeDoWorkspace}»` : "O workspace"
    if (agentId === null) {
      createToast.success(`${quem} agora usa o pool compartilhado.`)
    } else {
      const nome = executoresRef.current.find(e => e.id_hash === agentId)?.name ?? "o executor escolhido"
      createToast.success(`${quem} agora executa em ${nome}.`)
    }
  }, [])

  return {
    executores, alvos, politicas, desconhecidos, erro, salvando, trocar,
    recarregar: carregar,
  }
}
