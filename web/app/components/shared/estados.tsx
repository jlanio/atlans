"use client"

import type { ReactNode } from "react"
import type { IconType } from "react-icons"
import { TbAlertTriangle, TbFilterOff } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * Frames for the screen states (contract screen-patterns.md §3): the centered
 * error, empty and no-results card, and the amber partial-failure line.
 * Each screen keeps in its own `estados.tsx` only what is its own — the Skeleton*,
 * which draw the real layout, and the sentences — and builds the states from
 * these pieces.
 *
 * Before, each screen re-copied the frame, and the copies diverged: only three
 * announced the error to the screen reader, one didn't paint the destructive
 * border and three had nowhere to put the server message. Here the announcement
 * (`role="alert"`, §5) comes from the card's tone, not from whoever remembers to
 * add it.
 */

type Tom = "erro" | "neutro"

/**
 * - `compacto` (default): error, no-results and the empty state of a section —
 *   26 px icon, `text-sm` title, the button right below the sentence.
 * - `amplo`: the empty state that takes over the screen (first use, no access) —
 *   36 px icon, `text-base` title, and the primary action (or the steps) below
 *   the text.
 */
type Tamanho = "compacto" | "amplo"

/**
 * The centered card (§3.2 and §3.3). `tom="erro"` paints the destructive
 * frame — border and icon circle — and announces the card (`role="alert"`).
 */
export function CartaoDeEstado({
  icone: Icone, tom = "neutro", tamanho = "compacto", titulo, descricao, acao, children, tituloId, className,
}: {
  icone: IconType
  tom?: Tom
  tamanho?: Tamanho
  titulo: ReactNode
  descricao?: ReactNode
  /** Button(s) under the text. */
  acao?: ReactNode
  /** Content between the text and the action (the first-use steps). */
  children?: ReactNode
  /** The title's `id`, for a region labeled by it (`aria-labelledby`). */
  tituloId?: string
  className?: string
}) {
  const erro = tom === "erro"
  const amplo = tamanho === "amplo"
  return (
    <div
      role={erro ? "alert" : undefined}
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border bg-card px-6 py-14 text-center shadow-xs",
        amplo ? "gap-5" : "gap-3",
        erro && "border-destructive/20",
        className,
      )}
    >
      <div
        className={cn(
          "rounded-full",
          amplo ? "p-5" : "p-3",
          erro ? "border border-destructive/20 bg-destructive/10" : "bg-muted/60",
        )}
      >
        <Icone
          size={amplo ? 36 : 26}
          className={erro ? "text-destructive" : "text-muted-foreground/50"}
          aria-hidden="true"
        />
      </div>
      {amplo ? (
        <>
          <div className="flex max-w-md flex-col gap-1.5">
            <p id={tituloId} className="text-base font-semibold text-foreground">{titulo}</p>
            {descricao && <p className="text-sm text-muted-foreground">{descricao}</p>}
          </div>
          {children}
          {acao}
        </>
      ) : (
        <div className="flex max-w-[360px] flex-col items-center gap-0.5">
          <p id={tituloId} className="text-sm font-medium">{titulo}</p>
          {descricao && <p className="text-xs text-muted-foreground">{descricao}</p>}
          {children}
          {acao && <div className="mt-2 flex flex-wrap items-center justify-center gap-2">{acao}</div>}
        </div>
      )}
    </div>
  )
}

/**
 * The backbone source failed on the 1st load (§3.2): the error card takes the
 * place of the content. It only comes in when there was never an accepted load —
 * a reload that fails over data on screen becomes a toast or `AvisoAmbar`, and
 * that gate belongs to whoever composes the screen. `mensagem` is the server's,
 * when the screen has it.
 */
export function ErroDeCarga({ titulo, mensagem, onTentar, className }: {
  /** "Não foi possível carregar os arquivos" — the sentence belongs to the screen. */
  titulo: string
  mensagem?: string | null
  onTentar?: () => void
  className?: string
}) {
  return (
    <CartaoDeEstado
      tom="erro"
      icone={TbAlertTriangle}
      titulo={titulo}
      descricao={mensagem || undefined}
      acao={onTentar && (
        <Button variant="outline" size="sm" onClick={onTentar} className="max-md:h-10">Tentar de novo</Button>
      )}
      className={className}
    />
  )
}

