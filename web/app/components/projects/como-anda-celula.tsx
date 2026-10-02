"use client"

import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import { formatarDuracaoGrossa, plural } from "@/lib/formatos"
import { JANELA_EM_DIAS, type ComoAnda } from "./como-anda"

/**
 * Coluna "como anda" da linha (docs/specs/projects.md §3.5). O arquivo não se
 * chama `como-anda.tsx` de propósito: ao lado de `como-anda.ts`, o mesmo
 * `import "./como-anda"` cairia no `.ts` para o tsc e o Vite e no `.tsx` para
 * o webpack do Next, que prefere `.tsx` — e a página quebraria só no build.
 *
 * Duas linhas: a primeira com o status e o quando, a segunda com o contexto
 * que muda uma decisão — quantas rodaram e quantas falharam na janela, ou o
 * erro inteiro quando a última falhou. As cores são as do `StatusBadge`, para
 * quem lê o Histórico reconhecer o mesmo verde/vermelho/azul aqui.
 */

interface Props {
  comoAnda: ComoAnda
  className?: string
}

/** "61 execuções em 30 d · 3 falhas · mediana 3 min" — "nenhuma falha" no zero; a mediana some quando não há. */
export function textoDaContagem(c: { total: number; falhas: number; mediana: number | null }): string {
  const partes = [
    `${plural(c.total, "execução", "execuções")} em ${JANELA_EM_DIAS} d`,
    c.falhas === 0 ? "nenhuma falha" : plural(c.falhas, "falha"),
  ]
  if (c.mediana != null) partes.push(`mediana ${formatarDuracaoGrossa(c.mediana)}`)
  return partes.join(" · ")
}

/** "agendado · em geo-01 · costuma levar 7 min" — só o que se sabe do run vivo; nulo quando não se sabe nada. */
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
  /** A segunda linha em vermelho (erro) em vez de cinza. */
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
      // Sem texto de erro (o backend registrou a falha sem mensagem), a
      // contagem ainda diz algo; um espaço vazio não diria nada.
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
          // O erro inteiro fica no `title`: a coluna tem 260px e a mensagem
          // costuma ter mais que isso.
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

/** Azul com o mesmo ping do `StatusBadge` em andamento — sob `motion-safe`. */
function PontoVivo() {
  return (
    <span aria-hidden="true" className="relative flex size-2 shrink-0">
      <span className="absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-60 motion-safe:animate-ping" />
      <span className="relative inline-flex size-2 rounded-full bg-blue-500" />
    </span>
  )
}

/** Ponto vazado: "não há execução" é diferente de "acabou em cinza". */
function PontoVazio() {
  return <span aria-hidden="true" className="inline-block size-2 shrink-0 rounded-full border border-muted-foreground/60" />
}

function Traco() {
  return <span aria-hidden="true" className="inline-block h-px w-2 shrink-0 bg-muted-foreground/60" />
}
