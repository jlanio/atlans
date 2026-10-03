"use client"
import { useSession } from "next-auth/react"
import { useCallback, useEffect, useRef, useState } from "react"

interface FetchState<T> {
  data: T | null
  /** A request is in flight — first load OR reload.
   *
   *  It is the signal for the Refresh button (`disabled` + spinning icon). It must
   *  NOT become "first load only": when that happened, the /admin/settings button
   *  and the ones on the observability screens never spun or got disabled again —
   *  the screen sat frozen during the GETs and the user clicked again, thinking
   *  the first click had not registered. */
  loading: boolean
  /** First load: there is NOTHING on screen yet. It is the gate for the skeleton. */
  firstLoad: boolean
  /** Reload with data already on screen (auto-refresh, search, Refresh button).
   *  Meant for a spinner/opacity; swapping the list for skeletons here is what
   *  made the table flash on every keystroke and every 15 seconds. */
  refreshing: boolean
  error: string | null
  /** Timestamp (ms) of the last ACCEPTED response; `null` while there has been none.
   *
   *  It is the gate for the error card (screen contract, §3.2): the card only
   *  takes over the screen with `error && atualizadoEm == null`. A reload that
   *  fails over a ready list keeps what was there — the warning comes from
   *  `onErroComDados`. `setData` does not touch it: data set by hand is not a
   *  server response. */
  atualizadoEm: number | null
  /** Reloads. Resolves with the data accepted in THIS load, or `null` if it failed
   *  or was superseded by a newer one (the generation guard discarded it). */
  refetch: () => Promise<T | null>
  /** Background reload (auto-refresh, returning to the tab): `refetch`, except in one
   *  case. With the 1st load in error, it retries WITHOUT swapping the card for the
   *  skeleton, and the card only goes away if the response arrives. Through
   *  `refetch`, every tick removed the card and put it back, and each return was a
   *  new `role="alert"`: the screen reader announced the same failure every 15 s.
   *  The card's "Tentar de novo" (try again) still goes through `refetch`: there it
   *  was the person who asked. */
  recarregarEmFundo: () => Promise<T | null>
  /** Replaces the data on screen without fetching: the optimistic update, what a
   *  POST/PUT returned. Accepts a function of the previous value, like `setState`. */
  setData: (valor: T | null | ((anterior: T | null) => T | null)) => void
}

export interface FetchOptions<T> {
  /** Each ACCEPTED response (it already passed the generation guard), in the same
   *  tick in which the hook stores it. For whoever mirrors the data outside the
   *  hook — the credentials context, the allowlist draft — without a frame of lag. */
  onDados?: (dados: T) => void
  /** A load that fails when an accepted response is already on screen: the error
   *  card does not take the list's place, and the warning comes from this
   *  (typically a toast). Receives the error message. Not called on the 1st load
   *  — there the error is the card. */
  onErroComDados?: (mensagem: string) => void
  /** When off (`false`), the load does not run and the state goes back to the
   *  initial one — no data, no error, `firstLoad` —, discarding whatever is in
   *  flight; when turned back on, it loads from scratch. For what only fetches
   *  while open (a modal) or for whoever is allowed (an admin screen). `true` by
   *  default. */
  ativo?: boolean
}

