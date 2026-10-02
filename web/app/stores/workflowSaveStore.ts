import { create } from 'zustand'
import type { Viewport } from '@xyflow/react'
import { INodesDefinition, IEdgeDefinition } from '@/service/types'

export type SaveStatus = 'idle' | 'unsaved' | 'saving' | 'saved' | 'error' | 'needs_name'

interface WorkflowSaveState {
  isSaving: boolean
  saveStatus: SaveStatus
  lastSavedSnapshot: string | null
  /** Momento (epoch ms) do último save confirmado: o `updated_at` do servidor
   *  na hidratação, o relógio do navegador depois de um PUT/POST bem-sucedido.
   *  `null` = nada salvo que se conheça (workflow novo, ou backend sem a data).
   *  É o que o chip mostra em repouso ("Salvo há 5 min"). */
  lastSavedAt: number | null
  /** Mensagem do último save que falhou; `null` fora do status 'error'. */
  lastError: string | null
  /** Zoom e posição gravados no último save (ou carregados com o workflow).
   *  Pan/zoom NÃO é edição — não marca "não salvo" —, mas é parte do que se
   *  salva: quem pede o save quer reabrir onde estava. Comparado no save
   *  explícito para decidir se vale um PUT quando o grafo não mudou. */
  lastSavedViewport: Viewport | null
  workflowName: string
  flagActive: boolean
  /** Momento (epoch ms) em que o snapshot de referência foi tirado na hidratação.
   *  `null` = não há janela de autocorreção aberta. Ver `autocorrigirSnapshot`. */
  snapshotIniciadoEm: number | null
}

interface WorkflowSaveActions {
  setWorkflowName(name: string): void
  setFlagActive(v: boolean): void
  startSaving(): void
  completeSave(snapshot: string, viewport?: Viewport | null): void
  /** Save que não chegou ao fim. O status vira 'error', e não 'unsaved': o grafo
   *  continua diferente do snapshot, mas o que o usuário precisa saber é que a
   *  tentativa falhou — e ter onde tentar de novo. */
  failSave(mensagem?: string): void
  /** Salvar sem nada a salvar: pisca "Salvo" sem PUT e sem mexer em
   *  `lastSavedAt`. Antes o Ctrl+S nessa situação não respondia nada, e não
   *  havia como distinguir "já estava salvo" de "o atalho não funcionou". */
  flashSaved(): void
  setStatus(status: SaveStatus): void
  /** `savedAt` é o `updated_at` do servidor na hidratação e `viewport` o que
   *  veio na `definition`; omitidos, mantêm o valor atual (o reset ao trocar
   *  de workflow é quem zera). */
  initSnapshot(nodes: INodesDefinition[], edges: IEdgeDefinition[], name: string, savedAt?: number | null, viewport?: Viewport | null): void
  isDirty(nodes: INodesDefinition[], edges: IEdgeDefinition[], name: string): boolean
  /**
   * Absorve em silêncio uma diferença que apareceu na JANELA de hidratação —
   * o ReactFlow ainda medindo dimensões/posições logo após o mount. Devolve
   * `true` quando absorveu; `false` quando a janela já fechou, e aí quem chamou
   * precisa marcar 'unsaved', porque a diferença é edição real do usuário.
   *
   * A janela é de TEMPO, e não "a primeira diferença que aparecer": com o
   * detector de alterações debounced, a primeira comparação acontece só depois
   * que o usuário para de editar — então uma flag de "usar uma vez" engolia a
   * primeira edição INTEIRA (sem "Não salvo", com Ctrl+S virando no-op e o
   * Executar disparando a definição antiga).
   */
  autocorrigirSnapshot(nodes: INodesDefinition[], edges: IEdgeDefinition[], name: string): boolean
}

/** Quanto tempo o rótulo "Salvo" (verde) fica antes de virar o repouso
 *  ("Salvo há N min", em tom neutro). */
const TEMPO_DO_ROTULO_SALVO_MS = 3000

/** Por quanto tempo, após o snapshot de hidratação, uma diferença ainda pode ser
 *  creditada à remedição do ReactFlow em vez de ao usuário. */
