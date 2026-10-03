// desktop/src/renderer/lib/snapshot.ts
//
// The executor snapshot arrives via CONTEXT, not via prop.
//
// It is replaced by a new object every second. As a prop, it forced GeoSync
// and Ajustes — which stay MOUNTED behind `hidden` so unsaved edits are not
// lost — to re-render their whole tree at 1 Hz: ten cards, three radiogroups
// and the QuadroDoModo redrawn to update four numbers that live in a corner of
// the screen. The app burned CPU just by being open and idle.
//
// Through the context, the `memo` of both screens holds back the tick and only
// what actually reads the snapshot re-renders: GeoSync's Situação, Ajustes'
// Disco and the save bar.
import { createContext, useContext } from 'react'
import type { Snapshot } from '../../shared/events.js'

export const ContextoSnapshot = createContext<Snapshot | null>(null)

/** Latest executor snapshot, or `null` when it is stopped. */
export function useSnapshot(): Snapshot | null {
  return useContext(ContextoSnapshot)
}
