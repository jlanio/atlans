"use client"

// web/app/components/home/assistente/aviso-de-cota.tsx
//
// The quota-exhausted warning.
//
// **Why a component, and not three copies.** The text lived duplicated on THREE
// surfaces: the Home bar, the Home's floating panel and the assistant drawer in
// the editor. An offer hung on it (an extension's, see `ofertaDaCota` in
// `web/extensoes/tipos.ts`) would exist on one surface and not on another
// depending on the copy. The shell is still each one's own (the bar is a
// capsule, the panel is a block, the drawer is a block in the app theme), the
// content is from here.
//
// **The colors are theme-aware** because of the third one: the Home forces `dark`
// on its shells, but the editor drawer follows the viewer's theme. Fixing the
// dark palette here would paint amber-400 on a light background, which can't be read.
//
// `plano` and `assinaturasAtivas` come from `/estado` and only matter to the
// offer: without an extension, the server sends `null` and `false`, and the
// warning is just the warning.

import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela } from "../i18n"
import { FORMATOS } from "../i18n/formatos"
import { EXTENSOES, LimiteDaExtensao } from "@/extensoes"
import { cn } from "@/lib/utils"
import type { IAssistenteCota } from "@/service/types"

/** "reabre em 6 h 12 min" (reopens in 6 h 12 min), or the vague one when the server doesn't know the deadline.
 *
 *  The exact deadline comes in `reabre_em_segundos` and the donut right below
 *  already uses it — saying "algumas horas" (a few hours) here, with the number
 *  at hand, was the screen knowing more than it told. */
export function quandoReabre(cota: IAssistenteCota, idioma: Idioma = IDIOMA_PADRAO): string {
  const t = textosDe(idioma).assistente.cota
  return cota.reabre_em_segundos != null
    ? t.reabreEm(FORMATOS[idioma].duracao(cota.reabre_em_segundos))
    : t.reabreDepois
}

interface Props {
  cota: IAssistenteCota
  plano: string | null | undefined
  assinaturasAtivas: boolean | undefined
  /** The shell belongs to each surface: capsule in the bar, block in the panel. */
  className?: string
}

export function AvisoDeCotaCheia({ cota, plano, assinaturasAtivas, className }: Props) {
  const idioma = useIdiomaDaTela()
  const t = textosDe(idioma).assistente.cota

  return (
    <p
      role="status"
      data-testid="aviso-de-cota"
      className={cn(
        "flex flex-wrap items-center justify-center gap-x-2.5 gap-y-1 border border-amber-500/30 text-xs",
        "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
        className,
      )}
    >
      <span>
        {t.usou(FORMATOS[idioma].inteiro(cota.teto))} {quandoReabre(cota, idioma)}
      </span>
      {EXTENSOES.map(({ nome, ofertaDaCota: Oferta }) => Oferta && (
        <LimiteDaExtensao key={nome} nome={nome}>
          <Oferta plano={plano} assinaturasAtivas={assinaturasAtivas} />
        </LimiteDaExtensao>
      ))}
    </p>
  )
}
