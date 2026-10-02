// Vocabulário visual do TIPO de executor — fonte única de verdade.
//
// Nome, ícone e cor viviam espalhados: o badge tinha `teal-500`/`purple-500`
// crus com escada `dark:`, os cabeçalhos de seção da listagem repetiam os
// mesmos ícones com OUTRAS tonalidades (`teal-600`/`purple-600`) e o rótulo
// aparecia escrito à mão em três lugares. É o mesmo padrão que fez as cores do
// drawer de nós divergirem das do canvas — aqui a divergência já tinha começado
// pelo tom.
//
// Quem precisa da identidade do tipo (badge, aba do filtro, selo da linha,
// cabeçalho de grupo) lê daqui.
import { TbCrown, TbUsers } from "react-icons/tb"
import type { IconType } from "react-icons"
import type { IExecutor } from "@/service/types"

export type ExecutorType = IExecutor["executor_type"]

export interface EstiloDeTipo {
  /** Rótulo no singular — o plural é montado por quem exibe. */
  nome: string
  /** Frase curta para o cabeçalho de grupo. */
  grupo: string
  icone: IconType
  /** Cor do texto e do ícone. */
  texto: string
  /** Fundo tênue, para selo e ladrilho. */
  fundo: string
  /** Borda do selo. */
  borda: string
}

export const TIPOS_DE_EXECUTOR: Record<ExecutorType, EstiloDeTipo> = {
  default: {
    nome:  "Compartilhado",
    grupo: "Pool compartilhado",
    icone: TbUsers,
    texto: "text-teal-700 dark:text-teal-400",
    fundo: "bg-teal-500/15",
    borda: "border-teal-500/30",
  },
  dedicated: {
    nome:  "Dedicado",
    grupo: "Dedicados",
    icone: TbCrown,
    texto: "text-purple-700 dark:text-purple-400",
    fundo: "bg-purple-500/15",
    borda: "border-purple-500/30",
  },
}

const NEUTRO: EstiloDeTipo = {
  nome:  "Executor",
  grupo: "Executores",
  icone: TbUsers,
  texto: "text-muted-foreground",
  fundo: "bg-muted",
  borda: "border-border",
}

/** Estilo do tipo, com recuo para o neutro.
 *
 *  Leitura pela cadeia de protótipo é o que faz `TIPOS[t] ?? NEUTRO` devolver a
 *  função `Object` — que é truthy — para um `executor_type` inesperado vindo da
 *  API, e aí as classes saem `undefined`. */
export function estiloDoTipo(tipo: string): EstiloDeTipo {
  return Object.prototype.hasOwnProperty.call(TIPOS_DE_EXECUTOR, tipo)
    ? TIPOS_DE_EXECUTOR[tipo as ExecutorType]
    : NEUTRO
}
