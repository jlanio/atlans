"use client"
// This installation's map basemaps, from the root layout down to MapLibreMap.
// See web/lib/fundos-do-mapa.ts.
import { createContext, useContext, type ReactNode } from "react"
import { FUNDOS_PADRAO, type FundosDoMapa } from "@/lib/fundos-do-mapa"

const FundosDoMapaContexto = createContext<FundosDoMapa>(FUNDOS_PADRAO)

export function FundosDoMapaProvider({ fundos, children }: { fundos: FundosDoMapa; children: ReactNode }) {
  return <FundosDoMapaContexto.Provider value={fundos}>{children}</FundosDoMapaContexto.Provider>
}

/** The installation's basemaps; outside the provider (tests), only OpenStreetMap streets. */
export function useFundosDoMapa(): FundosDoMapa {
  return useContext(FundosDoMapaContexto)
}
