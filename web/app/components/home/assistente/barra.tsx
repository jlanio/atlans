"use client"

// web/app/components/home/assistente/barra.tsx
//
// The Home's command bar, in TWO variants of the SAME element:
//
// - `hero`: the initial state of every visit. Centered and larger (56 px, 16 px
//   text), with a discreet ring and glow, TYPED suggestions in the empty field
//   and three chips below. While the assistant processes the first question,
//   the chips give way to a status line ("Trabalhando…", Esc to stop).
// - `rodape`: the usual bar, in the footer, centered ON THE GLOBE AREA (it is
//   `absolute` inside the HomeView root, which already starts after the sidebar).
//
// The swap is of the SAME DOM node: HomeView changes `variante` on the first
// token of the response and the CSS (`.home-barra`, in globals.css) animates
// position, width and height over 900 ms; with `prefers-reduced-motion` the swap
// is immediate.
//
// Sending does NOT open the panel: the conversation stays in the center (the
// strip above the bar). The chevron opens the side panel, to read everything.
//
// Sending has a signal: a terracotta ring flashes on the box (`data-flash`, the
// `::after` of `.home-barra-caixa` in globals.css) and the button sinks. And when
// the panel opens, the bar doesn't unmount right away: HomeView holds it for an
// instant with `saindo`, and it fades out (`data-saindo`), with no clicks or focus.
//
// The box is also the VISUAL TARGET of file dragging (`data-arraste`): the one
// that accepts the file is the whole window (`useArrasteDeArquivos`), but what
// lights up is the box, and the files become chips right above — see `anexos.tsx`.

import { useEffect, useRef, useState } from "react"
import { TbArrowUp, TbChevronUp, TbPlayerStopFilled, TbSparkles } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import ExecActivity from "@/app/components/shared/exec-activity"
import {
  AvisoDeAnexosRecusados, ChipsDeAnexo, ConviteDeSoltura, comReferencia, sugestaoParaAnexos,
} from "@/app/components/home/assistente/anexos"
import { BotaoMais, ChipDeLocalizacao } from "@/app/components/home/assistente/mais"
import { AvisoDeCotaCheia } from "@/app/components/home/assistente/aviso-de-cota"
import { IndicadorDeEtapa, type Etapa } from "@/app/components/home/assistente/etapa"
import UsoDaCota from "@/app/components/home/assistente/uso-da-cota"
import MarcaAnimada from "@/app/components/home/assistente/marca-animada"
import { usePrefereMenosMovimento } from "@/app/hooks/usePrefereMenosMovimento"
import { useHomeStore } from "@/app/stores/homeStore"
import { cn } from "@/lib/utils"
import type { IAssistenteEstado } from "@/service/types"
import { useIdiomaDaTela, useTextos } from "../i18n"

export type VarianteDaBarra = "hero" | "rodape"

interface Props {
  enviar: (mensagem: string) => Promise<void> | void
  /** A stream is in progress — the hook's `enviar` returns silently. */
  correndo?: boolean
  estado?: IAssistenteEstado | null
  /** Returns focus to the field when the bar appeared via shortcut/button. */
  autoFoco?: boolean
  /** `hero` on the first visit; `rodape` after the first response. */
  variante?: VarianteDaBarra
  /** Interrupts the stream: the stop button (and Esc, via HomeView). */
  parar?: () => void
  /** The panel opened and the bar is leaving: fade, no clicks, no stealing focus. */
  saindo?: boolean
  /**
   * The height, in px, of what the bar stacks ABOVE the box (chips, invitation,
   * rejected warning). The strip (`Pilha`) is anchored from below counting only
   * the box; without knowing this height, the bar would grow upward and cover
   * the strip's "Expandir" — the same bug as the quota pill (2026-09-19). HomeView
   * passes this to the strip as clearance. The quota warning is NOT included here:
   * it already has its own clearance (`comAvisoDeCota`).
   */
  aoMedirExtras?: (altura: number) => void
  /** The current step of the response (reasoning or the tool in progress), shown
   *  in the footer while the assistant works. `null` when there is no step. */
  etapa?: Etapa | null
  /** Attaches files chosen via "+" (the same path as dragging). */
  aoAnexar?: (arquivos: File[]) => void
  /** Triggers the globe's location control (the "Usar minha localização" of "+"). */
  aoPedirLocalizacao?: () => void
}

