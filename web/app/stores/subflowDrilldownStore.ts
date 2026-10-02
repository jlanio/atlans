import { create } from 'zustand'

/** Um degrau da descida: o nó SubWorkflow atravessado e o fluxo que ele chama. */
export interface SubflowLevel {
  /** Id do nó SubWorkflow no canvas em que ele vive (o pai deste nível). */
  canvasNodeId: string
  /** `properties.workflowHash` desse nó — o fluxo a carregar e desenhar. */
  workflowHash: string
  /** Rótulo do nó SubWorkflow, para a trilha. */
  label: string
}

/**
 * Navegação para dentro dos sub-fluxos de uma execução.
 *
 * `path` é a cadeia de nós SubWorkflow atravessados: `[]` significa fechado, e
 * `path[i].canvasNodeId` juntos por `::` formam exatamente o prefixo com que os
 * eventos daquele nível chegam ao painel (ver utils/subflow-path).
 *
 * Vive numa store, e não em estado local do visualizador, porque quem ABRE está
 * espalhado — o painel de execução, a partir de um erro, e o próprio canvas —
 * enquanto quem RENDERIZA é um só componente montado ao lado do editor.
 */
interface SubflowDrilldownState {
  path: SubflowLevel[]
  /**
   * Nó (id local) a centralizar assim que o nível abrir. É o que faz "abrir
   * sub-fluxo" a partir de uma falha cair direto no nó que quebrou, em vez de
   * largar a pessoa num grafo enquadrado por inteiro para procurar o vermelho.
   */
  focusNodeId: string | null
}

interface SubflowDrilldownActions {
  /** Abre do zero, substituindo qualquer descida em andamento. */
  open(path: SubflowLevel[], focusNodeId?: string | null): void
  /** Desce mais um nível a partir do que já está aberto. */
  push(level: SubflowLevel): void
  /** Volta para um nível já visitado. Índice -1 volta ao fluxo do editor. */
  popTo(index: number): void
  close(): void
}

export const useSubflowDrilldownStore = create<SubflowDrilldownState & SubflowDrilldownActions>((set) => ({
  path: [],
  focusNodeId: null,

  open: (path, focusNodeId = null) => set({ path, focusNodeId }),
  push: (level) => set(state => ({ path: [...state.path, level], focusNodeId: null })),
  popTo: (index) => set(state => (
    index < 0
      ? { path: [], focusNodeId: null }
      : { path: state.path.slice(0, index + 1), focusNodeId: null }
  )),
  close: () => set({ path: [], focusNodeId: null }),
}))
