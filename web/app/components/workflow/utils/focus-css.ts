/**
 * Gera a folha de estilo do realce de caminho.
 *
 * A alternativa óbvia — um selector Zustand dentro de cada nó — reclassificaria
 * os ~50 nós do canvas a cada hover, exatamente a cascata de re-renders que os
 * `memo` de `icon-root.tsx` e `custom-edges/index.tsx` existem para evitar.
 * A alternativa imperativa (`classList.add`) quebra com `onlyRenderVisibleElements`,
 * porque um nó que entra na viewport durante o pan monta sem a classe.
 *
 * Aqui, trocar o foco re-renderiza um único componente e substitui o texto de
 * uma tag `<style>`: quem está no caminho recebe `--rf-focus-dim: 1`, e quem
 * não está cai no fallback da regra estática de `globals.css`.
 */

/** Caracteres que quebrariam a string CSS ou o texto da tag `<style>`. */
const UNSAFE = /[<>\u0000-\u001F\u007F]/g

/** Escapa um id para uso dentro de `[attr="…"]`, preservando hífens de UUID. */
export function escapeId(id: string): string {
  return id.replace(UNSAFE, "").replace(/["\\]/g, char => "\\" + char)
}

export function buildFocusCss(
  nodeIds: ReadonlySet<string>,
  edgeIds: ReadonlySet<string>,
  anchorId: string | null,
): string {
  if (!anchorId) return ""

  const selectors: string[] = []

  for (const id of nodeIds) {
    selectors.push(`.rf-focus .react-flow__node[data-id="${escapeId(id)}"]`)
  }

  for (const id of edgeIds) {
    const escaped = escapeId(id)
    selectors.push(`.rf-focus .react-flow__edge[data-id="${escaped}"]`)
    // O badge de label e o botão de excluir vivem num portal fora do <g> da
    // aresta, então precisam do próprio gancho.
    selectors.push(`.rf-focus [data-edge-id="${escaped}"]`)
  }

  if (!selectors.length) return ""

  return (
    `${selectors.join(",")}{--rf-focus-dim:1}` +
    `.rf-focus .react-flow__node[data-id="${escapeId(anchorId)}"]{outline-color:var(--primary)}`
  )
}
