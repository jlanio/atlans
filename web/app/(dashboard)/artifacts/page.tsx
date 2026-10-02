"use client"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IArtifactItem } from "@/service/types"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { useWorkspace } from "@/context/WorkspaceContext"
import { createToast } from "@/utils/createToast"
import { formatarInteiro, plural } from "@/lib/formatos"
import { CabecalhoDeArtefatos } from "@/app/components/artifacts/cabecalho"
import { AbasDeArtefatos, BuscaDeArtefatos, FiltroDeFormato } from "@/app/components/artifacts/controles"
import { ArtifactTable } from "@/app/components/artifacts/tabela"
import { ExcluirArtefatosDialog } from "@/app/components/artifacts/excluir-dialog"
import {
  SkeletonDeArtefatos, ErroDeCarga, VazioPrimeiroUso, SemResultado, AvisoDeRecarga,
} from "@/app/components/artifacts/estados"
import {
  useArtifactsQuery, idsSelecionadosVisiveis, type ArtifactTab,
} from "./use-artifacts-query"

type Tab = ArtifactTab

/**
 * Frase de escopo do cabeçalho: quantos artefatos a aba aberta tem. O zero só
 * vira "Nenhum … ainda" (primeiro uso) quando NÃO há recorte — sob um filtro
 * ativo que zera, dizer "ainda" mentiria (o workspace tem artefatos, nenhum
 * casa), então usamos uma frase de filtro. Com contagem, "N … de execução".
 */
function textoDoSubtitulo(tab: Tab, total: number, temRecorte: boolean): string {
  if (total === 0) {
    if (temRecorte) return "Nenhum resultado para o filtro"
    return tab === "execution" ? "Nenhum artefato ainda" : "Nenhuma publicação ainda"
  }
  return tab === "execution"
    ? `${plural(total, "artefato")} de execução`
    : plural(total, "publicação", "publicações")
}

