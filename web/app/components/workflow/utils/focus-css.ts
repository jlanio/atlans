/**
 * Generates the stylesheet for path highlighting.
 *
 * The obvious alternative — a Zustand selector inside each node — would
 * reclassify the canvas's ~50 nodes on every hover, exactly the re-render
 * cascade the `memo`s in `icon-root.tsx` and `custom-edges/index.tsx` exist to
 * avoid. The imperative alternative (`classList.add`) breaks with
 * `onlyRenderVisibleElements`, because a node entering the viewport during a
 * pan mounts without the class.
 *
 * Here, changing the focus re-renders a single component and replaces the text of
 * a `<style>` tag: whoever is on the path gets `--rf-focus-dim: 1`, and whoever is
 * not falls back to the static rule in `globals.css`.
 */

/** Characters that would break the CSS string or the `<style>` tag's text. */
const UNSAFE = /[<>\u0000-\u001F\u007F]/g

/** Escapes an id for use inside `[attr="…"]`, preserving UUID hyphens. */
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
    // The label badge and the delete button live in a portal outside the edge's
    // <g>, so they need their own hook.
    selectors.push(`.rf-focus [data-edge-id="${escaped}"]`)
  }

  if (!selectors.length) return ""

  return (
    `${selectors.join(",")}{--rf-focus-dim:1}` +
    `.rf-focus .react-flow__node[data-id="${escapeId(anchorId)}"]{outline-color:var(--primary)}`
  )
}
