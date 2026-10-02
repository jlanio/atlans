"use client"

import type { IconType } from "react-icons"
import { TbServer } from "react-icons/tb"
import { estiloDoTipo } from "@/consts/ExecutorTypeStyles"

export type FiltroDeTipo = "todos" | "default" | "dedicated"

/**
 * Opções do filtro por TIPO de executor, prontas para o grupo de toggle padrão
 * do contrato (`GrupoDeToggle`). São três estados úteis, não dois: "Todos" é o
 * comportamento padrão da página (as duas seções empilhadas) e precisa continuar
 * alcançável; por isso um grupo de toggle e não um `Switch`.
 *
 * O rótulo, o ícone e a cor do tipo vêm de `estiloDoTipo` (fonte única), então
 * o filtro nunca diverge do selo da linha nem do cabeçalho de grupo.
 */
export const OPCOES_DE_TIPO: { valor: FiltroDeTipo; rotulo: string; icone: IconType }[] = [
  { valor: "todos",     rotulo: "Todos",                                 icone: TbServer },
  { valor: "default",   rotulo: `${estiloDoTipo("default").nome}s`,      icone: estiloDoTipo("default").icone },
  { valor: "dedicated", rotulo: `${estiloDoTipo("dedicated").nome}s`,    icone: estiloDoTipo("dedicated").icone },
]
