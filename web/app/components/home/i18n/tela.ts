// web/app/components/home/i18n/tela.ts
//
// The SCREEN language and its formatters — no dictionary at all. A deliberately
// light module: the app shell (see ./da-casca) imports it on every route.

import { useIdioma, useNaHome } from "@/context/IdiomaContext"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { FORMATOS, type Formatos } from "./formatos"

/**
 * The SCREEN language: the person's inside the Home; Portuguese outside it (the
 * components shared with administration do not get it half-translated).
 */
export function useIdiomaDaTela(): Idioma {
  const { idioma } = useIdioma()
  return useNaHome() ? idioma : IDIOMA_PADRAO
}

/** The screen language's formatters (numbers, "há 5 min"…). */
export function useFormatos(): Formatos {
  return FORMATOS[useIdiomaDaTela()]
}
