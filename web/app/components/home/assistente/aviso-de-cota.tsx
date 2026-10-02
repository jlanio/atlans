"use client"

// web/app/components/home/assistente/aviso-de-cota.tsx
//
// O aviso de cota cheia.
//
// **Por que um componente, e não três cópias.** O texto vivia duplicado em TRÊS
// superfícies: a barra da Home, o painel flutuante da Home e a gaveta do
// assistente no editor. Uma oferta pendurada nele (a de uma extensão, ver
// `ofertaDaCota` em `web/extensoes/tipos.ts`) existiria numa superfície e não
// na outra conforme a cópia. A casca continua de cada uma (a barra é uma
// cápsula, o painel é um bloco, a gaveta é um bloco no tema do app), o conteúdo
// é daqui.
//
// **As cores são cientes de tema** por causa da terceira: a Home força `dark`
// nas suas cascas, mas a gaveta do editor segue o tema de quem olha. Fixar a
// paleta escura aqui pintaria âmbar-400 sobre fundo claro, que não se lê.
//
// `plano` e `assinaturasAtivas` vêm do `/estado` e só interessam à oferta: sem
// extensão, o servidor manda `null` e `false`, e o aviso é só o aviso.

import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela } from "../i18n"
import { FORMATOS } from "../i18n/formatos"
import { EXTENSOES, LimiteDaExtensao } from "@/extensoes"
import { cn } from "@/lib/utils"
import type { IAssistenteCota } from "@/service/types"

/** «reabre em 6 h 12 min», ou o vago quando o servidor não sabe o prazo.
 *
 *  O prazo exato vem em `reabre_em_segundos` e o donut logo abaixo já o usa —
 *  dizer «algumas horas» aqui, com o número na mão, era a tela sabendo mais do
 *  que contava. */
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
  /** A casca é de cada superfície: cápsula na barra, bloco no painel. */
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
