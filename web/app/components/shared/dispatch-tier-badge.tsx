import { Badge } from "@/app/components/ui/badge"
import type { DispatchTier } from "@/service/types"

/**
 * Selo de ONDE a execução de fato rodou, quando isso difere do esperado.
 *
 * `primary` é o caso normal e não ganha selo; runs anteriores à coluna
 * (`null`) também não — não se afirma nada sobre o que não foi registrado.
 * "rodou no pool" só faz sentido para workspace COM executor dedicado: no modo
 * Compartilhado o pool é o único destino, e o selo seria ruído em toda linha.
 */
export function DispatchTierBadge({
  tier, dedicado,
}: {
  tier: DispatchTier | null | undefined
  dedicado: boolean
}) {
  if (tier === "fallback") {
    return (
      <Badge
        variant="outline"
        className="border-amber-500/40 px-1 py-0 text-[9px] leading-tight text-amber-700 dark:text-amber-400"
        title="Rodou num executor de reserva da política, não num principal"
      >
        reserva
      </Badge>
    )
  }
  if (tier === "pool" && dedicado) {
    return (
      <Badge
        variant="outline"
        className="border-teal-500/30 px-1 py-0 text-[9px] leading-tight text-teal-700 dark:text-teal-400"
        title="Rodou no pool compartilhado da plataforma, não num executor dedicado do workspace"
      >
        rodou no pool
      </Badge>
    )
  }
  return null
}
