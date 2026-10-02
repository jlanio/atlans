// Store Zustand para dados "dinâmicos" do editor que antes viviam em FlowContext.
// Separa estado de UI (drawer, newly-added) e catálogo server-state (nodesAPI,
// credentials, pinnedNodes) do FlowContext — que agora só guarda refs imutáveis
// (reactFlowInstance, flowRef, reloadWorkflow).
//
// Motivação: cada `setFlowContext(prev => ...)` recriava o value do contexto
// inteiro, causando re-render em todos os ~40 consumers do hook mesmo quando
// a mudança afetava só 1 campo. Subscriptions granulares via Zustand eliminam
// essa cascata.
import { create } from 'zustand'

import { fromBackend } from '@/lib/dayjs'
import { GisFlowService } from '@/service/GisFlowService'
import type { INodesAPI } from '@/service/types'
import type { ICredentials } from '@/service/types'
import type { IPinNodeMeta } from '@/service/types'

export type NodesDrawerState = 'opened' | 'closed' | (string & {})

/** Validade do catálogo em memória. Nós e credenciais só mudam quando um admin
 *  desabilita um node ou o usuário cadastra uma credencial — não a cada abertura
 *  de canvas. */
const TTL_DO_CATALOGO_MS = 5 * 60 * 1000

// Requisições em voo, para que duas montagens simultâneas (canvas + Ctrl+K)
// compartilhem o mesmo download em vez de disparar dois.
let nosEmVoo: Promise<INodesAPI[]> | null = null
let credenciaisEmVoo: Promise<ICredentials[]> | null = null

const estaFresco = (carimbo: number | null) =>
  carimbo !== null && Date.now() - carimbo < TTL_DO_CATALOGO_MS

/** Compara conteúdo, não referência.
 *
 *  O canvas assina `nodesAPI` e re-hidrata o grafo quando essa lista troca de
 *  IDENTIDADE. Um refetch de TTL vencido devolve um array novo vindo do JSON
 *  mesmo quando o catálogo é byte a byte o mesmo — e isso bastava para
 *  redesenhar o grafo por cima de tudo que o usuário já tinha editado. */
const mesmoConteudo = (a: unknown[], b: unknown[]) =>
  a.length === b.length && JSON.stringify(a) === JSON.stringify(b)

interface WorkflowCatalogState {
  /** Catálogo de tipos de nós — resposta de GET /nodes */
  nodesAPI: INodesAPI[]
  /** Credenciais disponíveis ao usuário — resposta de GET /credentials */
  credentials: ICredentials[]
  /** Quando `nodesAPI` foi baixado (epoch ms). null = nunca. */
  nodesFetchedAt: number | null
  /** Quando `credentials` foi baixado (epoch ms). null = nunca. */
  credentialsFetchedAt: number | null
  /** Nós com output fixado (pin data) no workflow atual */
  pinnedNodes: IPinNodeMeta[]
  /** ID do nó recém-adicionado — usado para animação de destaque */
  newlyAddedNodeId: string | undefined
  /** Estado do drawer lateral de adicionar nós */
  nodesDrawerState: NodesDrawerState
}

interface WorkflowCatalogActions {
  setCredentials(v: ICredentials[]): void
  /** Garante o catálogo em memória: baixa só se estiver vazio ou vencido.
   *  Uma busca que falha PRESERVA o que já estava em memória e não carimba o
   *  TTL — a próxima chamada tenta de novo. */
  ensureNodesAPI(): Promise<INodesAPI[]>
  /** Idem para as credenciais. */
  ensureCredentials(): Promise<ICredentials[]>
  /** Marca as credenciais como vencidas — o próximo `ensureCredentials` refaz o GET.
   *  Chamado por quem cria/edita/exclui credencial fora do canvas, senão a
   *  credencial nova só apareceria no select do nó depois do TTL de 5 min. */
  invalidarCredenciais(): void
  setPinnedNodes(v: IPinNodeMeta[]): void
  setNewlyAddedNodeId(v: string | undefined): void
  setNodesDrawerState(v: NodesDrawerState): void
  /** Recalcula `expired` de cada pin com base no `expires_at` carregado e no
   * relógio atual. No-op quando nada muda — evita re-render dos consumers. */
  recomputeExpiredPins(): void
  /** Limpa campos dependentes do workflow (pinnedNodes, newlyAddedNodeId, drawer fechado).
   * nodesAPI e credentials são mantidos — são globais do usuário. */
  resetWorkflowScoped(): void
}

