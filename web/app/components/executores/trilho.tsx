"use client"

// The "rail" — dense table of executors, kept as a DELIBERATE VARIANT of the
// contract (it serves vertical comparison between machines; it doesn't become
// a list of cards). Here live the column grid, the header, the row
// (ExecutorRow) and the gauges it opens. The standardization was about
// presentation: status tokens (green instead of emerald), `tabular-nums` on
// numbers, visible focus, ≥40px touch targets on phones and formatting via
// `lib/formatos`.

import React, { useCallback, useEffect, useMemo, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IExecutor, IExecutorMetrics } from "@/service/GisFlowService"
import type { IExecutorUserAssignment } from "@/service/types"
import { estiloDoTipo } from "@/consts/ExecutorTypeStyles"
import { cn } from "@/lib/utils"
import { fromBackend } from "@/lib/dayjs"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { createToast } from "@/utils/createToast"
import {
  TbCopy, TbCheck, TbDots, TbServer,
  TbTag, TbLayoutGrid, TbClock,
  TbStar, TbUsers, TbUserMinus, TbUserPlus, TbSearch,
  TbCpu, TbDeviceDesktop, TbDatabase, TbChevronDown, TbChevronRight,
  TbShieldLock,
} from "react-icons/tb"
import { formatarPercentual, formatarDuracao, formatarQuando, plural } from "@/lib/formatos"
import { successRateColor } from "@/utils/formatters"
import { EnrollmentOtpDialog } from "./enroll"
import { EditAgentDialog, RevokeAgentDialog, DeleteAgentDialog } from "./dialogs"

// ── Helpers ────────────────────────────────────────────────────────────────────

// pt-BR label for the EXECUTOR status. Distinct from `rotuloDoStatus` (shared),
// which translates RUN statuses (success/failed/running…): the vocabularies
// don't overlap — an executor's "pending" is "aguardando enrollment", not "na
// fila" — so the executor's translation lives here, in its own domain.
const ROTULO_STATUS_EXECUTOR: Record<IExecutor["status"], string> = {
  active:   "Ativo",
  pending:  "Pendente",
  inactive: "Inativo",
  revoked:  "Revogado",
}

/** Uptime in seconds, to format in long form via `formatarDuracao`. */
function uptimeEmSegundos(connectedAt: string | null): number | null {
  if (!connectedAt) return null
  const start = fromBackend(connectedAt)?.valueOf()
  if (!start) return null
  return Math.max(0, Math.floor((Date.now() - start) / 1000))
}

// ── Rail grid ─────────────────────────────────────────────────────────────────
// The grid is declared ONCE and used by the header and by each row. That is
// what the stacked card lacked: the hardware strip was `flex-wrap`, so RAM
// and disk landed on a different x per executor and nothing was comparable
// vertically.
//
// Once, but in THREE widths. The fixed columns added up to 360px (492px with
// the type one) and didn't fit even on a tablet with the sidebar open — let
// alone on a phone, where the body's `overflow-x: clip` CUTS what overflows
// instead of scrolling: each row's action menu ended up off screen, with no
// way to reach it.
//
//   < md   phone — two lines per executor, no columns (see ExecutorRow)
//   md     lean rail — type and version go away; the name is what tells rows apart
//   lg     full rail
const TRILHO_COLUNAS = cn(
  "grid-cols-[1.25rem_minmax(0,1fr)_auto]",
  "md:grid-cols-[1.25rem_minmax(0,1fr)_6rem_5rem_2rem]",
  "lg:grid-cols-[1.25rem_minmax(0,1fr)_6rem_4.5rem_5rem_2rem]",
)
/** Type column — only in the full rail. In the `md` band the group header already
 *  names the type, and repeating it per row cost 120px the name was missing. */
const TRILHO_COLUNAS_TIPO = "lg:grid-cols-[1.25rem_minmax(0,1fr)_7.5rem_6rem_4.5rem_5rem_2rem]"

