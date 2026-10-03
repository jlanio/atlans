"use client"

import { useState, useEffect, useMemo, useRef } from "react"
import { useSession } from "next-auth/react"
import { GisFlowService, IExecutor, IExecutorMetrics } from "@/service/GisFlowService"
import { useFetchData } from "@/app/hooks/useFetchData"
import { useExecutorLocal } from "@/app/hooks/useExecutorLocal"
import { reconciliarExecutores } from "./reconciliar-executores"
import { type TypeFilter, TYPE_OPTIONS } from "./filtro-de-tipo"
import { typeStyle } from "@/consts/ExecutorTypeStyles"
import { cn } from "@/lib/utils"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/app/components/ui/tooltip"
import { TbRefresh, TbInfoCircle } from "react-icons/tb"
import { formatInteger, plural } from "@/lib/formatos"
import { CreateAgentDialog } from "@/app/components/executores/dialogs"
import { ToggleGroup } from "@/app/components/executores/grupo-de-toggle"
import { RailHeader, ExecutorRow } from "@/app/components/executores/trilho"
import {
  ExecutorsSkeleton,
  ErroDosExecutores,
  VazioDeExecutores,
  SemResultado,
  AvisoDeMetricas,
} from "@/app/components/executores/estados"

// ── Filter by live state ─────────────────────────────────────────────────────

type StatusFilter = "all" | "online" | "offline"

const STATUS_OPTIONS: { valor: StatusFilter; rotulo: string }[] = [
  { valor: "all",     rotulo: "Todos" },
  { valor: "online",  rotulo: "Online" },
  { valor: "offline", rotulo: "Offline" },
]

/**
 * Subtitle with the live counters (contract §1): "10 executores · 6 online
 * · 2 dedicados". Zero disappears — "0 dedicados" does not help — and the
 * correct plural of "executor" is "executores" (the default `+s` would give
 * "executors").
 */
function textoDoSubtitulo({ total, online, dedicados }: { total: number; online: number; dedicados: number }): string {
  if (total === 0) return "Nenhum executor ainda"
  const partes = [plural(total, "executor", "executores")]
  if (online > 0) partes.push(`${formatInteger(online)} online`)
  if (dedicados > 0) partes.push(plural(dedicados, "dedicado"))
  return partes.join(" · ")
}