// Generic hook to fetch authenticated data (waits for status === "authenticated").
// debounceMs: minimum interval between executions (useful for real-time search inputs).
//
// The screens that redid this by hand — each with its own loading/refreshing/
// loadError/atualizadoEm and the session gate — diverged where it hurt: without
// the generation guard, the response for an old filter arrived later and
// overwrote the list for the current filter (Admin › Users).
export function useFetchData<T>(
  fetcher: () => Promise<{ data?: T | null; error?: { message?: string } | null } | null>,
  errorMsg = "Erro ao carregar dados.",
  deps: unknown[] = [],
  debounceMs = 0,
  opcoes: FetchOptions<T> = {},
): FetchState<T> {
  const { status } = useSession()
  const ativo = opcoes.ativo ?? true
  const [data, setDataState]            = useState<T | null>(null)
  const [firstLoad, setFirstLoad]       = useState(true)
  const [refreshing, setRefreshing]     = useState(false)
  const [error, setError]               = useState<string | null>(null)
  const [atualizadoEm, setUpdatedAt] = useState<number | null>(null)
  const timerRef                        = useRef<ReturnType<typeof setTimeout> | null>(null)

  // The caller recreates `fetcher` (and `errorMsg`) on every render; reading them
  // from a ref is what lets `executar` have a CONSTANT identity. Without it, every
  // `useEffect(..., [refetch])` — the 15s auto-refresh of /executores — redid
  // clearInterval + setInterval on every render, and on a screen that renders
  // frequently the interval never reached its end: the automatic refresh
  // simply stopped, with no sign of it in the UI.
  const fetcherRef  = useRef(fetcher)
  const errorMsgRef = useRef(errorMsg)
  const debounceRef = useRef(debounceMs)
  const optionsRef   = useRef(opcoes)
  fetcherRef.current  = fetcher
  errorMsgRef.current = errorMsg
  debounceRef.current = debounceMs
  optionsRef.current   = opcoes

  // `data` in a ref too: `executar` needs to know whether something is already on
  // screen to choose between skeleton and refresh, and reading it from state would
  // pin the callback. Same for the timestamp, which decides between the error card
  // and `onErroComDados`.
  const dataRef         = useRef<T | null>(null)
  const updatedAtRef = useRef<number | null>(null)

  // Generation counter: two overlapping executions (the URL/deps change while the
  // previous one is still resolving) must not let the OLD response overwrite the
  // new one — before, whichever resolved last won. Each `executar` carries a
  // number; on returning from the await, if the generation has already advanced
  // the result is stale and is ignored.
  const geracao = useRef(0)

  const executar = useCallback(async (inBackground: boolean): Promise<T | null> => {
    const gen = ++geracao.current
    // In the background and with no data on screen, nothing changes while the
    // fetch is in flight: no skeleton and no cleared error (see `recarregarEmFundo`).
    if (!inBackground || dataRef.current !== null) {
      if (dataRef.current === null) setFirstLoad(true)
      else setRefreshing(true)
      setError(null)
    }

    function falhou(mensagem: string) {
      setError(mensagem)
      if (updatedAtRef.current != null) optionsRef.current.onErroComDados?.(mensagem)
    }

    try {
      const result = await fetcherRef.current()
      if (gen !== geracao.current) return null
      if (result?.data != null) {
        const dados = result.data
        const agora = Date.now()
        dataRef.current = dados
        updatedAtRef.current = agora
        setDataState(dados)
        setUpdatedAt(agora)
        // The background reload does not clear the error on its way out: the response does.
        setError(null)
        optionsRef.current.onDados?.(dados)
        return dados
      }
      falhou(result?.error?.message ?? errorMsgRef.current)
      return null
    } catch (exc) {
      if (gen !== geracao.current) return null
      falhou(exc instanceof Error ? exc.message : errorMsgRef.current)
      return null
    } finally {
      // Always clears — if the fetcher throws (e.g. a non-axios network error), the
      // Refresh button would stay disabled forever. But only for the CURRENT
      // generation: a stale resolve must not turn off the new request's spinner.
      if (gen === geracao.current) {
        setFirstLoad(false)
        setRefreshing(false)
      }
    }
  }, [])
  // Without forwarding arguments: `refetch` goes straight down to `onClick`, and
  // the click event must not become `deFundo`.
  const refetch = useCallback(() => executar(false), [executar])
  const recarregarEmFundo = useCallback(() => executar(true), [executar])

  const setData = useCallback((valor: T | null | ((anterior: T | null) => T | null)) => {
    const novo = typeof valor === "function"
      ? (valor as (anterior: T | null) => T | null)(dataRef.current)
      : valor
    dataRef.current = novo
    setDataState(novo)
  }, [])

  useEffect(() => {
    if (!ativo) {
      // Off: whatever is in flight no longer writes, and the screen goes back to
      // the start — the next time it is turned on is a 1st load, with skeleton.
      geracao.current++
      dataRef.current = null
      updatedAtRef.current = null
      setDataState(null)
      setUpdatedAt(null)
      setError(null)
      setRefreshing(false)
      setFirstLoad(true)
      return
    }
    // The session may resolve as "unauthenticated": there is nothing to fetch, and
    // without this the skeleton would stay forever, because `firstLoad` starts as
    // true and nothing would turn it off.
    if (status === "unauthenticated") {
      setFirstLoad(false)
      return
    }
    if (status !== "authenticated") return
    if (debounceRef.current > 0) {
      timerRef.current = setTimeout(refetch, debounceRef.current)
    } else {
      refetch()
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, refetch, ativo, ...deps])

  // `loading` is the union of the two: whoever only wants to know "is it fetching?"
  // (Refresh button) reads `loading`; whoever decides between skeleton and list
  // reads `firstLoad`.
  return {
    data, loading: firstLoad || refreshing, firstLoad, refreshing, error, atualizadoEm,
    refetch, recarregarEmFundo, setData,
  }
}
