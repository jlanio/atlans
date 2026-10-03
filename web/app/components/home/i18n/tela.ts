// web/app/components/home/i18n/tela.ts
//
// The SCREEN language and its formatters — no dictionary at all. A deliberately
// light module: the app shell (see ./da-casca) imports it on every route.

import { useLanguage, useNaHome } from "@/context/IdiomaContext"
import { DEFAULT_LANGUAGE, type Idioma } from "@/lib/idioma"
import { FORMATOS, type Formatos } from "./formatos"

/**
 * The SCREEN language: the person's inside the Home; Portuguese outside it (the
 * components shared with administration do not get it half-translated).
 */
export function useScreenLanguage(): Idioma {
  const { idioma } = useLanguage()
  return useNaHome() ? idioma : DEFAULT_LANGUAGE
}

/** The screen language's formatters (numbers, "há 5 min"…). */
export function useFormats(): Formatos {
  return FORMATOS[useScreenLanguage()]
}
