"use client"

// web/app/hooks/home/useArrasteDeArquivos.ts
//
// Dragging files over the Home.
//
// **The area that ACCEPTS is the whole window; what LIGHTS UP is the assistant box.**
// Aiming at a 44 px tall bar with a file in hand is hostile — and anchoring
// the visual target on the box is precisely the choice of option C, so as not
// to cover the globe with a veil on every drag. So the listener is global and
// the highlight belongs to the box (`data-arraste` in `barra.tsx` and `painel.tsx`).
//
// Listening on `window` has a second, necessary effect: without `preventDefault`
// on `dragover`/`drop` the browser OPENS the dropped file, replacing the Home
// with raw GeoJSON — and losing the ongoing conversation. With the global
// listener, a drop anywhere on the page is handled by us.
//
// `dragleave` is not reliable on its own: it fires when crossing the boundary
// of each child element, so a drag that crosses the sidebar would turn off the
// highlight midway. Hence the enter/leave counter — the highlight only goes
// off when the drag has actually left the window.

import { useEffect, useRef } from "react"

/** Does the drag carry FILES? Selected text and links also fire these
 *  events, and lighting up the box for them would be a false promise. */
function hasFiles(e: DragEvent): boolean {
  const tipos = e.dataTransfer?.types
  if (!tipos) return false
  return Array.from(tipos).includes("Files")
}

export function useArrasteDeArquivos({
  ativo,
  aoArrastar,
  aoSoltar,
}: {
  /** Off while the Home cannot receive (e.g. the bar has not even mounted). */
  ativo: boolean
  aoArrastar: (arrastando: boolean) => void
  aoSoltar: (arquivos: File[]) => void
}): void {
  // In refs so the effect does not resubscribe on every render: `aoSoltar` comes
  // from a `useCallback` whose dependencies change (the active workspace, for
  // example), and resubscribing in the middle of a drag would reset the counter —
  // the highlight would stay lit forever.
  const refDrag = useRef(aoArrastar)
  const refDrop = useRef(aoSoltar)
  refDrag.current = aoArrastar
  refDrop.current = aoSoltar

  useEffect(() => {
    if (!ativo) return
    let profundidade = 0

    function entrou(e: DragEvent) {
      if (!hasFiles(e)) return
      profundidade++
      refDrag.current(true)
    }
    function sobre(e: DragEvent) {
      if (!hasFiles(e)) return
      // Without this the `drop` never even happens — the browser handles the file.
      e.preventDefault()
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy"
    }
    function saiu(e: DragEvent) {
      if (!hasFiles(e)) return
      profundidade = Math.max(0, profundidade - 1)
      if (profundidade === 0) refDrag.current(false)
    }
    function soltou(e: DragEvent) {
      if (!hasFiles(e)) return
      e.preventDefault()
      profundidade = 0
      refDrag.current(false)
      const arquivos = e.dataTransfer?.files
      if (arquivos && arquivos.length > 0) refDrop.current(Array.from(arquivos))
    }
    // Leaving the window with the file still in hand does not fire `dragleave` in
    // every browser; `dragend` is the safety net so the highlight does not stay lit.
    function acabou() {
      profundidade = 0
      refDrag.current(false)
    }

    window.addEventListener("dragenter", entrou)
    window.addEventListener("dragover", sobre)
    window.addEventListener("dragleave", saiu)
    window.addEventListener("drop", soltou)
    window.addEventListener("dragend", acabou)
    return () => {
      window.removeEventListener("dragenter", entrou)
      window.removeEventListener("dragover", sobre)
      window.removeEventListener("dragleave", saiu)
      window.removeEventListener("drop", soltou)
      window.removeEventListener("dragend", acabou)
      // Unmounting in the middle of a drag would leave the highlight on in the store.
      refDrag.current(false)
    }
  }, [ativo])
}
