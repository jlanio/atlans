"use client"

// web/app/components/workflow/assistente/index.tsx
//
// The assistant drawer — a column DOCKED to the right of the canvas.
//
// **It is not shadcn's `Sheet`**: that is a modal overlay with a scrim, and
// darkening the canvas would hide precisely what the conversation is building.
// Here the drawer is a flex sibling of React Flow: the canvas SHRINKS, both stay
// visible, and you can watch the workflow appear while reading the explanation.
// It's the same reason `run-panel` stopped being a Sheet.
//
// Dragging comes from `useResizablePanel`, which already handles pointer capture,
// keyboard, viewport clamping and remembering the width in `localStorage`.

import { useCallback, useEffect, useState } from "react"
import { TbDotsVertical, TbPlayerStopFilled, TbSend, TbSparkles, TbX } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { Textarea } from "@/app/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useResizablePanel } from "@/app/hooks/useResizablePanel"
import { useAssistenteEditor } from "@/app/hooks/workflow/useAssistenteEditor"
import { useAssistenteEditorStore } from "@/app/stores/assistenteEditorStore"
import { AvisoDeCotaCheia } from "@/app/components/home/assistente/aviso-de-cota"
import type { ResultadoDaProposta } from "../utils/aplicar-proposta"
import Conversa from "@/app/components/home/assistente/conversa"
import CartaoProposta from "./cartao-proposta"
import UsoDaCota from "@/app/components/home/assistente/uso-da-cota"

const CHAVE_LARGURA = "atlans:assistente:largura"

// F4 renamed the width key (it was atlans:copiloto:largura) without a migration.
// Copies the old one to the new one ONCE, on module load (client only),
// before any useResizablePanel reads the preference.
;(function migrarLarguraLegada() {
  try {
    if (typeof window === "undefined") return
    if (window.localStorage.getItem(CHAVE_LARGURA) !== null) return
    const legada = window.localStorage.getItem("atlans:copiloto:largura")
    if (legada !== null) window.localStorage.setItem(CHAVE_LARGURA, legada)
  } catch { /* disposable preference */ }
})()

interface Props {
  /** The open workflow. Absent on the create screen — the backend keeps that conversation separately. */
  workflowId?: string
  /**
   * Opens by default when there is no stored preference. True on the create
   * screen, where the canvas is born empty and the drawer is the shortest path.
   */
  abrirPorPadrao?: boolean
  onAplicar: (resultado: ResultadoDaProposta) => void
}

