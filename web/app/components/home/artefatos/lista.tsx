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
import { MetadataDialog, type TextosDosMetadados } from "@/app/components/drive/dialogs"
import { LocalBadge } from "@/app/components/local-badge"
import { RetencaoHint, type TextosDaRetencao } from "@/app/components/artifacts/badges"
import { AvisoAmbar } from "@/app/components/shared/estados"
import { useAcervo } from "@/app/hooks/home/useAcervo"
import { baixarArtefato } from "@/lib/baixar-artefato"
import { NomeDeArquivo } from "../nome-de-arquivo"
import { LinhaDoMeu, GatilhoDeAcoes } from "../linha"
import { useFormatos, useTextosDaCasca } from "../i18n/da-casca"
import type { ItemDoAcervo } from "./normalizar"

// Acima disto a lista vira virtual — o acervo de um workspace grande passa de
// centenas de linhas e montar todas trava o scroll da casca.
const VIRTUAL_ACIMA = 150

// Ícones do Drive cobrem shp/gpkg; os formatos de artefato usam os mesmos nomes.
const ALIAS_DE_ICONE: Record<string, string> = { shapefile: "shp", geoparquet: "gpkg" }

// O trilho de 3rem só cabe ícone: o `SidebarMenuSub` já some sozinho no modo
// ícone, mas os blocos que NÃO são sublista (a lista virtual, os avisos) são
// `<div>` cru e ficavam recortados dentro do trilho.
const SO_EXPANDIDO = "group-data-[collapsible=icon]:hidden"

/**
 * "Meus → Artefatos": o acervo do workspace atual — artefatos de execução e
 * arquivos do Drive na MESMA lista, distinguidos só pelo ícone e pelo estado
 * (permanente / efêmero / local no executor). Clicar num artefato geojson/com
 * camada de portal o põe no globo (pedido pela store, que o HomeView drena);
 * arquivo do Drive não vai ao globo na v1 — abre os metadados.
 *
 * O painel NÃO troca de workspace: ele segue o `current` do WorkspaceContext (o
 * padrão da pessoa, ou o último usado). O seletor que vivia aqui saiu por
 * decisão do dono — a troca de escopo volta depois, em outro lugar da casca.
 * Por isso este componente só LÊ `current`, e quem o muda é o resto do app.
 */