/** Column header of the rail. */
export function CabecalhoDoTrilho({ mostrarTipo }: { mostrarTipo: boolean }) {
  return (
    // `hidden md:grid`: on phones the row has no columns, and a column header
    // over a stack would label what doesn't exist.
    // font-mono here is intentional — uppercase column labels give the rail its
    // "terminal" tone; they are not numbers (see contract §5 on tabular-nums).
    <div className={cn("hidden md:grid gap-3", TRILHO_COLUNAS, mostrarTipo && TRILHO_COLUNAS_TIPO,
      "items-center px-3 py-1.5 bg-muted/50 border-b border-border",
      "font-mono text-[10px] uppercase tracking-wider text-muted-foreground select-none")}>
      <span />
      <span className="flex items-center gap-1"><TbServer size={11} className="opacity-75" aria-hidden="true" />executor</span>
      {mostrarTipo && <span className="hidden lg:flex items-center gap-1"><TbTag size={11} className="opacity-75" aria-hidden="true" />tipo</span>}
      <span className="flex items-center gap-1"><TbLayoutGrid size={11} className="opacity-75" aria-hidden="true" />slots</span>
      <span className="hidden lg:flex items-center justify-end gap-1"><TbTag size={11} className="opacity-75" aria-hidden="true" />versão</span>
      <span className="flex items-center justify-end gap-1"><TbClock size={11} className="opacity-75" aria-hidden="true" />atividade</span>
      <span />
    </div>
  )
}

/** Status LED — a single signal.
 *
 *  The card stated the status four times: colored strip on the border, icon
 *  color, text badge and the sentence "Conectado há…". And the four could
 *  disagree — `status: "active"` with `online: false` gave an amber strip, a
 *  gray icon and a green "Ativo" badge at the same time. */
export function EstadoDoExecutor({ status, online, className }: {
  status: IExecutor["status"]; online: boolean; className?: string
}) {
  const { classe, titulo } =
    status === "revoked"  ? { classe: "bg-destructive/70",                        titulo: "Revogado" } :
    status === "pending"  ? { classe: "ring-1 ring-inset ring-muted-foreground",  titulo: "Aguardando enrollment" } :
    status === "inactive" ? { classe: "ring-1 ring-inset ring-muted-foreground",  titulo: "Inativo" } :
    online                ? { classe: "bg-green-500 shadow-[0_0_0_3px] shadow-green-500/20", titulo: "Ativo e conectado" } :
                            { classe: "ring-[1.5px] ring-inset ring-amber-500",   titulo: "Ativo, sem contato" }
  return (
    <span className={cn("flex justify-center", className)} title={titulo}>
      <span aria-label={titulo} role="img" className={cn("block size-2 rounded-full", classe)} />
    </span>
  )
}

/** Occupancy in cells, one per slot.
 *
 *  `running` and `max_concurrent` are DISCRETE counts. `LoadBar` drew a
 *  continuous bar, and there 4/4 and 4/4-with-six-queued became the same full
 *  bar. The queue cells sit BEYOND the limit, showing the excess. */
export function MedidorDeSlots({ running, queued, maxConcurrent, online }: {
  running: number; queued: number; maxConcurrent: number; online: boolean
}) {
  if (!online) return <span className="hidden md:inline text-[11px] tabular-nums text-muted-foreground">—</span>

  // Cell ceiling: `max_concurrent` is configurable and a machine with 64 slots
  // would stretch the column. Above that the number is enough.
  // Low ceiling on purpose: the column has a fixed width, and vertical
  // alignment is the rail's reason to exist. With 8 slots + 3 queued the
  // cells went past 110px in a 96px band and spilled into "versão",
  // breaking precisely what the grid was meant to guarantee. The number
  // beside it stays exact.
  const TETO = 5
  const vagas = Math.max(0, Math.min(maxConcurrent, TETO))
  const naFila = Math.min(queued, 2)

  return (
    <span className="flex items-center gap-[2px] min-w-0 overflow-hidden" title={`${running} de ${maxConcurrent} em execução${queued > 0 ? `, ${queued} na fila` : ""}`}>
      {Array.from({ length: vagas }).map((_, i) => (
        <span key={i} className={cn("block w-[5px] h-3 rounded-[2px]",
          i < running ? "bg-blue-500" : "bg-muted-foreground/25")} />
      ))}
      {Array.from({ length: naFila }).map((_, i) => (
        <span key={`f${i}`} className="block w-[5px] h-3 rounded-[2px] ring-[1.5px] ring-inset ring-blue-500/55" />
      ))}
      <span className="ml-1 text-[10px] tabular-nums text-muted-foreground">
        {running}/{maxConcurrent}{queued > 0 && ` +${queued}`}
      </span>
    </span>
  )
}

