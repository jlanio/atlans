"use client"
import { TbAlertTriangle, TbMap2 } from "react-icons/tb"
import type { AssistantLayer } from "@/app/components/home/assistente/quadros"
import { useTexts } from "../i18n"

/**
 * The inline mention of a layer the conversation put (or tried to put) on the
 * globe. The actual drawing happens on the globe (useCamadas); this is only the
 * acknowledgment in the conversation, with the reason when there is no preview.
 * Pops in on arrival (`home-pop`, globals.css) — on replay they all arrive
 * together, and it is brief.
 */
export default function CartaoCamada({ camada }: { camada: AssistantLayer }) {
  const t = useTexts().assistente.camada
  const nome = camada.nome?.trim() || t.camada

  if (!camada.available) {
    return (
      <div className="home-pop flex items-start gap-2 rounded-md border border-border bg-muted/30 px-2.5 py-2 text-xs text-muted-foreground">
        <TbAlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span className="min-w-0 break-words">
          {nome} — {camada.hint ?? t.semPrevia}
        </span>
      </div>
    )
  }

  return (
    <div className="home-pop flex items-center gap-2 rounded-md border border-border bg-muted/20 px-2.5 py-2 text-xs text-foreground">
      <TbMap2 size={14} className="shrink-0 text-primary" aria-hidden="true" />
      <span className="min-w-0 truncate">{t.noGlobo(nome)}</span>
    </div>
  )
}