export default function ArtifactsPage() {
  const [tab, setTab] = useState<Tab>("execution")
  const [search, setSearch] = useState("")
  const [formatFilter, setFormatFilter] = useState<string>("all")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [deleteOpen, setDeleteOpen] = useState(false)
  const { current: workspace, canEdit: podeEditar, loading: workspaceLoading } = useWorkspace()

  // A busca vai ao SERVIDOR com debounce. Antes cada tecla refiltrava a coleção
  // inteira em memória (e a coleção inteira era literalmente tudo o que o
  // usuário já produziu), o que congelava o caret.
  const [debouncedSearch, setDebouncedSearch] = useState("")
  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(search.trim()), 300)
    return () => clearTimeout(id)
  }, [search])

  const {
    items, total, erro, loading, loadingMore, hasMore, atualizadoEm, loadMore, reload,
  } = useArtifactsQuery({
    kind:        tab,
    search:      debouncedSearch,
    fmt:         formatFilter === "all" ? undefined : formatFilter,
    workspaceId: workspace?.id_hash,
    enabled:     !workspaceLoading,
  })

  // ── Seleção ─────────────────────────────────────────────────────────────────

  // Identidade estável (atualização funcional, sem deps): é o que faz o
  // React.memo das linhas valer alguma coisa.
  // `toggleAll` precisa da lista atual sem depender dela — senão volta a ser um
  // callback novo a cada resposta do servidor, e o memo das linhas não acerta.
  const itemsRef = useRef<IArtifactItem[]>([])
  itemsRef.current = items

  // A tela é escopada por workspace, e trocar de workspace no seletor do
  // cabeçalho não remonta nada: sem este reset a seleção do workspace A
  // sobrevivia à troca, o botão continuava dizendo "Excluir 10" com NENHUMA
  // linha marcada na tela, e confirmar apagava (de verdade, inclusive no MinIO)
  // 10 artefatos de outro workspace. Busca/formato/aba entram junto pelo mesmo
  // motivo, em versão menos grave: contariam o que saiu da tela.
  useEffect(() => {
    setSelected(prev => (prev.size > 0 ? new Set() : prev))
  }, [workspace?.id_hash, debouncedSearch, formatFilter, tab])

  /** O que o botão vermelho e o diálogo prometem apagar: a interseção da
   *  seleção com o que está CARREGADO. Assim o rótulo nunca fala de artefatos
   *  que o usuário não está vendo, e a exclusão nunca alcança o que sumiu da
   *  tela por uma troca de escopo. */
  const idsParaExcluir = useMemo(
    () => idsSelecionadosVisiveis(items, selected),
    [items, selected],
  )

  // Nome do único alvo, para o diálogo mostrá-lo entre aspas angulares.
  const nomeUnico = useMemo(() => {
    if (idsParaExcluir.length !== 1) return null
    return items.find(i => i.id_hash === idsParaExcluir[0])?.filename ?? null
  }, [idsParaExcluir, items])

  const toggleSelect = useCallback((id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  /** Marca/desmarca o que está CARREGADO — com paginação não existe mais um
   *  "todos" que caiba na tela. O botão de excluir conta o Set inteiro. */
  const toggleAll = useCallback(() => {
    setSelected(prev => {
      const idsNaTela = itemsRef.current.map(i => i.id_hash)
      const todosMarcados = idsNaTela.length > 0 && idsNaTela.every(id => prev.has(id))
      const next = new Set(prev)
      for (const id of idsNaTela) {
        if (todosMarcados) next.delete(id)
        else next.add(id)
      }
      return next
    })
  }, [])

  function switchTab(t: Tab) {
    setTab(t)
    setSelected(new Set())
    setFormatFilter("all")
    setSearch("")
    setDebouncedSearch("")
  }

  function limparFiltros() {
    setSearch("")
    setDebouncedSearch("")
    setFormatFilter("all")
  }

  // ── Exclusão ──────────────────────────────────────────────────────────────
  // O `DeleteDialog` compartilhado carrega a trava de "excluindo" por dentro:
  // este handler é async, ele aguarda, e a página só fecha o diálogo no sucesso
  // (no erro o diálogo fica aberto para tentar de novo).
  async function handleBatchDelete() {
    const alvos = idsParaExcluir
    if (alvos.length === 0) return
    try {
      // `deleteArtifact`/`batchDeleteArtifacts` NÃO lançam: como todo método do
      // GisFlowService, capturam por dentro e devolvem `IResponse` com `error`.
      // Um `catch` sozinho era inalcançável para falha HTTP, então um 403/500
      // caía no caminho de sucesso: toast de "excluídos" e um reload que
      // trazia os artefatos de volta.
      const res = alvos.length === 1
        ? await GisFlowService.deleteArtifact(alvos[0])
        : await GisFlowService.batchDeleteArtifacts(alvos)

      if (res?.error) {
        createToast.error("Falha ao excluir artefatos.", res.error.message)
        return
      }

      createToast.success(`${plural(alvos.length, "artefato")} ${alvos.length > 1 ? "excluídos" : "excluído"}.`)
      setSelected(new Set())
      setDeleteOpen(false)
      reload()
    } catch {
      // Rede caindo no meio do await ainda pode lançar.
      createToast.error("Falha ao excluir artefatos.")
    }
  }

  // ── Formatos disponíveis ──────────────────────────────────────────────────
  // Acumulados a partir do que já foi carregado: derivá-los da página atual
  // faria os chips sumirem justamente depois de escolher um formato (o servidor
  // devolve só ele), prendendo o filtro sem volta.
  const [availableFormats, setAvailableFormats] = useState<string[]>([])
  useEffect(() => { setAvailableFormats([]) }, [tab, workspace?.id_hash])
  useEffect(() => {
    if (items.length === 0) return
    setAvailableFormats(prev => {
      const vistos = new Set(prev)
      const antes = vistos.size
      for (const i of items) if (i.format) vistos.add(i.format)
      return vistos.size === antes ? prev : [...vistos].sort()
    })
  }, [items])

  // ── Precedência de estados (contrato §3) ────────────────────────────────────
  // carregando → erro (só se nunca houve carga) → conteúdo. `atualizadoEm` é o
  // gate: enquanto null, nenhuma carga vingou.
  const primeiraCarga = loading && atualizadoEm == null
  const erroDeEspinha = !!erro && atualizadoEm == null
  const temRecorte = debouncedSearch.length > 0 || formatFilter !== "all"

  return (
    <PageRoot>
      <CabecalhoDeArtefatos
        // Durante QUALQUER carga (`loading`) o subtítulo vira esqueleto em vez de
        // um número obsoleto/zerado — a troca de filtro/aba zera `total` antes da
        // resposta chegar, e mostrar "Nenhum artefato ainda" nesse intervalo
        // enganava (contrato §3: carregando tem precedência).
        subtitulo={(atualizadoEm == null || loading) ? null : textoDoSubtitulo(tab, total, temRecorte)}
        atualizando={loading}
        aExcluir={idsParaExcluir.length}
        podeExcluir={podeEditar}
        onAtualizar={reload}
        onExcluir={() => setDeleteOpen(true)}
      />

      {/* Abas + busca + formato. As abas ficam sempre visíveis; os filtros e a
          contagem só quando já há uma lista para filtrar. */}
      <div className="flex flex-col gap-3">
        <AbasDeArtefatos tab={tab} total={total} onTab={switchTab} />
        {!primeiraCarga && !erroDeEspinha && (
          <div className="flex flex-wrap items-center gap-3">
            <BuscaDeArtefatos valor={search} onChange={setSearch} />
            <FiltroDeFormato formatos={availableFormats} atual={formatFilter} onFormato={setFormatFilter} />
            {!erro && total > 0 && (
              <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                {formatarInteiro(items.length)} de {tab === "execution" ? plural(total, "artefato") : plural(total, "publicação", "publicações")}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Precedência do contrato §3: carregando → erro (só na 1ª carga) →
          conteúdo. `loading` cobre a 1ª carga E as recargas (troca de aba/filtro/
          busca, que zeram a lista): nesse intervalo mostramos o skeleton, nunca os
          estados vazios — senão «sem resultado»/«primeiro uso» piscariam durante o
          carregamento. Uma recarga que falha sobre a lista pronta (botão Atualizar/
          Ver mais) cai no ramo de conteúdo com o aviso âmbar, sem apagar a tabela. */}
      {loading ? (
        <SkeletonDeArtefatos />
      ) : erroDeEspinha ? (
        <ErroDeCarga mensagem={erro!} onTentar={reload} />
      ) : (
        <>
          {erro && <AvisoDeRecarga mensagem={erro} onTentar={reload} />}

          {items.length === 0 ? (
            temRecorte ? (
              <SemResultado q={debouncedSearch} formato={formatFilter} tab={tab} onLimpar={limparFiltros} />
            ) : (
              <VazioPrimeiroUso tab={tab} />
            )
          ) : (
            <ArtifactTable
              items={items}
              tab={tab}
              selected={selected}
              isOwner={podeEditar}
              onToggle={toggleSelect}
              onToggleAll={toggleAll}
            />
          )}

          {/* Ver mais — uma página por clique, em vez da coleção inteira. */}
          {hasMore && (
            <div className="flex justify-center">
              <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore} className="max-md:h-10">
                {loadingMore ? "Carregando…" : `Ver mais (${formatarInteiro(total - items.length)} ${total - items.length === 1 ? "restante" : "restantes"})`}
              </Button>
            </div>
          )}
        </>
      )}

      <ExcluirArtefatosDialog
        aberto={deleteOpen}
        quantidade={idsParaExcluir.length}
        nomeUnico={nomeUnico}
        onConfirmar={handleBatchDelete}
        onFechar={() => setDeleteOpen(false)}
      />
    </PageRoot>
  )
}
