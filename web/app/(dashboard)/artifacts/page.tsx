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
 * Header scope sentence: how many artifacts the open tab has. Zero only
 * becomes "Nenhum … ainda" (first use) when there is NO slice — under an
 * active filter that zeroes it, saying "ainda" (yet) would lie (the workspace
 * has artifacts, none match), so we use a filter sentence. With a count,
 * "N … de execução".
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

  // The search goes to the SERVER with debounce. Before, every keystroke
  // re-filtered the whole collection in memory (and the whole collection was
  // literally everything the user ever produced), which froze the caret.
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

  // ── Selection ───────────────────────────────────────────────────────────────

  // Stable identity (functional update, no deps): it is what makes the rows'
  // React.memo worth anything.
  // `toggleAll` needs the current list without depending on it — otherwise it
  // becomes a new callback on every server response again, and the rows' memo misses.
  const itemsRef = useRef<IArtifactItem[]>([])
  itemsRef.current = items

  // The screen is scoped by workspace, and switching workspace in the header
  // selector remounts nothing: without this reset, workspace A's selection
  // survived the switch, the button kept saying "Excluir 10" with NO row
  // checked on screen, and confirming deleted (for real, including in MinIO)
  // 10 artifacts from another workspace. Search/format/tab come in too for the
  // same reason, in a less severe form: they would count what left the screen.
  useEffect(() => {
    setSelected(prev => (prev.size > 0 ? new Set() : prev))
  }, [workspace?.id_hash, debouncedSearch, formatFilter, tab])

  /** What the red button and the dialog promise to delete: the intersection of
   *  the selection with what is LOADED. That way the label never talks about
   *  artifacts the user is not seeing, and the deletion never reaches what
   *  left the screen through a scope change. */
  const idsParaExcluir = useMemo(
    () => idsSelecionadosVisiveis(items, selected),
    [items, selected],
  )

  // Name of the single target, so the dialog shows it in angle quotes.
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

  /** Checks/unchecks what is LOADED — with pagination there is no longer an
   *  "all" that fits on screen. The delete button counts the whole Set. */
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

  // ── Deletion ──────────────────────────────────────────────────────────────
  // The shared `DeleteDialog` carries the "deleting" lock inside: this handler
  // is async, it awaits, and the page only closes the dialog on success
  // (on error the dialog stays open to try again).
  async function handleBatchDelete() {
    const alvos = idsParaExcluir
    if (alvos.length === 0) return
    try {
      // `deleteArtifact`/`batchDeleteArtifacts` do NOT throw: like every
      // GisFlowService method, they catch internally and return `IResponse`
      // with `error`. A lone `catch` was unreachable for an HTTP failure, so a
      // 403/500 fell into the success path: a "deleted" toast and a reload that
      // brought the artifacts back.
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
      // The network dropping mid-await can still throw.
      createToast.error("Falha ao excluir artefatos.")
    }
  }

  // ── Available formats ─────────────────────────────────────────────────────
  // Accumulated from what has already been loaded: deriving them from the
  // current page would make the chips vanish right after picking a format (the
  // server returns only that one), trapping the filter with no way back.
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

  // ── State precedence (contract §3) ──────────────────────────────────────────
  // loading → error (only if there was never a load) → content. `atualizadoEm`
  // is the gate: while null, no load has succeeded.
  const primeiraCarga = loading && atualizadoEm == null
  const erroDeEspinha = !!erro && atualizadoEm == null
  const temRecorte = debouncedSearch.length > 0 || formatFilter !== "all"

  return (
    <PageRoot>
      <CabecalhoDeArtefatos
        // During ANY load (`loading`) the subtitle becomes a skeleton instead of
        // a stale/zeroed number — switching filter/tab zeroes `total` before the
        // response arrives, and showing "Nenhum artefato ainda" in that interval
        // was misleading (contract §3: loading takes precedence).
        subtitulo={(atualizadoEm == null || loading) ? null : textoDoSubtitulo(tab, total, temRecorte)}
        atualizando={loading}
        aExcluir={idsParaExcluir.length}
        podeExcluir={podeEditar}
        onAtualizar={reload}
        onExcluir={() => setDeleteOpen(true)}
      />

      {/* Tabs + search + format. The tabs are always visible; the filters and the
          count only once there is a list to filter. */}
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

      {/* Contract §3 precedence: loading → error (only on the 1st load) →
          content. `loading` covers the 1st load AND reloads (tab/filter/search
          change, which zero the list): in that interval we show the skeleton, never
          the empty states — otherwise "no result"/"first use" would flash during
          loading. A reload that fails over the ready list (Refresh/See more
          button) falls into the content branch with the amber notice, without
          erasing the table. */}
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

          {/* See more — one page per click, instead of the whole collection. */}
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
