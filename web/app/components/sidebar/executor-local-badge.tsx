// web/app/components/sidebar/executor-local-badge.tsx
//
// Selo "Executor deste computador" no rodapé da sidebar.
//
// Só aparece dentro do app desktop: `useExecutorLocal` devolve `null` no
// navegador comum, e aí o componente não renderiza NADA — nem o `<li>` do
// SidebarMenuItem, que é dono deste componente (não do pai), para não deixar um
// item de lista vazio no rodapé fora do desktop. É a ponta visível da ponte
// read-only (ver web/lib/desktop.ts).
'use client'
import { useExecutorLocal } from '@/app/hooks/useExecutorLocal'
import type { EstadoExecutorLocal } from '@/lib/desktop'
import { SidebarMenuItem } from '@/app/components/ui/sidebar'
import { cn } from '@/lib/utils'

// Pontos de estado nos literais canônicos do contrato (§6): online = verde,
// ocupado = âmbar; sem sinal (offline / sem vínculo) usa o token neutro
// `bg-muted-foreground` em vez de um cinza cru. Nada de emerald/zinc.
const ESTILO: Record<EstadoExecutorLocal, { cor: string; texto: string }> = {
  online:        { cor: 'bg-green-500',          texto: 'Online' },
  ocupado:       { cor: 'bg-amber-500',          texto: 'Ocupado' },
  offline:       { cor: 'bg-muted-foreground',   texto: 'Offline' },
  'sem-vinculo': { cor: 'bg-muted-foreground',   texto: 'Sem vínculo' },
}

export default function ExecutorLocalBadge() {
  const status = useExecutorLocal()
  if (!status) return null

  // Fallback defensivo: `estado` chega por IPC (fronteira sem tipo em runtime) e
  // o tipo é duplicado entre dois pacotes de deploy independente — um valor
  // inesperado por skew de contrato não pode derrubar a sidebar.
  const estilo = ESTILO[status.estado] ?? ESTILO.offline
  const sufixo = status.estado === 'ocupado' && status.capacidade
    ? ` · ${status.emExecucao}/${status.capacidade}`
    : ''

  return (
    <SidebarMenuItem>
      {/* No modo ícone (sidebar colapsada) o texto some e o ponto centraliza,
          como os irmãos que usam SidebarMenuButton. */}
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
