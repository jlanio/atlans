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
import { useScreenLanguage } from "./tela"

export const SHELL_TEXTS = {
  "pt-BR": { comum: comum.pt, casca: casca.pt, listas: listas.pt },
  en: { comum: comum.en, casca: casca.en, listas: listas.en },
  es: { comum: comum.es, casca: casca.es, listas: listas.es },
} satisfies Record<Idioma, unknown>

export type ShellTexts = (typeof SHELL_TEXTS)["pt-BR"]

/** Outside React (a pure function that receives the language). */
export function shellTextsFor(idioma: Idioma): ShellTexts {
  return SHELL_TEXTS[idioma]
}

/** The shell texts in the screen's language. A stable object per language — usable as a dependency. */
export function useShellTexts(): ShellTexts {
  return SHELL_TEXTS[useScreenLanguage()]
}

export { useFormats, useScreenLanguage } from "./tela"
