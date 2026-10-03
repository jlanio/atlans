"use client"

// web/app/components/home/assistente/painel.tsx
//
// The FLOATING conversation over the globe — a fork of the editor drawer
// (`assistente/index.tsx`), with the height contract from #111 and without the
// `nowheel/nopan/nodrag` (there is no React Flow underneath here). Open/collapsed
// lives in `homeStore`; the width, in `useResizablePanel`.

import { useCallback, useEffect, useRef } from "react"
import { TbChevronDown, TbPencilPlus, TbPlayerStopFilled, TbSend, TbSparkles } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import { Textarea } from "@/app/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useIsMobile } from "@/hooks/use-mobile"
import { useResizablePanel } from "@/app/hooks/useResizablePanel"
import { useHomeStore } from "@/app/stores/homeStore"
import Conversa from "@/app/components/home/assistente/conversa"
import type { AssistantTurn } from "@/app/components/home/assistente/quadros"
import type { IAssistantState } from "@/service/types"
import type { DecisionResult } from "@/app/hooks/home/useAssistente"
import BadgeArtefatos from "./badge-artefatos"
import {
  RejectedAttachmentsNotice, AttachmentChips, DropPrompt,
  anexosProntos, comReferencia, suggestionForAttachments,
} from "@/app/components/home/assistente/anexos"
import { BotaoMais, ChipDeLocalizacao } from "@/app/components/home/assistente/mais"
import { QuotaFullNotice } from "@/app/components/home/assistente/aviso-de-cota"
import QuotaUsage from "@/app/components/home/assistente/uso-da-cota"
import { useAssistantExtras } from "./extras"
import MarcaAnimada from "./marca-animada"
import { useScreenLanguage, useTexts } from "../i18n"

const WIDTH_KEY = "atlans:home:largura"