export function ArtefatosLista() {
  const { current, workspaces } = useWorkspace()
  const {
    itens, carregando, atualizando, jaCarregou, erro, avisos, total, recarregar, remover,
  } = useAcervo(current?.id_hash)
  const pedirCamada = useHomeStore((s) => s.pedirCamada)
  const { isMobile, setOpenMobile } = useSidebar()
  const textos = useTextosDaCasca()
  const t = textos.listas
  const fmt = useFormatos()

  const [metaAlvo, setMetaAlvo] = useState<ItemDoAcervo | null>(null)
  const [excluindo, setExcluindo] = useState<ItemDoAcervo | null>(null)

  // As frases da dica de retenção (compartilhada com a tabela de Artefatos,
  // que segue em português) no idioma da Home.
  const retencao = useMemo<TextosDaRetencao>(() => ({
    expirado: t.artefatos.retencao.expirado,
    expiraHoje: t.artefatos.retencao.expiraHoje,
    expiraEm: (dias) => t.artefatos.retencao.expiraEm(dias, fmt.inteiro(dias)),
    removidoEm: (expiresAt) => t.artefatos.retencao.removidoEm(fmt.dataEHora(expiresAt)),
  }), [t, fmt])

  // O diálogo de metadados do Drive (que segue em português lá) no idioma da Home.
  const metadados = useMemo<TextosDosMetadados>(() => ({
    ...t.artefatos.metadadosDialogo,
    fechar: textos.comum.fechar,
    inteiro: fmt.inteiro,
    dataEHora: fmt.dataEHora,
  }), [t, textos, fmt])

  // No telefone o sidebar é um Sheet que cobre a tela: pôr uma camada no globo
  // atrás da gaveta parece "nada aconteceu". Mesmo gesto do "Nova conversa".
  const fecharNoTelefone = useCallback(() => {
    if (isMobile) setOpenMobile(false)
  }, [isMobile, setOpenMobile])

  const podeGerir = useCallback(
    (workspaceId: string | null | undefined) =>
      hasMinRole(workspaces.find((w) => w.id_hash === workspaceId)?.my_role, "editor"),
    [workspaces],
  )

  const baixar = useCallback(async (item: ItemDoAcervo) => {
    if (item.fonte === "artefato") {
      // ERA `window.open(getArtifactDownloadUrl(...))`, e não baixava nada: esse
      // endpoint devolve `{download_url, filename}` em JSON, então a aba nova
      // abria o JSON na cara da pessoa. Pior, navegação de topo não leva o
      // Bearer, e artefato `protected` virava 401. O caminho certo está em
      // `lib/baixar-artefato` — o mesmo que a tabela de Artefatos do app usa.
      const erro = await baixarArtefato(item.id, t.artefatos.download)
      if (erro) createToast.error(t.artefatos.baixarFalhou(item.nome), erro)
      return
    }
    const res = await GisFlowService.getDriveDownloadUrl(item.id)
    if (res.success && res.data) window.open(res.data.download_url, "_blank")
    else createToast.error(t.artefatos.baixarArquivoFalhou, res.error?.message ?? t.geral.tenteDeNovo)
  }, [t])

  const exibirNoGlobo = useCallback((item: ItemDoAcervo) => {
    pedirCamada(item.id, item.nome)
    fecharNoTelefone()
  }, [pedirCamada, fecharNoTelefone])

  const Linha = useCallback((item: ItemDoAcervo) => {
    const abrir = item.adicionavel
      ? () => exibirNoGlobo(item)
      : item.fonte === "drive"
        ? () => setMetaAlvo(item)
        : undefined
    const podeExcluir = podeGerir(item.workspaceId)
    const temMenu = item.adicionavel || item.estado !== "local" || item.fonte === "drive" || podeExcluir
    const ext = ALIAS_DE_ICONE[item.formato] ?? item.formato
    const titulo = `${item.nome}${item.formato ? ` · ${item.formato.toUpperCase()}` : ""}`
    // Pela chave, e não pela frase guardada no item: o acervo mora no hook, e a
    // frase tem de sair no idioma em uso, não no da carga.
    const motivo = item.motivo ? t.artefatos.semPrevia[item.motivo] : null
    const primario = (
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
            {primario}
          </button>
        ) : (
          <div
            title={motivo ? `${titulo} — ${motivo}` : titulo}
            className="flex min-w-0 flex-1 items-center gap-1.5 py-1 text-sidebar-foreground/80 max-md:min-h-10"
          >
            {primario}
            {/* O `title` só existe no hover do mouse: no teclado e no toque o
                motivo da linha inerte precisa chegar por texto. */}
            {motivo && <span className="sr-only">{motivo}</span>}
          </div>
        )}

        {item.estado === "local" && <LocalBadge executorId={item.executorId} textos={t.artefatos.local} />}
        {item.estado === "efemero" && <RetencaoHint expiresAt={item.expiresAt} textos={retencao} />}

        {temMenu && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <GatilhoDeAcoes rotulo={item.nome} />
            </DropdownMenuTrigger>
            {/* `home-portal`: o menu é portado para o <body>, FORA da árvore que
                declara a paleta da Home — sem a classe ele abria claro sobre a
                Home quase preta quando o app está no tema claro. Os itens ganham
                40px no telefone: o gatilho já era grande o bastante, o destino
                do toque é que não era. */}
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
                <DropdownMenuItem onSelect={() => setMetaAlvo(item)} className="gap-2 max-md:min-h-10">
                  <TbInfoCircle className="size-4" /> {t.artefatos.metadados}
                </DropdownMenuItem>
              )}
              {podeExcluir && (
                <DropdownMenuItem
                  onSelect={() => setExcluindo(item)}
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
  }, [baixar, exibirNoGlobo, podeGerir, t, retencao])

  // A lista veio cortada no teto do servidor: sem dizer o total, quem rola até o
  // fim conclui que viu tudo e que o artefato que procura foi apagado.
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
    // §3: o bloco de erro só toma a lista quando nunca houve carga aceita.
    corpo = <ErroDaLista mensagem={t.artefatos.carregarFalhou} onTentar={recarregar} />
  } else if (!current) {
    // Sem seletor aqui, "selecione um workspace" mandaria fazer algo que este
    // painel não oferece mais. O estado é transitório (o contexto ainda não
    // resolveu o workspace da pessoa), então o texto só descreve.
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
  } else if (itens.length > VIRTUAL_ACIMA) {
    corpo = <ListaVirtual itens={itens} renderLinha={Linha} />
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

      {/* Os avisos vivem FORA dos ramos: acima de 150 itens o corpo vira lista
          virtual e no ramo vazio não há `<ul>` — era justamente no workspace
          grande que a falha de uma fonte ficava silenciosa. */}
      {(erro || avisos.drive || avisos.artefatos || truncado) && (
        <div className={`flex flex-col gap-1 px-2 pb-1 ${SO_EXPANDIDO}`}>
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

      {/* `home-portal` nos dois diálogos: são portais no <body>, fora da árvore
          que declara a paleta da Home — abriam claros sobre a Home quase preta. */}
      <MetadataDialog
        className="home-portal"
        file={metaAlvo?.driveFile ?? null}
        open={!!metaAlvo?.driveFile}
        onClose={() => setMetaAlvo(null)}
        textos={metadados}
      />

      <Dialog open={!!excluindo} onOpenChange={(v) => { if (!v) setExcluindo(null) }}>
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
              setExcluindo(null)
            }}
          />
        )}
      </Dialog>
    </>
  )
}

