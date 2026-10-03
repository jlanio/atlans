"use client"

// The standardized shell of each section of the Settings page (contract §2).

// ── Section shell (contract §2) ──────────────────────────────────────────────

/**
 * Standardized section shell: `<section aria-labelledby>` with the contract's
 * frame (border + `bg-card` + `shadow-xs`), a `px-4 pt-4 pb-1` header with the
 * `<h2>` and the supporting line, and the body in `px-4 pb-4`. Replaces
 * `SettingCard` (shadcn's Card + CardHeader + Separator), which brought a shadow
 * and separator that are not part of the pattern. `aria-busy` marks the section
 * while its source loads.
 */
export function SettingsSection({
  id, titulo, apoio, carregando, children,
}: {
  id: string
  titulo: string
  apoio: string
  carregando?: boolean
  children: React.ReactNode
}) {
  return (
    <section
      aria-labelledby={`${id}-titulo`}
      aria-busy={carregando || undefined}
      className="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs"
    >
      <div className="px-4 pt-4 pb-1">
        <h2 id={`${id}-titulo`} className="text-sm font-semibold">{titulo}</h2>
        <p className="text-xs text-muted-foreground">{apoio}</p>
      </div>
      <div className="px-4 pb-4">{children}</div>
    </section>
  )
}
