"use client"

// web/app/components/home/assistente/passo.tsx
//
// One tool line in the conversation.
//
// The step is deliberately discreet: what matters is the EXPLANATION around
// it. But it cannot disappear — seeing "Consultando o guia · edges" is what
// turns an eight-second pause into visible work, and it is what lets you say
// afterwards "it checked the node before using it".

import { TbAlertTriangle, TbCheck, TbLoader2 } from "react-icons/tb"

import { cn } from "@/lib/utils"
import type { BlocoDoAssistente } from "@/app/components/home/assistente/quadros"
import { detalheDaChamada, rotuloDaFerramenta } from "@/app/components/home/assistente/rotulos"
import { useIdiomaDaTela } from "../i18n"

type BlocoDeFerramenta = Extract<BlocoDoAssistente, { tipo: "ferramenta" }>

export default function Passo({ bloco }: { bloco: BlocoDeFerramenta }) {
  const idioma = useIdiomaDaTela()
  const detalhe = detalheDaChamada(bloco.argumentos)
  const { progresso } = bloco

  return (
    <li
      className="flex items-start gap-2 py-1 text-xs"
      data-estado={bloco.estado}
      data-ferramenta={bloco.nome}
    >
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        {bloco.estado === "correndo" && (
          <TbLoader2 size={14} className="text-muted-foreground motion-safe:animate-spin" />
        )}
        {bloco.estado === "ok" && <TbCheck size={14} className="text-green-600 dark:text-green-400" />}
        {bloco.estado === "erro" && (
          <TbAlertTriangle size={14} className="text-destructive" />
        )}
      </span>

      <span className="min-w-0 flex-1">
        <span className={cn("font-medium", bloco.estado === "erro" ? "text-destructive" : "text-foreground")}>
          {rotuloDaFerramenta(bloco.nome, idioma)}
        </span>
        {detalhe && <span className="text-muted-foreground"> · {detalhe}</span>}

        {progresso && (
          <span className="mt-1 flex items-center gap-2">
            {progresso.total != null && progresso.total > 0 && (
              <span className="h-1 w-16 shrink-0 overflow-hidden rounded-full bg-muted">
                <span
                  className="block h-full rounded-full bg-primary transition-[width] duration-300"
                  style={{ width: `${Math.min(100, (progresso.concluidos / progresso.total) * 100)}%` }}
                />
              </span>
            )}
            <span className="min-w-0 truncate text-[11px] tabular-nums text-muted-foreground">
              {/* `total` may be null: the node reports progress without a total when
                  the branch detour makes the denominator a lie. */}
              {progresso.total != null
                ? `${progresso.concluidos}/${progresso.total}`
                : `${progresso.concluidos}`}
              {progresso.mensagem ? ` · ${progresso.mensagem}` : ""}
            </span>
          </span>
        )}
      </span>
    </li>
  )
}
