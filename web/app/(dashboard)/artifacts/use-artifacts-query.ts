"use client"
import { useCallback, useEffect, useMemo, useState } from "react"
import { infiniteQueryOptions, useInfiniteQuery, useQueryClient } from "@tanstack/react-query"
import { GisFlowService } from "@/service/GisFlowService"
import type { IArtifactItem } from "@/service/types"

export type ArtifactTab = "execution" | "publication"

/** Tamanho da página. O "ver mais" soma uma página por clique — a tela nunca
 *  mais baixa a coleção inteira de artefatos do usuário. */
export const PAGE_SIZE = 50

interface Filtros { kind: ArtifactTab; search: string; fmt?: string; workspaceId?: string }

/**
 * A listagem como consulta infinita: a chave são os filtros, a página é o
 * offset. Fora do hook para que a recarga peça ao cliente a MESMA consulta —
 * chave, busca e paginação — em vez de uma cópia que divergisse.
 */
function consultaDeArtefatos({ kind, search, fmt, workspaceId }: Filtros) {
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
      // O service não lança: a falha volta em `res.error`. Lançar aqui põe a
      // consulta em erro SEM tocar nas páginas já carregadas — falha de rede
      // não é "nenhum artefato". Quando o 500 do "Ver mais" gravava
      // `total = 0`, o rodapé passava a dizer "50 de 0", o botão sumia e as
      // outras 130 linhas ficavam inalcançáveis.
      if (res.error || !res.data) throw new Error(res.error?.message ?? "Erro ao carregar artefatos.")
      return { items: res.data.items ?? [], total: res.data.total ?? 0 }
    },
    initialPageParam: 0,
    // O próximo offset é o que já veio; a lista acaba quando alcança o total da
    // resposta mais recente (o total é do filtro inteiro, não da página).
    getNextPageParam: (ultima, paginas) => {
      const carregados = paginas.reduce((n, p) => n + p.items.length, 0)
      return carregados < ultima.total ? carregados : undefined
    },
  })
}

/**
 * Uma página de artefatos por vez, com acumulação no "ver mais".
 *
 * É a prova da camada de dados (docs/specs/screen-patterns.md §10): o que o hook
 * fazia à mão agora é da consulta. A chave (os filtros) descarta a resposta de
 * um filtro que já não é o atual — era o `seq`; o offset é derivado das
 * páginas; e `fetchNextPage` tem identidade estável — é o que obriga o
 * `useExecucoes` a guardar o offset num ref, para não anular o memo da
 * `TabelaExecucoes`, que recebe o `carregarMais` como prop.
 *
 * O que a tela mostra não mudou (tela-de-artefatos.test.tsx):
 *   - sem cache: os padrões do cliente (lib/consultas.ts) fazem cada montagem e
 *     cada troca de filtro começar do zero, com o skeleton, como antes — por
 *     isso não há `placeholderData: keepPreviousData` aqui: a tela zera a lista
 *     na troca de filtro de propósito, em vez de deixar a do filtro anterior
 *     sob o chip do novo;
 *   - `loading` é a busca da 1ª página (1ª carga, filtro, recarga) e
 *     `loadingMore` a do "Ver mais", que não troca a tabela por skeletons;
 *   - o erro é mensagem e preserva as páginas carregadas.
 */
export function useArtifactsQuery({ kind, search, fmt, workspaceId, enabled }: {
  kind: ArtifactTab; search: string; fmt?: string; workspaceId?: string; enabled: boolean
}) {
  const cliente = useQueryClient()
  const consulta = useMemo(
    () => consultaDeArtefatos({ kind, search, fmt, workspaceId }),
    [kind, search, fmt, workspaceId],
  )
  // O gate de `enabled` evita a requisição sem workspace_id que sairia
  // enquanto o contexto de workspace ainda está carregando (e traria artefatos
  // de todos os workspaces, só para descartá-los no fetch seguinte).
  const {
    data, error, isPending, isFetching, isFetchingNextPage, hasNextPage, fetchNextPage, dataUpdatedAt,
  } = useInfiniteQuery({ ...consulta, enabled })

  const items = useMemo(() => data?.pages.flatMap(p => p.items) ?? [], [data])

  // Sair da chave (outro filtro, outra aba, outra tela) cancela a busca dela.
  // O `queryFn` não aborta a requisição, e o `gcTime: 0` só descarta a consulta
  // ociosa: sem isto, um "Ver mais" em voo mantinha viva a consulta da chave
  // que a tela deixou, e voltar a ela (ou remontar a tela) pegava carona nessa
  // busca e mostrava a lista guardada, sem skeleton e sem buscar a 1ª página
  // de novo. Cancelada, ela volta ao que era antes da busca, fica ociosa e o
  // `gcTime: 0` a descarta: a volta começa do zero, como a tela fazia.
  useEffect(() => () => {
    void cliente.cancelQueries({ queryKey: consulta.queryKey, exact: true })
  }, [cliente, consulta])

  // Carimbo (ms) da última resposta ACEITA nesta montagem — o gate da
  // precedência de estados da página: enquanto `null`, nenhuma carga vingou
  // (1ª carga = skeleton; erro = cartão). Não é o `dataUpdatedAt` da consulta
  // porque ele zera com a chave nova: um filtro que falha depois de uma carga
  // aceita é aviso âmbar, com a barra de filtros na tela para a pessoa sair
  // dele — não o cartão, que a esconde.
  const [atualizadoEm, setAtualizadoEm] = useState<number | null>(null)
  if (dataUpdatedAt > (atualizadoEm ?? 0)) setAtualizadoEm(dataUpdatedAt)

  const loadMore = useCallback(() => { void fetchNextPage() }, [fetchNextPage])

  // Recarregar volta à PRIMEIRA página (`pages: 1`): o `refetch` de uma
  // consulta infinita refaria, uma a uma, todas as páginas já abertas. Durante
  // a busca as páginas anteriores ficam na consulta — se ela falhar, a lista
  // continua inteira sob o aviso. Um "Ver mais" em voo é cancelado antes, e a
  // recarga vence, como vencia pelo `seq`.
  const reload = useCallback(() => {
    void cliente.cancelQueries({ queryKey: consulta.queryKey, exact: true })
    cliente.infiniteQuery({ ...consulta, pages: 1, staleTime: 0 }).catch(() => {})
  }, [cliente, consulta])

  return {
    items,
    total:       data?.pages.at(-1)?.total ?? 0,
    // Como antes, o erro sai da tela enquanto uma nova busca está em voo.
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
 * Interseção da seleção com o que está CARREGADO na tela.
 *
 * A tela é escopada por workspace e trocar de workspace não a remonta: a
 * seleção feita no workspace A sobrevivia à troca e o botão "Excluir 10"
 * continuava lá, com nenhuma linha marcada visível. Confirmar apagava, de
 * verdade, 10 artefatos de OUTRO workspace (o backend só exige role editor+ em
 * algum workspace do usuário, então a exclusão passava). Derivar os alvos da
 * lista visível torna esse caminho impossível, mesmo que algum id escape do
 * reset de seleção.
 */
export function idsSelecionadosVisiveis(
  items: IArtifactItem[],
  selecionados: Set<string>,
): string[] {
  return items.filter(i => selecionados.has(i.id_hash)).map(i => i.id_hash)
}
