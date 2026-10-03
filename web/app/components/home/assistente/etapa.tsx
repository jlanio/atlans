"use client"

// web/app/components/home/assistente/etapa.tsx
//
// The CURRENT step of the answer, shown in the footer bar while the assistant
// works.
//
// **Why it exists.** The bar drops to the footer as soon as the person sends —
// before the first text token (see the hero in HomeView). During reasoning and
// tool calls (catalog, WFS), which can take seconds, the bar would say nothing.
// This indicator tells what is happening NOW: "Pensando…", or the label of the
// tool in progress ("Consultando o guia · edges"). The strip (the `Pilha`) shows
// the whole timeline; the bar shows only the current step, right next to where
// the person types.
//
// The labels are the SAME as the panel's (`assistente/rotulos.ts` and `Passo`):
// the raw tool name never reaches the screen.

import MarcaAnimada from "./marca-animada"
import { callDetail, toolLabel } from "@/app/components/home/assistente/rotulos"
import type { AssistantTurn } from "@/app/components/home/assistente/quadros"
import { cn } from "@/lib/utils"
import { DEFAULT_LANGUAGE, type Idioma } from "@/lib/idioma"
import { textosDe } from "../i18n"

export interface Stage {
  tipo: "pensando" | "ferramenta"
  rotulo: string
  detalhe?: string
}

/**
 * The current step, derived from the turns and `correndo`.
 *
 * - Stopped (`!correndo`) or no assistant turn → `null`.
 * - Turn with no block yet, last block is reasoning, or tool already
 *   FINISHED (the model is digesting the result) → "Pensando".
 * - Tool IN PROGRESS → its label, with the call's detail.
 * - Already writing the answer (last block is text/card) → `null`: the text
 *   shows up in the strip, and a "step" there would be noise.
 */
export function etapaDaConversa(
  turnos: AssistantTurn[],
  correndo: boolean,
  idioma: Idioma = DEFAULT_LANGUAGE,
): Stage | null {
  if (!correndo) return null
  let ultimo: AssistantTurn | undefined
  for (let i = turnos.length - 1; i >= 0; i--) {
    if (turnos[i].papel === "assistant") { ultimo = turnos[i]; break }
  }
  if (!ultimo) return null

  const bloco = ultimo.blocos[ultimo.blocos.length - 1]
  if (bloco?.tipo === "ferramenta" && bloco.estado === "correndo") {
    const detalhe = callDetail(bloco.argumentos)
    return { tipo: "ferramenta", rotulo: toolLabel(bloco.nome, idioma), detalhe: detalhe ?? undefined }
  }
  if (!bloco || bloco.tipo === "pensando" || bloco.tipo === "ferramenta") {
    return { tipo: "pensando", rotulo: textosDe(idioma).assistente.etapa.pensando }
  }
  return null
}

/** The step line: the site's animated logo + the label (the "…" sweeps while thinking). */
export function IndicadorDeEtapa({ etapa, className }: { etapa: Stage; className?: string }) {
  return (
    <p
      role="status"
      aria-live="polite"
      data-testid="etapa-da-barra"
      className={cn("flex items-center gap-2 text-[12px] text-muted-foreground", className)}
    >
      <MarcaAnimada size={13} />
      {etapa.tipo === "pensando" ? (
        <span className="texto-pensando">{etapa.rotulo}…</span>
      ) : (
        <span className="min-w-0 truncate">
          {etapa.rotulo}
          {etapa.detalhe ? <span className="text-muted-foreground/70"> · {etapa.detalhe}</span> : null}
        </span>
      )}
    </p>
  )
}
