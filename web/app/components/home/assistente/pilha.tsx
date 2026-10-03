"use client"

// web/app/components/home/assistente/pilha.tsx
//
// The conversation in the CENTER: a STRIP attached to the bar, the globe's
// caption. It shows only the last exchange — the question on one line and, from
// the answer, what remained (the last text clipped to 4 lines, the errors, the
// cards) and what is live (the step in progress) —, to take up little of the
// screen and keep the globe in view. Nothing scrolls or slides: the text just
// swaps, with a fade-in (`.home-pilha` in globals.css). It is the SAME
// conversation as the side panel — the same turns, the same `Conversa` (in
// `compacta`), the same cards (`useExtrasDoAssistente`) — trimmed to the last
// items. Whoever wants to read everything (reasoning, steps, full texts)
// expands to the side, via the button, the bar's chevron or Ctrl+I; the panel
// has its own field and "Recolher" brings the conversation back here. One
// model, two views; nothing is duplicated.

import { TbArrowsMaximize } from "react-icons/tb"

import Conversa from "@/app/components/home/assistente/conversa"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { useHomeStore } from "@/app/stores/homeStore"
import { useExtrasDoAssistente, type Confirmar, type Enviar } from "./extras"
import MarcaAnimada from "./marca-animada"
import { useTextos } from "../i18n"

/** How many turns stay in the center: the last exchange (the question and the answer). */
export const ITENS_AO_CENTRO = 2

interface Props {
  turnos: TurnoDoAssistente[]
  correndo: boolean
  confirmar: Confirmar
  /** Quick replies are sent through here — the same `enviar` as the bar. */
  enviar: Enviar
  /** The panel opened and the strip is leaving: slides to the right and fades out, without clicks. */
  saindo?: boolean
  /** The bar has the quota-exceeded pill above the box: the strip moves up by its
   *  height, otherwise the pill (z-30) paints over this footer (z-25). */
  comAvisoDeCota?: boolean
  /** The height, in px, of what the bar stacks above the box (attachment chips,
   *  invitation, rejected-files notice). Same reason as `comAvisoDeCota`, except
   *  measured instead of fixed, because these grow and wrap. */
  folgaExtras?: number
}

export default function Pilha({
  turnos, correndo, confirmar, enviar, saindo = false, comAvisoDeCota = false, folgaExtras = 0,
}: Props) {
  const abrir = useHomeStore((s) => s.abrirPainel)
  const extras = useExtrasDoAssistente({ confirmar, correndo, enviar })
  const t = useTextos().assistente

  if (turnos.length === 0) return null

  const ultimos = turnos.slice(-ITENS_AO_CENTRO)
  const ocultos = turnos.length - ultimos.length

  return (
    <section
      aria-label={t.pilha.rotulo}
      className="home dark home-pilha flex flex-col gap-1.5"
      style={{ "--folga-extras": `${folgaExtras}px` } as React.CSSProperties}
      data-saindo={saindo}
      data-aviso-de-cota={comAvisoDeCota}
      data-testid="pilha"
    >
      {/* The height ceiling (CSS) is only a safeguard: with the question on one
          line and the answer on 4, the strip fits; the `Conversa` only scrolls
          if the cards exceed it. */}
      <div className="home-pilha-itens flex min-h-0 flex-col">
        <Conversa
          turnos={ultimos}
          correndo={correndo}
          extras={extras}
          nome={t.nome}
          compacta
          indicador={MarcaAnimada}
          cursorAoEscrever
        />
      </div>
      {/* The footer comes AFTER the items, attached to the bar: the counter on the
          left, the exit to the side panel on the right. */}
      <div className="flex min-h-[18px] items-center justify-end gap-3 text-[11.5px] text-muted-foreground">
        {ocultos > 0 && (
          <span className="mr-auto">
            {t.pilha.anteriores(ocultos)}
          </span>
        )}
        <button
          type="button"
          onClick={abrir}
          className="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
          title={t.pilha.expandirTitulo}
        >
          <TbArrowsMaximize size={12} aria-hidden="true" /> {t.pilha.expandir}
        </button>
      </div>
    </section>
  )
}
