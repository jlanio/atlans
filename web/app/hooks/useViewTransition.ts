"use client"

import { useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"

type TransicaoDeVisao = {
  skipTransition: () => void
  ready?: Promise<void>
}

type DocumentoComTransicao = Document & {
  startViewTransition?: (cb: () => void | Promise<void>) => TransicaoDeVisao
}

// Ceiling on the wait for the route commit. Routes already in cache commit in a
// few frames; the editor's (`/workflow/[id]`) downloads React Flow and Monaco and
// takes seconds — holding the transition for all that time would leave the
// screen frozen on a static snapshot, which is worse than no transition at all.
const TETO_DE_ESPERA_MS = 200
// Polling via `setTimeout`, and NOT via `requestAnimationFrame`: while the
// `startViewTransition` callback has not resolved, the browser suspends
// rendering of the document and rAF callbacks stop running. Timers don't.
const INTERVALO_DA_SONDA_MS = 16

function documentoComTransicao(): DocumentoComTransicao | null {
  if (typeof document === "undefined") return null
  const doc = document as DocumentoComTransicao
  return typeof doc.startViewTransition === "function" ? doc : null
}

/**
 * Navigates by wrapping the route change in `document.startViewTransition`.
 *
 * The callback returns a PROMISE that only resolves once the route has actually
 * committed. Without it — which was the case — the App Router's `router.push`
 * returns with the DOM still unchanged: the browser took the "new" snapshot of
 * the SAME screen and cross-faded two identical snapshots. The result was the
 * exact opposite of the intended effect: the whole page flashed and slid the 4px
 * of `vt-fade-in` without changing route, and the real change, seconds later,
 * happened with no transition at all. That was the "wobble" of the project
 * listing when opening a workflow.
 *
 * If the route does not commit within the ceiling, `skipTransition()` discards
 * the animation: with no DOM change there is nothing to animate, and animating
 * anyway is the bug.
 */
function navegarComTransicao(navegar: () => void, href: string) {
  const doc = documentoComTransicao()
  if (!doc) {
    navegar()
    return
  }

  // `location.pathname` is the commit signal observable from outside Next: the App
  // Router syncs history in a `useInsertionEffect`, that is, in the commit phase
  // of the new route and before paint.
  const destino = new URL(href, window.location.href).pathname
  // A holder object instead of `let`: the callback below reads the transition that
  // `startViewTransition` itself returns. It is only called after the assignment
  // has happened, but writing the direct reference inside the variable's own
  // initializer does not pass TS.
  const transicao: { atual?: TransicaoDeVisao } = {}

  transicao.atual = doc.startViewTransition(
    () =>
      new Promise<void>(resolve => {
        navegar()

        let pendente = true
        let sonda: ReturnType<typeof setTimeout> | null = null
        const inicio = Date.now()

        const encerrar = (comitou: boolean) => {
          if (!pendente) return
          pendente = false
          if (sonda) clearTimeout(sonda)
          if (!comitou) transicao.atual?.skipTransition()
          resolve()
        }

        const verificar = () => {
          if (window.location.pathname === destino) return encerrar(true)
          if (Date.now() - inicio >= TETO_DE_ESPERA_MS) return encerrar(false)
          sonda = setTimeout(verificar, INTERVALO_DA_SONDA_MS)
        }

        sonda = setTimeout(verificar, INTERVALO_DA_SONDA_MS)
      }),
  )

  // `ready` rejects with AbortError when the transition is skipped — without this
  // `catch` the deliberate discard shows up in the console as an unhandled error.
  transicao.atual?.ready?.catch(() => {})
}

// Wrapper around Next.js's `useRouter`. In browsers without View Transitions
// (Firefox, Safari <18) it falls back to the default behavior.
//
// Usage:
//   const router = useViewTransitionRouter()
//   router.push("/projects")
export function useViewTransitionRouter() {
  const router = useRouter()

  const push = useCallback(
    (href: string) => navegarComTransicao(() => router.push(href), href),
    [router],
  )

  // `useMemo`: consumers derive callbacks with `[router]` in the dependencies
  // and pass them to memoized lists. A new object on every render invalidated
  // those dependencies every time, and the `React.memo` of the /projects cards
  // never hit — the whole list re-rendered on every search keystroke, which is
  // exactly what the memoization there claims to avoid. The App Router's
  // `useRouter` already returns a stable instance, so only `push` goes in.
  return useMemo(
    () => ({ push, prefetch: router.prefetch }),
    [push, router],
  )
}