export const useWorkflowCatalogStore = create<WorkflowCatalogState & WorkflowCatalogActions>((set, get) => ({
  nodesAPI: [],
  credentials: [],
  nodesFetchedAt: null,
  credentialsFetchedAt: null,
  pinnedNodes: [],
  newlyAddedNodeId: undefined,
  nodesDrawerState: 'closed',

  setCredentials: (v) => set({ credentials: v, credentialsFetchedAt: Date.now() }),

  ensureNodesAPI: () => {
    const { nodesAPI, nodesFetchedAt } = get()
    if (nodesAPI.length > 0 && estaFresco(nodesFetchedAt)) return Promise.resolve(nodesAPI)
    if (nosEmVoo) return nosEmVoo
    nosEmVoo = GisFlowService.getNodes()
      .then(res => {
        // O service NÃO rejeita em falha: resolve com { data: undefined, error }.
        // Sem esta guarda, um 502/401/queda de rede gravava `nodesAPI: []` por
        // cima do catálogo bom e o drawer, a paleta e o "command-add-node"
        // ficavam vazios sem nenhuma mensagem de erro. Em falha, preserva o que
        // está em memória e NÃO carimba o TTL — a próxima chamada tenta de novo.
        if (res?.error || !Array.isArray(res?.data)) return get().nodesAPI
        const lista = res.data
        const atual = get().nodesAPI
        if (mesmoConteudo(atual, lista)) {
          // Conteúdo idêntico: renova só a validade e mantém a MESMA referência,
          // para não acordar os consumers que assinam o array.
          set({ nodesFetchedAt: Date.now() })
          return atual
        }
        set({ nodesAPI: lista, nodesFetchedAt: Date.now() })
        return lista
      })
      .finally(() => { nosEmVoo = null })
    return nosEmVoo
  },

  ensureCredentials: () => {
    const { credentials, credentialsFetchedAt } = get()
    if (credentials.length > 0 && estaFresco(credentialsFetchedAt)) return Promise.resolve(credentials)
    if (credenciaisEmVoo) return credenciaisEmVoo
    credenciaisEmVoo = GisFlowService.getCredentials()
      .then(res => {
        // Mesma regra do catálogo de nós: falha não derruba a lista boa. Aqui o
        // sintoma seria o select de credencial do nó ficar vazio e o usuário
        // salvar o nó sem credencial nenhuma.
        if (res?.error || !Array.isArray(res?.data)) return get().credentials
        const lista = res.data
        const atual = get().credentials
        if (mesmoConteudo(atual, lista)) {
          set({ credentialsFetchedAt: Date.now() })
          return atual
        }
        set({ credentials: lista, credentialsFetchedAt: Date.now() })
        return lista
      })
      .finally(() => { credenciaisEmVoo = null })
    return credenciaisEmVoo
  },

  invalidarCredenciais: () => set({ credentialsFetchedAt: null }),

  setPinnedNodes: (v) => set({ pinnedNodes: v }),
  setNewlyAddedNodeId: (v) => set({ newlyAddedNodeId: v }),
  setNodesDrawerState: (v) => set({ nodesDrawerState: v }),

  recomputeExpiredPins: () => set(state => {
    const now = Date.now()
    let changed = false
    const updated = state.pinnedNodes.map(p => {
      if (!p.expires_at) return p
      // expires_at vem UTC naive (sem offset). `new Date()` cru o interpretava
      // como local, deslocando o epoch pelo offset do fuso → a expiracao do pin
      // errava por ~horas. fromBackend trata como UTC; valueOf() da o epoch
      // absoluto correto para comparar com Date.now().
      const expiresAtMs = fromBackend(p.expires_at)?.valueOf() ?? Number.POSITIVE_INFINITY
      const expired = now > expiresAtMs
      if (expired === p.expired) return p
      changed = true
      return { ...p, expired }
    })
    return changed ? { pinnedNodes: updated } : {}
  }),

  resetWorkflowScoped: () => set({
    pinnedNodes: [],
    newlyAddedNodeId: undefined,
    nodesDrawerState: 'closed',
  }),
}))
