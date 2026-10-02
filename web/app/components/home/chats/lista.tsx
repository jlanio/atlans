"use client"
import { useEffect, useRef, useState } from "react"
import { TbLoader2 } from "react-icons/tb"
import {
  SidebarMenuSub, SidebarMenuSubItem, SidebarMenuSkeleton, useSidebar,
} from "@/app/components/ui/sidebar"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { AvisoAmbar } from "@/app/components/shared/estados"
import { createToast } from "@/utils/createToast"
import { useConversas } from "@/app/hooks/home/useConversas"
import { useHomeStore } from "@/app/stores/homeStore"
import { LinhaDoMeu, GatilhoDeAcoes } from "../linha"
import { useFormatos, useTextosDaCasca } from "../i18n/da-casca"
import type { IConversaResumo } from "@/service/types"
import { RenomearDialog } from "./renomear-dialog"

// Os blocos que não são `SidebarMenuSub` (avisos, rodapé) precisam sumir à mão
// no trilho de 3rem: só a sublista traz a classe de ocultação de fábrica.
const SO_EXPANDIDO = "group-data-[collapsible=icon]:hidden"

/**
 * "Recentes": a lista de conversas do assistente, dentro do grupo Meus → Chats.
 * Renderiza um `SidebarMenuSub` (o `<ul>` indentado). A conversa ativa fica
 * destacada; cada linha tem um menu ⋯ com Renomear e Apagar.
 *
 * Clicar seleciona a conversa e abre o painel flutuante. A lista vem cortada no
 * teto do servidor — o rodapé diz o total e oferece "Ver mais", porque não há
 * outra tela de Chats onde procurar o que ficou de fora.
 */
