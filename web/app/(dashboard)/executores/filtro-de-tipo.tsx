"use client"

import type { IconType } from "react-icons"
import { TbServer } from "react-icons/tb"
import { estiloDoTipo } from "@/consts/ExecutorTypeStyles"

export type FiltroDeTipo = "todos" | "default" | "dedicated"

/**
 * Options for the filter by executor TYPE, ready for the contract's standard
 * toggle group (`GrupoDeToggle`). There are three useful states, not two:
 * "Todos" (all) is the page's default behavior (the two sections stacked) and
 * must stay reachable; hence a toggle group and not a `Switch`.
 *
 * The type's label, icon and color come from `estiloDoTipo` (single source), so
 * the filter never diverges from the row's badge or the group header.
 */
export const OPCOES_DE_TIPO: { valor: FiltroDeTipo; rotulo: string; icone: IconType }[] = [
  { valor: "todos",     rotulo: "Todos",                                 icone: TbServer },
  { valor: "default",   rotulo: `${estiloDoTipo("default").nome}s`,      icone: estiloDoTipo("default").icone },
  { valor: "dedicated", rotulo: `${estiloDoTipo("dedicated").nome}s`,    icone: estiloDoTipo("dedicated").icone },
]