interface Props {
  estado: IAssistantState | null
  turnos: AssistantTurn[]
  correndo: boolean
  /** The replay of the selected conversation is still coming in. */
  carregandoReplay?: boolean
  /** Returns focus to the field when the panel was opened by shortcut/button. */
  autoFoco?: boolean
  enviar: (mensagem: string) => Promise<void> | void
  confirmar: (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => Promise<DecisionResult> | void
  parar: () => void
  /** Attaches files chosen in the "+" (the same path as dragging). */
  aoAnexar?: (arquivos: File[]) => void
  /** Triggers the globe's location control (the "+"'s "Usar minha localização"). */
  aoPedirLocalizacao?: () => void
}

export default function Painel({
  estado, turnos, correndo, carregandoReplay = false, autoFoco = false,
  enviar, confirmar, parar, aoAnexar, aoPedirLocalizacao,
}: Props) {
  const recolher = useHomeStore((s) => s.recolherBarra)
  const novaConversa = useHomeStore((s) => s.novaConversa)
  // The cards (confirmation, layer, quick replies) and the "clicked, locked"
  // rule live in the hook shared with the center strip: they are the SAME
  // conversation in two views.
  const extras = useAssistantExtras({ confirmar, correndo, enviar })
  const isMobile = useIsMobile()
  const idioma = useScreenLanguage()
  const t = useTexts().assistente

  // The draft also lives in the store: Ctrl+I collapses to the bar and UNMOUNTS
  // this panel — with local state, the shortcut erased what had been typed.
  // Shared with the bar, the text survives the swap in both directions.
  const rascunho = useHomeStore((s) => s.rascunho)
  const definirRascunho = useHomeStore((s) => s.definirRascunho)
  // The attachments, for the same reason: the feature must not vanish just because
  // the person collapsed the bar into the panel (the editor drawer was finding 4 of
  // review 3 — a feature on one surface and not the other).
  const anexos = useHomeStore((s) => s.anexos)
  const arrastando = useHomeStore((s) => s.arrastandoArquivo)
  const removerAnexo = useHomeStore((s) => s.removerAnexo)
  const limparAnexosProntos = useHomeStore((s) => s.limparAnexosProntos)
  const descartarAnexosRecusados = useHomeStore((s) => s.descartarAnexosRecusados)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Toggling unmounts the focused component and focus falls to <body>: the next Tab
  // starts over from the top of the document. Only when the swap was requested
  // (shortcut/button) — stealing focus on page load would be worse.
  useEffect(() => {
    if (autoFoco) inputRef.current?.focus()
  }, [autoFoco])

  const { width, isResizing, resizeHandleProps } = useResizablePanel({
    storageKey: WIDTH_KEY,
    defaultWidth: 420,
    minWidth: 340,
    maxWidth: 600,
    side: "right",
    enabled: !isMobile,
  })

  const submeter = useCallback(() => {
    const texto = rascunho.trim()
    // With an attachment ready and the field empty, the submission is the reference
    // alone — whoever dropped the file already said what they want. Only the READY
    // ones go in and only they go out.
    if (!texto && anexosProntos(anexos).length === 0) return
    if (correndo) return
    definirRascunho("")
    void enviar(comReferencia(texto, anexos, idioma))
    limparAnexosProntos()
  }, [rascunho, correndo, enviar, definirRascunho, anexos, limparAnexosProntos, idioma])

  const cota = estado?.cota ?? null
  const estourou = cota != null && cota.gasto >= cota.teto

  // The suggested question when there is a ready attachment — the same as the bar's.
  const attachmentSuggestion = suggestionForAttachments(anexos, idioma)
  const hasReadyAttachment = attachmentSuggestion !== null

  return (
    <aside
      // The width goes through a CSS var, and the phone is decided by MEDIA QUERY and
      // not by JS: `useIsMobile` returns `false` on each instance's 1st render,
      // and a 420px panel anchored to the right started with 84px off screen on
      // a 360px phone before jumping to full screen.
      //
      // `absolute` and not `fixed`: the HomeView root is already `relative` and
      // starts AFTER the sidebar. With fixed, the reference corner was the
      // viewport's, and the panel/bar painted over the HomeSidebar.
      style={{ "--largura-painel": `${width}px` } as React.CSSProperties}
      className={cn(
        // Enters from the right, with a fade (globals.css); zero under `prefers-reduced-motion`.
        "home dark home-painel-entra absolute z-30 flex flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl",
        "max-md:inset-x-3 max-md:bottom-3 max-md:top-16 max-md:pb-safe",
        "md:bottom-6 md:right-6 md:h-[min(640px,calc(100svh-6rem))] md:max-h-[calc(100svh-3rem)] md:w-[var(--largura-painel)]",
        !isResizing && "motion-safe:transition-[width]",
      )}
      aria-label={t.painel.titulo}
    >
      {!isMobile && (
        <div
          {...resizeHandleProps}
          // After the spread: the hook labels the handle in Portuguese (the rest of the
          // app is its domain); here it speaks the Home's language.
          aria-label={t.painel.redimensionar}
          title={t.painel.dicaRedimensionar}
          className="group/alca absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize touch-none focus-visible:outline-none"
        >
          <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover/alca:bg-primary group-focus-visible/alca:bg-primary" />
        </div>
      )}

      <header className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <TbSparkles size={16} className="text-primary" aria-hidden="true" />
        <h2 className="flex-1 truncate text-sm font-semibold">{t.painel.titulo}</h2>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => novaConversa()}
          className="size-8 max-md:size-10"
          aria-label={t.painel.novaConversa}
          title={t.painel.novaConversa}
        >
          <TbPencilPlus size={15} aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => recolher()}
          className="size-8 max-md:size-10"
          aria-label={t.painel.recolher}
          title={t.painel.recolher}
        >
          <TbChevronDown size={15} aria-hidden="true" />
        </Button>
      </header>

      <BadgeArtefatos turnos={turnos} />

      <Conversa
        turnos={turnos}
        correndo={correndo}
        extras={extras}
        nome={t.nome}
        // The default empty conversation is the EDITOR's: it asks you to describe a
        // workflow and talks about applying it on the canvas, which does not exist here.
        vazio={carregandoReplay ? <LoadingConversation /> : <Primeira />}
        // The pending item with the site's logo: here the one thinking is the site.
        indicador={MarcaAnimada}
        // The terracotta cursor at the end of the paragraph being written.
        cursorAoEscrever
      />

