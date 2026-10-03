// web/lib/consultas.ts
//
// The @tanstack/react-query client, with the defaults of TODAY's screens.
//
// The data layer migrates screen by screen (docs/specs/screen-patterns.md §10).
// Each default below reproduces what the hand-written hooks already do, so that
// migrating a screen does not change what it shows: retrying, refetching on
// focus or caching is each query's decision, declared on it — never a silent
// inheritance from here.

import { QueryClient } from "@tanstack/react-query"

export function criarClienteDeConsultas(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // No screen retries a read that failed: the failure immediately becomes
        // the error card (1st load) or the reload notice. The library default
        // (three retries, 1 s + 2 s + 4 s) would hold the skeleton for about
        // 7 s before showing the error.
        retry: false,
        // No screen refetches on focus return or on reconnect. Screens that poll
        // turn both on in their own query (see §10).
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        // No cache: every mount and every filter change fetches again, with the
        // skeleton — that is what the screens do today. Whoever wants a cache
        // (the History TTL) declares `staleTime` and `gcTime` on its own query.
        staleTime: 0,
        gcTime: 0,
        // The request goes out even with `navigator.onLine` false, as it does today,
        // and the drop becomes an error. In the default mode ("online") the
        // query would be paused: an endless skeleton, no error card.
        networkMode: "always",
      },
      mutations: {
        networkMode: "always",
      },
    },
  })
}
