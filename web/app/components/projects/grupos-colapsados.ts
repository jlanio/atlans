/**
 * Quais grupos ficam recolhidos, entre uma visita e outra.
 *
 * Era `useState` puro: quem recolhia os grupos que não usa via tudo aberto de
 * novo ao recarregar, e recolhia tudo outra vez. Numa lista com muitos grupos,
 * o estado é justamente o que torna a página utilizável.
 *
 * `localStorage` lança em janela privada e com a cota cheia — e um erro ao
 * LER não pode impedir a página de abrir. Toda operação é protegida, e o
 * fracasso é "nenhum grupo recolhido", que é o estado inicial de sempre.
 *
 * A chave é por workspace: recolher um grupo num workspace não deve mexer na
 * leitura de outro, onde os ids nem existem.
 */
const PREFIXO = "atlans:grupos-recolhidos"

export function chaveDosColapsados(workspaceId: string | null | undefined): string {
  return `${PREFIXO}:${workspaceId ?? "sem-workspace"}`
}

export function lerColapsados(chave: string): Set<string> {
  try {
    const cru = window.localStorage.getItem(chave)
    if (!cru) return new Set()
    const lista = JSON.parse(cru)
    // Conteúdo de outra versão, ou editado à mão: vale mais começar do zero do
    // que deixar um `Set` com números dentro chegar ao `has()`.
    if (!Array.isArray(lista)) return new Set()
    return new Set(lista.filter((x): x is string => typeof x === "string"))
  } catch {
    return new Set()
  }
}

export function gravarColapsados(chave: string, recolhidos: Set<string>): void {
  try {
    window.localStorage.setItem(chave, JSON.stringify([...recolhidos]))
  } catch {
    // Preferência de exibição não vale interromper nada.
  }
}
