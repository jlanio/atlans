import { useEffect } from 'react'

import { useWorkflowCatalogStore } from '@/app/stores/workflowCatalogStore'

// Pin expiration is measured in hours; 60s granularity is enough and avoids
// waking the tab every 10s. Like the other pollers in the codebase, it pauses
// while the tab is hidden and recomputes when focus returns.
const TICK_MS = 60_000

// Keeps the pins' `expired` flag up to date without a refetch. Needed because
// the backend only precomputes `expired` on the initial GET — without this timer
// the pin icon stays visible until F5 or a workflow switch.
export function usePinExpirationTimer() {
  const recompute = useWorkflowCatalogStore(s => s.recomputeExpiredPins)
  useEffect(() => {
    recompute()
    const tick = () => {
      if (typeof document === "undefined" || document.visibilityState === "visible") recompute()
    }
    const id = setInterval(tick, TICK_MS)
    // Focus returning may have left expired pins: recompute right away, without waiting for the tick.
    document.addEventListener("visibilitychange", tick)
    return () => {
      clearInterval(id)
      document.removeEventListener("visibilitychange", tick)
    }
  }, [recompute])
}