const JANELA_DE_AUTOCORRECAO_MS = 1000

// O timer de 'saved' → 'idle' mora aqui, e não no componente que salvou, porque
// quem precisa neutralizá-lo é o detector de alterações — que vive em OUTRO
// componente. Antes, uma edição feita dentro da janela de 3s marcava "Não
// salvo" e o timer antigo apagava o aviso logo depois.
let timerDoRotuloSalvo: ReturnType<typeof setTimeout> | null = null

export const useWorkflowSaveStore = create<WorkflowSaveState & WorkflowSaveActions>((set, get) => {

  function agendarVoltaAoRepouso() {
    if (timerDoRotuloSalvo) clearTimeout(timerDoRotuloSalvo)
    timerDoRotuloSalvo = setTimeout(() => {
      timerDoRotuloSalvo = null
      // Só apaga o rótulo se ninguém mexeu no status no meio tempo: se o
      // usuário editou o canvas nesses 3s, o status já é 'unsaved' e voltar
      // para 'idle' esconderia o aviso.
      if (get().saveStatus === 'saved') set({ saveStatus: 'idle' })
    }, TEMPO_DO_ROTULO_SALVO_MS)
  }

  return {
    isSaving: false,
    saveStatus: 'idle',
    lastSavedSnapshot: null,
    lastSavedAt: null,
    lastError: null,
    lastSavedViewport: null,
    workflowName: '',
    flagActive: true,
    snapshotIniciadoEm: null,

    setWorkflowName: (name) => {
      set({ workflowName: name })
    },

    setFlagActive: (v) => {
      set({ flagActive: v })
    },

    startSaving: () => {
      set({ isSaving: true, saveStatus: 'saving' })
    },

    completeSave: (snapshot, viewport) => {
      // Fecha a janela de autocorreção: depois de um save bem-sucedido não existe
      // mais "medição pendente do ReactFlow" a absorver — toda diferença dali em
      // diante é edição do usuário e precisa virar "Não salvo".
      set({
        isSaving: false,
        lastSavedSnapshot: snapshot,
        lastSavedAt: Date.now(),
        lastError: null,
        saveStatus: 'saved',
        snapshotIniciadoEm: null,
        ...(viewport !== undefined ? { lastSavedViewport: viewport } : {}),
      })
      agendarVoltaAoRepouso()
    },

    failSave: (mensagem) => {
      set({ isSaving: false, saveStatus: 'error', lastError: mensagem ?? null })
    },

    flashSaved: () => {
      set({ saveStatus: 'saved' })
      agendarVoltaAoRepouso()
    },

    setStatus: (status) => {
      set({ saveStatus: status })
    },

    initSnapshot: (nodes, edges, name, savedAt, viewport) => {
      const snapshot = JSON.stringify({ name, nodes, edges })
      // Abre a janela de autocorreção junto com o snapshot: é este instante que o
      // detector de alterações usa como referência.
      set({
        lastSavedSnapshot: snapshot,
        snapshotIniciadoEm: Date.now(),
        ...(savedAt !== undefined ? { lastSavedAt: savedAt } : {}),
        ...(viewport !== undefined ? { lastSavedViewport: viewport } : {}),
      })
    },

    isDirty: (nodes, edges, name) => {
      const currentSnapshot = JSON.stringify({ name, nodes, edges })
      return currentSnapshot !== get().lastSavedSnapshot
    },

    autocorrigirSnapshot: (nodes, edges, name) => {
      const { snapshotIniciadoEm, saveStatus } = get()
      if (saveStatus !== 'idle') return false
      if (snapshotIniciadoEm === null) return false
      if (Date.now() - snapshotIniciadoEm >= JANELA_DE_AUTOCORRECAO_MS) return false
      set({
        lastSavedSnapshot: JSON.stringify({ name, nodes, edges }),
        // Vale uma vez por hidratação: re-abrir a janela aqui a esticaria
        // indefinidamente enquanto diferenças continuassem aparecendo.
        snapshotIniciadoEm: null,
      })
      return true
    },
  }
})
