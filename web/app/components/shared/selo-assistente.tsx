import { TbSparkles } from "react-icons/tb"

import { cn } from "@/lib/utils"

/**
 * "criado pelo assistente" (created by the assistant) badge — the same in every
 * list of the panel.
 *
 * The workflows the Home assistant creates are complete workflows like the
 * others: they show up in Projects, the Dashboard, History, the palette and the
 * selectors. The badge is what says where they came from, so they aren't
 * confused with what the person built in the editor — without it they "went
 * unnoticed".
 *
 * Same sparkle as the Home's Schedules (the template), in `primary`; shape and
 * size of the sub-workflow badge, so the two can coexist on the same row.
 *
 * `compacto` leaves only the icon, for places where the text doesn't fit (rows
 * of a dense table, a palette item). The `title`/`aria-label` remain: the
 * information can't depend on recognizing the drawing.
 */
export function SeloAssistente({
  origem, compacto = false, className,
}: {
  origem: string | null | undefined
  compacto?: boolean
  className?: string
}) {
  if (origem !== "assistente") return null

  const rotulo = "Fluxo criado pelo assistente"

  if (compacto) {
    return (
      <TbSparkles
        size={12}
        className={cn("shrink-0 text-primary", className)}
        title={rotulo}
        aria-label={rotulo}
      />
    )
  }

  return (
    <span
      title={rotulo}
      aria-label={rotulo}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded bg-primary/10 px-1.5 py-px text-[10px] font-medium text-primary",
        className,
      )}
    >
      <TbSparkles size={11} aria-hidden="true" /> assistente
    </span>
  )
}
