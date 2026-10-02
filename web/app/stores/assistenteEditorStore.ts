import { create } from "zustand"

/**
 * Aberto/fechado da gaveta do assistente.
 *
 * Numa store, e não em estado local do editor, porque três lugares precisam
 * dele: a gaveta, o botão que a abre e o atalho de teclado — que vive num
 * efeito global e não pode depender de a gaveta estar montada.
 *
 * A LARGURA não mora aqui: ela é do `useResizablePanel`, que já resolve
 * arraste, teclado, clamp de viewport e `localStorage`. Duas memórias para a
 * mesma gaveta divergiriam na primeira mudança.
 */

/** Chave do `localStorage`. A largura usa `CHAVE_LARGURA`, no componente. */
const CHAVE_ABERTO = "atlans:assistente:aberto"

function lembrado(): boolean | null {
  if (typeof window === "undefined") return null
  try {
    let cru = window.localStorage.getItem(CHAVE_ABERTO)
    if (cru === null) {
      // A F4 renomeou a chave (era atlans:copiloto:aberto) sem migração — o
      // painel "esquecia" a preferência de todo mundo. Lê a antiga uma vez e
      // regrava na nova; a antiga fica, para quem voltar a uma versão anterior.
      cru = window.localStorage.getItem("atlans:copiloto:aberto")
      if (cru !== null) window.localStorage.setItem(CHAVE_ABERTO, cru)
    }
    return cru === null ? null : cru === "1"
  } catch {
    // Janela privada ou cota cheia. Preferência é descartável.
    return null
  }
}

function lembrar(aberto: boolean): void {
  try {
    window.localStorage.setItem(CHAVE_ABERTO, aberto ? "1" : "0")
  } catch {
    /* preferência descartável */
  }
}

interface AssistenteEditorState {
  aberto: boolean
}

interface AssistenteEditorActions {
  fechar(): void
  alternar(): void
  /**
   * Lê a preferência do navegador. `padrao` vale quando não há nada guardado:
   * a tela de criar abre a gaveta (o canvas nasce vazio e ela é o caminho mais
   * curto), o editor de um fluxo existente não (quem abre um fluxo pronto veio
   * para o canvas).
   */
  hidratar(padrao: boolean): void
}

export const useAssistenteEditorStore = create<AssistenteEditorState & AssistenteEditorActions>((set) => ({
  aberto: false,

  fechar: () => set(() => { lembrar(false); return { aberto: false } }),
  alternar: () => set(state => { lembrar(!state.aberto); return { aberto: !state.aberto } }),

  // Não grava: hidratar é LER a preferência, e escrever aqui transformaria o
  // default da tela de criar numa escolha que a pessoa nunca fez — e que
  // passaria a valer no editor também.
  hidratar: (padrao) => set(() => ({ aberto: lembrado() ?? padrao })),
}))
