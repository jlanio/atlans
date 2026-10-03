"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { useSession } from "next-auth/react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IDriveFile } from "@/service/types"
import { useFetchData } from "@/app/hooks/useFetchData"
import { useWorkspace } from "@/context/WorkspaceContext"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { Checkbox } from "@/app/components/ui/checkbox"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { LocalBadge, isLocalDoExecutor } from "@/app/components/local-badge"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { TbDotsVertical, TbDownload, TbFileInfo, TbTrash } from "react-icons/tb"
import { createToast } from "@/utils/createToast"
import { formatLocal } from "@/lib/dayjs"
import { formatBytes } from "@/utils/formatters"
import { formatInteger, formatarQuando, plural } from "@/lib/formatos"
import { DriveHeader } from "@/app/components/drive/cabecalho"
import { ErroDeCarga, SemResultado, SkeletonDoDrive, VazioPrimeiroUso } from "@/app/components/drive/estados"
import { ExtBadge, ExtIcon } from "@/app/components/drive/ext"
import { DriveFilters } from "@/app/components/drive/filtros"
import { MetadataDialog, wasRewritten, lastWrite } from "@/app/components/drive/dialogs"
import { PaginationFooter } from "@/app/components/drive/paginacao"
import { UploadZone, type UploadZoneHandle } from "@/app/components/drive/upload-zone"
import {
  UploadResult, classifyUploadError, type UploadError,
} from "@/app/components/drive/resultado-upload"

// The file type lives in service/types.ts (IDriveFile) because the canvas's
// file picker consumes the same listing.
type DriveFile = IDriveFile

/** Same default as the backend (`page_size`), made explicit here because the
 *  pagination footer computes "Mostrando X–Y de N" from it. */
const PAGE_SIZE = 50

