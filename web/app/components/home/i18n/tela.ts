// web/app/components/home/i18n/tela.ts
//
// O idioma da TELA e os formatadores dele — sem dicionário nenhum. Módulo leve
// de propósito: a casca do app (ver ./da-casca) o importa em toda rota.

import { useIdioma, useNaHome } from "@/context/IdiomaContext"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { FORMATOS, type Formatos } from "./formatos"

/**
 * O idioma da TELA: o da pessoa dentro da Home; português fora dela (os
 * componentes compartilhados com a administração não a traduzem pela metade).
 */
export function useIdiomaDaTela(): Idioma {
  const { idioma } = useIdioma()
  return useNaHome() ? idioma : IDIOMA_PADRAO
}

/** Os formatadores do idioma da tela (números, "há 5 min"…). */
export function useFormatos(): Formatos {
  return FORMATOS[useIdiomaDaTela()]
}
