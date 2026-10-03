"use client"

// Side navigation of the admin Settings, the section catalog and the header's
// freshness stamp.

import { useEffect, useState } from "react"
import { Badge } from "@/app/components/ui/badge"
import { TbArchive, TbCategory, TbCpu, TbDatabase, TbDatabaseImport, TbLayoutDashboard, TbServer, TbShield } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { textoDeFrescor } from "@/app/components/observability/cabecalho"

// ── Navigation and overview ───────────────────────────────────────────────────

export type SectionId = "overview" | "seguranca" | "armazenamento" | "drive" | "nodes" | "assistente" | "execucao" | "lixeira"

export const SECTIONS: { id: SectionId; label: string; icon: React.ElementType }[] = [
  { id: "overview",      label: "Visão geral",   icon: TbLayoutDashboard },
  { id: "seguranca",     label: "Segurança",     icon: TbShield },
  { id: "armazenamento", label: "Armazenamento", icon: TbDatabase },
  { id: "drive",         label: "Drive",         icon: TbDatabaseImport },
  { id: "nodes",         label: "Nodes",         icon: TbCategory },
  { id: "assistente",    label: "Assistente",    icon: TbCpu },
  { id: "execucao",      label: "Execução",      icon: TbServer },
  // TbArchive, not TbTrash: the latter is already the storage purge button
  // just above, and they are different actions (bytes vs. record).
  { id: "lixeira",       label: "Lixeira",       icon: TbArchive },
]

export function SettingsNav({
  active, onSelect, alertsBySection,
}: {
  active: SectionId
  onSelect: (s: SectionId) => void
  alertsBySection: Partial<Record<SectionId, number>>
}) {
  return (
    <nav
      aria-label="Seções de configuração"
      // Scrolls horizontally on mobile and becomes a fixed column from lg up.
      className="flex gap-1 overflow-x-auto pb-1 lg:sticky lg:top-4 lg:w-52 lg:shrink-0 lg:flex-col lg:overflow-visible lg:pb-0"
    >
      {SECTIONS.map(s => {
        const Icon = s.icon
        const count = alertsBySection[s.id] ?? 0
        const isActive = active === s.id
        return (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10 lg:w-full",
              isActive
                ? "bg-accent font-medium text-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            <Icon size={16} className="shrink-0" aria-hidden="true" />
            <span className="flex-1 text-left whitespace-nowrap">{s.label}</span>
            {count > 0 && (
              <Badge variant="secondary" className="h-4 min-w-4 justify-center px-1 text-[11px] tabular-nums">
                {count}
              </Badge>
            )}
          </button>
        )
      })}
    </nav>
  )
}

/** "atualizado há 20 s" (updated 20 s ago) with its own clock: only this span re-renders. */
export function Frescor({ carimbo }: { carimbo: number }) {
  const [agora, setNow] = useState(() => Date.now())
  useEffect(() => {
    setNow(Date.now())
    const t = setInterval(() => setNow(Date.now()), 5_000)
    return () => clearInterval(t)
  }, [carimbo])
  return (
    <span className="text-xs tabular-nums text-muted-foreground" data-testid="frescor">
      {textoDeFrescor(carimbo, agora)}
    </span>
  )
}
