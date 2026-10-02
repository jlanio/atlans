// web/app/components/home/i18n/index.ts
//
// Os textos da Home em três idiomas. Cada seção mora num arquivo (casca,
// assistente, entrada, listas) com o português como MOLDE: `en` e `es` são
// tipados como `typeof pt`, então uma chave esquecida ou sobrando é erro de
// compilação, não texto faltando em produção. Texto que depende de número
// (plural, "3 anexos") é função na própria seção.
//
// Sem provider de idioma (testes de componente, o portal /share) vale o
// português — ver IdiomaContext.

import type { Idioma } from "@/lib/idioma"
import { TEXTOS_DA_CASCA } from "./da-casca"
import * as assistente from "./secoes/assistente"
import * as entrada from "./secoes/entrada"
import { useIdiomaDaTela } from "./tela"

// A casca (comum, casca, listas) vem montada de ./da-casca — ver lá por quê.
const TEXTOS = {
  "pt-BR": { ...TEXTOS_DA_CASCA["pt-BR"], assistente: assistente.pt, entrada: entrada.pt },
  en: { ...TEXTOS_DA_CASCA.en, assistente: assistente.en, entrada: entrada.en },
  es: { ...TEXTOS_DA_CASCA.es, assistente: assistente.es, entrada: entrada.es },
} satisfies Record<Idioma, unknown>

export type Textos = (typeof TEXTOS)["pt-BR"]

/** Fora do React (uma função pura que recebe o idioma). */
export function textosDe(idioma: Idioma): Textos {
  return TEXTOS[idioma]
}

/** Os textos do idioma da tela. Objeto estável por idioma — serve de dependência. */
export function useTextos(): Textos {
  return TEXTOS[useIdiomaDaTela()]
}

export { useIdiomaDaTela } from "./tela"
