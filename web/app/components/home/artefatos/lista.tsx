"use client"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  TbWorld, TbDownload, TbInfoCircle, TbTrash,
} from "react-icons/tb"
import { useVirtualizer } from "@tanstack/react-virtual"
import {
  SidebarMenuSub, SidebarMenuSubItem, SidebarMenuSkeleton, useSidebar,
} from "@/app/components/ui/sidebar"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { useWorkspace, hasMinRole } from "@/context/WorkspaceContext"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { useHomeStore } from "@/app/stores/homeStore"
import { ExtIcon } from "@/app/components/drive/ext"
import { MetadataDialog, type MetadataTexts } from "@/app/components/drive/dialogs"
import { LocalBadge } from "@/app/components/local-badge"
import { RetencaoHint, type RetentionTexts } from "@/app/components/artifacts/badges"
import { AvisoAmbar } from "@/app/components/shared/estados"
import { useAcervo } from "@/app/hooks/home/useAcervo"
import { baixarArtefato } from "@/lib/baixar-artefato"
import { NomeDeArquivo } from "../nome-de-arquivo"
import { LinhaDoMeu, GatilhoDeAcoes } from "../linha"
import { useFormats, useShellTexts } from "../i18n/da-casca"
import type { CollectionItem } from "./normalizar"

// Above this the list becomes virtual — the collection of a large workspace
// exceeds hundreds of rows and mounting them all freezes the shell's scroll.
const VIRTUAL_ABOVE = 150

// Drive icons cover shp/gpkg; the artifact formats use the same names.
const ICON_ALIAS: Record<string, string> = { shapefile: "shp", geoparquet: "gpkg" }

// The 3rem rail only fits an icon: `SidebarMenuSub` already hides on its own
// in icon mode, but the blocks that are NOT a sublist (the virtual list, the
// warnings) are raw `<div>`s and got clipped inside the rail.
const EXPANDED_ONLY = "group-data-[collapsible=icon]:hidden"

/**
 * "Meus → Artefatos" (Mine → Artifacts): the current workspace's collection —
 * run artifacts and Drive files in the SAME list, distinguished only by icon
 * and state (permanent / ephemeral / local on the executor). Clicking a
 * geojson artifact/one with a portal layer puts it on the globe (requested via
 * the store, which HomeView drains); a Drive file doesn't go to the globe in v1
 * — it opens the metadata.
 *
 * The panel does NOT switch workspaces: it follows the WorkspaceContext's
 * `current` (the person's default, or the last one used). The selector that
 * lived here was removed by the owner's decision — scope switching comes back
 * later, elsewhere in the shell. That's why this component only READS
 * `current`, and the rest of the app is what changes it.
 */
