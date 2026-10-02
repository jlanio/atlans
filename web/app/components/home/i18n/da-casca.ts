// web/app/components/home/i18n/da-casca.ts
//
// Os textos da CASCA do app — barra lateral, cabeçalho, conta e Preferências,
// as listas do "Meus" — e só eles. A casca mora no layout do dashboard, que
// toda rota carrega (a administração inclusive); importar dali o ./index
// levava junto os dicionários do assistente e da entrada, nos três idiomas,
// para telas que nunca os mostram. O que é da casca importa DAQUI; o
// ./index soma o resto para a Home (o teste do layout confere que o grafo dele
// não alcança o ./index).

import type { Idioma } from "@/lib/idioma"
import * as casca from "./secoes/casca"
import * as comum from "./secoes/comum"
import * as listas from "./secoes/listas"
import { useIdiomaDaTela } from "./tela"

export const TEXTOS_DA_CASCA = {
  "pt-BR": { comum: comum.pt, casca: casca.pt, listas: listas.pt },
  en: { comum: comum.en, casca: casca.en, listas: listas.en },
  es: { comum: comum.es, casca: casca.es, listas: listas.es },
} satisfies Record<Idioma, unknown>

export type TextosDaCasca = (typeof TEXTOS_DA_CASCA)["pt-BR"]

/** Fora do React (uma função pura que recebe o idioma). */
export function textosDaCascaDe(idioma: Idioma): TextosDaCasca {
  return TEXTOS_DA_CASCA[idioma]
}

/** Os textos da casca no idioma da tela. Objeto estável por idioma — serve de dependência. */
export function useTextosDaCasca(): TextosDaCasca {
  return TEXTOS_DA_CASCA[useIdiomaDaTela()]
}

export { useFormatos, useIdiomaDaTela } from "./tela"
