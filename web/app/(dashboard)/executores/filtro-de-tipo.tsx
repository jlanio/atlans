"use client"

import type { IconType } from "react-icons"
import { TbServer } from "react-icons/tb"
import { typeStyle } from "@/consts/ExecutorTypeStyles"

export type TypeFilter = "todos" | "default" | "dedicated"

/**
 * Options for the filter by executor TYPE, ready for the contract's standard
 * toggle group (`ToggleGroup`). There are three useful states, not two:
 * "Todos" (all) is the page's default behavior (the two sections stacked) and
 * must stay reachable; hence a toggle group and not a `Switch`.
 *
 * The type's label, icon and color come from `typeStyle` (single source), so
 * the filter never diverges from the row's badge or the group header.
 */
export const TYPE_OPTIONS: { valor: TypeFilter; rotulo: string; icone: IconType }[] = [
  { valor: "todos",     rotulo: "Todos",                                 icone: TbServer },
  { valor: "default",   rotulo: `${typeStyle("default").nome}s`,      icone: typeStyle("default").icone },
  { valor: "dedicated", rotulo: `${typeStyle("dedicated").nome}s`,    icone: typeStyle("dedicated").icone },
]