/**
 * O erro de 1ª carga dentro do sidebar: o cartão centralizado do §3.2 não cabe
 * num trilho de 16rem, então fica a forma compacta — mesma semântica
 * (`role="alert"`), mesma microcopy e a mesma saída ("Tentar de novo").
 */
function ErroDaLista({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  const { tentarDeNovo } = useTextosDaCasca().comum
  return (
    <div role="alert" className={`flex flex-col items-start gap-1 px-2 py-1.5 ${SO_EXPANDIDO}`}>
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
 * O caminho virtual (acima de 150 itens): um scroller próprio com altura teto,
 * linhas absolutas. Molde de `run-panel/output-tab.tsx`. Fora do `SidebarMenuSub`
 * (que é `<ul>`) porque as linhas absolutas não são `<li>` — daí os papéis ARIA
 * na mão, e o `aria-setsize`/`aria-posinset` que diz ao leitor de tela o tamanho
 * real da lista (só a janela existe no DOM).
 */
function ListaVirtual({
  itens,
  renderLinha,
}: {
  itens: ItemDoAcervo[]
  renderLinha: (item: ItemDoAcervo) => React.ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  // A lista fica MONTADA quando o item do grupo Meus fecha (o wrapper vira
  // `hidden`), e `display:none` pode zerar o `scrollTop` do scroller sem o
  // virtualizador saber: ao reabrir, a janela calculada era de um offset velho
  // e as linhas ficavam em branco até rolar. `enabled` amarrado à visibilidade
  // — desabilitar descarta a assinatura e reabilitar relê o `scrollTop` real.
  const [visivel, setVisivel] = useState(true)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === "undefined") return
    const ro = new ResizeObserver(([entrada]) => setVisivel(entrada.contentRect.height > 0))
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
      className={`mx-3.5 max-h-[45vh] overflow-y-auto border-l border-sidebar-border pl-0.5 ${SO_EXPANDIDO}`}
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
            // Mede de verdade em vez de confiar nos 32px estimados: a linha
            // cresce no telefone (alvo de 40px) e com badge de retenção, e sem
            // medida as linhas se sobrepunham sem nenhum sinal.
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
