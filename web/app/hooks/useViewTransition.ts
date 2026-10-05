"use client"

import { useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"

export type ViewTransitionLike = {
  skipTransition: () => void
  ready?: Promise<void>
  /** Settles when the animation ends, skipped or not. */
  finished?: Promise<void>
}

export type TransitionOptions = {
  /**
   * Ceiling on the wait for the route commit, in ms (default `MAX_WAIT_MS`).
   * The mode switcher (Chat / Workspace) raises it: the two sides of the switch
   * are prefetched, but the Home's globe and the dashboard's first render take
   * longer than a cached listing, and its animation is the point of the click.
   */
  maxWaitMs?: number
}

type DocumentWithTransition = Document & {
  startViewTransition?: (cb: () => void | Promise<void>) => ViewTransitionLike
}

// Ceiling on the wait for the route commit. Routes already in cache commit in a
// few frames; the editor's (`/workflow/[id]`) downloads React Flow and Monaco and
// takes seconds — holding the transition for all that time would leave the
// screen frozen on a static snapshot, which is worse than no transition at all.
const MAX_WAIT_MS = 200
// Polling via `setTimeout`, and NOT via `requestAnimationFrame`: while the
// `startViewTransition` callback has not resolved, the browser suspends
// rendering of the document and rAF callbacks stop running. Timers don't.
const PROBE_INTERVAL_MS = 16

function documentWithTransition(): DocumentWithTransition | null {
  if (typeof document === "undefined") return null
  const doc = document as DocumentWithTransition
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
function navigateWithTransition(
  navegar: () => void,
  href: string,
  { maxWaitMs = MAX_WAIT_MS }: TransitionOptions = {},
): ViewTransitionLike | null {
  const doc = documentWithTransition()
  if (!doc) {
    navegar()
    return null
  }

  // `location.pathname` is the commit signal observable from outside Next: the App
  // Router syncs history in a `useInsertionEffect`, that is, in the commit phase
  // of the new route and before paint.
  const destino = new URL(href, window.location.href).pathname
  // A holder object instead of `let`: the callback below reads the transition that
  // `startViewTransition` itself returns. It is only called after the assignment
  // has happened, but writing the direct reference inside the variable's own
  // initializer does not pass TS.
  const transicao: { atual?: ViewTransitionLike } = {}

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
          if (Date.now() - inicio >= maxWaitMs) return encerrar(false)
          sonda = setTimeout(verificar, PROBE_INTERVAL_MS)
        }

        sonda = setTimeout(verificar, PROBE_INTERVAL_MS)
      }),
  )

  // `ready` rejects with AbortError when the transition is skipped — without this
  // `catch` the deliberate discard shows up in the console as an unhandled error.
  transicao.atual?.ready?.catch(() => {})
  // Same for `finished`, which callers chain cleanup on.
  transicao.atual?.finished?.catch(() => {})
  return transicao.atual ?? null
}

// Wrapper around Next.js's `useRouter`. In browsers without View Transitions
// (Firefox, Safari <18) it falls back to the default behavior.
//
// Usage:
//   const router = useViewTransitionRouter()
//   router.push("/projects")
//   router.push("/dashboard", { maxWaitMs: 600 })  // returns the transition, or null
export function useViewTransitionRouter() {
  const router = useRouter()

  const push = useCallback(
    (href: string, opcoes?: TransitionOptions) =>
      navigateWithTransition(() => router.push(href), href, opcoes),
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
