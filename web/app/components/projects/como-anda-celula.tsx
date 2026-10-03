"use client"

import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import { formatarDuracaoGrossa, plural } from "@/lib/formatos"
import { JANELA_EM_DIAS, type ComoAnda } from "./como-anda"

/**
 * The row's "como anda" (how it is going) column (docs/specs/projects.md §3.5).
 * The file is not called `como-anda.tsx` on purpose: next to `como-anda.ts`,
 * the same `import "./como-anda"` would resolve to the `.ts` for tsc and Vite
 * and to the `.tsx` for Next's webpack, which prefers `.tsx` — and the page
 * would break only in the build.
 *
 * Two lines: the first with the status and the when, the second with the
 * context that changes a decision — how many ran and how many failed in the
 * window, or the whole error when the last one failed. The colors are those of
 * `StatusBadge`, so whoever reads History recognizes the same green/red/blue here.
 */

interface Props {
  comoAnda: ComoAnda
  className?: string
}

/** "61 execuções em 30 d · 3 falhas · mediana 3 min" — "nenhuma falha" at zero; the median disappears when there is none. */
export function textoDaContagem(c: { total: number; falhas: number; mediana: number | null }): string {
  const partes = [
    `${plural(c.total, "execução", "execuções")} em ${JANELA_EM_DIAS} d`,
    c.falhas === 0 ? "nenhuma falha" : plural(c.falhas, "falha"),
  ]
  if (c.mediana != null) partes.push(`mediana ${formatarDuracaoGrossa(c.mediana)}`)
  return partes.join(" · ")
}

/** "agendado · em geo-01 · costuma levar 7 min" — only what is known of the live run; null when nothing is known. */
export function textoDaExecucao(c: { origem: string | null; executor: string | null; tipica: number | null }): string | null {
  const partes = [
    c.origem,
    c.executor ? `em ${c.executor}` : null,
    c.tipica != null ? `costuma levar ${formatarDuracaoGrossa(c.tipica)}` : null,
  ].filter((p): p is string => !!p)
  return partes.length > 0 ? partes.join(" · ") : null
}

type Leitura = {
  marcador: ReactNode
  tom: string
  primeira: string
  segunda: string | null
  /** The second line in red (error) instead of gray. */
  segundaEmAlerta: boolean
}

function ler(c: ComoAnda): Leitura {
  switch (c.tipo) {
    case "executando":
      return {
        marcador: <PontoVivo />,
        tom: "text-blue-700 dark:text-blue-400",
        primeira: c.desde ? `Em execução ${c.desde}` : "Em execução",
        segunda: textoDaExecucao(c),
        segundaEmAlerta: false,
      }
    case "concluida":
      return {
        marcador: <Ponto className="bg-green-500" />,
        tom: "text-green-700 dark:text-green-400",
        primeira: `Concluída ${c.quando}`,
        segunda: textoDaContagem(c),
        segundaEmAlerta: false,
      }
    case "falhou":
      // With no error text (the backend recorded the failure without a message), the
      // count still says something; an empty space would say nothing.
      return {
        marcador: <Ponto className="bg-red-500" />,
        tom: "text-red-600 dark:text-red-400",
        primeira: `Falhou ${c.quando}`,
        segunda: c.erro ?? textoDaContagem(c),
        segundaEmAlerta: c.erro != null,
      }
    case "cancelada":
      return {
        marcador: <Ponto className="bg-muted-foreground/50" />,
        tom: "text-muted-foreground",
        primeira: `Cancelada ${c.quando}`,
        segunda: textoDaContagem(c),
        segundaEmAlerta: false,
      }
    case "sem-execucoes":
      return {
        marcador: <PontoVazio />,
        tom: "text-muted-foreground",
        primeira: `Sem execuções em ${JANELA_EM_DIAS} dias`,
        segunda: null,
        segundaEmAlerta: false,
      }
    case "nunca":
      return {
        marcador: <PontoVazio />,
        tom: "text-muted-foreground",
        primeira: "Ainda não executou",
        segunda: "execute uma vez para validar",
        segundaEmAlerta: false,
      }
    case "indisponivel":
      return {
        marcador: <Traco />,
        tom: "text-muted-foreground",
        primeira: "Sem dados de execução",
        segunda: null,
        segundaEmAlerta: false,
      }
  }
}

export function ComoAndaCelula({ comoAnda, className }: Props) {
  const l = ler(comoAnda)
  return (
    <div className={cn("flex min-w-0 flex-col gap-0.5", className)} data-como-anda={comoAnda.tipo}>
      <span className={cn("inline-flex min-w-0 items-center gap-1.5 text-[13px] font-medium leading-tight", l.tom)}>
        {l.marcador}
        <span className="truncate">{l.primeira}</span>
      </span>
      {l.segunda && (
        <span
          className={cn("truncate text-xs", l.segundaEmAlerta ? "text-red-600 dark:text-red-400" : "text-muted-foreground")}
          // The whole error stays in the `title`: the column is 260px and the message
          // is usually longer than that.
          title={l.segundaEmAlerta ? l.segunda : undefined}
        >
          {l.segunda}
        </span>
      )}
    </div>
  )
}

function Ponto({ className }: { className: string }) {
  return <span aria-hidden="true" className={cn("inline-block size-2 shrink-0 rounded-full", className)} />
}

/** Blue with the same ping as the in-progress `StatusBadge` — under `motion-safe`. */
function PontoVivo() {
  return (
    <span aria-hidden="true" className="relative flex size-2 shrink-0">
      <span className="absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-60 motion-safe:animate-ping" />
      <span className="relative inline-flex size-2 rounded-full bg-blue-500" />
    </span>
  )
}

/** Hollow dot: "there is no run" is different from "ended in gray". */
function PontoVazio() {
  return <span aria-hidden="true" className="inline-block size-2 shrink-0 rounded-full border border-muted-foreground/60" />
}

function Traco() {
  return <span aria-hidden="true" className="inline-block h-px w-2 shrink-0 bg-muted-foreground/60" />
}
