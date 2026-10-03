"use client"
// This installation's map basemaps, from the root layout down to MapLibreMap.
// See web/lib/fundos-do-mapa.ts.
import { createContext, useContext, type ReactNode } from "react"
import { DEFAULT_BASEMAPS, type MapBasemaps } from "@/lib/fundos-do-mapa"

const MapBasemapsContext = createContext<MapBasemaps>(DEFAULT_BASEMAPS)

export function MapBasemapsProvider({ fundos, children }: { fundos: MapBasemaps; children: ReactNode }) {
  return <MapBasemapsContext.Provider value={fundos}>{children}</MapBasemapsContext.Provider>
}

/** The installation's basemaps; outside the provider (tests), only OpenStreetMap streets. */
export function useFundosDoMapa(): MapBasemaps {
  return useContext(MapBasemapsContext)
}