export default function AgentsPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const currentUserId = session?.user?.id_hash
  const quota = session?.user?.agent_quota ?? 0
  const canCreate = isAdmin || quota > 0

  // Inside the desktop app, marks in the list which executor is THIS machine. In
  // a regular browser it is `null` (see useExecutorLocal / lib/desktop).
  const executorLocal = useExecutorLocal()
  const idExecutorLocal = executorLocal?.vinculado ? executorLocal.executorId : null

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("todos")
  // See the header's <Tooltip>: on a phone there is no hover nor keyboard focus,
  // and without controlling the open state the hint had no way to be read there.
  const [tipOpen, setTipOpen] = useState(false)

  const { data, firstLoad, loading, refreshing, error, refetch, recarregarEmFundo } = useFetchData(
    () => isAdmin ? GisFlowService.getAgents() : GisFlowService.getMyAgents(),
    "Erro ao carregar executores."
  )
  const { data: metricsData, error: metricsError, refetch: refetchMetrics } = useFetchData(
    () => GisFlowService.getExecutorMetrics(),
    "Erro ao carregar métricas."
  )

  // `useMemo` on everything derived: without them, every auto-refresh tick
  // rebuilt the metrics map and the list scans, and the cards' props changed
  // identity for nothing.
  //
  // Content-based reconciliation (see reconciliar-executores.ts): without it,
  // ExecutorRow's React.memo never hit, because every 15s tick brings new
  // objects from the JSON even for executors that did not change at all.
  const previousRef = useRef<IExecutor[]>([])
  const executores: IExecutor[] = useMemo(() => {
    previousRef.current = reconciliarExecutores(previousRef.current, data ?? [])
    return previousRef.current
  }, [data])

  const metricsMap = useMemo(() => {
    const mapa: Record<string, IExecutorMetrics> = {}
    for (const m of metricsData?.executores ?? []) {
      // The "Sem executor" row (dispatch failures) has no host: it belongs to nobody.
      if (!m.agent_host) continue
      const id = m.agent_host.startsWith("executor:") ? m.agent_host.slice("executor:".length) : m.agent_host
      mapa[id] = m
    }
    return mapa
  }, [metricsData])

  // Auto-refresh every 15s to keep the load real-time — only with the tab
  // focused, and with an immediate update on regaining focus (same gate as
  // workspaces/page.tsx). A hidden tab has nobody to read the result. It is a
  // background reload: with the 1st load in error, the card stays on screen
  // during the attempt, instead of leaving and coming back (and being announced
  // again) on every tick.
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === "visible") recarregarEmFundo()
    }, 15_000)
    const onVisibility = () => {
      if (document.visibilityState === "visible") recarregarEmFundo()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(id)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [recarregarEmFundo])

  // Admin: getAgents() returns all; non-admin: getMyAgents() already returns only the accessible ones
  const visibleAgents = executores

  // Executors created by the user themself (used to compute the remaining quota)
  const ownedCount = useMemo(
    () => (currentUserId ? visibleAgents.filter(a => a.created_by === currentUserId).length : 0),
    [visibleAgents, currentUserId],
  )

  // Live counters for the subtitle. "Online" counts only ACTIVE executors that
  // are online — it matches the green LED the user sees in the rail (an online
  // one with revoked/inactive status is not real capacity). "Dedicados" counts
  // the current dedicated ones (active status), not those already revoked/inactive.
  const online = useMemo(() => visibleAgents.filter(a => a.status === "active" && a.online).length, [visibleAgents])
  const dedicados = useMemo(() => visibleAgents.filter(a => a.executor_type === "dedicated" && a.status === "active").length, [visibleAgents])

  const filteredAgents = useMemo(() => visibleAgents.filter(a => {
    if (statusFilter === "online")   return a.online
    if (statusFilter === "offline")  return a.status === "active" && !a.online
    return true
  }), [visibleAgents, statusFilter])

  const agentesVisiveis = useMemo(
    () => typeFilter === "todos" ? filteredAgents : filteredAgents.filter(a => a.executor_type === typeFilter),
    [filteredAgents, typeFilter],
  )

  // In "Todos" (all) the list mixes types, so it gets group headers and the
  // type column. With a type chosen both become redundant.
  const grouped = typeFilter === "todos"
  const grupos = useMemo<{ tipo: IExecutor["executor_type"]; itens: IExecutor[] }[]>(() => {
    if (!grouped) return [{ tipo: typeFilter as IExecutor["executor_type"], itens: agentesVisiveis }]
    // Enumerating a fixed `["default","dedicated"]` hid any other
    // `executor_type` the API might send: it went into the count and
    // passed the empty-list guard, but no group rendered it — the rail
    // ended up with a header and no row. Grouping by the types that
    // EXIST in the response covers that, and `estiloDoTipo` already has the neutral one.
    const ordem = ["default", "dedicated"]
    const presentes = [...new Set(agentesVisiveis.map(a => a.executor_type))]
      .sort((x, y) => {
        const ix = ordem.indexOf(x), iy = ordem.indexOf(y)
        return (ix < 0 ? ordem.length : ix) - (iy < 0 ? ordem.length : iy)
      })
    return presentes.map(t => ({ tipo: t, itens: agentesVisiveis.filter(a => a.executor_type === t) }))
  }, [grouped, typeFilter, agentesVisiveis])

  function limparFiltros() {
    setStatusFilter("all")
    setTypeFilter("todos")
  }

  // Metrics are a SECONDARY source: if they go down, the rail stays complete,
  // just without the history numbers — it becomes an amber notice, not a screen error.
  const metricsFailed = metricsData === null && metricsError != null

  return (
    <PageRoot>
      {/* ── Header (contract §1) ─────────────────────────────────────────────── */}
      {/* `flex-wrap`: without it the title and the action row fight for the same line
          on a phone, and the actions' `shrink-0` squeezed "Executores" down to
          an ellipsis. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold text-foreground">Executores</h1>
            <TooltipProvider delayDuration={100}>
              {/* Controlled, and a click opens it: Radix opens a tooltip on hover and
                  on keyboard focus, and the phone has neither —
                  the instructions for bringing up the executor were unreachable
                  there. Closes on an outside tap, like any Radix layer. */}
              <Tooltip open={tipOpen} onOpenChange={setTipOpen}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="Como executar um executor"
                    onClick={() => setTipOpen(true)}
                    // `p-1 -m-1`: a larger touch target without touching the icon's
                    // alignment with the title.
                    className="mt-0.5 -m-1 rounded-sm p-1 text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
                  >
                    <TbInfoCircle size={17} aria-hidden="true" />
                  </button>
                </TooltipTrigger>
                <TooltipContent
                  side="right"
                  collisionPadding={16}
                  // A fixed `max-w-sm` (384px) is wider than the 360px screen, and
                  // the content leaked under the edge.
                  className="max-w-[min(24rem,calc(100vw-2rem))] space-y-2 border border-border bg-popover p-3 text-popover-foreground shadow-md"
                >
                  <p className="text-xs font-semibold">Executar um executor</p>
                  <p className="text-xs text-muted-foreground">
                    Após criar e configurar o executor, execute a partir da raiz do repositório:
                  </p>
                  <pre className="select-all whitespace-pre-wrap break-all rounded bg-muted px-2 py-1.5 font-mono text-[11px] leading-relaxed text-foreground">
                    {`python -m executor.main`}
                  </pre>
                  <p className="text-[11px] text-muted-foreground">
                    Certifique-se de preencher <code>executor/.env</code> antes de iniciar.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          {/* While there is nothing to count (1st load), the subtitle becomes a skeleton
              — it never writes "— online". */}
          {data !== null ? (
            <p className="text-sm font-medium text-muted-foreground">
              {textoDoSubtitulo({ total: visibleAgents.length, online, dedicados })}
            </p>
          ) : (
            <Skeleton className="mt-1 h-4 w-64" />
          )}
        </div>

        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={refetch}
            disabled={loading}
            aria-label="Atualizar a lista de executores"
            className="gap-1.5 max-md:h-10"
          >
            {/* `loading` covers the 1st load AND reloads (including the 15s
                tick) — it is the only sign the list is being reloaded,
                since the rows no longer fade. */}
            <TbRefresh size={14} className={loading ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
            Atualizar
          </Button>
          {canCreate && (
            <CreateAgentDialog
              onCreated={refetch}
              executores={executores}
              isAdmin={isAdmin}
              quota={quota}
              ownedCount={ownedCount}
            />
          )}
        </div>
      </div>

      {/* Shared-pool notice — guides the end user about the types */}
      {!isAdmin && visibleAgents.length > 0 && (
        <div className="flex items-start gap-2 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          <TbInfoCircle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>
            Executores marcados como <span className="font-medium text-foreground">Padrão</span> fazem parte de um{" "}
            <span className="font-medium text-foreground">pool compartilhado</span> entre todos os usuários.
            Executores <span className="font-medium text-foreground">Dedicados</span> são exclusivos do seu acesso.
          </span>
        </div>
      )}

      {/* Filters — two standard toggle groups (contract §1). They only appear when
          there is a list; in a first-use empty state there is nothing to filter. */}
      {data !== null && visibleAgents.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup
            rotulo="Tipo de executor"
            valor={typeFilter}
            onChange={setTypeFilter}
            opcoes={TYPE_OPTIONS}
          />
          <ToggleGroup
            rotulo="Estado do executor"
            valor={statusFilter}
            onChange={setStatusFilter}
            opcoes={STATUS_OPTIONS}
          />
        </div>
      )}

      {/* ── States (contract §3): loading → error (only with no accepted load) →
             first use → content; within the content, no-result and the
             metrics notice. ───────────────────────────────────────────────── */}
      {firstLoad ? (
        <ExecutorsSkeleton />
      ) : data === null ? (
        <ErroDosExecutores mensagem={error ?? "Erro ao carregar executores."} onTentar={refetch} />
      ) : visibleAgents.length === 0 ? (
        <VazioDeExecutores
          isAdmin={isAdmin}
          acao={canCreate ? (
            <CreateAgentDialog
              onCreated={refetch}
              executores={executores}
              isAdmin={isAdmin}
              quota={quota}
              ownedCount={ownedCount}
            />
          ) : undefined}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {metricsFailed && <AvisoDeMetricas onTentar={refetchMetrics} />}

          {agentesVisiveis.length === 0 ? (
            <SemResultado onLimpar={limparFiltros} />
          ) : (
            // Rail — deliberate variant (dense table). A <section> with the card
            // frame and an h2 (sr-only, since the column header already labels
            // it visually); `aria-busy` during a reload.
            <section
              aria-labelledby="executores-trilho-titulo"
              aria-busy={refreshing}
              className="flex min-w-0 flex-col overflow-hidden rounded-lg border bg-card shadow-xs"
            >
              <h2 id="executores-trilho-titulo" className="sr-only">Executores registrados</h2>
              <RailHeader mostrarTipo={grouped} />
              {grupos.map(grupo => {
                const estilo = typeStyle(grupo.tipo)
                const GroupIcon = estilo.icone
                return (
                  <div key={grupo.tipo}>
                    {grouped && (
                      <div className={cn(
                        "flex items-center gap-1.5 border-b border-border bg-muted/40 px-3 py-1",
                        "font-mono text-[10px] uppercase tracking-wider", estilo.texto,
                      )}>
                        <GroupIcon size={11} aria-hidden="true" />
                        <span>{estilo.grupo}</span>
                        <span className="tabular-nums opacity-60">· {grupo.itens.length}</span>
                      </div>
                    )}
                    {grupo.itens.map(executor => (
                      <ExecutorRow
                        key={executor.id_hash}
                        executor={executor}
                        metrics={metricsMap[executor.id_hash]}
                        onRefresh={refetch}
                        isAdmin={isAdmin}
                        currentUserId={currentUserId}
                        mostrarTipo={grouped}
                        ehEsteComputador={!!idExecutorLocal && idExecutorLocal === executor.id_hash}
                      />
                    ))}
                  </div>
                )
              })}
            </section>
          )}
        </div>
      )}
    </PageRoot>
  )
}
