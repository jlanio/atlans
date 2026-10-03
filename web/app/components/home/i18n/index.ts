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
import { SHELL_TEXTS } from "./da-casca"
import * as assistente from "./secoes/assistente"
import * as entrada from "./secoes/entrada"
import { useScreenLanguage } from "./tela"

// The shell (comum, casca, listas) comes assembled from ./da-casca — see there for why.
const TEXTS = {
  "pt-BR": { ...SHELL_TEXTS["pt-BR"], assistente: assistente.pt, entrada: entrada.pt },
  en: { ...SHELL_TEXTS.en, assistente: assistente.en, entrada: entrada.en },
  es: { ...SHELL_TEXTS.es, assistente: assistente.es, entrada: entrada.es },
} satisfies Record<Idioma, unknown>

export type Texts = (typeof TEXTS)["pt-BR"]

/** Outside React (a pure function that receives the language). */
export function textosDe(idioma: Idioma): Texts {
  return TEXTS[idioma]
}

/** The texts in the screen's language. A stable object per language — usable as a dependency. */
export function useTexts(): Texts {
  return TEXTS[useScreenLanguage()]
}

export { useScreenLanguage } from "./tela"