// ── Listing grid ─────────────────────────────────────────────────────────────
//
// The fixed columns add up to 536px. The content area is NARROWER on a tablet
// than on a phone — the 16rem sidebar comes in at `md` and PageRoot's `max-w-6xl`
// is no longer the limit: ~448px remain at 768px versus ~703px at 767px. That is
// why the cutoff is `lg` and not `md`: below it the row stacks (identity and
// actions on top, type/size/date below), and only from `lg` up do the columns return.
function gradeDoDrive(podeEditar: boolean) {
  return podeEditar
    ? "grid-cols-[32px_minmax(0,1fr)_auto] lg:grid-cols-[32px_1fr_100px_120px_140px_48px]"
    : "grid-cols-[minmax(0,1fr)_auto] lg:grid-cols-[1fr_100px_120px_140px_48px]"
}
/** First content column — after the selection checkbox, when there is one. */
const nameColumn = (podeEditar: boolean) => (podeEditar ? "col-start-2" : "col-start-1")

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DrivePage() {
  const { data: session } = useSession()
  const { current: workspace, canEdit: podeEditar } = useWorkspace()

  const [search, setSearch] = useState("")
  const [extFilter, setExtFilter] = useState("")
  const [page, setPage] = useState(1)
  const [uploading, setUploading] = useState(false)
  const [uploadErrors, setUploadErrors] = useState<UploadError[]>([])
  const [uploadSuccess, setUploadSuccess] = useState(0)

  const [metadataFile, setMetadataFile] = useState<DriveFile | null>(null)
  const [deleteFile, setDeleteFile] = useState<DriveFile | null>(null)

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [batchDelOpen, setBatchDelOpen] = useState(false)

  const uploadZoneRef = useRef<UploadZoneHandle>(null)
  const token = (session?.user as { access_token?: string })?.access_token

  // ── Listing fetch ────────────────────────────────────────────────────────
  // `page`/`page_size` are really sent: the backend always cut at 50 and the UI
  // never sent anything, so in a workspace with 300 files the other 250 were
  // unreachable while the header announced the real total.
  const fetcher = useCallback(async () => {
    if (!workspace) return null
    return GisFlowService.getDriveFiles({
      workspace_id: workspace.id_hash,
      search:       search || undefined,
      ext:          extFilter || undefined,
      page,
      page_size:    PAGE_SIZE,
    })
  }, [workspace, search, extFilter, page])

  const { data: resposta, firstLoad, loading, refreshing, error, refetch } = useFetchData(
    fetcher,
    "Não foi possível carregar os arquivos.",
    [workspace?.id_hash, search, extFilter, page],
    300,
  )

  // Switching workspace in the header selector does not remount the screen:
  // without this reset, the previous workspace's page/search/filter stayed in
  // effect. The selection goes too — it feeds "Excluir N", and deleting
  // id_hashes of the previous workspace is data loss.
  useEffect(() => {
    setPage(1)
    setSearch("")
    setExtFilter("")
    setSelected(prev => (prev.size > 0 ? new Set() : prev))
  }, [workspace?.id_hash])

  // During a workspace switch the hook keeps the previous page on screen — that
  // is what keeps the table from flashing on every search keystroke. But showing
  // the previous workspace's files under the new one's name would be a lie:
  // until the right response arrives, this counts as "no data yet".
  const data =
    resposta && resposta.items.length > 0 && resposta.items[0].workspace_id !== workspace?.id_hash
      ? null
      : resposta

  // ── Known extensions for the filter chips ────────────────────────────────
  // Accumulated instead of derived from the current page: with `ext=csv` the
  // server only returns csv, and the derived list lost all the other chips —
  // including "Todos" (all), leaving the filter stuck with no way back.
  const [extensions, setExtensions] = useState<string[]>([])
  useEffect(() => { setExtensions([]) }, [workspace?.id_hash])
  useEffect(() => {
    if (!data?.items?.length) return
    setExtensions(prev => {
      const conhecidas = new Set(prev)
      const antes = conhecidas.size
      for (const f of data.items) conhecidas.add(f.extension)
      return conhecidas.size === antes ? prev : [...conhecidas].sort()
    })
  }, [data])

  // ── Pagination ───────────────────────────────────────────────────────────
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const mostrandoDe = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const mostrandoAte = (page - 1) * PAGE_SIZE + (data?.items?.length ?? 0)
  const mostrados = data?.items?.length ?? 0

  /** Safety net for the count SHRINKING under the user (a batch delete on
   *  the last page, for example): without this they stay on a page that no
   *  longer exists, looking at an empty list. Only clamps with a response in hand. */
  useEffect(() => {
    if (data && page > totalPages) setPage(1)
  }, [data, page, totalPages])

  /** Every filter change goes back to the first page — otherwise searching for
   *  a term with 3 results while on page 4 returns an empty screen. */
  function applySearch(valor: string) { setSearch(valor); setPage(1) }
  function applyExtension(ext: string) { setExtFilter(ext); setPage(1) }
  function limparFiltros() { setSearch(""); setExtFilter(""); setPage(1) }

  // ── Upload ───────────────────────────────────────────────────────────────
  async function handleFiles(files: FileList) {
    if (!workspace || !token) return
    setUploading(true)
    setUploadErrors([])
    setUploadSuccess(0)
    const errors: UploadError[] = []
    let successCount = 0

    for (const file of Array.from(files)) {
      const res = await GisFlowService.uploadDriveFile(workspace.id_hash, file)
      if (res.error) {
        errors.push({
          fileName: file.name,
          detail:   res.error.message ?? `Não foi possível enviar «${file.name}».`,
          type:     classifyUploadError(res.status, res.error.code),
        })
      } else {
        successCount++
      }
    }

    setUploading(false)
    setUploadErrors(errors)
    setUploadSuccess(successCount)
    refetch()
  }

  // ── Download ─────────────────────────────────────────────────────────────
  async function handleDownload(file: DriveFile) {
    if (!token) return
    // Blocked here too, and not only in the backend: the menu item already comes
    // disabled, but a keyboard shortcut or a cached version of the list would
    // reach the server only to get a 409 — better to explain right away.
    if (isLocalDoExecutor(file)) {
      createToast.error(
        "Este arquivo permanece no executor.",
        "O conteúdo nunca saiu daquela máquina e não pode ser baixado pela plataforma. " +
        "Ele continua disponível para workflows que rodem nesse executor.",
      )
      return
    }
    const res = await GisFlowService.getDriveDownloadUrl(file.id_hash)
    if (res.error) {
      // 409 is the refusal by locality (drive_service._recusar_se_local), not a
      // failure: it deserves the reason, not "could not download".
      if (res.status === 409 && res.error.message) {
        createToast.error("Download indisponível.", res.error.message)
        return
      }
      createToast.error("Não foi possível baixar o arquivo.")
      return
    }
    // API retorna pre-signed URL — abre diretamente no browser.
    const downloadUrl = res.data?.download_url
    if (downloadUrl) window.open(downloadUrl, "_blank")
  }

  // ── Delete ───────────────────────────────────────────────────────────────
  // Async: the shared `DeleteDialog` awaits and locks the buttons, so the
  // double-click lock comes for free (no `deleting` state in the page).
  async function confirmDelete() {
    if (!deleteFile || !token) return
    const res = await GisFlowService.deleteDriveFile(deleteFile.id_hash)
    if (res.error) {
      createToast.error("Não foi possível excluir o arquivo.")
      return
    }
    createToast.success("Arquivo excluído.")
    setDeleteFile(null)
    refetch()
  }

  // ── Multiple selection ──────────────────────────────────────────────────
  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  /** Checks/unchecks the CURRENT PAGE, preserving what was already selected on
   *  other pages — the "Excluir N" button counts the whole Set, not the page. */
  function toggleAll() {
    if (!data?.items) return
    const pageIds = data.items.map(f => f.id_hash)
    const allChecked = pageIds.every(id => selected.has(id))
    setSelected(prev => {
      const next = new Set(prev)
      for (const id of pageIds) {
        if (allChecked) next.delete(id)
        else next.add(id)
      }
      return next
    })
  }

  async function handleBatchDelete() {
    if (!token || selected.size === 0) return
    try {
      // The count comes from the BACKEND, not from `selected.size`: cataloged files
      // are skipped in the batch (the content belongs to the executor), and
      // reporting the selected total would say that what is still there vanished.
      const resposta = await GisFlowService.batchDeleteDriveFiles([...selected])
      if (resposta.error) {
        createToast.error("Não foi possível excluir os arquivos.")
        return
      }
      const res = resposta.data!
      const pulados = res?.no_executor ?? 0
      createToast.success(
        pulados > 0
          ? `${formatInteger(res.deleted)} arquivo(s) excluído(s). ${formatInteger(pulados)} mantido(s): o conteúdo está no executor.`
          : `${formatInteger(res.deleted)} arquivo(s) excluído(s).`,
      )
      setSelected(new Set())
      setBatchDelOpen(false)
      refetch()
    } catch {
      createToast.error("Não foi possível excluir os arquivos.")
    }
  }

  // ── Estados (contrato §3) ──────────────────────────────────────────────────
  const hasFilter = search !== "" || extFilter !== ""
  // The error takes over the screen only when there is no data for the CURRENT
  // workspace to show (`data === null`): a 1st load that fails, or a reload that
  // fails right after switching workspace — then the hook's `resposta` is stale
  // (from the previous workspace) and the `data` guard nulls it. A reload that
  // fails with the current workspace's list on screen (`data` non-null) keeps it
  // + a toast (contract §3.2).
  const showError = !!error && data === null
  // The Skeleton covers any state without current-workspace data that is not an
  // error — including the 1st load of the new scope after switching workspace.
  // With that, the list branch is only reached with non-null `data` (no null
  // dereference when a post-switch refresh fails).
  const showSkeleton = !showError && (firstLoad || data === null)
  const vazio = !!data && data.items.length === 0
  const showFilters = !showSkeleton && !showError && (mostrados > 0 || hasFilter)

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <PageRoot>
      <DriveHeader
        total={data ? total : null}
        mostrados={mostrados}
        atualizando={loading}
        selecionados={selected.size}
        canEdit={podeEditar}
        onAtualizar={refetch}
        onExcluirSelecionados={() => setBatchDelOpen(true)}
      />

      {/* Upload zone — editors only. */}
      {podeEditar && <UploadZone ref={uploadZoneRef} uploading={uploading} onFiles={handleFiles} />}

      {/* Result of the last upload. */}
      {(uploadErrors.length > 0 || uploadSuccess > 0) && (
        <UploadResult
          sucessos={uploadSuccess}
          erros={uploadErrors}
          onFechar={() => { setUploadErrors([]); setUploadSuccess(0) }}
        />
      )}

      {/* Filtros. */}
      {showFilters && (
        <DriveFilters
          busca={search}
          onBusca={applySearch}
          ext={extFilter}
          onExt={applyExtension}
          extensoes={extensions}
        />
      )}

      {/* List and its states. */}
      {showSkeleton ? (
        <SkeletonDoDrive />
      ) : showError ? (
        <ErroDeCarga mensagem={error!} onTentar={refetch} />
      ) : vazio ? (
        hasFilter ? (
          <SemResultado busca={search} ext={extFilter} onLimpar={limparFiltros} />
        ) : (
          <VazioPrimeiroUso canEdit={podeEditar} onEnviar={() => uploadZoneRef.current?.abrirSeletor()} />
        )
      ) : (
        // The table stays mounted during a reload (debounced search, page
        // change, Refresh button): swapping it for skeletons made the content
        // flash on every keystroke and lost the scroll. `overflow-x-auto`
        // stays as a net: from `lg` up a narrow window may still run out of
        // space, and without it the excess would be clipped by the body.
        <section
          aria-labelledby="drive-lista-titulo"
          className={`overflow-x-auto rounded-lg border bg-card shadow-xs transition-opacity duration-200 ${refreshing ? "opacity-60" : ""}`}
        >
          <h2 id="drive-lista-titulo" className="sr-only">Arquivos do workspace</h2>

          {/* Column header — only where there are columns. When stacked it would
              label what does not exist. */}
          <div className={`hidden lg:grid lg:min-w-[560px] ${gradeDoDrive(podeEditar)} items-center gap-4 border-b bg-muted/40 px-4 py-2.5 text-xs font-medium text-muted-foreground`}>
            {podeEditar && (
              <Checkbox
                aria-label="Marcar todos os arquivos desta página"
                checked={
                  data?.items?.length
                    ? data.items.every(f => selected.has(f.id_hash))
                      ? true
                      : data.items.some(f => selected.has(f.id_hash))
                        ? "indeterminate"
                        : false
                    : false
                }
                onCheckedChange={toggleAll}
              />
            )}
            <span>Nome</span>
            <span>Tipo</span>
            <span>Tamanho</span>
            <span>Enviado em</span>
            <span />
          </div>

          {/* Linhas. */}
          {data!.items.map((file, idx) => (
            <div
              key={file.id_hash}
              className={`grid items-center gap-x-3 gap-y-1.5 lg:min-w-[560px] lg:gap-4 ${gradeDoDrive(podeEditar)} px-4 py-3 text-sm transition-colors hover:bg-muted/20 ${
                idx < data!.items.length - 1 ? "border-b border-border/60" : ""
              }`}
            >
              {/* Checkbox — always the first cell of the first row. */}
              {podeEditar && (
                <Checkbox
                  aria-label={`Selecionar «${file.original_name}»`}
                  className="col-start-1 row-start-1 lg:col-auto lg:row-auto"
                  checked={selected.has(file.id_hash)}
                  onCheckedChange={() => toggleSelect(file.id_hash)}
                />
              )}
              {/* Nome. */}
              <div className={`flex min-w-0 items-center gap-2 row-start-1 lg:col-auto lg:row-auto ${nameColumn(podeEditar)}`}>
                <span className="shrink-0 text-muted-foreground">
                  <ExtIcon ext={file.extension} />
                </span>
                <span className="truncate font-medium">{file.original_name}</span>
                {isLocalDoExecutor(file) && <LocalBadge executorId={file.content_executor_id} />}
              </div>

              {/* Type, size and date: a single strip below the name when
                  stacked; `lg:contents` returns the three cells to the grid
                  when the columns come back, with no duplicated markup. */}
              <div className={`flex flex-wrap items-center gap-x-3 gap-y-1 row-start-2 col-end-[-1] lg:contents ${nameColumn(podeEditar)}`}>
                <div><ExtBadge ext={file.extension} /></div>
                <span className="font-mono text-xs text-muted-foreground tabular-nums">
                  {formatBytes(file.size)}
                </span>
                {/* Date of the last write — same sort key as the backend. */}
                <span
                  className="text-xs text-muted-foreground tabular-nums"
                  title={
                    wasRewritten(file)
                      ? `Atualizado em ${formatLocal(lastWrite(file))} · enviado em ${formatLocal(file.created_at)}`
                      : formatLocal(lastWrite(file))
                  }
                >
                  {formatarQuando(lastWrite(file))}
                </span>
              </div>

              {/* Actions. */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Ações de «${file.original_name}»`}
                    className="size-7 row-start-1 col-end-[-1] justify-self-end max-md:size-10 lg:col-auto lg:row-auto"
                  >
                    <TbDotsVertical size={14} aria-hidden="true" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => setMetadataFile(file)}>
                    <TbFileInfo size={13} className="mr-2" /> Metadados
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={isLocalDoExecutor(file)}
                    onClick={() => handleDownload(file)}
                    title={
                      isLocalDoExecutor(file)
                        ? "O conteúdo permanece no executor e não pode ser baixado."
                        : undefined
                    }
                  >
                    <TbDownload size={13} className="mr-2" /> Download
                  </DropdownMenuItem>
                  {podeEditar && (
                    <>
                      <DropdownMenuSeparator />
                      {/* Cataloged: the record reflects a file that never belonged
                          to the platform. Deleting here would erase nothing on
                          the disk of whoever has it — and the backend refuses with 409. */}
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        disabled={isLocalDoExecutor(file)}
                        onClick={() => setDeleteFile(file)}
                        title={
                          isLocalDoExecutor(file)
                            ? "O arquivo permanece no executor. Para removê-lo, apague-o na pasta sincronizada ou tire essa pasta do GeoSync."
                            : undefined
                        }
                      >
                        <TbTrash size={13} className="mr-2" /> Excluir
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}
        </section>
      )}

      {/* Pagination footer — `page > 1` in the condition on purpose: if the list
          shrinks to fit on a single page, the footer is the ONLY way out of a
          page that no longer exists. */}
      {!showSkeleton && !showError && (total > PAGE_SIZE || page > 1) && (
        <PaginationFooter
          page={page}
          totalPages={totalPages}
          total={total}
          mostrandoDe={mostrandoDe}
          mostrandoAte={mostrandoAte}
          refreshing={refreshing}
          onPrev={() => setPage(p => Math.max(1, p - 1))}
          onNext={() => setPage(p => p + 1)}
        />
      )}

      {/* Dialogs. */}
      <MetadataDialog file={metadataFile} open={!!metadataFile} onClose={() => setMetadataFile(null)} />

      <Dialog open={!!deleteFile} onOpenChange={v => !v && setDeleteFile(null)}>
        {deleteFile && (
          <DeleteDialog
            title="Excluir arquivo"
            description="Esta ação não pode ser desfeita. O arquivo será removido permanentemente do Drive."
            note={<>«{deleteFile.original_name}»</>}
            confirmLabel="Excluir"
            onConfirm={confirmDelete}
          />
        )}
      </Dialog>

      <Dialog open={batchDelOpen} onOpenChange={v => !v && setBatchDelOpen(false)}>
        <DeleteDialog
          title={`Excluir ${plural(selected.size, "arquivo")}`}
          description="Esta ação não pode ser desfeita. Os arquivos selecionados serão removidos permanentemente do Drive."
          note="Arquivos cujo conteúdo está no executor são mantidos — os bytes não estão na plataforma."
          confirmLabel={`Excluir ${formatInteger(selected.size)}`}
          loadingLabel="Excluindo…"
          onConfirm={handleBatchDelete}
        />
      </Dialog>
    </PageRoot>
  )
}
