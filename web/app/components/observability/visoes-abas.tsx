"use client"

import { useRef } from "react"
import { cn } from "@/lib/utils"
import { formatarInteiro } from "@/lib/formatos"
import type { Visao } from "./historico-url"

export interface ContagensDasVisoes {
  execucoes: number | null
  workflows: number | null
  executores: number | null
  confirmacoes: number | null
}

interface Props {
  visao: Visao
  onVisao: (v: Visao) => void
  contagens: ContagensDasVisoes
  /** "Confirmações" é admin-only: `/pending-acks` responde 403 aos demais. */
  isAdmin: boolean
  /** Há confirmação atrasada — a pílula de Confirmações fica vermelha. */
  alerta?: boolean
}

const ABAS: { id: Visao; rotulo: string; soAdmin?: boolean }[] = [
  { id: "execucoes", rotulo: "Execuções" },
  { id: "workflows", rotulo: "Por workflow" },
  { id: "executores", rotulo: "Por executor" },
  { id: "confirmacoes", rotulo: "Confirmações", soAdmin: true },
]

/**
 * Barra de visões da tabela (spec §4.3). Mesma lista, quatro recortes; a
 * contagem em cada pílula diz quantas linhas há do outro lado antes de a
 * pessoa clicar. Segue o padrão ARIA de abas: setas movem o foco e já trocam
 * a visão, Home/End vão às pontas.
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
    // `overflow-y-hidden` junto do `-mb-px`: sem ele o navegador abre uma barra
    // vertical de 1px e, em cascata, uma horizontal (mesmo caso da página antiga).
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
                {formatarInteiro(n)}
                {vermelha && <span className="sr-only"> atrasadas</span>}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
