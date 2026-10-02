"use client"
// O nome que a tela mostra (NOME_NA_TELA), lido pelo layout raiz e consultado
// pela marca da barra lateral e pela tela de entrada. Ver lib/nome-na-tela.ts.

import { createContext, useContext, type ReactNode } from "react"
import { NOME_PADRAO } from "@/lib/nome-na-tela"

const NomeNaTelaContexto = createContext<string>(NOME_PADRAO)

export function NomeNaTelaProvider({ nome, children }: { nome: string; children: ReactNode }) {
  return <NomeNaTelaContexto.Provider value={nome}>{children}</NomeNaTelaContexto.Provider>
}

/** O nome desta instalação na tela; «Atlans» quando ela não o declara. */
export function useNomeNaTela(): string {
  return useContext(NomeNaTelaContexto)
}
