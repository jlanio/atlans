import { create } from 'zustand'

// Known columns per node — the memory that feeds "Vistas na última execução"
// (seen in the last execution) in the fields that ask for a column name.
//
// It lives in its OWN store, outside workflowExecutionStore, on purpose: the
// lifecycle is different. Execution state is born and dies with the run
// (`startExecution`/`resetExecution` wipe everything, and should); the columns
// are accumulated knowledge about the WORKFLOW — clicking Executar again,
// a save error or a tab switch does not change what the last execution saw.
// While the columns lived in `statusWorkflow`, each of the ~6 reset paths
// erased them and the suggestion seemed to work "sometimes".
//
// What wipes this store is ONE thing only: opening ANOTHER workflow. Node ids
// are UUIDs, but a duplicated workflow inherits the original's ids — without the
// per-workflow cut, A's columns would show up as suggestions in B.

export interface NodeColumns {
  /** Columns per output port — the same `output_columns` shape that the
   *  executor publishes in the event and writes to `node_stats`. `{}` is a
   *  TOMBSTONE: the node completed live WITHOUT publishing columns, and the
   *  absence is information (it keeps the late seeding from resurrecting older data). */
  porPorta: Record<string, string[]>
  /** Run they came from. Tracing for debugging, not identity. */
  runId: string | null
  /** true  = seen LIVE in this session (run event);
   *  false = re-hydrated from the last persisted run — they may be
   *          out of date, and the suggestion label says so. */
  fresh: boolean
  /** true when the source stat came truncated (the executor's 8KB cut
   *  reduces each list to the first 50) — the label warns "lista parcial"
   *  (partial list) instead of asserting completeness. Only re-hydration knows
   *  this; a live event does not carry the mark. */
  parciais?: boolean
}

interface KnownColumnsState {
  /** Workflow that owns the `porNo` entries. */
  workflowId: string | null
  porNo: Map<string, NodeColumns>
}

interface KnownColumnsActions {
  /** Called on workflow switch/open: clears if the workflow changed, and does NOT
   *  touch anything if it is the same — reopening the same screen does not erase memory. */
  prepararParaWorkflow(workflowId: string | null): void
  /**
   * Writes from a LIVE run, batched (one per frame, like the rest of the
   * events pipeline). `porPorta === null` means the node COMPLETED without
   * publishing columns — non-tabular output, or the key cut off in transport —
   * and the entry becomes a TOMBSTONE (`porPorta: {}`, `fresh: true`): the
   * suggestion stops asserting columns the last execution did not produce, and
   * the tombstone keeps the late seeding from the PREVIOUS run from resurrecting
   * them (a delete left the result depending on which network response arrived last).
   */
  aplicarDeExecucao(
    workflowId: string,
    runId: string,
    mudancas: Map<string, Record<string, string[]> | null>,
  ): void
  /**
   * Seeding from the `node_stats` of the last persisted run, when the workflow
   * opens. It goes in as `fresh: false` and NEVER overwrites a `fresh: true`
   * entry (tombstones included) — if a live run has already written (the API
   * response arrived late), the newer data wins.
   */
  semearDoHistorico(
    workflowId: string,
    runId: string,
    columnsByNode: Record<string, { porPorta: Record<string, string[]>; parciais?: boolean }>,
  ): void
}

const EMPTY: Map<string, NodeColumns> = new Map()

export const useKnownColumnsStore = create<KnownColumnsState & KnownColumnsActions>((set) => ({
  workflowId: null,
  porNo: EMPTY,

  prepararParaWorkflow: (workflowId) => {
    set(state => (state.workflowId === workflowId
      ? state
      : { workflowId, porNo: new Map() }))
  },

  aplicarDeExecucao: (workflowId, runId, mudancas) => {
    if (mudancas.size === 0) return
    set(state => {
      // A write from another workflow (late rAF after the switch): starts over with
      // only what arrived — the per-run filter in `drenarLote` already blocks
      // almost everything, this is the seat belt.
      const base = state.workflowId === workflowId ? state.porNo : EMPTY
      const porNo = new Map(base)
      for (const [nodeId, porPorta] of mudancas) {
        porNo.set(nodeId, { porPorta: porPorta ?? {}, runId, fresh: true })
      }
      return { workflowId, porNo }
    })
  },

  semearDoHistorico: (workflowId, runId, columnsByNode) => {
    set(state => {
      // A LATE response from another workflow: ignore. A live write may adopt the
      // workflow (the event proves that it is the one running); an old API
      // response proves nothing — flipping the store over to it would put A's
      // columns on B's screen.
      if (state.workflowId !== null && state.workflowId !== workflowId) return state
      const porNo = new Map(state.porNo)
      for (const [nodeId, { porPorta, parciais }] of Object.entries(columnsByNode)) {
        // A live run has already written to this node (tombstone included): the API
        // response is older.
        if (porNo.get(nodeId)?.fresh) continue
        porNo.set(nodeId, { porPorta, runId, fresh: false, parciais: !!parciais })
      }
      return { workflowId, porNo }
    })
  },
}))
