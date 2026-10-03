"use client"

// web/app/components/home/assistente/mais.tsx
//
// The composer's "+" and the location chip — the two new pieces of "locate in
// the assistant". Mounted by the bar AND by the panel, like the attachments,
// because Ctrl+I swaps one surface for the other and the feature must not vanish
// with the swap (finding 4 of review 3: a feature on one surface and not the other).
//
// - `BotaoMais`: the "+" menu. It gathers what ENTERS the conversation besides
//   text — today "Anexar arquivo" (the same path as drag-and-drop, now with a
//   discoverable home) and "Usar minha localização" (triggers the globe control).
//   One menu, not two loose buttons, so as not to bloat the bar's pill.
// - `ChipDeLocalizacao`: the attached location, visible and removable — the
//   mirror of `ChipsDeAnexo`. Reads the store directly (like the attachments), so
//   it needs no prop; the × only removes it from the conversation, it does not
//   turn off follow mode on the globe.

import { useRef } from "react"
import { TbCurrentLocation, TbMapPin, TbPaperclip, TbPlus, TbX } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { useHomeStore } from "@/app/stores/homeStore"
import { cn } from "@/lib/utils"
import { useTextos } from "../i18n"

/** lat/lon with 4 decimal places (~11 m) — the rest is noise to the assistant. */
function coord(n: number): string {
  return n.toFixed(4)
}

/**
 * The composer's "+": a menu with what can be added to the turn besides text.
 * `aoAnexar`/`aoLocalizar` come from HomeView (the upload and triggering the
 * globe). Without either of them the bar does not mount it (that is what keeps
 * the existing tests intact), so here they are optional only for type safety.
 */
export function BotaoMais({
  aoAnexar, aoLocalizar, className,
}: {
  aoAnexar?: (arquivos: File[]) => void
  aoLocalizar?: () => void
  className?: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const t = useTextos().assistente.mais

  return (
    <>
      {/* The same path as drag-and-drop (useAnexos.receber); the server is
          the one that filters, so no `accept` here — same as dragging. */}
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        tabIndex={-1}
        aria-hidden="true"
        data-testid="entrada-de-arquivo"
        onChange={(e) => {
          const arquivos = Array.from(e.target.files ?? [])
          // Reset so that dropping/choosing the SAME file again re-fires the change.
          e.target.value = ""
          if (arquivos.length) aoAnexar?.(arquivos)
        }}
      />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className={cn("shrink-0 text-muted-foreground", className)}
            aria-label={t.rotulo}
            title={t.titulo}
          >
            <TbPlus size={16} aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        {/* `home-portal`: the menu is portaled to <body>, OUTSIDE the `home dark`
            tree — without the class it would render light over the always-dark
            Home when the app theme is light (the same idiom as the Chats menu). */}
        <DropdownMenuContent align="start" side="top" className="home-portal min-w-56">
          <DropdownMenuItem onSelect={() => inputRef.current?.click()}>
            <TbPaperclip size={15} aria-hidden="true" />
            {t.anexar}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => aoLocalizar?.()}>
            <TbCurrentLocation size={15} aria-hidden="true" />
            {t.localizacao}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  )
}

/**
 * The attached location — visible, in the same row as the attachment chips.
 * Reads the store directly (the coordinate can change live in follow mode). Only
 * shows up with SHARING on: the × turns off the intent — and it stays off, even
 * with the globe's follow mode still emitting positions — until a new gesture on
 * the "+". Follow mode on the globe continues until the person turns it off there.
 */
export function ChipDeLocalizacao({ className }: { className?: string }) {
  const compartilhar = useHomeStore((s) => s.compartilharLocalizacao)
  const localizacao = useHomeStore((s) => s.localizacao)
  const limpar = useHomeStore((s) => s.limparLocalizacao)
  const t = useTextos().assistente.mais
  if (!compartilhar || !localizacao) return null

  const precisao = localizacao.precisao_m != null && Number.isFinite(localizacao.precisao_m)
    ? `±${Math.round(localizacao.precisao_m)} m`
    : null

  return (
    <div
      data-testid="chip-de-localizacao"
      className={cn("flex list-none flex-wrap gap-1.5 p-0", className)}
    >
      <span className="flex min-w-0 max-w-full items-center gap-1.5 rounded-md border border-primary/40 bg-primary/10 px-2 py-1 text-[11.5px]">
        <TbMapPin size={13} className="shrink-0 text-primary" aria-hidden="true" />
        <span className="min-w-0 truncate font-mono tabular-nums text-foreground">
          {coord(localizacao.lat)}, {coord(localizacao.lon)}
        </span>
        {precisao && <span className="shrink-0 font-mono text-muted-foreground">{precisao}</span>}
        <button
          type="button"
          onClick={limpar}
          aria-label={t.tirarLocalizacao}
          className="shrink-0 rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <TbX size={12} aria-hidden="true" />
        </button>
      </span>
    </div>
  )
}
