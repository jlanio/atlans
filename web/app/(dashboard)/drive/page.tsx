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
import { formatarInteiro, formatarQuando, plural } from "@/lib/formatos"
import { CabecalhoDoDrive } from "@/app/components/drive/cabecalho"
import { ErroDeCarga, SemResultado, SkeletonDoDrive, VazioPrimeiroUso } from "@/app/components/drive/estados"
import { ExtBadge, ExtIcon } from "@/app/components/drive/ext"
import { FiltrosDoDrive } from "@/app/components/drive/filtros"
import { MetadataDialog, foiReescrito, lastWrite } from "@/app/components/drive/dialogs"
import { RodapeDePaginacao } from "@/app/components/drive/paginacao"
import { UploadZone, type UploadZoneHandle } from "@/app/components/drive/upload-zone"
import {
  ResultadoDoUpload, classifyUploadError, type UploadError,
} from "@/app/components/drive/resultado-upload"

// O tipo do arquivo mora em service/types.ts (IDriveFile) porque o seletor de
// arquivo do canvas consome a mesma listagem.
type DriveFile = IDriveFile

/** Mesmo default do backend (`page_size`), explicitado aqui porque o rodapé de
 *  paginação calcula "Mostrando X–Y de N" a partir dele. */
const PAGE_SIZE = 50

// ── Grade da listagem ────────────────────────────────────────────────────────
//
// As colunas fixas somam 536px. A área de conteúdo é MAIS ESTREITA em tablet do
// que em telefone — a sidebar de 16rem entra em `md` e o `max-w-6xl` do PageRoot
// já não é o limite: sobram ~448px em 768px contra ~703px em 767px. Por isso o
// corte é `lg` e não `md`: abaixo dele a linha empilha (identidade e ações em
// cima, tipo/tamanho/data embaixo), e só de `lg` para cima as colunas voltam.
function gradeDoDrive(podeEditar: boolean) {
  return podeEditar
    ? "grid-cols-[32px_minmax(0,1fr)_auto] lg:grid-cols-[32px_1fr_100px_120px_140px_48px]"
    : "grid-cols-[minmax(0,1fr)_auto] lg:grid-cols-[1fr_100px_120px_140px_48px]"
}
/** Primeira coluna de conteúdo — depois da caixa de seleção, quando ela existe. */
const colunaDoNome = (podeEditar: boolean) => (podeEditar ? "col-start-2" : "col-start-1")

// ── Página principal ──────────────────────────────────────────────────────────

