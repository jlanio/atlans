"use client"
// Os fundos do mapa desta instalação, do layout raiz até o MapLibreMap.
// Ver web/lib/fundos-do-mapa.ts.
import { createContext, useContext, type ReactNode } from "react"
import { FUNDOS_PADRAO, type FundosDoMapa } from "@/lib/fundos-do-mapa"

const FundosDoMapaContexto = createContext<FundosDoMapa>(FUNDOS_PADRAO)

export function FundosDoMapaProvider({ fundos, children }: { fundos: FundosDoMapa; children: ReactNode }) {
  return <FundosDoMapaContexto.Provider value={fundos}>{children}</FundosDoMapaContexto.Provider>
}

/** Os fundos da instalação; fora do provider (testes), só as ruas do OpenStreetMap. */
export function useFundosDoMapa(): FundosDoMapa {
  return useContext(FundosDoMapaContexto)
}
