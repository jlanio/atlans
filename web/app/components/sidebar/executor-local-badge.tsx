// web/app/components/sidebar/executor-local-badge.tsx
//
// "Executor deste computador" (this computer's executor) badge in the sidebar footer.
//
// Only appears inside the desktop app: `useExecutorLocal` returns `null` in a
// regular browser, and then the component renders NOTHING — not even the
// SidebarMenuItem's `<li>`, which this component owns (not the parent), so as not
// to leave an empty list item in the footer outside the desktop. It's the visible
// tip of the read-only bridge (see web/lib/desktop.ts).
'use client'
import { useExecutorLocal } from '@/app/hooks/useExecutorLocal'
import type { EstadoExecutorLocal } from '@/lib/desktop'
import { SidebarMenuItem } from '@/app/components/ui/sidebar'
import { cn } from '@/lib/utils'

// Status dots in the contract's canonical literals (§6): online = green,
// busy = amber; no signal (offline / not linked) uses the neutral token
// `bg-muted-foreground` instead of a raw gray. No emerald/zinc.
const ESTILO: Record<EstadoExecutorLocal, { cor: string; texto: string }> = {
  online:        { cor: 'bg-green-500',          texto: 'Online' },
  ocupado:       { cor: 'bg-amber-500',          texto: 'Ocupado' },
  offline:       { cor: 'bg-muted-foreground',   texto: 'Offline' },
  'sem-vinculo': { cor: 'bg-muted-foreground',   texto: 'Sem vínculo' },
}

export default function ExecutorLocalBadge() {
  const status = useExecutorLocal()
  if (!status) return null

  // Defensive fallback: `estado` arrives over IPC (a boundary with no runtime type)
  // and the type is duplicated between two independently deployed packages — an
  // unexpected value from contract skew must not bring down the sidebar.
  const estilo = ESTILO[status.estado] ?? ESTILO.offline
  const sufixo = status.estado === 'ocupado' && status.capacidade
    ? ` · ${status.emExecucao}/${status.capacidade}`
    : ''

  return (
    <SidebarMenuItem>
      {/* In icon mode (collapsed sidebar) the text disappears and the dot centers,
          like the siblings that use SidebarMenuButton. */}
      <div
        className="flex items-center gap-2 overflow-hidden px-2 py-1.5 text-xs text-muted-foreground group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
        title={`Executor deste computador: ${estilo.texto}${sufixo}`}
      >
        <span className={cn('size-2 shrink-0 rounded-full', estilo.cor)} />
        <span className="truncate group-data-[collapsible=icon]:hidden">
          Executor deste computador ·{' '}
          <span className="font-medium text-foreground/80">{estilo.texto}{sufixo}</span>
        </span>
      </div>
    </SidebarMenuItem>
  )
}