export function ArtefatosLista() {
  const { current, workspaces } = useWorkspace()
  const {
    itens, carregando, atualizando, jaCarregou, erro, avisos, total, recarregar, remover,
  } = useAcervo(current?.id_hash)
  const pedirCamada = useHomeStore((s) => s.pedirCamada)
  const { isMobile, setOpenMobile } = useSidebar()
  const textos = useShellTexts()
  const t = textos.listas
  const fmt = useFormats()

  const [metadataTarget, setMetadataTarget] = useState<CollectionItem | null>(null)
  const [excluindo, setDeleting] = useState<CollectionItem | null>(null)

  // The sentences of the retention hint (shared with the Artifacts table,
  // which stays in Portuguese) in the Home's language.
  const retencao = useMemo<RetentionTexts>(() => ({
    expirado: t.artefatos.retencao.expirado,
    expiraHoje: t.artefatos.retencao.expiraHoje,
    expiraEm: (dias) => t.artefatos.retencao.expiraEm(dias, fmt.inteiro(dias)),
    removidoEm: (expiresAt) => t.artefatos.retencao.removidoEm(fmt.dataEHora(expiresAt)),
  }), [t, fmt])

  // The Drive metadata dialog (which stays in Portuguese there) in the Home's language.
  const metadados = useMemo<MetadataTexts>(() => ({
    ...t.artefatos.metadadosDialogo,
    fechar: textos.comum.fechar,
    inteiro: fmt.inteiro,
    dataEHora: fmt.dataEHora,
  }), [t, textos, fmt])

  // On phones the sidebar is a Sheet that covers the screen: putting a layer on
  // the globe behind the drawer looks like "nothing happened". Same gesture as "Nova conversa".
  const closeOnPhone = useCallback(() => {
    if (isMobile) setOpenMobile(false)
  }, [isMobile, setOpenMobile])

  const canManage = useCallback(
    (workspaceId: string | null | undefined) =>
      hasMinRole(workspaces.find((w) => w.id_hash === workspaceId)?.my_role, "editor"),
    [workspaces],
  )

  const baixar = useCallback(async (item: CollectionItem) => {
    if (item.fonte === "artefato") {
      // It WAS `window.open(getArtifactDownloadUrl(...))`, and it downloaded
      // nothing: that endpoint returns `{download_url, filename}` as JSON, so the
      // new tab opened the JSON in the person's face. Worse, a top-level
      // navigation doesn't carry the Bearer, and a `protected` artifact became a
      // 401. The right path is in `lib/baixar-artefato` — the same one the app's
      // Artifacts table uses.
      const erro = await baixarArtefato(item.id, t.artefatos.download)
      if (erro) createToast.error(t.artefatos.baixarFalhou(item.nome), erro)
      return
    }
    const res = await GisFlowService.getDriveDownloadUrl(item.id)
    if (res.success && res.data) window.open(res.data.download_url, "_blank")
    else createToast.error(t.artefatos.baixarArquivoFalhou, res.error?.message ?? t.geral.tenteDeNovo)
  }, [t])

  const exibirNoGlobo = useCallback((item: CollectionItem) => {
    pedirCamada(item.id, item.nome)
    closeOnPhone()
  }, [pedirCamada, closeOnPhone])

  const Linha = useCallback((item: CollectionItem) => {
    const abrir = item.adicionavel
      ? () => exibirNoGlobo(item)
      : item.fonte === "drive"
        ? () => setMetadataTarget(item)
        : undefined
    const podeExcluir = canManage(item.workspaceId)
    const hasMenu = item.adicionavel || item.estado !== "local" || item.fonte === "drive" || podeExcluir
    const ext = ICON_ALIAS[item.formato] ?? item.formato
    const titulo = `${item.nome}${item.formato ? ` · ${item.formato.toUpperCase()}` : ""}`
    // By the key, not by the sentence stored in the item: the collection lives in
    // the hook, and the sentence must come out in the current language, not the
    // one at load time.
    const motivo = item.motivo ? t.artefatos.semPrevia[item.motivo] : null
    const primaryContent = (
      <>
        <span className="shrink-0 text-sidebar-foreground/55">
          <ExtIcon ext={ext} />
        </span>
        <NomeDeArquivo nome={item.nome} className="text-[13px]" />
      </>
    )
    return (
      <LinhaDoMeu>
        {abrir ? (
          <button
            type="button"
            onClick={abrir}
            title={item.adicionavel ? `${titulo} — ${t.artefatos.dicaExibirNoGlobo}` : titulo}
            className="flex min-w-0 flex-1 items-center gap-1.5 py-1 text-left text-sidebar-foreground max-md:min-h-10"
          >
            {primaryContent}
          </button>
        ) : (
          <div
            title={motivo ? `${titulo} — ${motivo}` : titulo}
            className="flex min-w-0 flex-1 items-center gap-1.5 py-1 text-sidebar-foreground/80 max-md:min-h-10"
          >
            {primaryContent}
            {/* `title` only exists on mouse hover: on keyboard and touch the reason
                for the inert row has to arrive as text. */}
            {motivo && <span className="sr-only">{motivo}</span>}
          </div>
        )}

        {item.estado === "local" && <LocalBadge executorId={item.executorId} textos={t.artefatos.local} />}
        {item.estado === "efemero" && <RetencaoHint expiresAt={item.expiresAt} textos={retencao} />}

        {hasMenu && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <GatilhoDeAcoes rotulo={item.nome} />
            </DropdownMenuTrigger>
            {/* `home-portal`: the menu is portaled to <body>, OUTSIDE the tree that
                declares the Home's palette — without the class it opened light over
                the near-black Home when the app is in the light theme. The items get
                40px on phones: the trigger was already big enough, it was the tap
                target that wasn't. */}
            <DropdownMenuContent align="end" className="home-portal min-w-40">
              {item.adicionavel && (
                <DropdownMenuItem onSelect={() => exibirNoGlobo(item)} className="gap-2 max-md:min-h-10">
                  <TbWorld className="size-4" /> {t.artefatos.exibirNoGlobo}
                </DropdownMenuItem>
              )}
              {item.estado !== "local" && (
                <DropdownMenuItem onSelect={() => baixar(item)} className="gap-2 max-md:min-h-10">
                  <TbDownload className="size-4" /> {t.artefatos.baixar}
                </DropdownMenuItem>
              )}
              {item.fonte === "drive" && (
                <DropdownMenuItem onSelect={() => setMetadataTarget(item)} className="gap-2 max-md:min-h-10">
                  <TbInfoCircle className="size-4" /> {t.artefatos.metadados}
                </DropdownMenuItem>
              )}
              {podeExcluir && (
                <DropdownMenuItem
                  onSelect={() => setDeleting(item)}
                  className="gap-2 text-destructive focus:text-destructive max-md:min-h-10"
                >
                  <TbTrash className="size-4" /> {t.artefatos.excluir}
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </LinhaDoMeu>
    )
  }, [baixar, exibirNoGlobo, canManage, t, retencao])

  // The list came cut at the server's ceiling: without stating the total, whoever
  // scrolls to the end concludes they saw everything and that the artifact they
  // are looking for was deleted.
  const truncado = total != null && total > itens.length

  let corpo: React.ReactNode
  if (carregando) {
    corpo = (
      <SidebarMenuSub role="status" aria-busy="true" aria-label={t.artefatos.carregando}>
        {[0, 1, 2].map((i) => (
          <SidebarMenuSubItem key={i}>
            <SidebarMenuSkeleton />
          </SidebarMenuSubItem>
        ))}
      </SidebarMenuSub>
    )
  } else if (erro && !jaCarregou) {
    // §3: the error block only takes over the list when there was never an accepted load.
    corpo = <ListError mensagem={t.artefatos.carregarFalhou} onTentar={recarregar} />
  } else if (!current) {
    // With no selector here, "selecione um workspace" would tell the person to do
    // something this panel no longer offers. The state is transient (the context
    // hasn't resolved the person's workspace yet), so the text only describes.
    corpo = (
      <SidebarMenuSub>
        <li className="px-2 py-1.5 text-xs text-sidebar-foreground/55">
          {t.artefatos.semWorkspace}
        </li>
      </SidebarMenuSub>
    )
  } else if (itens.length === 0) {
    corpo = (
      <SidebarMenuSub>
        <li className="px-2 py-1.5 text-xs text-sidebar-foreground/55">
          {avisos.drive
            ? t.artefatos.vazioSemDrive
            : avisos.artefatos
              ? t.artefatos.vazioSemArtefatos
              : t.artefatos.vazio}
        </li>
      </SidebarMenuSub>
    )
  } else if (itens.length > VIRTUAL_ABOVE) {
    corpo = <VirtualList itens={itens} renderLinha={Linha} />
  } else {
    corpo = (
      <SidebarMenuSub aria-busy={atualizando || undefined}>
        {itens.map((item) => (
          <SidebarMenuSubItem key={item.chave}>{Linha(item)}</SidebarMenuSubItem>
        ))}
      </SidebarMenuSub>
    )
  }

  return (
    <>
      {corpo}

      {/* The warnings live OUTSIDE the branches: above 150 items the body becomes a
          virtual list and in the empty branch there is no `<ul>` — it was precisely
          in the large workspace that a source failure went silent. */}
      {(erro || avisos.drive || avisos.artefatos || truncado) && (
        <div className={`flex flex-col gap-1 px-2 pb-1 ${EXPANDED_ONLY}`}>
          {erro && jaCarregou && (
            <AvisoAmbar
              onTentar={recarregar}
              rotuloDoBotao={textos.comum.tentarDeNovo}
            >
              {t.artefatos.atualizarFalhou}
            </AvisoAmbar>
          )}
          {avisos.drive && (
            <AvisoAmbar
              onTentar={recarregar}
              rotuloDoBotao={textos.comum.tentarDeNovo}
            >
              {t.artefatos.driveFalhou}
            </AvisoAmbar>
          )}
          {avisos.artefatos && (
            <AvisoAmbar
              onTentar={recarregar}
              rotuloDoBotao={textos.comum.tentarDeNovo}
            >
              {t.artefatos.artefatosFalharam}
            </AvisoAmbar>
          )}
          {truncado && (
            <p className="px-1 text-[11px] tabular-nums text-sidebar-foreground/55">
              {t.geral.mostrando(fmt.inteiro(itens.length), fmt.inteiro(total ?? 0))}
            </p>
          )}
        </div>
      )}

      {/* `home-portal` on both dialogs: they are portals in <body>, outside the tree
          that declares the Home's palette — they opened light over the near-black Home. */}
      <MetadataDialog
        className="home-portal"
        file={metadataTarget?.driveFile ?? null}
        open={!!metadataTarget?.driveFile}
        onClose={() => setMetadataTarget(null)}
        textos={metadados}
      />

      <Dialog open={!!excluindo} onOpenChange={(v) => { if (!v) setDeleting(null) }}>
        {excluindo && (
          <DeleteDialog
            className="home-portal"
            title={excluindo.fonte === "drive"
              ? t.artefatos.excluirDialogo.tituloArquivo
              : t.artefatos.excluirDialogo.tituloArtefato}
            description={t.artefatos.excluirDialogo.descricao(excluindo.nome)}
            confirmLabel={t.artefatos.excluir}
            loadingLabel={t.artefatos.excluirDialogo.excluindo}
            cancelLabel={textos.comum.cancelar}
            closeLabel={textos.comum.fechar}
            onConfirm={async () => {
              const ok = await remover(excluindo)
              if (!ok) createToast.error(t.artefatos.excluirFalhou, t.geral.tenteDeNovo)
              setDeleting(null)
            }}
          />
        )}
      </Dialog>
    </>
  )
}

/**
 * The 1st-load error inside the sidebar: the centered card of §3.2 doesn't fit
 * in a 16rem rail, so the compact form stays — same semantics
 * (`role="alert"`), same microcopy and the same way out ("Tentar de novo").
 */
function ListError({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  const { tentarDeNovo } = useShellTexts().comum
  return (
    <div role="alert" className={`flex flex-col items-start gap-1 px-2 py-1.5 ${EXPANDED_ONLY}`}>
      <p className="text-xs text-sidebar-foreground/70">{mensagem}</p>
      <button
        type="button"
        onClick={onTentar}
        className="inline-flex items-center rounded-sm text-xs font-medium text-sidebar-foreground underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        {tentarDeNovo}
      </button>
    </div>
  )
}

/**
 * The virtual path (above 150 items): its own scroller with a ceiling height,
 * absolute rows. Modeled on `run-panel/output-tab.tsx`. Outside `SidebarMenuSub`
 * (which is a `<ul>`) because absolute rows are not `<li>` — hence the ARIA roles
 * by hand, and the `aria-setsize`/`aria-posinset` that tells the screen reader
 * the list's real size (only the window exists in the DOM).
 */
function VirtualList({
  itens,
  renderLinha,
}: {
  itens: CollectionItem[]
  renderLinha: (item: CollectionItem) => React.ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  // The list stays MOUNTED when the Mine group item closes (the wrapper becomes
  // `hidden`), and `display:none` can reset the scroller's `scrollTop` without
  // the virtualizer knowing: on reopening, the computed window was from a stale
  // offset and the rows stayed blank until scrolling. `enabled` tied to
  // visibility — disabling drops the subscription and re-enabling rereads the real `scrollTop`.
  const [visivel, setVisible] = useState(true)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === "undefined") return
    const ro = new ResizeObserver(([entrada]) => setVisible(entrada.contentRect.height > 0))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const virtual = useVirtualizer({
    count: itens.length,
    getScrollElement: () => ref.current,
    estimateSize: () => 32,
    overscan: 12,
    getItemKey: (i) => itens[i].chave,
    enabled: visivel,
  })
  return (
    <div
      ref={ref}
      className={`mx-3.5 max-h-[45vh] overflow-y-auto border-l border-sidebar-border pl-0.5 ${EXPANDED_ONLY}`}
    >
      <div
        role="list"
        style={{ height: virtual.getTotalSize(), position: "relative", width: "100%" }}
      >
        {virtual.getVirtualItems().map((vi) => (
          <div
            key={vi.key}
            role="listitem"
            aria-setsize={itens.length}
            aria-posinset={vi.index + 1}
            data-index={vi.index}
            // Measures for real instead of trusting the estimated 32px: the row
            // grows on phones (40px target) and with a retention badge, and
            // without measuring the rows overlapped with no sign at all.
            ref={virtual.measureElement}
            style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${vi.start}px)` }}
          >
            {renderLinha(itens[vi.index])}
          </div>
        ))}
      </div>
    </div>
  )
}
