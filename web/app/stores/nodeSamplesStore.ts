import { create } from "zustand"
import type { AmostraDoNo } from "@/types/amostra"

/**
 * Data samples of each node's outputs, for the Entradas/Saídas panels of the
 * node modal (docs/specs/node-data-panels.md §6.1).
 *
 * Kept OUTSIDE the execution store on purpose: `resetExecution` wipes the
 * canvas state before every run and when the workflow opens, and the panels
 * must keep showing the previous run's data (marked as stale) until the new
 * run replaces it node by node. Scoped to one workflow: opening another one
 * starts empty.
 */

export interface AmostraRegistrada {
  sample: AmostraDoNo
  runId: string
  /** From an earlier run: the current one has not reached this node yet. */
  stale: boolean
}

interface NodeSamplesState {
  workflowId: string | null
  runId: string | null
  byNode: Record<string, AmostraRegistrada>
  /** The last run came back with `data_preview: false`: the admin turned samples off. */
  disabledByAdmin: boolean
}

interface NodeSamplesActions {
  /** A run of `workflowId` started. With `dataPreview` false, the admin switch is off. */
  beginRun(workflowId: string, runId: string, dataPreview: boolean): void
  /** One `sample` event arrived (live or from the replay). */
  apply(workflowId: string, runId: string, nodeId: string, sample: AmostraDoNo): void
  /** Samples read from the history of finished runs, when the workflow opens.
   *  `runId` is the newest of them; `runIdPorNo` says which run each sample came
   *  from (an older full run under a partial one), and those show as stale. */
  seedFromHistory(workflowId: string, runId: string, samples: Record<string, AmostraDoNo>, runIdPorNo?: Record<string, string>): void
  clear(): void
}

const VAZIO: NodeSamplesState = { workflowId: null, runId: null, byNode: {}, disabledByAdmin: false }

export const useNodeSamplesStore = create<NodeSamplesState & NodeSamplesActions>((set) => ({
  ...VAZIO,

  beginRun: (workflowId, runId, dataPreview) => set(state => {
    const mesmo = state.workflowId === workflowId
    const byNode: Record<string, AmostraRegistrada> = {}
    if (mesmo) {
      for (const [id, reg] of Object.entries(state.byNode)) byNode[id] = { ...reg, stale: true }
    }
    return { workflowId, runId, byNode, disabledByAdmin: !dataPreview }
  }),

  apply: (workflowId, runId, nodeId, sample) => set(state => {
    if (state.workflowId !== workflowId) {
      return { workflowId, runId, byNode: { [nodeId]: { sample, runId, stale: false } }, disabledByAdmin: false }
    }
    // An event of an older run (late replay) never overwrites a newer sample.
    if (state.runId && runId !== state.runId) {
      const atual = state.byNode[nodeId]
      if (atual && !atual.stale) return {}
    }
    return {
      byNode: { ...state.byNode, [nodeId]: { sample, runId, stale: state.runId !== null && runId !== state.runId } },
    }
  }),

  seedFromHistory: (workflowId, runId, samples, runIdPorNo = {}) => set(state => {
    // A run started in this session already owns the panels.
    if (state.workflowId === workflowId && state.runId) return {}
    const byNode: Record<string, AmostraRegistrada> = {}
    for (const [id, sample] of Object.entries(samples)) {
      const deQual = runIdPorNo[id] ?? runId
      byNode[id] = { sample, runId: deQual, stale: deQual !== runId }
    }
    return { workflowId, runId, byNode, disabledByAdmin: false }
  }),

  clear: () => set({ ...VAZIO }),
}))

/** `{node_id: sample}` out of raw run events (`status: "sample"`), the last one per node winning. */
export function amostrasDosEventos(eventos: Array<{ node?: string; status?: string; extra?: unknown }>): Record<string, AmostraDoNo> {
  const porNo: Record<string, AmostraDoNo> = {}
  for (const ev of eventos) {
    const sample = amostraDoEvento(ev)
    if (sample && ev.node) porNo[ev.node] = sample
  }
  return porNo
}

/** The `output_sample` of one `sample` event, or null when absent or malformed
 *  (an event cut down by the protocol reduction arrives without it). */
export function amostraDoEvento(ev: { status?: string; extra?: unknown }): AmostraDoNo | null {
  if (ev.status !== "sample" || !ev.extra || typeof ev.extra !== "object") return null
  const sample = (ev.extra as { output_sample?: unknown }).output_sample
  if (!sample || typeof sample !== "object") return null
  const outputs = (sample as { outputs?: unknown }).outputs
  if (!outputs || typeof outputs !== "object") return null
  return sample as AmostraDoNo
}