/**
 * First use (§3.3): there is nothing yet and no active slice. Says what it is
 * and where to start; the primary action (`cta`, or `acao` when it comes ready —
 * a dialog with its own trigger) appears for whoever `podeCriar`, and whoever
 * can't reads whom to ask: `pedirA="criar o primeiro workflow"` becomes "Peça a
 * um editor do workspace para criar o primeiro workflow.".
 */
export function VazioPrimeiroUso({
  icone, titulo, descricao, passos, cta, acao, podeCriar = true, pedirA,
}: {
  icone: IconType
  titulo: ReactNode
  descricao: ReactNode
  /** Numbered steps of the "where to start". */
  passos?: readonly { titulo: string; detalhe: string }[]
  cta?: { rotulo: string; icone?: IconType; onClick: () => void }
  acao?: ReactNode
  podeCriar?: boolean
  pedirA?: string
}) {
  let final: ReactNode = null
  if (podeCriar) {
    const CtaIcon = cta?.icone
    final = acao ?? (cta && (
      <Button onClick={cta.onClick} className="max-md:h-10">
        {CtaIcon && <CtaIcon size={15} aria-hidden="true" />} {cta.rotulo}
      </Button>
    ))
  } else if (pedirA) {
    final = <p className="text-sm text-muted-foreground">{`Peça a um editor do workspace para ${pedirA}.`}</p>
  }
  return (
    <CartaoDeEstado icone={icone} tamanho="amplo" titulo={titulo} descricao={descricao} acao={final}>
      {passos && passos.length > 0 && (
        <ol className="grid w-full max-w-lg gap-2 text-left sm:grid-cols-3">
          {passos.map((passo, i) => (
            <li key={passo.titulo} className="flex gap-2.5 rounded-md border bg-background/60 px-3 py-2.5">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                {i + 1}
              </span>
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-sm font-medium">{passo.titulo}</span>
                <span className="text-xs text-muted-foreground">{passo.detalhe}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </CartaoDeEstado>
  )
}

/**
 * The no-results sentence: "Nenhum arquivo com «bacia» e este filtro" /
 * "…com «bacia»" / "…com este filtro". `sufixoFiltro` replaces "este filtro"
 * when the slice has a name ("em GEOJSON"); `semRecorte` is what to say with
 * neither term nor filter (by default, `nada` itself).
 */
export function textoDeSemResultado({ nada, termo, comFiltro, sufixoFiltro, semRecorte }: {
  /** "Nenhum arquivo", "Nenhuma credencial"… */
  nada: string
  termo: string
  comFiltro: boolean
  sufixoFiltro?: string
  semRecorte?: string
}): string {
  const t = termo.trim()
  if (t && comFiltro) return `${nada} com «${t}» ${sufixoFiltro ?? "e este filtro"}`
  if (t) return `${nada} com «${t}»`
  if (comFiltro) return `${nada} ${sufixoFiltro ?? "com este filtro"}`
  return semRecorte ?? nada
}

/**
 * Active slice with no rows at all (§3.3): the `TbFilterOff` icon sets it apart
 * from a true empty state, and the obvious way out — clearing the slice — comes
 * in the button.
 */
export function SemResultado({ texto, dica, onLimpar }: {
  texto: string
  dica?: ReactNode
  onLimpar?: () => void
}) {
  return (
    <CartaoDeEstado
      icone={TbFilterOff}
      titulo={texto}
      descricao={dica}
      acao={onLimpar && (
        <Button variant="outline" size="sm" onClick={onLimpar} className="max-md:h-10">Limpar filtros</Button>
      )}
    />
  )
}

/**
 * Partial failure of a section (§3.4): the source for that block failed, but the
 * rest stays on screen — a discreet amber line (`role="status"`, not alert) with
 * the "Tentar de novo" (try again) inline. `rotuloDoBotao` exists for the Home,
 * which speaks three languages; without it the button is the usual
 * "Tentar de novo".
 */
export function AvisoAmbar({ children, onTentar, rotuloDoBotao = "Tentar de novo" }: {
  children: ReactNode
  onTentar: () => void
  rotuloDoBotao?: string
}) {
  return (
    <p
      role="status"
      className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-amber-500/30 bg-amber-50 px-3 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
    >
      <TbAlertTriangle size={14} className="shrink-0" aria-hidden="true" />
      <span>{children}</span>
      <button
        type="button"
        onClick={onTentar}
        className="inline-flex items-center rounded-sm font-medium underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        {rotuloDoBotao}
      </button>
    </p>
  )
}
