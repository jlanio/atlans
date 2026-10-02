"use client"
import { TbAlertTriangle, TbMap2 } from "react-icons/tb"
import type { CamadaDoAssistente } from "@/app/components/home/assistente/quadros"
import { useTextos } from "../i18n"

/**
 * A menção inline de uma camada que a conversa pôs (ou tentou pôr) no globo. O
 * desenho de verdade é no globo (useCamadas); aqui é só o reconhecimento na
 * conversa, com o motivo quando não há prévia. Pipoca ao chegar (`home-pop`,
 * globals.css) — no replay todos chegam juntos, e é breve.
 */
export default function CartaoCamada({ camada }: { camada: CamadaDoAssistente }) {
  const t = useTextos().assistente.camada
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