      {estourou && cota && (
        <QuotaFullNotice
          cota={cota}
          plano={estado?.plano}
          assinaturasAtivas={estado?.assinaturas_ativas}
          className="mx-3 mb-2 shrink-0 justify-start rounded-md px-2.5 py-1.5"
        />
      )}

      <RejectedAttachmentsNotice anexos={anexos} onFechar={descartarAnexosRecusados} className="mx-3 mb-2 shrink-0" />

      <form
        className="shrink-0 border-t border-border p-2"
        // The drag highlight in the drawer follows the same contract as the bar
        // (`data-arraste`), except that here the target is the composer, not a pill.
        data-arraste={arrastando}
        onSubmit={(e) => { e.preventDefault(); submeter() }}
      >
        {arrastando && <DropPrompt className="mb-2 px-1" />}
        <AttachmentChips anexos={anexos} onRemover={removerAnexo} className="mb-2 px-0.5" />
        <ChipDeLocalizacao className="mb-2 px-0.5" />
        <div className="flex items-end gap-2">
          {(aoAnexar || aoPedirLocalizacao) && (
            <BotaoMais aoAnexar={aoAnexar} aoLocalizar={aoPedirLocalizacao} className="size-9 max-md:size-10" />
          )}
          <Textarea
            ref={inputRef}
            value={rascunho}
            onChange={(e) => definirRascunho(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submeter() }
            }}
            rows={2}
            maxLength={8000}
            disabled={estourou}
            placeholder={attachmentSuggestion ?? t.barra.placeholder}
            className="max-h-40 min-h-[2.75rem] resize-none text-sm"
            aria-label={t.barra.rotuloDoCampo}
          />
          {correndo ? (
            <Button type="button" variant="outline" size="icon" onClick={parar} className="size-9 shrink-0 max-md:size-10" aria-label={t.painel.parar} title={t.painel.parar}>
              <TbPlayerStopFilled size={14} aria-hidden="true" />
            </Button>
          ) : (
            <Button type="submit" size="icon" disabled={(!rascunho.trim() && !hasReadyAttachment) || estourou} className="size-9 shrink-0 active:scale-90 max-md:size-10" aria-label={t.barra.enviar}>
              <TbSend size={15} aria-hidden="true" />
            </Button>
          )}
        </div>
        {cota != null && (
          <div className="mt-1.5 flex justify-end">
            <QuotaUsage cota={cota} />
          </div>
        )}
      </form>
    </aside>
  )
}

/**
 * The Home's invitation. The Conversa's is the EDITOR's — it asks you to describe
 * a workflow and talks about "aplicar no canvas", two things that do not exist on
 * `/` and that also contradicted the placeholder right below ("O que você quer saber?").
 */
function Primeira() {
  const t = useTexts().assistente.painel
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-3 px-6 py-10 text-center">
      <span className="rounded-full bg-muted/60 p-4" aria-hidden="true">
        <TbSparkles size={22} className="text-muted-foreground/50" />
      </span>
      <p className="text-sm font-semibold text-foreground">{t.primeiraTitulo}</p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {t.primeiraTexto}
      </p>
      <p className="rounded-md bg-muted/50 px-2.5 py-2 text-left text-xs italic text-muted-foreground">
        {t.primeiraExemplo}
      </p>
    </div>
  )
}

/** The conversation replay is on its way — this is not an empty conversation. */
function LoadingConversation() {
  const t = useTexts().assistente.painel
  return (
    <div className="flex min-h-full flex-col justify-end gap-3 px-1 py-2" role="status">
      <span className="sr-only">{t.carregandoConversa}</span>
      <span className="h-3 w-2/5 animate-pulse rounded bg-muted/60" aria-hidden="true" />
      <span className="ml-auto h-8 w-3/5 animate-pulse rounded-lg bg-primary/10" aria-hidden="true" />
      <span className="h-3 w-4/5 animate-pulse rounded bg-muted/60" aria-hidden="true" />
      <span className="h-3 w-3/5 animate-pulse rounded bg-muted/60" aria-hidden="true" />
    </div>
  )
}
