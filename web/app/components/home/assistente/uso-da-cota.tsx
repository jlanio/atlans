"use client"

// web/app/components/home/assistente/uso-da-cota.tsx
//
// O medidor da cota diária de tokens do assistente: um donut fino com o
// percentual, na linha de meta LOGO ABAIXO do campo — o desenho e o lugar são
// os do indicador de contexto do Claude Code, que foi a referência do dono.
//
// Ele não fala com a rede: lê `estado.cota` (`GET /assistente/estado` /
// `GET /assistente/editor/estado`), que as três superfícies já recebem por prop, sobem
// durante o turno pelo quadro `cota` do stream e releem quando ele fecha.
// Sem `cota` (Redis fora, assistente
// desligado), o componente simplesmente não existe — o mesmo "degrada aberto"
// do backend. O pill de cota estourada continua onde sempre esteve; aqui, no
// mesmo estado, o donut fecha e o rótulo vira a contagem de reabertura.
//
// Faixas: terracota (`--primary`) até 79%, âmbar de 80% em diante — âmbar cru
// do Tailwind porque é o precedente da casa para "aproximando do limite" (o
// pill e o LoadBar dos executores usam o mesmo). O detalhe completo (gasto,
// teto, percentual e prazo) vai no tooltip e no aria-label. O balde ser o mesmo
// da Home e do editor (app/mcp/cotas.py) fica fora do texto: é ruído para quem
// lê um medidor.

import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela } from "../i18n"
import { FORMATOS } from "../i18n/formatos"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/app/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { IAssistenteCota } from "@/service/types"

export type FaixaDaCota = "normal" | "alerta" | "cheia"

/** 0–100, já clampado: `gasto` PODE passar do teto (a checagem do servidor é
 *  uma por conversa), e um donut de 133% seria mentira visual. */
export function percentualDaCota(cota: IAssistenteCota): number {
  if (!cota.teto || cota.teto <= 0) return 0
  return Math.max(0, Math.min(100, Math.round((cota.gasto / cota.teto) * 100)))
}

export function faixaDaCota(cota: IAssistenteCota): FaixaDaCota {
  if (cota.gasto >= cota.teto) return "cheia"
  return percentualDaCota(cota) >= 80 ? "alerta" : "normal"
}

/** O texto do tooltip e do aria-label — exportado para os testes. */
export function detalheDaCota(cota: IAssistenteCota, idioma: Idioma = IDIOMA_PADRAO): string {
  const t = textosDe(idioma).assistente.cota
  const f = FORMATOS[idioma]
  const pct = percentualDaCota(cota)
  const cheia = cota.gasto >= cota.teto
  const prazo = cota.reabre_em_segundos != null
    ? t.janela(cheia, f.duracao(cota.reabre_em_segundos))
    : ""
  return t.detalhe(f.inteiro(cota.gasto), f.inteiro(cota.teto), pct, prazo)
}

const COR_DO_ANEL: Record<FaixaDaCota, string> = {
  normal: "text-primary",
  alerta: "text-amber-400",
  cheia: "text-amber-500",
}

// Donut de 16 px, traço 2.6 — a geometria da referência.
const DIAMETRO = 16
const RAIO = DIAMETRO / 2 - 1.6
const VOLTA = 2 * Math.PI * RAIO

interface Props {
  cota?: IAssistenteCota | null
  /** O editor respeita o tema claro/escuro; a Home é sempre escura e o
   *  conteúdo portalizado do tooltip precisa da paleta dela (`.home-portal`). */
  superficie?: "home" | "editor"
  className?: string
}

export default function UsoDaCota({ cota, superficie = "home", className }: Props) {
  const idioma = useIdiomaDaTela()
  if (!cota || !cota.teto || cota.teto <= 0) return null
  const t = textosDe(idioma).assistente.cota

  const pct = percentualDaCota(cota)
  const faixa = faixaDaCota(cota)
  const cheia = faixa === "cheia"
  const detalhe = detalheDaCota(cota, idioma)
  const rotulo = cheia
    ? cota.reabre_em_segundos != null
      ? t.reabreEmCurto(FORMATOS[idioma].duracao(cota.reabre_em_segundos))
      : t.usada
    : `${pct}%`

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            tabIndex={0}
            data-testid="uso-da-cota"
            data-faixa={faixa}
            aria-label={t.rotulo(detalhe)}
            className={cn(
              "inline-flex cursor-help items-center gap-1.5 rounded-full text-[11px] tabular-nums",
              "text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              className,
            )}
          >
            <svg
              width={DIAMETRO}
              height={DIAMETRO}
              viewBox={`0 0 ${DIAMETRO} ${DIAMETRO}`}
              aria-hidden="true"
              className={cn("shrink-0", COR_DO_ANEL[faixa])}
            >
              <circle
                cx={DIAMETRO / 2} cy={DIAMETRO / 2} r={RAIO}
                fill="none" strokeWidth="2.6" stroke="currentColor"
                className="text-muted-foreground/30"
              />
              <circle
                cx={DIAMETRO / 2} cy={DIAMETRO / 2} r={RAIO}
                fill="none" strokeWidth="2.6" stroke="currentColor" strokeLinecap="round"
                strokeDasharray={VOLTA.toFixed(2)}
                strokeDashoffset={(VOLTA * (1 - pct / 100)).toFixed(2)}
                transform={`rotate(-90 ${DIAMETRO / 2} ${DIAMETRO / 2})`}
              />
            </svg>
            <span
              className={cn(
                cheia && (superficie === "editor"
                  ? "text-amber-700 dark:text-amber-400"
                  : "text-amber-400"),
              )}
            >
              {rotulo}
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className={cn("max-w-60 text-center", superficie === "home" && "home-portal")}>
          {detalhe}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