export function ChatsLista() {
  const {
    conversas, carregando, atualizando, jaCarregou, erro, total, carregandoMais,
    recarregar, carregarMais, tentarDeNovo, anunciar, renomear, apagar,
  } = useConversas()
  const conversaId = useHomeStore((s) => s.conversaId)
  const selecionar = useHomeStore((s) => s.selecionarConversa)
  const abrirPainel = useHomeStore((s) => s.abrirPainel)
  const novaConversa = useHomeStore((s) => s.novaConversa)
  const anuncio = useHomeStore((s) => s.anuncioDeConversa)
  const { isMobile, setOpenMobile } = useSidebar()
  const textos = useTextosDaCasca()
  const t = textos.listas
  const fmt = useFormatos()

  // O stream do assistente (no HomeView, irmão desta lista na casca) deixa na
  // store o anúncio "esta conversa ganhou atividade", e a lista o aplica sem
  // GET — é assim que a conversa nova entra nos Recentes sem F5. O que já
  // existia ao montar é passado (a carga de montagem traz a verdade; no telefone
  // a lista remonta a cada abertura da gaveta). E espera uma carga em voo: a
  // resposta dela SUBSTITUI a lista e apagaria o anúncio aplicado no meio;
  // depois dela o upsert é no-op se a resposta já trouxe a conversa.
  const visto = useRef(anuncio)
  useEffect(() => {
    if (!anuncio || anuncio === visto.current || carregando || atualizando) return
    visto.current = anuncio
    anunciar(anuncio)
  }, [anuncio, carregando, atualizando, anunciar])

  const [renomeando, setRenomeando] = useState<IConversaResumo | null>(null)
  const [apagando, setApagando] = useState<IConversaResumo | null>(null)

  // O painel abriria ATRÁS da gaveta no telefone: fecha junto, como o botão
  // "Nova conversa" do HomeSidebar já faz.
  function escolher(id: string) {
    selecionar(id)
    abrirPainel()
    if (isMobile) setOpenMobile(false)
  }

  const faltam = total > conversas.length

  // O corpo é escolhido numa VARIÁVEL, não por `return` antecipado: o rodapé
  // (aviso de recarga falhada + "Ver mais") tem de viver FORA dos ramos. Com a
  // lista vazia o `return` curto saía antes dele e uma recarga que falhava não
  // tinha onde aparecer. Mesmo desenho de `artefatos/lista.tsx`.
  let corpo: React.ReactNode
  if (carregando) {
    corpo = (
      <SidebarMenuSub role="status" aria-busy="true" aria-label={t.chats.carregando}>
        {[0, 1, 2].map((i) => (
          <SidebarMenuSubItem key={i}>
            <SidebarMenuSkeleton />
          </SidebarMenuSubItem>
        ))}
      </SidebarMenuSub>
    )
  } else if (erro && !jaCarregou) {
    // §3: o bloco de erro só toma a lista quando nunca houve carga aceita. Com
    // conversas na tela, a falha vira o aviso âmbar do rodapé.
    corpo = (
      <div role="alert" className={`flex flex-col items-start gap-1 px-2 py-1.5 ${SO_EXPANDIDO}`}>
        <p className="text-xs text-sidebar-foreground/70">{erro}</p>
        <button
          type="button"
          onClick={recarregar}
          className="inline-flex items-center rounded-sm text-xs font-medium text-sidebar-foreground underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
        >
          {textos.comum.tentarDeNovo}
        </button>
      </div>
    )
  } else if (conversas.length === 0) {
    corpo = (
      <SidebarMenuSub>
        <li className="px-2 py-1.5 text-xs text-sidebar-foreground/55">{t.chats.vazio}</li>
      </SidebarMenuSub>
    )
  } else {
    corpo = (
      <SidebarMenuSub aria-busy={atualizando || undefined}>
        {conversas.map((c) => {
          const rotulo = c.titulo?.trim() || t.chats.semTitulo
          const ativa = conversaId === c.id
          return (
            <SidebarMenuSubItem key={c.id}>
              <LinhaDoMeu ativa={ativa}>
                {/* Um `<button>` cru, e não o `SidebarMenuSubButton` do shadcn:
                    aquele primitivo é feito para `<a>` e não tem `w-full` — e um
                    `<button>` flex sem largura fica do tamanho do CONTEÚDO. Com
                    o título em `nowrap`, o botão transbordava a linha inteira
                    até a borda da barra, sem truncar nunca (medido: 546px numa
                    linha de 207px). `flex-1` no flex da linha o prende ao
                    espaço que existe, e só então o `truncate` tem onde cortar.

                    `aria-current`: o `data-active` da linha é só visual, e a
                    diferença de fundo na paleta da Home é quase imperceptível —
                    sem isto nada dizia qual conversa está no painel. */}
                <button
                  type="button"
                  aria-current={ativa ? "true" : undefined}
                  onClick={() => escolher(c.id)}
                  title={rotulo}
                  className="flex h-7 min-w-0 flex-1 items-center rounded-md text-left text-sm text-sidebar-foreground outline-hidden ring-sidebar-ring focus-visible:ring-2 max-md:min-h-10"
                >
                  <span className="truncate">{rotulo}</span>
                </button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <GatilhoDeAcoes rotulo={rotulo} />
                  </DropdownMenuTrigger>
                  {/* `home-portal`: o menu é portado para o <body>, FORA da árvore
                      que declara a paleta da Home — sem a classe ele abria claro
                      sobre a Home quase preta quando o app está no tema claro.
                      Os itens ganham 40px no telefone: o gatilho já era grande o
                      bastante, o destino do toque é que não era. */}
                  <DropdownMenuContent align="end" className="home-portal min-w-32">
                    <DropdownMenuItem onSelect={() => setRenomeando(c)} className="max-md:min-h-10">
                      {textos.comum.renomear}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onSelect={() => setApagando(c)}
                      className="text-destructive focus:text-destructive max-md:min-h-10"
                    >
                      {textos.comum.apagar}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </LinhaDoMeu>
            </SidebarMenuSubItem>
          )
        })}
      </SidebarMenuSub>
    )
  }

  return (
    <>
      {corpo}

      {/* O rodapé vive FORA dos ramos: com a lista VAZIA e uma recarga que
          falhou, o aviso âmbar não tinha onde aparecer. */}
      {((erro && jaCarregou) || faltam) && (
        <div className={`flex flex-col gap-1 px-2 pb-1 ${SO_EXPANDIDO}`}>
          {/* Refaz o que FALHOU: depois de um "Ver mais" que caiu, é a página —
              não a lista inteira, que ainda por cima voltava ao teto de 100. */}
          {erro && jaCarregou && (
            <AvisoAmbar onTentar={tentarDeNovo} rotuloDoBotao={textos.comum.tentarDeNovo}>{erro}</AvisoAmbar>
          )}
          {faltam && (
            <div className="flex flex-wrap items-center gap-x-2 px-1">
              <span className="text-[11px] tabular-nums text-sidebar-foreground/55">
                {t.geral.mostrando(fmt.inteiro(conversas.length), fmt.inteiro(total))}
              </span>
              <button
                type="button"
                onClick={carregarMais}
                disabled={carregandoMais}
                className="inline-flex items-center gap-1 rounded-sm text-[11px] font-medium text-sidebar-foreground underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-60 max-md:min-h-10"
              >
                {carregandoMais && <TbLoader2 className="size-3 animate-spin" aria-hidden="true" />}
                {t.geral.verMais}
              </button>
            </div>
          )}
        </div>
      )}

      <RenomearDialog
        conversa={renomeando}
        onClose={() => setRenomeando(null)}
        onRenomear={renomear}
      />

      <Dialog open={!!apagando} onOpenChange={(v) => { if (!v) setApagando(null) }}>
        {apagando && (
          <DeleteDialog
            className="home-portal"
            title={t.chats.apagar.titulo}
            description={t.chats.apagar.descricao(apagando.titulo?.trim() || t.chats.semTitulo)}
            confirmLabel={textos.comum.apagar}
            loadingLabel={t.chats.apagar.apagando}
            cancelLabel={textos.comum.cancelar}
            closeLabel={textos.comum.fechar}
            onConfirm={async () => {
              // O DeleteDialog não tem canal de erro e fecha de qualquer jeito:
              // sem o toast, a conversa continuava na lista e parecia que a
              // exclusão tinha dado certo e a tela é que não atualizara.
              const r = await apagar(apagando.id)
              if (!r.ok) createToast.error(t.chats.apagar.falhou, r.erro)
              // Apagar a ATIVA deixa a Home como o botão "Nova conversa": sem
              // isto o painel seguia na conversa morta e a mensagem seguinte
              // batia num 404. Lido na hora (`getState`), não pelo closure.
              else if (useHomeStore.getState().conversaId === apagando.id) novaConversa()
              setApagando(null)
            }}
          />
        )}
      </Dialog>
    </>
  )
}