export default function Barra({
  enviar, correndo = false, estado, autoFoco = false, variante = "rodape", parar, saindo = false,
  aoMedirExtras, etapa = null, aoAnexar, aoPedirLocalizacao,
}: Props) {
  const idioma = useIdiomaDaTela()
  const t = useTextos().assistente
  const sugestoes = t.barra.sugestoes
  const abrir = useHomeStore((s) => s.abrirPainel)
  // The draft lives in the store, shared with the panel: opening/collapsing (via
  // the button or Ctrl+I) unmounts this box, and in local state whatever was
  // written went with it. This way the text simply continues in the other's box.
  const rascunho = useHomeStore((s) => s.rascunho)
  const definirRascunho = useHomeStore((s) => s.definirRascunho)
  // The files dropped on the Home. In the store for the same reason as the draft:
  // Ctrl+I unmounts this box and the chips would go with it, with the uploads
  // still running and nothing on screen saying so.
  const anexos = useHomeStore((s) => s.anexos)
  const arrastando = useHomeStore((s) => s.arrastandoArquivo)
  const removerAnexo = useHomeStore((s) => s.removerAnexo)
  const limparAnexosProntos = useHomeStore((s) => s.limparAnexosProntos)
  const descartarAnexosRecusados = useHomeStore((s) => s.descartarAnexosRecusados)
  // Only for measuring/clearance of the extras (the chip reads the store on its
  // own). A DERIVED boolean on purpose: the position changes on every tick of
  // follow mode, but the extras' height only changes when the chip enters/leaves
  // — subscribing to the object re-rendered the bar (and re-measured) on every GPS tick.
  const temLocalizacao = useHomeStore((s) => s.compartilharLocalizacao && s.localizacao !== null)
  const campoRef = useRef<HTMLInputElement>(null)
  // The ruler of the extras above the box: its height becomes the strip's
  // clearance. Measured in layout (before paint) on every content change, and
  // observed for the line breaks only a resize causes.
  const extrasRef = useRef<HTMLDivElement>(null)
  const [focado, setFocado] = useState(false)
  // The send flash: turns on when sending, turns off at the end of the `::after`
  // animation (the element's own `animationend` — a child with an infinite
  // animation, like the cursor, never fires it). With reduced motion the animation
  // is `none`, the flag stays on with no visible effect and the next send reuses it.
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    if (autoFoco) campoRef.current?.focus()
  }, [autoFoco])

  // The current step only in the footer: in the hero "Trabalhando…" already
  // takes that space, and the hero ends on send anyway. Declared HERE (before
  // the effects) because the measurement below depends on it: the indicator
  // appearing/disappearing changes the extras' height. A boolean on purpose —
  // `etapa` is a new object per render, and as a dep it would make the
  // measurement run on every frame of the stream; the HEIGHT only changes on
  // appear/disappear (the label truncates, it never wraps).
  const mostrarEtapa = variante !== "hero" && etapa != null

  // Measures the extras on every content change (chips enter/leave, the
  // rejected warning opens/closes, the step appears/disappears). `useEffect`
  // and not `useLayoutEffect` to avoid the SSR warning (the repo's convention);
  // the one-frame delay is imperceptible — the chips don't animate, and what
  // this calculation prevents is the PERSISTENT overlap, not a one-frame one.
  useEffect(() => {
    if (extrasRef.current) aoMedirExtras?.(extrasRef.current.offsetHeight)
  }, [aoMedirExtras, anexos, arrastando, mostrarEtapa, temLocalizacao])

  // Observes resize separately: with many chips the row wraps into more lines
  // when the window narrows, without `anexos` changing. Mounted once (stable
  // deps), it resets the clearance only on the real UNMOUNT — the strip can't
  // stay suspended over a bar that has already left.
  useEffect(() => {
    const el = extrasRef.current
    if (!el || !aoMedirExtras) return
    const ro = new ResizeObserver(() => aoMedirExtras(el.offsetHeight))
    ro.observe(el)
    return () => { ro.disconnect(); aoMedirExtras(0) }
  }, [aoMedirExtras])

  const cota = estado?.cota ?? null
  const estourou = cota != null && cota.gasto >= cota.teto
  const bloqueado = correndo || estourou
  const hero = variante === "hero"

  // The question the attachments suggest, when there is one in the Drive. It takes
  // the place of the typed suggestions: offering "Mostre os focos de calor" to
  // someone who just dropped a shapefile is ignoring what the person did.
  const sugestaoDeAnexo = sugestaoParaAnexos(anexos, idioma)
  const temAnexoPronto = sugestaoDeAnexo !== null
  // There is something above the box (chips, rejected warning, the step, the location) or the invitation.
  const temExtras = anexos.length > 0 || arrastando || mostrarEtapa || temLocalizacao

  // The typed suggestion only exists in the hero, with the field empty and nothing running.
  const sugestaoVisivel = hero && rascunho === "" && !correndo && !estourou && !temAnexoPronto
  const { texto: sugestao, indice } = useSugestaoDigitada(sugestaoVisivel, sugestoes)

  function submeter() {
    const digitado = rascunho.trim()
    // An empty field sends the current suggestion — that's the hint's "Enter
    // envia". With a ready attachment the suggestion is its own, and it applies in
    // BOTH variants: whoever dropped a file has already said what they want, even
    // outside the hero.
    const texto = digitado || sugestaoDeAnexo || (sugestaoVisivel ? (sugestoes[indice] ?? "") : "")
    if (!texto) return
    // With a stream in progress (or the quota exceeded) the hook's `enviar` returns
    // silently: the typed sentence vanished forever without any signal. Here the
    // send simply doesn't happen and the draft stays in view, in the same box,
    // to go when the stream ends.
    if (bloqueado) return
    definirRascunho("")
    // The message carries the list of what was uploaded — without it, "analise
    // isso" reaches the assistant without any "this". Only the READY ones go in,
    // and only they leave the box: what is still uploading wasn't in the message,
    // and the rejected one never had anything to do with it.
    void enviar(comReferencia(texto, anexos, idioma))
    limparAnexosProntos()
    setFlash(true)
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault()
      submeter()
      return
    }
    if (e.key === "Tab" && !e.shiftKey && sugestaoVisivel) {
      // Tab accepts the suggestion instead of leaving the field — that's what the hint promises.
      e.preventDefault()
      definirRascunho(sugestoes[indice] ?? "")
    }
  }

  function escolherChip(chip: string) {
    definirRascunho(chip)
    campoRef.current?.focus()
  }

  const placeholder = correndo
    ? t.barra.respondendo
    : sugestaoDeAnexo ?? t.barra.placeholder

  return (
    <div className="home dark home-barra pb-safe" data-variante={variante} data-saindo={saindo} data-testid="barra">
      {estourou && cota && (
        <AvisoDeCotaCheia
          cota={cota}
          plano={estado?.plano}
          assinaturasAtivas={estado?.assinaturas_ativas}
          className="mb-1.5 justify-center rounded-full px-3 py-1 text-center"
        />
      )}

      {/* Everything that stacks ABOVE the box lives in this ruler, and its height
          is what the strip receives as clearance (aoMedirExtras). The quota
          warning stays OUTSIDE it on purpose — it already has its own clearance.

          `flex flex-col gap` (not `mb` on the children) and `pb` when there is
          content: that way the gap down to the box goes into `offsetHeight`. With
          `mb` on the last child, the margin collapsed OUTSIDE the measured height,
          and the strip rose ~6 px too little — touching "Expandir" again. Empty,
          with no `pb`, it measures zero. */}
      <div ref={extrasRef} className={cn("flex flex-col gap-1.5", temExtras && "pb-1.5")}>
        <AvisoDeAnexosRecusados anexos={anexos} onFechar={descartarAnexosRecusados} />

        {/* Above the box, not inside: it is a 44 px `rounded-full` (56 in the
            hero) and has no room for a row that wraps. */}
        {arrastando && <ConviteDeSoltura className="justify-center" />}
        <ChipsDeAnexo anexos={anexos} onRemover={removerAnexo} className="justify-center" />
        <ChipDeLocalizacao className="justify-center" />
        {/* The current step, while the assistant works. */}
        {mostrarEtapa && etapa && <IndicadorDeEtapa etapa={etapa} className="justify-center px-1" />}
      </div>

      <div
        className="home-barra-caixa flex items-center gap-2 rounded-full border border-border bg-background/95 pl-2.5 pr-1.5 backdrop-blur"
        data-flash={flash}
        // The drag highlight. The area that ACCEPTS the file is the whole window
        // (useArrasteDeArquivos); only the box lights up — no veil covers
        // the globe, which is this option's choice.
        data-arraste={arrastando}
        onAnimationEnd={(e) => { if (e.target === e.currentTarget) setFlash(false) }}
      >
        <span className="home-barra-ico grid shrink-0 place-items-center rounded-full text-primary" aria-hidden="true">
          {correndo ? <ExecActivity size={hero ? 16 : 14} /> : <TbSparkles size={hero ? 17 : 16} />}
        </span>
        {(aoAnexar || aoPedirLocalizacao) && (
          <BotaoMais aoAnexar={aoAnexar} aoLocalizar={aoPedirLocalizacao} className="home-barra-btn rounded-full" />
        )}
        <div className="relative flex h-full min-w-0 flex-1 items-center">
          <input
            ref={campoRef}
            value={rascunho}
            onChange={(e) => definirRascunho(e.target.value)}
            onKeyDown={aoTeclar}
            onFocus={() => setFocado(true)}
            onBlur={() => setFocado(false)}
            maxLength={8000}
            disabled={estourou}
            autoComplete="off"
            placeholder={sugestaoVisivel ? "" : placeholder}
            aria-describedby={sugestaoVisivel ? "home-barra-dica" : undefined}
            className="home-barra-campo w-full min-w-0 bg-transparent text-foreground outline-none placeholder:text-muted-foreground disabled:opacity-60"
            aria-label={t.barra.rotuloDoCampo}
          />
          {sugestaoVisivel && (
            <span
              className="home-barra-sugestao pointer-events-none absolute inset-0 flex items-center overflow-hidden text-ellipsis whitespace-nowrap text-muted-foreground"
              aria-hidden="true"
              data-testid="sugestao"
            >
              {sugestao}
              <span className="home-caret" />
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={abrir}
          className="home-barra-btn shrink-0 rounded-full text-muted-foreground"
          aria-label={t.barra.abrir}
          title={t.barra.abrirTitulo}
        >
          <TbChevronUp size={15} aria-hidden="true" />
        </Button>
        {correndo && parar ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={parar}
            className="home-barra-btn shrink-0 rounded-full"
            aria-label={t.barra.parar}
            title={t.barra.pararTitulo}
          >
            <TbPlayerStopFilled size={14} aria-hidden="true" />
          </Button>
        ) : (
          <Button
            size="icon"
            onClick={submeter}
            disabled={(!rascunho.trim() && !sugestaoVisivel && !temAnexoPronto) || bloqueado}
            // The press: sinks more than every button's `active:scale-[0.98]`.
            className="home-barra-btn shrink-0 rounded-full active:scale-90"
            aria-label={t.barra.enviar}
          >
            <TbArrowUp size={15} aria-hidden="true" />
          </Button>
        )}
      </div>

      {(cota != null || sugestaoVisivel) && (
        // The meta line under the box, on the right — the place of Claude Code's
        // context indicator, which was the owner's reference. The typing hint
        // (visible only with the cursor in the field; outside it, it stays in the
        // DOM for the screen reader, which is who doesn't see the typed sentence)
        // and the quota donut share the same line so they don't fight over the corner.
        <div className="home-barra-meta flex items-center justify-end gap-3 pr-2">
          {sugestaoVisivel && (
            <p
              id="home-barra-dica"
              className={cn("text-[11px] text-muted-foreground/80", !focado && "sr-only")}
            >
              {t.barra.dica}
            </p>
          )}
          {cota != null && <UsoDaCota cota={cota} />}
        </div>
      )}

      {hero && (correndo ? (
        <p role="status" className="home-chips flex items-center justify-center gap-2 text-sm text-muted-foreground">
          {/* The site's thinking mark (the same as the conversation's pending item) and
              the text with a sweeping shimmer — static, the status looked frozen. */}
          <MarcaAnimada size={15} /> <span className="texto-pensando">{t.barra.trabalhando}</span>
          {parar && (
            <button
              type="button"
              onClick={parar}
              className="rounded px-1.5 py-0.5 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
            >
              {t.barra.escParaParar}
            </button>
          )}
        </p>
      ) : (
        <div className="home-chips flex flex-wrap justify-center gap-2" role="group" aria-label={t.barra.rotuloDasSugestoes}>
          {t.barra.chips.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => escolherChip(chip)}
              className="rounded-full border border-white/10 bg-background/60 px-3 py-1.5 text-[12.5px] text-[#cfcfcf] backdrop-blur hover:border-primary/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
            >
              {chip}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}

/**
 * The hero's sentences typed letter by letter (26–56 ms), read for 2.3 s,
 * erased quickly (14 ms) and replaced by the next one, in a cycle. Stopping and
 * resuming (the person typed and erased) continues from where it was. With
 * reduced motion, the whole sentence, static.
 */
function useSugestaoDigitada(ativa: boolean, sugestoes: readonly string[]): { texto: string; indice: number } {
  const [indice, setIndice] = useState(0)
  const [pos, setPos] = useState(0)
  const [apagando, setApagando] = useState(false)
  const reduz = usePrefereMenosMovimento()

  useEffect(() => {
    if (!ativa || reduz) return
    const alvo = sugestoes[indice] ?? ""
    let atraso: number
    let passo: () => void
    if (!apagando) {
      if (pos >= alvo.length) {
        atraso = 2300
        passo = () => setApagando(true)
      } else {
        atraso = 26 + Math.random() * 30
        passo = () => setPos((p) => p + 1)
      }
    } else if (pos === 0) {
      atraso = 420
      passo = () => {
        setApagando(false)
        setIndice((i) => (i + 1) % sugestoes.length)
      }
    } else {
      atraso = 14
      passo = () => setPos((p) => Math.max(0, p - 1))
    }
    const timer = setTimeout(passo, atraso)
    return () => clearTimeout(timer)
  }, [ativa, reduz, indice, pos, apagando, sugestoes])

  const alvo = sugestoes[indice] ?? ""
  const texto = reduz ? alvo : alvo.slice(0, pos)
  return { texto, indice }
}