// ── Load bar (in the drawer) ──────────────────────────────────────────────────

export function LoadBar({ running, queued, maxConcurrent, maxQueue }: {
  running: number
  queued: number
  maxConcurrent: number
  maxQueue: number
}) {
  const usedPct  = Math.min((running / maxConcurrent) * 100, 100)
  const queuePct = Math.min((queued / Math.max(maxQueue, 1)) * 100, 100)

  return (
    <div className="flex flex-col gap-1 min-w-[120px]">
      {/* Execution */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground w-14 shrink-0">Rodando</span>
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500 motion-safe:transition-all"
            style={{ width: `${usedPct}%` }}
          />
        </div>
        <span className="text-[10px] tabular-nums text-muted-foreground w-10 text-right shrink-0">
          {running}/{maxConcurrent}
        </span>
      </div>
      {/* Fila */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground w-14 shrink-0">Na fila</span>
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={cn("h-full rounded-full motion-safe:transition-all", queued > 0 ? "bg-amber-500" : "bg-muted-foreground/20")}
            style={{ width: `${queuePct}%` }}
          />
        </div>
        <span className="text-[10px] tabular-nums text-muted-foreground w-10 text-right shrink-0">
          {queued}/{maxQueue}
        </span>
      </div>
    </div>
  )
}

// ── Historical metrics block ─────────────────────────────────────────────────

export function ExecutorHistoricMetrics({ metrics }: { metrics: IExecutorMetrics }) {
  return (
    <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
      <span>
        <span className="font-medium tabular-nums text-foreground">{metrics.total_runs}</span> execuções
      </span>
      <span>
        {/* Percentage in pt-BR: "96,4%" with a comma (formatarPercentual), not
            "96.4%" with a period. The color follows the unified successRate rule. */}
        <span className={cn("font-medium tabular-nums", successRateColor(metrics.success_rate, "amber"))}>
          {formatarPercentual(metrics.success_rate)}
        </span> sucesso
      </span>
      {metrics.avg_duration_seconds != null && (
        <span>
          <span className="font-medium tabular-nums text-foreground">{formatarDuracao(metrics.avg_duration_seconds)}</span> média
        </span>
      )}
      {metrics.last_run_at && (
        <span className="tabular-nums">última {formatarQuando(metrics.last_run_at)}</span>
      )}
    </div>
  )
}

// ── Section of users assigned to the executor ────────────────────────────────

// The section sits behind a disclosure because it used to be mounted on EVERY
// dedicated executor card: opening /executores as admin fired one
// GET /executores/{id}/users per card, dozens of parallel requests
// competing for the browser's 6 connections just to fill a block almost
// no one opens. Now the fetch only happens when the admin actually expands it.
export function AgentUsersSection({ agentId }: { agentId: string }) {
  const [aberto, setAberto]       = useState(false)
  const [users, setUsers]         = useState<IExecutorUserAssignment[]>([])
  const [loading, setLoading]     = useState(false)
  const [email, setEmail]         = useState("")
  const [searching, setSearching] = useState(false)
  const [results, setResults]     = useState<{ id_hash: string; username: string; email: string }[]>([])
  const [assigning, setAssigning] = useState(false)
  const [removingId, setRemovingId] = useState<string | null>(null)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    const res = await GisFlowService.getAgentUsers(agentId)
    if (res.data) setUsers(res.data)
    setLoading(false)
  }, [agentId])

  useEffect(() => { if (aberto) loadUsers() }, [aberto, loadUsers])

  async function handleSearch() {
    if (email.length < 3) return
    setSearching(true)
    setResults([])
    const res = await GisFlowService.searchUsersByEmail(email)
    if (res.data) setResults(res.data)
    setSearching(false)
  }

  async function handleAssign(userId: string, username: string) {
    setAssigning(true)
    const res = await GisFlowService.assignAgentToUser(agentId, userId)
    setAssigning(false)
    if (res.error) {
      createToast.error("Erro ao atribuir executor.")
    } else {
      createToast.success(`Executor atribuído a ${username}.`)
      setEmail("")
      setResults([])
      loadUsers()
    }
  }

  async function handleRemove(userId: string, username: string) {
    setRemovingId(userId)
    const res = await GisFlowService.removeAgentUser(agentId, userId)
    setRemovingId(null)
    if (res.error) {
      createToast.error("Erro ao remover atribuição.")
    } else {
      createToast.success(`Atribuição de ${username} removida.`)
      loadUsers()
    }
  }

  // Memoized: without this the Set was rebuilt on every render — including on
  // every keystroke in the email search. Only changes when the assigned list changes.
  const assignedIds = useMemo(() => new Set(users.map(u => u.user_id)), [users])

  return (
    <div className="border-t border-border pt-3 mt-1 flex flex-col gap-3">
      <button
        type="button"
        onClick={() => setAberto(v => !v)}
        aria-expanded={aberto}
        className="flex items-center gap-1.5 self-start rounded-sm text-xs font-medium text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        {aberto ? <TbChevronDown size={13} aria-hidden="true" /> : <TbChevronRight size={13} aria-hidden="true" />}
        <TbUsers size={13} aria-hidden="true" />
        <span>Usuários atribuídos</span>
        {aberto && !loading && <span className="tabular-nums text-foreground">({users.length})</span>}
      </button>

      {!aberto ? null : loading ? (
        <div className="text-xs italic text-muted-foreground">Carregando…</div>
      ) : users.length === 0 ? (
        <div className="text-xs italic text-muted-foreground">Nenhum usuário atribuído.</div>
      ) : (
        <ul className="flex flex-col gap-1">
          {users.map(u => (
            <li key={u.user_id} className="flex items-center justify-between gap-2 text-xs">
              <div className="min-w-0 truncate">
                <span className="font-medium text-foreground">{u.username}</span>
                <span className="ml-1.5 text-muted-foreground">{u.email}</span>
              </div>
              <button
                type="button"
                onClick={() => handleRemove(u.user_id, u.username)}
                disabled={removingId === u.user_id}
                aria-label={`Remover atribuição de ${u.username}`}
                title="Remover atribuição"
                className="shrink-0 rounded p-1 text-muted-foreground outline-none transition-colors hover:text-destructive focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10 max-md:min-w-10"
              >
                <TbUserMinus size={14} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Search and assignment */}
      {aberto && (
        <div className="flex gap-2">
          <Input
            placeholder="Buscar usuário por e-mail…"
            value={email}
            onChange={e => { setEmail(e.target.value); setResults([]) }}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            className="h-8 text-xs max-md:h-10"
          />
          <Button size="sm" variant="outline" onClick={handleSearch} disabled={searching || email.length < 3} className="h-8 shrink-0 px-2 max-md:h-10 max-md:w-10" aria-label="Buscar usuário">
            <TbSearch size={14} aria-hidden="true" />
          </Button>
        </div>
      )}

      {aberto && results.length > 0 && (
        <ul className="flex flex-col gap-1 overflow-hidden rounded-md border border-border">
          {results.map(r => (
            <li key={r.id_hash} className="flex items-center justify-between gap-2 px-3 py-1.5 text-xs hover:bg-muted/50">
              <div className="min-w-0 truncate">
                <span className="font-medium text-foreground">{r.username}</span>
                <span className="ml-1.5 text-muted-foreground">{r.email}</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleAssign(r.id_hash, r.username)}
                disabled={assigning || assignedIds.has(r.id_hash)}
                className="h-6 shrink-0 px-2 text-xs max-md:h-10"
              >
                {assignedIds.has(r.id_hash) ? (
                  <><TbCheck size={12} className="mr-1 text-green-500" aria-hidden="true" /> Atribuído</>
                ) : (
                  <><TbUserPlus size={12} className="mr-1" aria-hidden="true" /> Atribuir</>
                )}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Executor row ──────────────────────────────────────────────────────────────

// React.memo: the 15s auto-refresh brings new objects from the JSON, but only a
// few executors actually change. Without the memo (and with `onRefresh` already
// stabilized by useFetchData), the whole list was recreated on every cycle.
// Reconciliation by content (see reconciliar-executores.ts) is what makes the
// memo's shallow comparison actually save work.
export const ExecutorRow = React.memo(function ExecutorRow({ executor, metrics, onRefresh, isAdmin, currentUserId, mostrarTipo, ehEsteComputador }: {
  executor: IExecutor
  metrics: IExecutorMetrics | undefined
  onRefresh: () => void
  isAdmin: boolean
  currentUserId?: string
  /** The type badge only informs when the list mixes types — under a category
   *  filter it would be the same word on every row. */
  mostrarTipo: boolean
  /** This executor is the machine where the desktop app is running (desktop only). */
  ehEsteComputador?: boolean
}) {
  // Detail closed by default: hardware, history and users were what made
  // each executor take ~200px of height, and they are precisely what isn't
  // compared between machines — out of the scan, back on demand.
  const [aberto, setAberto] = useState(false)
  const estiloTipo = estiloDoTipo(executor.executor_type)
  const IconeTipo = estiloTipo.icone
  const isOnline = executor.online
  const cap = executor.capacity
  const uptimeSecs = uptimeEmSegundos(executor.connected_at)
  // Owner = created the executor (created_by). Can generate an OTP and revoke/remove their own executor,
  // but has no admin-only actions (edit, default pool).
  const isOwner = !isAdmin && !!currentUserId && executor.created_by === currentUserId
  const canManage = isAdmin || isOwner

  async function handleSetDefault() {
    const res = await GisFlowService.setDefaultAgent(executor.id_hash)
    if (res.error) {
      createToast.error("Erro ao adicionar ao pool padrão.")
    } else {
      createToast.success("Executor adicionado ao pool padrão.")
      onRefresh()
    }
  }

  async function handleUnsetDefault() {
    const res = await GisFlowService.unsetDefaultAgent(executor.id_hash)
    if (res.error) {
      createToast.error("Erro ao remover do pool padrão.")
    } else {
      createToast.success("Executor removido do pool padrão.")
      onRefresh()
    }
  }

  return (
    <div className="border-b border-border/60 last:border-b-0">
      {/* Compact row — the grid is the SAME as the column header's (see
          CabecalhoDoTrilho), and that is what makes every executor's memory
          land on the same x. */}
      <div
        onClick={() => setAberto(v => !v)}
        className={cn("grid gap-x-3 gap-y-1.5 md:gap-3", TRILHO_COLUNAS, mostrarTipo && TRILHO_COLUNAS_TIPO,
          "items-center px-3 py-2 min-h-[2.75rem] cursor-pointer transition-colors hover:bg-accent/50")}
      >
        {/* Status — a single LED, instead of strip + icon + badge saying the
            same thing. On phones the three cells of the first line are positioned
            by hand — status, name and actions — and the rest drops to the second. */}
        <EstadoDoExecutor
          status={executor.status}
          online={isOnline}
          className="col-start-1 row-start-1 md:col-auto md:row-auto"
        />

        {/* Identidade */}
        <div className="min-w-0 col-start-2 row-start-1 md:col-auto md:row-auto">
          <div className="flex items-center gap-1.5 min-w-0">
            {/* The name IS the drawer button. The whole row also toggles on
                click, but as a mouse convenience: turning it into
                `role="button"` would be invalid, because the action menu is a
                button inside it — and without a real control none of this (load,
                hardware, metrics, users) was reachable by keyboard. */}
            <button
              type="button"
              aria-expanded={aberto}
              onClick={e => { e.stopPropagation(); setAberto(v => !v) }}
              className="flex min-w-0 cursor-pointer items-center gap-1 rounded-sm text-left outline-none
                         focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <TbChevronRight
                size={12}
                className={cn("shrink-0 text-muted-foreground transition-transform", aberto && "rotate-90")}
                aria-hidden="true"
              />
              <span className="font-medium text-sm truncate">{executor.name}</span>
            </button>
            {executor.is_default && (
              <span className="shrink-0 rounded bg-primary/10 px-1 text-[9px] font-semibold text-primary">pool</span>
            )}
            {ehEsteComputador && (
              <span className="shrink-0 rounded bg-green-500/15 px-1 text-[9px] font-semibold text-green-700 dark:text-green-400">este computador</span>
            )}
          </div>
          <span className="block font-mono text-[10px] text-muted-foreground truncate">
            {executor.status !== "active" && (
              <span className="font-sans font-medium text-foreground/80">{ROTULO_STATUS_EXECUTOR[executor.status]} · </span>
            )}
            {executor.system_info?.hostname ?? executor.description ?? "—"}
            {executor.system_info?.cpu_cores != null && ` · ${executor.system_info.cpu_cores}c`}
            {executor.system_info?.container && " · container"}
          </span>
        </div>

        {/* `md:contents` is what allows ONE markup for both forms: on the
            phone this div is the second line (type, slots, version and
            activity side by side, below the name); from `md` up it
            disappears from the layout and the children become grid cells again. */}
        <div className="col-start-2 col-end-4 row-start-2 flex flex-wrap items-center gap-x-3 gap-y-1 md:contents">
          {/* Type — only when the list mixes types */}
          {mostrarTipo && (
            <span className={cn(
              "inline-flex items-center gap-1 w-fit text-[10px] font-medium px-1.5 py-0.5 rounded",
              // hidden in the `md` band along with the column (see TRILHO_COLUNAS_TIPO);
              // on phones it stays visible, since there is spare width on the 2nd line.
              "md:hidden lg:inline-flex",
              estiloTipo.fundo, estiloTipo.texto,
            )}>
              <IconeTipo size={11} aria-hidden="true" /> {estiloTipo.nome}
            </span>
          )}

          {/* Slots — one cell per slot. */}
          <MedidorDeSlots
            running={cap?.running ?? 0}
            queued={cap?.queued ?? 0}
            maxConcurrent={cap?.max_concurrent ?? executor.max_concurrent_jobs}
            online={isOnline}
          />

          <span
            className={cn(
              "text-[11px] tabular-nums text-muted-foreground text-right truncate md:hidden lg:block",
              // Same reason as the slots' dash: with no version reported, on phones
              // nothing is left but an unlabeled "—".
              !executor.executor_version && "hidden",
            )}
            // The Docker executor's one carries the commit (v2.15.0+3f02f44) and doesn't
            // fit whole in the column: the truncation is the same as the next
            // column's, and the full version goes in the title.
            title={executor.executor_version ? `v${executor.executor_version}` : undefined}
          >
            {executor.executor_version ? `v${executor.executor_version}` : "—"}
          </span>

          {/* Uptime and "visto em" (last seen) are OPPOSITE quantities and shared the
              same unlabeled column: "2 h 15 min" on a connected executor read as
              two hours WITHOUT contact, the opposite of what it is. The prefix disambiguates. */}
          <span className="text-[11px] tabular-nums text-muted-foreground text-right truncate">
            {isOnline && uptimeSecs != null ? `no ar ${formatarDuracao(uptimeSecs)}`
              : executor.last_seen_at ? `visto ${formatarQuando(executor.last_seen_at)}`
              : "nunca"}
          </span>
        </div>

        {canManage && (
          // `stopPropagation`: a click on the menu must not toggle the row's
          // drawer — opening the dropdown and seeing the detail expand along
          // with it would be a side effect nobody asked for.
          <div
            className="shrink-0 justify-self-end col-start-3 row-start-1 md:col-auto md:row-auto"
            onClick={e => e.stopPropagation()}
          >
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="icon" variant="ghost" className="max-md:size-10" aria-label={`Ações de ${executor.name}`}>
                  <TbDots className="text-muted-foreground" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => {
                    navigator.clipboard.writeText(executor.id_hash)
                    createToast.success("Agent ID copiado.")
                  }}
                >
                  <TbCopy className="mr-2" aria-hidden="true" /> Copiar Agent ID
                </DropdownMenuItem>
                {executor.status !== "revoked" && (
                  <EnrollmentOtpDialog
                    agentId={executor.id_hash}
                    agentStatus={executor.status}
                    trigger={
                      <DropdownMenuItem onSelect={e => e.preventDefault()}>
                        <TbShieldLock className="mr-2" aria-hidden="true" /> Gerar OTP de enrollment
                      </DropdownMenuItem>
                    }
                  />
                )}
                {isAdmin && executor.status !== "revoked" && (
                  <EditAgentDialog executor={executor} onUpdated={onRefresh} />
                )}
                {isAdmin && !executor.is_default && executor.status === "active" && (
                  <DropdownMenuItem onClick={handleSetDefault}>
                    <TbStar className="mr-2" aria-hidden="true" /> Adicionar ao pool padrão
                  </DropdownMenuItem>
                )}
                {isAdmin && executor.is_default && executor.status === "active" && (
                  <DropdownMenuItem onClick={handleUnsetDefault}>
                    <TbStar className="mr-2 text-muted-foreground" aria-hidden="true" /> Remover do pool padrão
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                {executor.status !== "revoked" && (
                  <RevokeAgentDialog executor={executor} onRevoked={onRefresh} />
                )}
                {executor.status === "revoked" && (
                  <DeleteAgentDialog executor={executor} onDeleted={onRefresh} />
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      {/* Drawer — everything that isn't compared between machines and therefore
          doesn't deserve its own column. */}
      {aberto && (
      <div className="flex flex-col gap-3 px-3 pb-3 pt-1 bg-muted/25">

      {/* The description is written by the user and vanished entirely when the
          executor reported a hostname — the subline shows one or the other, never
          both. Here it has a guaranteed place. */}
      {executor.description && (
        <p className="text-xs text-muted-foreground">{executor.description}</p>
      )}

      {executor.capabilities.length > 0 && (
        <div className="flex gap-1 flex-wrap">
          {executor.capabilities.map(c => (
            <span key={c} className="px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground border border-border">
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Metrics line — always visible if online or with history */}
      {isOnline || metrics ? (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border pt-3">
          {isOnline && (
            <LoadBar
              running={cap?.running ?? 0}
              queued={cap?.queued ?? 0}
              maxConcurrent={cap?.max_concurrent ?? executor.max_concurrent_jobs}
              maxQueue={cap?.max_queue ?? executor.max_queue_size}
            />
          )}
          {metrics && metrics.total_runs > 0 && (
            <ExecutorHistoricMetrics metrics={metrics} />
          )}
        </div>
      ) : null}

      {/* Hardware information */}
      {executor.system_info && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border pt-2 text-xs text-muted-foreground">
          {executor.system_info.os_name && (
            <span className="flex items-center gap-1">
              <TbDeviceDesktop size={14} aria-hidden="true" />
              {executor.system_info.os_name} {executor.system_info.os_version}
            </span>
          )}
          {executor.system_info.cpu_cores != null && (
            <span className="flex items-center gap-1 tabular-nums">
              <TbCpu size={14} aria-hidden="true" />
              {plural(executor.system_info.cpu_cores, "core")}
            </span>
          )}
          {executor.system_info.ram_total_gb != null && (
            <span className="flex items-center gap-1 tabular-nums">
              <TbServer size={14} aria-hidden="true" />
              {executor.system_info.ram_available_gb != null
                ? `${executor.system_info.ram_available_gb} / ${executor.system_info.ram_total_gb} GB RAM`
                : `${executor.system_info.ram_total_gb} GB RAM`}
            </span>
          )}
          {executor.system_info.disk_total_gb != null && (
            <span className="flex items-center gap-1 tabular-nums">
              <TbDatabase size={14} aria-hidden="true" />
              {executor.system_info.disk_free_gb != null
                ? `${executor.system_info.disk_free_gb} / ${executor.system_info.disk_total_gb} GB disco`
                : `${executor.system_info.disk_total_gb} GB disco`}
            </span>
          )}
          {executor.system_info.hostname && (
            <span className="font-mono text-[11px]">
              {executor.system_info.hostname}
              {executor.system_info.container && (
                <span className="ml-1 rounded bg-blue-500/10 px-1 py-0.5 text-[10px] font-sans text-blue-500">
                  container
                </span>
              )}
            </span>
          )}
        </div>
      )}

      {/* Assigned users — admin + dedicated executor */}
      {isAdmin && executor.executor_type === "dedicated" && (
        <AgentUsersSection agentId={executor.id_hash} />
      )}

      </div>
      )}
    </div>
  )
})
