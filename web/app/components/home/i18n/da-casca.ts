// web/app/components/home/i18n/da-casca.ts
//
// The texts of the app SHELL — sidebar, header, account and Preferências, the
// "Meus" lists — and only those. The shell lives in the dashboard layout, which
// every route loads (administration included); importing ./index from there
// dragged along the assistant and sign-in dictionaries, in all three languages,
// into screens that never show them. What belongs to the shell imports from
// HERE; ./index adds the rest for the Home (the layout test checks that its
// graph does not reach ./index).

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

/** Outside React (a pure function that receives the language). */
export function textosDaCascaDe(idioma: Idioma): TextosDaCasca {
  return TEXTOS_DA_CASCA[idioma]
}

/** The shell texts in the screen's language. A stable object per language — usable as a dependency. */
export function useTextosDaCasca(): TextosDaCasca {
  return TEXTOS_DA_CASCA[useIdiomaDaTela()]
}

export { useFormatos, useIdiomaDaTela } from "./tela"
