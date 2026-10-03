import { Badge } from "@/app/components/ui/badge"
import type { DispatchTier } from "@/service/types"

/**
 * Badge for WHERE the run actually ran, when that differs from what was expected.
 *
 * `primary` is the normal case and gets no badge; runs predating the column
 * (`null`) don't either — nothing is asserted about what wasn't recorded.
 * "rodou no pool" (ran on the pool) only makes sense for a workspace WITH a
 * dedicated executor: in Shared mode the pool is the only destination, and the
 * badge would be noise on every row.
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
