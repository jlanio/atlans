"use client"
import { useCallback, useEffect, useMemo, useState } from "react"
import { infiniteQueryOptions, useInfiniteQuery, useQueryClient } from "@tanstack/react-query"
import { GisFlowService } from "@/service/GisFlowService"
import type { IArtifactItem } from "@/service/types"

export type ArtifactTab = "execution" | "publication"

/** Page size. "See more" adds one page per click — the screen never again
 *  downloads the user's whole collection of artifacts. */
export const PAGE_SIZE = 50

interface Filtros { kind: ArtifactTab; search: string; fmt?: string; workspaceId?: string }

/**
 * The listing as an infinite query: the key is the filters, the page is the
 * offset. Outside the hook so that the reload asks the client for the SAME
 * query — key, fetch and pagination — instead of a copy that could diverge.
 */
function artifactsQuery({ kind, search, fmt, workspaceId }: Filtros) {
  return infiniteQueryOptions({
    queryKey: ["artefatos", { kind, search, fmt, workspaceId }],
    queryFn: async ({ pageParam }) => {
      const res = await GisFlowService.getArtifacts({
        kind,
        search:       search || undefined,
        fmt,
        workspace_id: workspaceId,
        limit:        PAGE_SIZE,
        offset:       pageParam,
      })
      // The service does not throw: the failure comes back in `res.error`. Throwing
      // here puts the query in error WITHOUT touching the pages already loaded —
      // a network failure is not "no artifacts". When the 500 from "Ver mais"
      // stored `total = 0`, the footer started saying "50 de 0", the button
      // vanished and the other 130 rows became unreachable.
      if (res.error || !res.data) throw new Error(res.error?.message ?? "Erro ao carregar artefatos.")
      return { items: res.data.items ?? [], total: res.data.total ?? 0 }
    },
    initialPageParam: 0,
    // The next offset is what has already come; the list ends when it reaches the
    // total of the latest response (the total is for the whole filter, not the page).
    getNextPageParam: (ultima, paginas) => {
      const carregados = paginas.reduce((n, p) => n + p.items.length, 0)
      return carregados < ultima.total ? carregados : undefined
    },
  })
}

/**
 * One page of artifacts at a time, accumulating on "see more".
 *
 * It is the proof of the data layer (docs/specs/screen-patterns.md §10): what the
 * hook did by hand now belongs to the query. The key (the filters) discards the
 * response of a filter that is no longer current — that used to be `seq`; the
 * offset is derived from the pages; and `fetchNextPage` has a stable identity —
 * which is what forces `useExecucoes` to keep the offset in a ref, so as not to
 * defeat the memo of `TabelaExecucoes`, which receives `carregarMais` as a prop.
 *
 * What the screen shows did not change (tela-de-artefatos.test.tsx):
 *   - no cache: the client defaults (lib/consultas.ts) make every mount and
 *     every filter change start from scratch, with the skeleton, as before —
 *     that is why there is no `placeholderData: keepPreviousData` here: the
 *     screen clears the list on filter change on purpose, instead of leaving
 *     the previous filter's list under the new one's chip;
 *   - `loading` is the fetch of the 1st page (1st load, filter, reload) and
 *     `loadingMore` that of "Ver mais", which does not swap the table for skeletons;
 *   - the error is a message and preserves the loaded pages.
 */
export function useArtifactsQuery({ kind, search, fmt, workspaceId, enabled }: {
  kind: ArtifactTab; search: string; fmt?: string; workspaceId?: string; enabled: boolean
}) {
  const cliente = useQueryClient()
  const consulta = useMemo(
    () => artifactsQuery({ kind, search, fmt, workspaceId }),
    [kind, search, fmt, workspaceId],
  )
  // The `enabled` gate avoids the request without workspace_id that would go
  // out while the workspace context is still loading (and would bring artifacts
  // from every workspace, only to discard them on the next fetch).
  const {
    data, error, isPending, isFetching, isFetchingNextPage, hasNextPage, fetchNextPage, dataUpdatedAt,
  } = useInfiniteQuery({ ...consulta, enabled })

  const items = useMemo(() => data?.pages.flatMap(p => p.items) ?? [], [data])

  // Leaving the key (another filter, another tab, another screen) cancels its fetch.
  // The `queryFn` does not abort the request, and `gcTime: 0` only discards an
  // idle query: without this, a "Ver mais" in flight kept alive the query of the
  // key the screen left, and going back to it (or remounting the screen)
  // piggybacked on that fetch and showed the stored list, with no skeleton and
  // without fetching the 1st page again. Once canceled, it returns to what it was
  // before the fetch, goes idle and `gcTime: 0` discards it: going back starts
  // from scratch, as the screen used to.
  useEffect(() => () => {
    void cliente.cancelQueries({ queryKey: consulta.queryKey, exact: true })
  }, [cliente, consulta])

  // Stamp (ms) of the last ACCEPTED response in this mount — the gate of the
  // page's state precedence: while `null`, no load has succeeded (1st load =
  // skeleton; error = card). It is not the query's `dataUpdatedAt` because that
  // resets with the new key: a filter that fails after an accepted load is an
  // amber notice, with the filter bar on screen so the person can get out of
  // it — not the card, which hides it.
  const [atualizadoEm, setUpdatedAt] = useState<number | null>(null)
  if (dataUpdatedAt > (atualizadoEm ?? 0)) setUpdatedAt(dataUpdatedAt)

  const loadMore = useCallback(() => { void fetchNextPage() }, [fetchNextPage])

  // Reloading goes back to the FIRST page (`pages: 1`): the `refetch` of an
  // infinite query would redo, one by one, every page already opened. During
  // the fetch the previous pages stay in the query — if it fails, the list
  // stays whole under the notice. A "Ver mais" in flight is canceled first, and
  // the reload wins, as it won via `seq`.
  const reload = useCallback(() => {
    void cliente.cancelQueries({ queryKey: consulta.queryKey, exact: true })
    cliente.infiniteQuery({ ...consulta, pages: 1, staleTime: 0 }).catch(() => {})
  }, [cliente, consulta])

  return {
    items,
    total:       data?.pages.at(-1)?.total ?? 0,
    // As before, the error leaves the screen while a new fetch is in flight.
    erro:        isFetching ? null : (error?.message ?? null),
    loading:     isPending || (isFetching && !isFetchingNextPage),
    loadingMore: isFetchingNextPage,
    atualizadoEm,
    hasMore:     hasNextPage,
    loadMore,
    reload,
  }
}

/**
 * Intersection of the selection with what is LOADED on screen.
 *
 * The screen is scoped by workspace and switching workspace does not remount
 * it: the selection made in workspace A survived the switch and the "Excluir 10"
 * button was still there, with no checked row visible. Confirming deleted, for
 * real, 10 artifacts from ANOTHER workspace (the backend only requires role
 * editor+ in some workspace of the user, so the deletion went through).
 * Deriving the targets from the visible list makes that path impossible, even
 * if some id escapes the selection reset.
 */
export function visibleSelectedIds(
  items: IArtifactItem[],
  selecionados: Set<string>,
): string[] {
  return items.filter(i => selecionados.has(i.id_hash)).map(i => i.id_hash)
}
