"use client"
// The name the screen shows (NOME_NA_TELA), read by the root layout and consulted
// by the sidebar brand and the sign-in screen. See lib/nome-na-tela.ts.

import { createContext, useContext, type ReactNode } from "react"
import { DEFAULT_NAME } from "@/lib/nome-na-tela"

const DisplayNameContext = createContext<string>(DEFAULT_NAME)

export function DisplayNameProvider({ nome, children }: { nome: string; children: ReactNode }) {
  return <DisplayNameContext.Provider value={nome}>{children}</DisplayNameContext.Provider>
}

/** This installation's on-screen name; "Atlans" when it doesn't declare one. */
export function useDisplayName(): string {
  return useContext(DisplayNameContext)
}
