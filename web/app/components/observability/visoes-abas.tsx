"use client"

import { useRef } from "react"
import { cn } from "@/lib/utils"
import { formatInteger } from "@/lib/formatos"
import type { ViewKind } from "./historico-url"

export interface ViewCounts {
  execucoes: number | null
  workflows: number | null
  executores: number | null
  confirmacoes: number | null
}

interface Props {
  visao: ViewKind
  onVisao: (v: ViewKind) => void
  contagens: ViewCounts
  /** "Confirmações" is admin-only: `/pending-acks` answers 403 to everyone else. */
  isAdmin: boolean
  /** There is a late acknowledgment — the Confirmações pill turns red. */
  alerta?: boolean
}

const ABAS: { id: ViewKind; rotulo: string; soAdmin?: boolean }[] = [
  { id: "execucoes", rotulo: "Execuções" },
  { id: "workflows", rotulo: "Por workflow" },
  { id: "executores", rotulo: "Por executor" },
  { id: "confirmacoes", rotulo: "Confirmações", soAdmin: true },
]

/**
 * The table's view bar (spec §4.3). Same list, four slices; the count on each
 * pill says how many rows are on the other side before the person clicks.
 * Follows the ARIA tabs pattern: arrows move focus and switch the view right
 * away, Home/End go to the ends.
 */
export function VisoesAbas({ visao, onVisao, contagens, isAdmin, alerta = false }: Props) {
  const abas = ABAS.filter(a => !a.soAdmin || isAdmin)
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function aoTeclar(e: React.KeyboardEvent, i: number) {
    let alvo = -1
    if (e.key === "ArrowRight") alvo = (i + 1) % abas.length
    else if (e.key === "ArrowLeft") alvo = (i - 1 + abas.length) % abas.length
    else if (e.key === "Home") alvo = 0
    else if (e.key === "End") alvo = abas.length - 1
    if (alvo < 0) return
    e.preventDefault()
    refs.current[alvo]?.focus()
    onVisao(abas[alvo].id)
  }

  return (
    // `overflow-y-hidden` together with `-mb-px`: without it the browser opens a 1px
    // vertical bar and, in cascade, a horizontal one (same case as the old page).
    <div
      role="tablist"
      aria-label="Visões do histórico"
      className="no-scrollbar flex items-center gap-0.5 overflow-x-auto overflow-y-hidden border-b border-border"
    >
      {abas.map((aba, i) => {
        const ativa = aba.id === visao
        const n = contagens[aba.id]
        const vermelha = aba.id === "confirmacoes" && alerta
        return (
          <button
            key={aba.id}
            ref={el => { refs.current[i] = el }}
            type="button"
            role="tab"
            id={`visao-aba-${aba.id}`}
            aria-selected={ativa}
            aria-controls="visao-painel"
            tabIndex={ativa ? 0 : -1}
            onClick={() => onVisao(aba.id)}
            onKeyDown={e => aoTeclar(e, i)}
            className={cn(
              "-mb-px flex h-10 shrink-0 items-center gap-1.5 border-b-2 px-3.5 text-sm font-medium whitespace-nowrap transition-colors outline-none",
              "focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:rounded-t-md",
              ativa ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {aba.rotulo}
            {n != null && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 font-mono text-[10px] leading-none",
                  vermelha
                    ? "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {formatInteger(n)}
                {vermelha && <span className="sr-only"> atrasadas</span>}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
