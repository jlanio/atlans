"use client"
// The name the screen shows (NOME_NA_TELA), read by the root layout and consulted
// by the sidebar brand and the sign-in screen. See lib/nome-na-tela.ts.

import { createContext, useContext, type ReactNode } from "react"
import { NOME_PADRAO } from "@/lib/nome-na-tela"

const NomeNaTelaContexto = createContext<string>(NOME_PADRAO)

export function NomeNaTelaProvider({ nome, children }: { nome: string; children: ReactNode }) {
  return <NomeNaTelaContexto.Provider value={nome}>{children}</NomeNaTelaContexto.Provider>
}

/** This installation's on-screen name; "Atlans" when it doesn't declare one. */
export function useNomeNaTela(): string {
  return useContext(NomeNaTelaContexto)
}
