import { create } from 'zustand'

/** Degraus de detalhe. Quanto mais afastado o zoom, menos informação na tela. */
export type LodTier = 'far' | 'mid' | 'near'

/** Origem do realce: `hover` é transitório, `pin` sobrevive ao mouse sair. */
export type FocusOrigin = 'hover' | 'pin'

const EMPTY: ReadonlySet<string> = new Set()

/** Estado visual do canvas — realce de caminho e nível de detalhe por zoom.
 *
 * As duas coisas moram na mesma store porque são consumidas pelos mesmos dois
 * lugares: a camada que escreve o CSS (`canvas-view-layer.tsx`) e a toolbar.
 *
 * Note que os conjuntos chegam prontos: o cálculo do caminho vive em
 * `useCanvasFocus`, que tem acesso às arestas. A store só guarda o resultado.
 */
interface CanvasViewState {
  /** Preferência do usuário — desliga o realce por hover por completo. */
  focusEnabled: boolean
  /** Nó âncora do realce. `null` = nenhum realce ativo. */
  focusNodeId: string | null
  focusOrigin: FocusOrigin | null
  /** Ancestrais ∪ âncora ∪ descendentes. */
  focusNodeIds: ReadonlySet<string>
  focusEdgeIds: ReadonlySet<string>
  lod: LodTier
}

interface CanvasViewActions {
  setFocusEnabled(v: boolean): void
  toggleFocusEnabled(): void
  applyFocus(nodeId: string, origin: FocusOrigin, nodes: Set<string>, edges: Set<string>): void
  /** `clearFocus('hover')` é ignorado enquanto houver um pin ativo. */
  clearFocus(origin?: FocusOrigin): void
  setLod(lod: LodTier): void
  /** Zera o estado por-workflow ao trocar de canvas. */
  resetView(): void
}

export const useCanvasViewStore = create<CanvasViewState & CanvasViewActions>((set, get) => ({
  focusEnabled: true,
  focusNodeId: null,
  focusOrigin: null,
  focusNodeIds: EMPTY,
  focusEdgeIds: EMPTY,
  lod: 'near',

  setFocusEnabled: (focusEnabled) => set(
    focusEnabled
      ? { focusEnabled }
      // Desligar precisa apagar o realce corrente, senão ele congela na tela.
      : { focusEnabled, focusNodeId: null, focusOrigin: null, focusNodeIds: EMPTY, focusEdgeIds: EMPTY }
  ),

  toggleFocusEnabled: () => get().setFocusEnabled(!get().focusEnabled),

  applyFocus: (focusNodeId, focusOrigin, nodes, edges) => {
    if (!get().focusEnabled) return
    set({ focusNodeId, focusOrigin, focusNodeIds: nodes, focusEdgeIds: edges })
  },

  clearFocus: (origin) => {
    // O pin é deliberado; passar o mouse por fora dele não deve apagá-lo.
    if (origin === 'hover' && get().focusOrigin === 'pin') return
    set({ focusNodeId: null, focusOrigin: null, focusNodeIds: EMPTY, focusEdgeIds: EMPTY })
  },

  setLod: (lod) => set({ lod }),

  resetView: () => set({
    focusNodeId: null,
    focusOrigin: null,
    focusNodeIds: EMPTY,
    focusEdgeIds: EMPTY,
  }),
}))
