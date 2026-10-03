// Visual vocabulary of the executor TYPE — single source of truth.
//
// Name, icon and color lived scattered around: the badge had raw
// `teal-500`/`purple-500` with a `dark:` ladder, the listing's section headers
// repeated the same icons in OTHER shades (`teal-600`/`purple-600`) and the
// label was hand-written in three places. It is the same pattern that made the
// node drawer's colors drift from the canvas's — here the drift had already
// started with the shade.
//
// Whoever needs the type's identity (badge, filter tab, row badge, group
// header) reads it from here.
import { TbCrown, TbUsers } from "react-icons/tb"
import type { IconType } from "react-icons"
import type { IExecutor } from "@/service/types"

export type ExecutorType = IExecutor["executor_type"]

export interface TypeStyle {
  /** Singular label — the plural is built by whoever displays it. */
  nome: string
  /** Short phrase for the group header. */
  grupo: string
  icone: IconType
  /** Text and icon color. */
  texto: string
  /** Faint background, for badge and tile. */
  fundo: string
  /** Badge border. */
  borda: string
}

export const EXECUTOR_TYPES: Record<ExecutorType, TypeStyle> = {
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

const NEUTRAL: TypeStyle = {
  nome:  "Executor",
  grupo: "Executores",
  icone: TbUsers,
  texto: "text-muted-foreground",
  fundo: "bg-muted",
  borda: "border-border",
}

/** The type's style, falling back to neutral.
 *
 *  Reading through the prototype chain is what makes `TIPOS[t] ?? NEUTRAL` return
 *  the `Object` function — which is truthy — for an unexpected `executor_type`
 *  coming from the API, and then the classes come out `undefined`. */
export function typeStyle(tipo: string): TypeStyle {
  return Object.prototype.hasOwnProperty.call(EXECUTOR_TYPES, tipo)
    ? EXECUTOR_TYPES[tipo as ExecutorType]
    : NEUTRAL
}
