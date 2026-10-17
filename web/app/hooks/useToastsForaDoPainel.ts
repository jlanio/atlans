"use client"

// web/app/hooks/useToastsForaDoPainel.ts
//
// Keeps the toasts off an assistant panel anchored to the right of the screen.
//
// The Toaster (sonner, root layout) stacks the toasts in the bottom right
// corner, and that is where the editor's assistant drawer and the Home's
// conversation keep their message field: a toast landed on what the person was
// typing, send button included. While a panel is on screen, this hook tells the
// Toaster where it is, in two root CSS variables, and `globals.css` picks by
// width which one moves the toasts: beside the panel while it is a column,
// above its field once it takes the screen (phone).
//
// Measured, not derived from props: the drawer is docked flush, the Home panel
// floats 24px from the corner, and both are resized by dragging.
import { useEffect, type RefObject } from "react"

/** How much of the screen's right edge the panel takes (left of it is free). */
const OCUPA_DIREITA = "--painel-ocupa-direita"
/** How much of the screen's bottom edge the panel's field takes. */
const OCUPA_BAIXO = "--painel-ocupa-baixo"

/**
 * @param painel  the panel's outer element.
 * @param campo   its message field (the form at the bottom).
 * @param ativo   whether the panel is on screen now.
 * @param folga   extra room beside the panel, for what sits right next to it
 *                (the canvas's toolbar column, in the editor).
 */
export function useToastsForaDoPainel(
  painel: RefObject<HTMLElement | null>,
  campo: RefObject<HTMLElement | null>,
  ativo: boolean,
  folga = 0,
): void {
  useEffect(() => {
    const elemento = painel.current
    if (!ativo || !elemento) return
    const raiz = document.documentElement

    const medir = () => {
      // `clientWidth`/`clientHeight`, not `innerWidth`: the toaster is
      // `position: fixed`, and its edges are the viewport's without the scrollbar.
      const ladoDoPainel = raiz.clientWidth - elemento.getBoundingClientRect().left
      const topoDoCampo = campo.current ? raiz.clientHeight - campo.current.getBoundingClientRect().top : 0
      raiz.style.setProperty(OCUPA_DIREITA, `${Math.max(0, Math.round(ladoDoPainel + folga))}px`)
      raiz.style.setProperty(OCUPA_BAIXO, `${Math.max(0, Math.round(topoDoCampo))}px`)
    }

    medir()
    // The width comes from dragging the handle and the field grows with the
    // text; the window, from the person. `animationend`: the Home panel slides in
    // from the right, and the first measure catches it still on its way.
    const observador = new ResizeObserver(medir)
    observador.observe(elemento)
    if (campo.current) observador.observe(campo.current)
    window.addEventListener("resize", medir)
    elemento.addEventListener("animationend", medir)
    return () => {
      observador.disconnect()
      window.removeEventListener("resize", medir)
      elemento.removeEventListener("animationend", medir)
      raiz.style.removeProperty(OCUPA_DIREITA)
      raiz.style.removeProperty(OCUPA_BAIXO)
    }
  }, [painel, campo, ativo, folga])
}
