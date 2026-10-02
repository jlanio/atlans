import { useEffect } from 'react'

import { useWorkflowCatalogStore } from '@/app/stores/workflowCatalogStore'

// A expiração de pin é medida em horas; 60s de granularidade basta e evita
// acordar a aba a cada 10s. Como os demais pollers da base, pausa com a aba
// oculta e recompõe ao voltar o foco.
const TICK_MS = 60_000

// Mantém o flag `expired` dos pins em dia sem refetch. Necessário porque o
// backend só pré-computa `expired` no GET inicial — sem este timer o ícone de
// pin permanece visível até F5 ou troca de workflow.
export function usePinExpirationTimer() {
  const recompute = useWorkflowCatalogStore(s => s.recomputeExpiredPins)
  useEffect(() => {
    recompute()
    const tick = () => {
      if (typeof document === "undefined" || document.visibilityState === "visible") recompute()
    }
    const id = setInterval(tick, TICK_MS)
    // Voltar o foco pode ter deixado pins vencidos: recompõe na hora, sem esperar o tick.
    document.addEventListener("visibilitychange", tick)
    return () => {
      clearInterval(id)
      document.removeEventListener("visibilitychange", tick)
    }
  }, [recompute])
}