export default function DrivePage() {
  const { data: session } = useSession()
  const { current: workspace, canEdit: podeEditar } = useWorkspace()

  const [search, setSearch] = useState("")
  const [extFilter, setExtFilter] = useState("")
  const [page, setPage] = useState(1)
  const [uploading, setUploading] = useState(false)
  const [uploadErrors, setUploadErrors] = useState<UploadError[]>([])
  const [uploadSuccess, setUploadSuccess] = useState(0)

  const [metaFile, setMetaFile] = useState<DriveFile | null>(null)
  const [deleteFile, setDeleteFile] = useState<DriveFile | null>(null)

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [batchDelOpen, setBatchDelOpen] = useState(false)

  const uploadZoneRef = useRef<UploadZoneHandle>(null)
  const token = (session?.user as { access_token?: string })?.access_token

  // ── Fetch da listagem ────────────────────────────────────────────────────
  // `page`/`page_size` viajam de verdade: o backend sempre cortou em 50 e a UI
  // nunca mandou nada, então num workspace com 300 arquivos os outros 250 eram
  // inalcançáveis enquanto o cabeçalho anunciava o total real.
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

  // Trocar de workspace no seletor do cabeçalho não remonta a tela: sem este
  // reset, a página/busca/filtro do workspace anterior continuavam valendo. A
  // seleção também vai junto — ela alimenta "Excluir N", e apagar id_hashes do
  // workspace anterior é perda de dado.
  useEffect(() => {
    setPage(1)
    setSearch("")
    setExtFilter("")
    setSelected(prev => (prev.size > 0 ? new Set() : prev))
  }, [workspace?.id_hash])

  // Durante a troca de workspace o hook mantém a página anterior na tela — é o
  // que evita a tabela piscar a cada tecla da busca. Mas exibir os arquivos do
  // workspace anterior sob o nome do novo seria mentira: enquanto a resposta
  // certa não chega, isto vale como "ainda não há dados".
  const data =
    resposta && resposta.items.length > 0 && resposta.items[0].workspace_id !== workspace?.id_hash
      ? null
      : resposta

  // ── Extensões conhecidas para os chips de filtro ─────────────────────────
  // Acumuladas em vez de derivadas da página atual: com `ext=csv` o servidor só
  // devolve csv, e a lista derivada perdia todos os outros chips — inclusive o
  // "Todos", deixando o filtro preso sem como voltar.
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

  // ── Paginação ────────────────────────────────────────────────────────────
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const mostrandoDe = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const mostrandoAte = (page - 1) * PAGE_SIZE + (data?.items?.length ?? 0)
  const mostrados = data?.items?.length ?? 0

  /** Rede de segurança para a contagem ENCOLHER debaixo do usuário (exclusão em
   *  lote na última página, por exemplo): sem isto ele fica numa página que não
   *  existe mais, vendo a lista vazia. Só clampa com resposta na mão. */
  useEffect(() => {
    if (data && page > totalPages) setPage(1)
  }, [data, page, totalPages])

  /** Toda mudança de filtro volta para a primeira página — senão a busca por um
   *  termo com 3 resultados na página 4 devolve tela vazia. */
  function aplicarBusca(valor: string) { setSearch(valor); setPage(1) }
  function aplicarExtensao(ext: string) { setExtFilter(ext); setPage(1) }
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
    // Barrado aqui também, e não só no backend: o item do menu já vem
    // desabilitado, mas um atalho de teclado ou uma versão em cache da lista
    // chegariam ao servidor para receber um 409 — melhor explicar na hora.
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
      // 409 é a recusa por localidade (drive_service._recusar_se_local), não uma
      // falha: merece o motivo, não "não foi possível baixar".
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

  // ── Excluir ──────────────────────────────────────────────────────────────
  // Async: o `DeleteDialog` compartilhado aguarda e trava os botões, então a
  // trava contra duplo clique vem de graça (sem estado `deleting` na página).
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

  // ── Seleção múltipla ────────────────────────────────────────────────────
  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  /** Marca/desmarca a PÁGINA ATUAL, preservando o que já estava selecionado em
   *  outras páginas — o botão "Excluir N" conta o Set inteiro, não a página. */
  function toggleAll() {
    if (!data?.items) return
    const idsDaPagina = data.items.map(f => f.id_hash)
    const todosMarcados = idsDaPagina.every(id => selected.has(id))
    setSelected(prev => {
      const next = new Set(prev)
      for (const id of idsDaPagina) {
        if (todosMarcados) next.delete(id)
        else next.add(id)
      }
      return next
    })
  }

  async function handleBatchDelete() {
    if (!token || selected.size === 0) return
    try {
      // A contagem vem do BACKEND, não de `selected.size`: arquivos catalogados
      // são pulados no lote (o conteúdo é do executor), e reportar o total
      // selecionado diria que sumiu o que continua lá.
      const resposta = await GisFlowService.batchDeleteDriveFiles([...selected])
      if (resposta.error) {
        createToast.error("Não foi possível excluir os arquivos.")
        return
      }
      const res = resposta.data!
      const pulados = res?.no_executor ?? 0
      createToast.success(
        pulados > 0
          ? `${formatarInteiro(res.deleted)} arquivo(s) excluído(s). ${formatarInteiro(pulados)} mantido(s): o conteúdo está no executor.`
          : `${formatarInteiro(res.deleted)} arquivo(s) excluído(s).`,
      )
      setSelected(new Set())
      setBatchDelOpen(false)
      refetch()
    } catch {
      createToast.error("Não foi possível excluir os arquivos.")
    }
  }

  // ── Estados (contrato §3) ──────────────────────────────────────────────────
  const temFiltro = search !== "" || extFilter !== ""
  // Erro toma a tela só quando não há dados do workspace ATUAL para mostrar
  // (`data === null`): a 1ª carga que falha, ou uma recarga que falha logo após
  // trocar de workspace — aí a `resposta` do hook fica obsoleta (do workspace
  // anterior) e o guard de `data` a anula. Uma recarga que falha com a lista do
  // workspace atual na tela (`data` não-nulo) a mantém + toast (contrato §3.2).
  const mostrarErro = !!error && data === null
  // Skeleton cobre qualquer estado sem dados do workspace atual que não seja
  // erro — inclusive a 1ª carga do novo escopo após trocar de workspace. Com
  // isso o ramo da lista só é alcançado com `data` não-nulo (sem desreferência
  // de null quando um refresh pós-troca falha).
  const mostrarSkeleton = !mostrarErro && (firstLoad || data === null)
  const vazio = !!data && data.items.length === 0
  const mostrarFiltros = !mostrarSkeleton && !mostrarErro && (mostrados > 0 || temFiltro)

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <PageRoot>
      <CabecalhoDoDrive
        total={data ? total : null}
        mostrados={mostrados}
        atualizando={loading}
        selecionados={selected.size}
        canEdit={podeEditar}
        onAtualizar={refetch}
        onExcluirSelecionados={() => setBatchDelOpen(true)}
      />

      {/* Zona de envio — somente para editores. */}
      {podeEditar && <UploadZone ref={uploadZoneRef} uploading={uploading} onFiles={handleFiles} />}

      {/* Resultado do último envio. */}
      {(uploadErrors.length > 0 || uploadSuccess > 0) && (
        <ResultadoDoUpload
          sucessos={uploadSuccess}
          erros={uploadErrors}
          onFechar={() => { setUploadErrors([]); setUploadSuccess(0) }}
        />
      )}

      {/* Filtros. */}
      {mostrarFiltros && (
        <FiltrosDoDrive
          busca={search}
          onBusca={aplicarBusca}
          ext={extFilter}
          onExt={aplicarExtensao}
          extensoes={extensions}
        />
      )}

      {/* Lista e seus estados. */}
      {mostrarSkeleton ? (
        <SkeletonDoDrive />
      ) : mostrarErro ? (
        <ErroDeCarga mensagem={error!} onTentar={refetch} />
      ) : vazio ? (
        temFiltro ? (
          <SemResultado busca={search} ext={extFilter} onLimpar={limparFiltros} />
        ) : (
          <VazioPrimeiroUso canEdit={podeEditar} onEnviar={() => uploadZoneRef.current?.abrirSeletor()} />
        )
      ) : (
        // A tabela permanece montada durante a recarga (busca com debounce,
        // troca de página, botão Atualizar): trocá-la por skeletons fazia o
        // conteúdo piscar a cada tecla e perdia a rolagem. `overflow-x-auto`
        // continua como rede: de `lg` para cima uma janela estreita ainda pode
        // faltar espaço, e sem ele o excesso seria cortado pelo body.
        <section
          aria-labelledby="drive-lista-titulo"
          className={`overflow-x-auto rounded-lg border bg-card shadow-xs transition-opacity duration-200 ${refreshing ? "opacity-60" : ""}`}
        >
          <h2 id="drive-lista-titulo" className="sr-only">Arquivos do workspace</h2>

          {/* Cabeçalho de colunas — só onde há colunas. No empilhamento ele
              rotularia o que não existe. */}
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
              {/* Checkbox — sempre a primeira célula da primeira linha. */}
              {podeEditar && (
                <Checkbox
                  aria-label={`Selecionar «${file.original_name}»`}
                  className="col-start-1 row-start-1 lg:col-auto lg:row-auto"
                  checked={selected.has(file.id_hash)}
                  onCheckedChange={() => toggleSelect(file.id_hash)}
                />
              )}
              {/* Nome. */}
              <div className={`flex min-w-0 items-center gap-2 row-start-1 lg:col-auto lg:row-auto ${colunaDoNome(podeEditar)}`}>
                <span className="shrink-0 text-muted-foreground">
                  <ExtIcon ext={file.extension} />
                </span>
                <span className="truncate font-medium">{file.original_name}</span>
                {isLocalDoExecutor(file) && <LocalBadge executorId={file.content_executor_id} />}
              </div>

              {/* Tipo, tamanho e data: uma faixa só embaixo do nome no
                  empilhamento; `lg:contents` devolve as três células à grade
                  quando as colunas voltam, sem markup duplicado. */}
              <div className={`flex flex-wrap items-center gap-x-3 gap-y-1 row-start-2 col-end-[-1] lg:contents ${colunaDoNome(podeEditar)}`}>
                <div><ExtBadge ext={file.extension} /></div>
                <span className="font-mono text-xs text-muted-foreground tabular-nums">
                  {formatBytes(file.size)}
                </span>
                {/* Data da última escrita — mesma chave de ordenação do backend. */}
                <span
                  className="text-xs text-muted-foreground tabular-nums"
                  title={
                    foiReescrito(file)
                      ? `Atualizado em ${formatLocal(lastWrite(file))} · enviado em ${formatLocal(file.created_at)}`
                      : formatLocal(lastWrite(file))
                  }
                >
                  {formatarQuando(lastWrite(file))}
                </span>
              </div>

              {/* Ações. */}
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
                  <DropdownMenuItem onClick={() => setMetaFile(file)}>
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
                      {/* Catalogado: o registro reflete um arquivo que nunca
                          pertenceu à plataforma. Excluir aqui não apagaria nada
                          no disco de quem o tem — e o backend recusa com 409. */}
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

      {/* Rodapé de paginação — `page > 1` na condição de propósito: se a lista
          encolher para caber numa página só, o rodapé é a ÚNICA saída de uma
          página que já não existe. */}
      {!mostrarSkeleton && !mostrarErro && (total > PAGE_SIZE || page > 1) && (
        <RodapeDePaginacao
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

      {/* Diálogos. */}
      <MetadataDialog file={metaFile} open={!!metaFile} onClose={() => setMetaFile(null)} />

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
          confirmLabel={`Excluir ${formatarInteiro(selected.size)}`}
          loadingLabel="Excluindo…"
          onConfirm={handleBatchDelete}
        />
      </Dialog>
    </PageRoot>
  )
}
