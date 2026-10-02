import { create } from 'zustand'

export type RunPanelTab = 'nodes' | 'output' | 'problems' | 'raw'

/** Altura da barra sempre visível (o "HUD"). */
export const RUN_BAR_HEIGHT = 34
const DEFAULT_HEIGHT = 320
const MIN_HEIGHT = 160

/** Fração da janela que o painel pode tomar ao ABRIR, sem o usuário pedir. */
const FRACAO_INICIAL = 0.45

/**
 * Altura de abertura, limitada pela janela.
 *
 * Os 320px fixos foram escolhidos para um monitor, onde são ~30% da tela. Num
 * telefone de 640px úteis viravam metade do canvas — o usuário abria o painel
 * para acompanhar um run e perdia de vista justamente o grafo que queria
 * acompanhar. O limite só ENCOLHE: num monitor, 45% é bem mais que 320px, e o
 * padrão continua valendo.
 *
 * Não pode virar valor inicial da store: ela é criada na importação do módulo,
 * que também roda no servidor, e ler `window` ali quebraria o SSR (além de
 * congelar a altura da primeira renderização).
 */
function alturaDeAbertura(atual: number): number {
  if (typeof window === "undefined") return atual
  return Math.max(MIN_HEIGHT, Math.min(atual, Math.round(window.innerHeight * FRACAO_INICIAL)))
}

/** Estado de UI do painel de execução.
 *
 * Vive numa store própria (e não local no componente) porque três lugares
 * precisam dele: o painel, a coluna de botões do canvas — que sobe para não
 * ficar embaixo do dock — e o canvas, que revela um nó no painel ao ser clicado.
 */
interface RunPanelState {
  open: boolean
  height: number
  tab: RunPanelTab
  search: string
  /** Nó que o painel deve rolar até e destacar (setado pelo clique no canvas). */
  revealNodeId: string | null
  /** Nó sob o cursor no painel — destacado no canvas. */
  hoveredNodeId: string | null
}

interface RunPanelActions {
  setOpen(v: boolean): void
  /** Abre o painel já numa aba específica (ex.: "Problemas" quando falha). */
  openAt(tab: RunPanelTab): void
  setHeight(h: number): void
  setTab(tab: RunPanelTab): void
  setSearch(s: string): void
  reveal(nodeId: string | null): void
  setHovered(nodeId: string | null): void
}

export const useRunPanelStore = create<RunPanelState & RunPanelActions>((set) => ({
  open: false,
  height: DEFAULT_HEIGHT,
  tab: 'nodes',
  search: '',
  revealNodeId: null,
  hoveredNodeId: null,

  // O clamp vai no ABRIR, e não no `setHeight`: quem arrastou a alça escolheu
  // aquela altura e pode passar da fração à vontade.
  setOpen: (v) => set(state => v ? { open: true, height: alturaDeAbertura(state.height) } : { open: false }),
  openAt: (tab) => set(state => ({ open: true, tab, height: alturaDeAbertura(state.height) })),
  setHeight: (h) => set({ height: Math.max(MIN_HEIGHT, h) }),
  setTab: (tab) => set({ tab }),
  setSearch: (search) => set({ search }),
  reveal: (revealNodeId) => set({ revealNodeId }),
  setHovered: (hoveredNodeId) => set({ hoveredNodeId }),
}))

/** Espaço vertical que a coluna de botões do canvas precisa acima do dock. */
const BUTTON_COLUMN_HEIGHT = 300

/** Altura ocupada pelo dock — a coluna de botões do canvas usa para se deslocar.
 *
 * Limitada para que, com o painel maximizado, a coluna não seja empurrada para
 * fora do topo do canvas (onde ficava recortada e inalcançável). Passando do
 * limite ela fica atrás do painel, que tem z-index maior — comportamento
 * previsível para quem escolheu maximizar o painel.
 */
export function useRunDockHeight(): number {
  const open = useRunPanelStore(s => s.open)
  const height = useRunPanelStore(s => s.height)
  if (!open) return RUN_BAR_HEIGHT
  const ceiling = typeof window !== "undefined"
    ? Math.max(RUN_BAR_HEIGHT, window.innerHeight - BUTTON_COLUMN_HEIGHT)
    : height
  return Math.min(height, ceiling)
}
