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
import { useFormats, useShellTexts } from "../i18n/da-casca"
import type { IConversationSummary } from "@/service/types"
import { RenameDialog } from "./renomear-dialog"

// The blocks that are not `SidebarMenuSub` (notices, footer) must be hidden by
// hand in the 3rem rail: only the sublist comes with the hiding class built in.
const EXPANDED_ONLY = "group-data-[collapsible=icon]:hidden"

/**
 * "Recentes": the list of assistant conversations, inside the Meus → Chats group.
 * Renders a `SidebarMenuSub` (the indented `<ul>`). The active conversation is
 * highlighted; each row has a ⋯ menu with Renomear and Apagar.
 *
 * Clicking selects the conversation and opens the floating panel. The list comes
 * cut at the server's ceiling — the footer states the total and offers "Ver
 * mais", because there is no other Chats screen to search for what was left out.
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
  const announcement = useHomeStore((s) => s.anuncioDeConversa)
  const { isMobile, setOpenMobile } = useSidebar()
  const textos = useShellTexts()
  const t = textos.listas
  const fmt = useFormats()

  // The assistant stream (in HomeView, this list's sibling in the shell) leaves in
  // the store the announcement "this conversation got activity", and the list
  // applies it without a GET — that is how the new conversation enters Recentes
  // without F5. Whatever already existed at mount is past (the mount load brings
  // the truth; on the phone the list remounts on every drawer opening). And it
  // waits for an in-flight load: its response REPLACES the list and would erase
  // the announcement applied in the meantime; after it, the upsert is a no-op if
  // the response already brought the conversation.
  const visto = useRef(announcement)
  useEffect(() => {
    if (!announcement || announcement === visto.current || carregando || atualizando) return
    visto.current = announcement
    anunciar(announcement)
  }, [announcement, carregando, atualizando, anunciar])

  const [renaming, setRenaming] = useState<IConversationSummary | null>(null)
  const [apagando, setErasing] = useState<IConversationSummary | null>(null)

  // The panel would open BEHIND the drawer on the phone: close it too, as the
  // HomeSidebar's "Nova conversa" button already does.
  function escolher(id: string) {
    selecionar(id)
    abrirPainel()
    if (isMobile) setOpenMobile(false)
  }

  const faltam = total > conversas.length

  // The body is chosen in a VARIABLE, not by an early `return`: the footer
  // (failed-reload notice + "Ver mais") has to live OUTSIDE the branches. With
  // the list empty the short `return` exited before it and a failing reload had
  // nowhere to show up. Same design as `artefatos/lista.tsx`.
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
    // §3: the error block only takes over the list when no load was ever accepted.
    // With conversations on screen, the failure becomes the amber footer notice.
    corpo = (
      <div role="alert" className={`flex flex-col items-start gap-1 px-2 py-1.5 ${EXPANDED_ONLY}`}>
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
                {/* A raw `<button>`, not shadcn's `SidebarMenuSubButton`: that
                    primitive is made for `<a>` and has no `w-full` — and a flex
                    `<button>` without a width is the size of its CONTENT. With
                    the title `nowrap`, the button overflowed the whole row up to
                    the edge of the bar, never truncating (measured: 546px in a
                    207px row). `flex-1` in the row's flex pins it to the space
                    that exists, and only then does `truncate` have somewhere to cut.

                    `aria-current`: the row's `data-active` is only visual, and
                    the background difference in the Home palette is almost
                    imperceptible — without this nothing said which conversation
                    is in the panel. */}
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
                  {/* `home-portal`: the menu is portaled to <body>, OUTSIDE the tree
                      that declares the Home palette — without the class it
                      opened light over the near-black Home when the app is in
                      the light theme. The items get 40px on the phone: the
                      trigger was already big enough, the tap target was not. */}
                  <DropdownMenuContent align="end" className="home-portal min-w-32">
                    <DropdownMenuItem onSelect={() => setRenaming(c)} className="max-md:min-h-10">
                      {textos.comum.renomear}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onSelect={() => setErasing(c)}
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

      {/* The footer lives OUTSIDE the branches: with the list EMPTY and a reload
          that failed, the amber notice had nowhere to show up. */}
      {((erro && jaCarregou) || faltam) && (
        <div className={`flex flex-col gap-1 px-2 pb-1 ${EXPANDED_ONLY}`}>
          {/* Redo what FAILED: after a "Ver mais" that dropped, it is the page —
              not the whole list, which on top of that went back to the 100 ceiling. */}
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

      <RenameDialog
        conversa={renaming}
        onClose={() => setRenaming(null)}
        onRenomear={renomear}
      />

      <Dialog open={!!apagando} onOpenChange={(v) => { if (!v) setErasing(null) }}>
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
              // The DeleteDialog has no error channel and closes regardless:
              // without the toast, the conversation stayed in the list and it
              // looked as if the deletion had worked and the screen just had not updated.
              const r = await apagar(apagando.id)
              if (!r.ok) createToast.error(t.chats.apagar.falhou, r.erro)
              // Deleting the ACTIVE one leaves the Home like the "Nova conversa" button:
              // without this the panel stayed on the dead conversation and the
              // next message hit a 404. Read on the spot (`getState`), not via the closure.
              else if (useHomeStore.getState().conversaId === apagando.id) novaConversa()
              setErasing(null)
            }}
          />
        )}
      </Dialog>
    </>
  )
}
