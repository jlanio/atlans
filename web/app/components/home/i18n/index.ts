// web/app/components/home/i18n/index.ts
//
// The Home's texts in three languages. Each section lives in a file (casca,
// assistente, entrada, listas) with Portuguese as the TEMPLATE: `en` and `es`
// are typed as `typeof pt`, so a forgotten or extra key is a compile error, not
// missing text in production. Text that depends on a number (plural,
// "3 anexos") is a function in the section itself.
//
// Without a language provider (component tests, the /share portal) Portuguese
// applies — see IdiomaContext.

import type { Idioma } from "@/lib/idioma"
import { TEXTOS_DA_CASCA } from "./da-casca"
import * as assistente from "./secoes/assistente"
import * as entrada from "./secoes/entrada"
import { useIdiomaDaTela } from "./tela"

// The shell (comum, casca, listas) comes assembled from ./da-casca — see there for why.
const TEXTOS = {
  "pt-BR": { ...TEXTOS_DA_CASCA["pt-BR"], assistente: assistente.pt, entrada: entrada.pt },
  en: { ...TEXTOS_DA_CASCA.en, assistente: assistente.en, entrada: entrada.en },
  es: { ...TEXTOS_DA_CASCA.es, assistente: assistente.es, entrada: entrada.es },
} satisfies Record<Idioma, unknown>

export type Textos = (typeof TEXTOS)["pt-BR"]

/** Outside React (a pure function that receives the language). */
export function textosDe(idioma: Idioma): Textos {
  return TEXTOS[idioma]
}

/** The texts in the screen's language. A stable object per language — usable as a dependency. */
export function useTextos(): Textos {
  return TEXTOS[useIdiomaDaTela()]
}

export { useIdiomaDaTela } from "./tela"
