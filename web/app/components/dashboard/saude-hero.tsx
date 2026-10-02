"use client"

import { TbAlertTriangle, TbArrowRight, TbCircleCheck } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { INowBlock } from "@/service/types"
import { ItensAgora } from "../observability/agora-faixa"
import type { EstadoDoEscopo } from "./dashboard-url"
import { type ResumoDaAtencao, type TomDeSaude, veredito } from "./saude"

interface Props {
  now: INowBlock | null | undefined
  tom: TomDeSaude
  /** Contagem por tipo da lista "Precisa de atenção" (via `montarAtencao` no `index`); o veredito cita "N workflows falhando" sem reimplementar `top_failing`. */
  resumo: ResumoDaAtencao
  /** Escopo tem workflows mas nenhuma execução: o calmo vira "nada rodando ainda" (§3.10). */
  semExecucoes: boolean
  escopo: EstadoDoEscopo
  /** Workspace ativo quando escopado; `null` no "todos". O `index` o usa ao rotear. */
  workspaceId: string | null
  /** 1ª carga: sem `now` ainda, a linha vira esqueleto em vez de "sem leitura". */
  carregando: boolean
  onVerEmAndamento: () => void
  onAbrirPresa: (runId: string) => void
}

/**
 * A cor por tom, com as MESMAS classes que `StatusBadge` e `agora-faixa` já
 * usam — nada de hex solto, para os dois temas seguirem coerentes: verde
 * (calmo), âmbar (atenção), vermelho (crítico).
 */
const CORES: Record<TomDeSaude, { friso: string; texto: string }> = {
  calmo: { friso: "bg-green-500", texto: "text-green-700 dark:text-green-400" },
  atencao: { friso: "bg-amber-500", texto: "text-amber-700 dark:text-amber-400" },
  critico: { friso: "bg-red-500", texto: "text-red-700 dark:text-red-400" },
}

/**
 * Faixa de Saúde do topo do Dashboard (docs/specs/dashboard.md §3.4). O que a
 * tela responde primeiro: "está tudo bem agora?".
 *
 * No CALMO, uma linha verde fina (friso de 4px + check + veredito + a mesma
 * linha "agora" do Histórico) — não um cartão grande, que gritaria por atenção
 * que não é preciso dar. Na ATENÇÃO/CRÍTICO, o envelope `rounded-xl` ganha o
 * friso grosso e o brilho difuso do `workspace-hero`, e o veredito vem em duas
 * partes ("Precisa de você:" + os 1–2 motivos mais graves).
 *
 * A linha de itens ("N em andamento · 1 presa há X · Executores N de M") é a
 * `ItensAgora` extraída de `agora-faixa.tsx`: a mesma lógica de "some o que é
 * zero", sem duplicar. "Ver em andamento" e a presa clicável sobem como
 * callbacks — quem roteia (com `&workspace=` quando escopado) é o `index`.
 */
export function SaudeHero({ now, tom, resumo, semExecucoes, carregando, onVerEmAndamento, onAbrirPresa }: Props) {
  const cor = CORES[tom]
  const frase = veredito(now, tom, resumo, semExecucoes)
  const calmo = tom === "calmo"

  // Corpo comum aos dois estados: os itens do instante e o atalho para a
  // tabela filtrada por "em andamento".
  const corpo = (
    <div className="flex flex-1 flex-wrap items-center gap-x-3.5 gap-y-2">
      {now ? (
        <ItensAgora now={now} onAbrirPresa={onAbrirPresa} />
      ) : carregando ? (
        <Skeleton className="h-4 w-56" />
      ) : (
        <span className="text-muted-foreground">Sem leitura do instante.</span>
      )}
      <button
        type="button"
        onClick={onVerEmAndamento}
        aria-label="Ver execuções em andamento"
        className="ml-auto inline-flex items-center gap-1 rounded-sm text-xs font-medium text-primary underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        Ver em andamento <TbArrowRight size={13} aria-hidden="true" />
      </button>
    </div>
  )

  if (calmo) {
    // Linha fina: o friso de 4px à esquerda, o check e o veredito numa frase só.
    return (
      <section
        aria-labelledby="saude-titulo"
        aria-busy={carregando && !now}
        className="relative flex flex-wrap items-center gap-x-3.5 gap-y-2 overflow-hidden rounded-lg border bg-card py-2.5 pr-4 pl-5 text-sm shadow-xs"
      >
        <h2 id="saude-titulo" className="sr-only">Saúde · agora</h2>
        <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1", cor.friso)} />
        <span className={cn("inline-flex items-center gap-2 font-medium", cor.texto)}>
          <TbCircleCheck size={17} className="shrink-0" aria-hidden="true" />
          {frase}
        </span>
        {corpo}
      </section>
    )
  }

  // Atenção/crítico: o envelope grande, com friso grosso e o veredito em duas
  // partes. A cor de identidade entra só como friso — sem o brilho difuso.
  const [prefixo, motivos] = partesDoVeredito(frase)
  return (
    <section
      aria-labelledby="saude-titulo"
      className="relative overflow-hidden rounded-xl border bg-card shadow-xs motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300"
    >
      <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1.5", cor.friso)} />
      <div className="relative flex flex-col gap-2.5 p-4 pl-6 sm:p-5 sm:pl-7">
        <div className="flex items-start gap-2.5">
          <TbAlertTriangle size={20} className={cn("mt-0.5 shrink-0", cor.texto)} aria-hidden="true" />
          <div className="min-w-0">
            <h2 id="saude-titulo" className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
              Saúde · agora
            </h2>
            <p className="text-[15px] leading-snug font-medium text-balance">
              <span className={cor.texto}>{prefixo}</span>
              {motivos && <span className="text-foreground">{motivos}</span>}
            </p>
          </div>
        </div>
        {corpo}
      </div>
    </section>
  )
}

/**
 * Quebra o veredito no primeiro ": " — "Precisa de você:" pinta com a cor do
 * tom, os motivos ficam em texto normal. Sem o separador (frase única), tudo
 * vai no prefixo.
 */
function partesDoVeredito(frase: string): [string, string | null] {
  const i = frase.indexOf(": ")
  if (i === -1) return [frase, null]
  return [frase.slice(0, i + 1), frase.slice(i + 1)]
}