export default function AssistentePainel({ workflowId, abrirPorPadrao = false, onAplicar }: Props) {
  const aberto = useAssistenteEditorStore(s => s.aberto)
  const fechar = useAssistenteEditorStore(s => s.fechar)
  const alternar = useAssistenteEditorStore(s => s.alternar)
  const hidratar = useAssistenteEditorStore(s => s.hidratar)

  const { estado, consultando, turnos, correndo, enviar, parar, esquecer } = useAssistenteEditor(workflowId)
  const [rascunho, setRascunho] = useState("")
  // The acceptance to draw on a canvas that ALREADY HAS work, once per conversation.
  // Resets when switching workflows and when restarting the conversation, for the
  // same reasons the conversation resets: it's another conversation, and consent
  // doesn't carry over.
  const [liberado, setLiberado] = useState(false)
  useEffect(() => { setLiberado(false) }, [workflowId])

  useEffect(() => { hidratar(abrirPorPadrao) }, [hidratar, abrirPorPadrao])

  // Ctrl+I, on the template of the run dock's Ctrl+` — and with the same guard:
  // without it, the shortcut would fire while someone types a node's SQL query.
  useEffect(() => {
    function editando(alvo: EventTarget | null) {
      const el = alvo as HTMLElement | null
      return !!el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))
    }
    function aoTeclar(e: KeyboardEvent) {
      if (editando(e.target)) return
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "i") {
        e.preventDefault()
        alternar()
      }
    }
    window.addEventListener("keydown", aoTeclar)
    return () => window.removeEventListener("keydown", aoTeclar)
  }, [alternar])

  const { width, isResizing, resizeHandleProps } = useResizablePanel({
    storageKey: CHAVE_LARGURA,
    defaultWidth: 380,
    minWidth: 300,
    maxWidth: 560,
    side: "right",
    enabled: aberto,
  })

  const submeter = useCallback(() => {
    const texto = rascunho.trim()
    if (!texto || correndo) return
    setRascunho("")
    void enviar(texto)
  }, [rascunho, correndo, enviar])

  // Disabled in the installation: the drawer doesn't exist, and nothing in the
  // editor changes. It's the right behavior for whoever runs Atlans without the
  // external dependency.
  if (consultando || estado?.ativo !== true) return null

  if (!aberto) {
    return (
      <Button
        variant="outline"
        size="icon"
        onClick={alternar}
        title="Assistente (Ctrl+I)"
        aria-label="Abrir o assistente"
        className="absolute right-5 top-[4.5rem] z-10 size-11 rounded-lg shadow-lg max-md:hidden"
      >
        <TbSparkles size={20} aria-hidden="true" />
      </Button>
    )
  }

  const cota = estado.cota ?? null
  const estourou = cota != null && cota.gasto >= cota.teto

  return (
    <aside
      // nowheel/nopan/nodrag: without them React Flow captures the conversation's
      // scrolling and the handle's drag, and scrolling the list zoomed the graph.
      //
      // `max-h-svh` is the CEILING, and without it the conversation's
      // `overflow-y-auto` never scrolls. The dashboard shell is `min-h-svh`
      // (`ui/sidebar.tsx`), which is a FLOOR and not a ceiling: since this drawer
      // is the only IN-FLOW child of the editor container — everything else in
      // there is `absolute` —, its intrinsic contribution is the whole
      // conversation, and the height climbs up the chain until the page grows.
      // Then the scrolling goes to the viewport instead of the list, and the send
      // field leaves the screen. The ceiling breaks that circularity at a single
      // point.
      //
      // `h-full` STAYS alongside: on its own, `h-svh` would decouple the drawer
      // from the box that contains it and would overflow the day there was a
      // header above. The pair says "be the height you were given, but don't go
      // beyond one screen".
      //
      // `svh` and not `dvh`, and the reason is in the floor: `dvh >= svh`, so a
      // ceiling in `dvh` sits ABOVE the shell's `min-h-svh` and the defect would
      // come back with the address bar retracted — intermittent, which is worse.
      // The repository's uses of `dvh` (`ui/dialog.tsx` and the modals that use
      // it) are the opposite case: boxes that need to fit a moving target. This
      // is a shell, like the sidebar container's `h-svh`, and a shell can't
      // reflow in the middle of scrolling.
      className={cn(
        "nowheel nopan nodrag relative z-20 flex h-full max-h-svh shrink-0 flex-col border-l border-border bg-background",
        // On the phone the drawer takes over the screen: a 360px canvas split in two
        // serves neither half.
        "max-md:absolute max-md:inset-0 max-md:w-full max-md:border-l-0",
        !isResizing && "motion-safe:transition-[width]",
      )}
      style={{ width }}
      aria-label="Assistente"
      onContextMenu={e => e.stopPropagation()}
    >
      <div
        {...resizeHandleProps}
        className="group/alca absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize touch-none max-md:hidden focus-visible:outline-none"
      >
        <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover/alca:bg-primary group-focus-visible/alca:bg-primary" />
      </div>

      <header className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <TbSparkles size={16} className="text-primary" aria-hidden="true" />
        <h2 className="flex-1 truncate text-sm font-semibold">Assistente</h2>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-8 max-md:size-10" aria-label="Mais ações do assistente">
              <TbDotsVertical size={15} aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => { setLiberado(false); void esquecer() }}>
              Recomeçar a conversa
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="icon"
          onClick={fechar}
          className="size-8 max-md:size-10"
          aria-label="Fechar o assistente"
          title="Fechar (Ctrl+I)"
        >
          <TbX size={15} aria-hidden="true" />
        </Button>
      </header>

      <Conversa
        turnos={turnos}
        correndo={correndo}
        proposta={(p) => (
          <CartaoProposta
            proposta={p}
            onAplicar={onAplicar}
            liberado={liberado}
            onLiberar={() => setLiberado(true)}
          />
        )}
      />

      {estourou && cota && (
        // The THIRD surface of the warning. It had been left with the old copy:
        // without the offer and saying "reabre em algumas horas" (reopens in a
        // few hours) with the exact deadline at hand — the offer (from an
        // extension, see `web/extensoes`) disappeared depending on the screen
        // where the person hit the ceiling, which is precisely what the
        // component exists to prevent.
        <AvisoDeCotaCheia
          cota={cota}
          plano={estado.plano}
          assinaturasAtivas={estado.assinaturas_ativas}
          className="mx-3 mb-2 shrink-0 justify-start rounded-md px-2.5 py-1.5"
        />
      )}

      <form
        className="shrink-0 border-t border-border p-2"
        onSubmit={e => { e.preventDefault(); submeter() }}
      >
        <div className="flex items-end gap-2">
          <Textarea
            value={rascunho}
            onChange={e => setRascunho(e.target.value)}
            // Enter sends, Shift+Enter breaks the line — what every chat field
            // does, and the opposite of what a textarea does on its own.
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                submeter()
              }
            }}
            rows={2}
            maxLength={8000}
            disabled={estourou}
            placeholder="Descreva o fluxo que você quer…"
            className="max-h-40 min-h-[2.75rem] resize-none text-sm"
            aria-label="Mensagem para o assistente"
          />
          {correndo ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={parar}
              className="size-9 shrink-0 max-md:size-10"
              aria-label="Parar"
              title="Parar"
            >
              <TbPlayerStopFilled size={14} aria-hidden="true" />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              disabled={!rascunho.trim() || estourou}
              className="size-9 shrink-0 max-md:size-10"
              aria-label="Enviar"
            >
              <TbSend size={15} aria-hidden="true" />
            </Button>
          )}
        </div>
        {cota != null && (
          <div className="mt-1.5 flex justify-end">
            <UsoDaCota cota={cota} superficie="editor" />
          </div>
        )}
      </form>
    </aside>
  )
}
