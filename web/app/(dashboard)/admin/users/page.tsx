"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useSession } from "next-auth/react"
import { TbBan, TbCheck, TbDownload, TbRefresh, TbSearch, TbTrash } from "react-icons/tb"
import { GisFlowService } from "@/service/GisFlowService"
import { useFetchData } from "@/app/hooks/useFetchData"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Skeleton } from "@/app/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { TooltipProvider } from "@/app/components/ui/tooltip"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { formatInteger, plural } from "@/lib/formatos"
import { BulkActionDialog } from "@/app/components/admin/users/dialogs"
import { UsersTable } from "@/app/components/admin/users/tabela"
import {
  ErroDeCarga, SemAcesso, SemResultado, UsersSkeleton, VazioPrimeiroUso,
} from "@/app/components/admin/users/estados"

// ── Main page ────────────────────────────────────────────────────────────────

type StatusFilter = "all" | "active" | "suspended" | "deleted"

const PAGE_SIZE = 25

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all",       label: "Todos" },
  { value: "active",    label: "Ativos" },
  { value: "suspended", label: "Suspensos" },
  { value: "deleted",   label: "Excluídos" },
]

/**
 * Scope subtitle: says how many accounts the current slice reaches and what
 * filters it. The total comes from the backend for the current query
 * (`data.total`); the role/search parts only come in when there is a filter.
 * While there is nothing to count (1st load), the header shows a Skeleton in
 * its place (contract §1).
 */
function scopeText(total: number, status: StatusFilter, role: string, q: string): string {
  const nucleo = (() => {
    switch (status) {
      case "active":    return total === 1 ? "1 usuário ativo"    : `${formatInteger(total)} usuários ativos`
      case "suspended": return total === 1 ? "1 usuário suspenso" : `${formatInteger(total)} usuários suspensos`
      case "deleted":   return total === 1 ? "1 usuário excluído" : `${formatInteger(total)} usuários excluídos`
      default:          return plural(total, "usuário")
    }
  })()
  const partes = [nucleo]
  if (role === "admin") partes.push("apenas admins")
  else if (role === "user") partes.push("apenas usuários comuns")
  const termo = q.trim()
  if (termo) partes.push(`busca «${termo}»`)
  return partes.join(" · ")
}

export default function AdminUsersPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const currentUserId = session?.user?.id_hash ?? null

  // Filter and search state
  const [search, setSearch]                   = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [statusFilter, setStatusFilter]       = useState<StatusFilter>("active")
  const [roleFilter, setRoleFilter]           = useState<string>("all")
  const [sortBy, setSortBy]                   = useState("created_at")
  const [sortOrder, setSortOrder]             = useState<"asc" | "desc">("desc")
  const [offset, setOffset]                   = useState(0)

  // Bulk selection
  const [selected, setSelected]     = useState<Set<string>>(new Set())
  const [bulkAction, setBulkAction] = useState<"suspend" | "reactivate" | "delete" | null>(null)

  // Search debounce (400ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
      setOffset(0) // reset pagination on search
    }, 400)
    return () => clearTimeout(timer)
  }, [search])

  // Data fetch. The filters are deps of `useFetchData`: every change of filter,
  // page or (debounced) search triggers a new fetch, and its generation guard
  // discards the response of an earlier fetch that arrives later — before, the
  // one that resolved last won, and an old filter's list overwrote the current
  // one. `loading` is its own: any fetch in flight.
  //
  // `erro` only governs the error card on the 1st load; on a reload that fails
  // over the ready list we keep what was there + a toast (contract §3.2).
  const { data, loading, error, refetch: fetchUsers } = useFetchData(
    () => GisFlowService.getAdminUsers({
      search: debouncedSearch || undefined,
      status: statusFilter !== "all" ? statusFilter : undefined,
      role: roleFilter !== "all" ? roleFilter : undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
      limit: PAGE_SIZE,
      offset,
    }),
    "Não foi possível carregar os usuários.",
    [debouncedSearch, statusFilter, roleFilter, sortBy, sortOrder, offset],
    0,
    {
      ativo: isAdmin,
      onErroComDados: () => createToast.error("Não foi possível atualizar os usuários."),
    },
  )
  const erro = error != null

  // useCallback: `handleRefresh` goes down as `onCompleted` to the memoized
  // table — recreating it on every keystroke in the search would defeat React.memo.
  const handleRefresh = useCallback(() => {
    setSelected(new Set())
    fetchUsers()
  }, [fetchUsers])

  function limparFiltros() {
    setSearch("")
    setDebouncedSearch("")
    setStatusFilter("all")
    setRoleFilter("all")
    setOffset(0)
  }

  // Selection
  // Memoized by `data`: the `?? []` produced a new array on every render when
  // `data.items` was undefined, and that would destabilize the deps below.
  const users = useMemo(() => data?.items ?? [], [data])
  const total = data?.total ?? 0
  // useMemo: stable props for the memoized table — without this the array/boolean
  // recreated on every keystroke in the search would defeat React.memo.
  const selectableUsers = useMemo(
    () => users.filter(u => u.id_hash !== currentUserId && u.status !== "deleted"),
    [users, currentUserId],
  )
  const allOnPageSelected = useMemo(
    () => selectableUsers.length > 0 && selectableUsers.every(u => selected.has(u.id_hash)),
    [selectableUsers, selected],
  )

  // useCallback: stable handlers passed to the memoized table.
  const toggleSelect = useCallback((id: string) => {
    if (id === currentUserId) return
    const user = users.find(u => u.id_hash === id)
    if (user?.status === "deleted") return
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [currentUserId, users])

  const toggleSelectAll = useCallback(() => {
    if (allOnPageSelected) {
      setSelected(prev => {
        const next = new Set(prev)
        selectableUsers.forEach(u => next.delete(u.id_hash))
        return next
      })
    } else {
      setSelected(prev => {
        const next = new Set(prev)
        selectableUsers.forEach(u => next.add(u.id_hash))
        return next
      })
    }
  }, [allOnPageSelected, selectableUsers])

  // Export CSV
  async function handleExportCSV() {
    const res = await GisFlowService.exportUsersCSV({
      search: debouncedSearch || undefined,
      status: statusFilter !== "all" ? statusFilter : undefined,
      role: roleFilter !== "all" ? roleFilter : undefined,
    })
    if (res.data) {
      const url = window.URL.createObjectURL(res.data)
      const a = document.createElement("a")
      a.href = url
      a.download = "users.csv"
      a.click()
      window.URL.revokeObjectURL(url)
    } else {
      createToast.error("Erro ao exportar CSV.")
    }
  }

  // Sorting by column. useCallback: stable `onSort` for the memoized table.
  const handleSort = useCallback((col: string) => {
    if (sortBy === col) {
      setSortOrder(prev => prev === "asc" ? "desc" : "asc")
    } else {
      setSortBy(col)
      setSortOrder("asc")
    }
    setOffset(0)
  }, [sortBy])

  if (!isAdmin) {
    return (
      <PageRoot>
        <SemAcesso />
      </PageRoot>
    )
  }

  const filtrosAtivos =
    debouncedSearch.trim() !== "" || statusFilter !== "all" || roleFilter !== "all"

  return (
    // One provider for the whole page: each disabled-checkbox `<td>` mounted its
    // own, and the provider exists to be unique per tree — 25 copies are 25
    // independent contexts, without the "skip delay" between neighboring
    // tooltips and with the mount cost multiplied on every page change.
    <TooltipProvider delayDuration={100}>
      <PageRoot>
        {/* Header (contract §1). `flex-wrap`: without it the title and the action
            row fight for the same line on the phone and the title gives way. */}
        <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold text-foreground">Usuários</h1>
            {data ? (
              <p className="text-sm font-medium text-muted-foreground">
                {scopeText(total, statusFilter, roleFilter, debouncedSearch)}
              </p>
            ) : (
              <Skeleton className="mt-1 h-4 w-64" />
            )}
          </div>

          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <Button variant="outline" size="sm" className="max-md:h-10" onClick={handleExportCSV}>
              <TbDownload size={15} aria-hidden="true" /> Exportar CSV
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={loading}
              aria-label="Atualizar a lista de usuários"
              className="gap-1.5 max-md:h-10"
            >
              <TbRefresh size={14} className={loading ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
              Atualizar
            </Button>
          </div>
        </div>

        {/* Toolbar: busca + filtros */}
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3">
            {/* Busca */}
            <div className="relative min-w-[200px] max-w-sm flex-1">
              <TbSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} aria-hidden="true" />
              <Input
                placeholder="Buscar por nome ou e-mail…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9 max-md:h-10"
                aria-label="Buscar usuários por nome ou e-mail"
              />
            </div>

            {/* Status filter: canonical toggle group (contract §1). */}
            <div
              role="group"
              aria-label="Filtrar por status"
              className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
            >
              {STATUS_OPTIONS.map(opt => {
                const ativo = statusFilter === opt.value
                return (
                  <button
                    key={opt.value}
                    type="button"
                    aria-pressed={ativo}
                    onClick={() => { setStatusFilter(opt.value); setOffset(0) }}
                    className={cn(
                      "px-3 text-xs font-medium outline-none transition-colors",
                      "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                      ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                    )}
                  >
                    {opt.label}
                  </button>
                )
              })}
            </div>

            {/* Role filter */}
            <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v); setOffset(0) }}>
              <SelectTrigger className="w-[150px] max-md:h-10">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os roles</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="user">Usuário</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Bulk action bar. Entrance via CSS under `motion-safe:` instead of
              framer-motion. */}
          {selected.size > 0 && (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-card px-4 py-2.5 shadow-xs motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-top-1 motion-safe:duration-200">
              <span className="text-sm font-medium tabular-nums">
                {plural(selected.size, "selecionado")}
              </span>
              <div className="ml-auto flex flex-wrap gap-2">
                <Button size="sm" variant="outline" className="max-md:h-10" onClick={() => setBulkAction("suspend")}>
                  <TbBan className="mr-1.5" size={14} aria-hidden="true" /> Suspender
                </Button>
                <Button size="sm" variant="outline" className="max-md:h-10" onClick={() => setBulkAction("reactivate")}>
                  <TbCheck className="mr-1.5" size={14} aria-hidden="true" /> Reativar
                </Button>
                <Button size="sm" variant="destructive" className="max-md:h-10" onClick={() => setBulkAction("delete")}>
                  <TbTrash className="mr-1.5" size={14} aria-hidden="true" /> Excluir
                </Button>
                <Button size="sm" variant="ghost" className="max-md:h-10" onClick={() => setSelected(new Set())}>
                  Limpar
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Body — precedence: loading → error (only if there was never a load) →
            empty/no-result → table (contract §3). */}
        {data === null && loading && <UsersSkeleton />}

        {data === null && erro && !loading && (
          <ErroDeCarga
            mensagem="A listagem de contas não respondeu. Verifique a conexão e tente de novo."
            onTentar={fetchUsers}
          />
        )}

        {data !== null && users.length === 0 && (
          filtrosAtivos
            ? <SemResultado q={debouncedSearch} onLimpar={limparFiltros} />
            : <VazioPrimeiroUso />
        )}

        {data !== null && users.length > 0 && (
          <UsersTable
            users={users}
            loading={loading}
            currentUserId={currentUserId}
            selected={selected}
            selectableUsers={selectableUsers}
            allOnPageSelected={allOnPageSelected}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
            total={total}
            offset={offset}
            pageSize={PAGE_SIZE}
            onOffset={setOffset}
            onCompleted={handleRefresh}
          />
        )}

        {/* Bulk action dialog */}
        {bulkAction && (
          <BulkActionDialog
            action={bulkAction}
            userIds={Array.from(selected)}
            onCompleted={() => { setSelected(new Set()); handleRefresh() }}
            onClose={() => setBulkAction(null)}
          />
        )}
      </PageRoot>
    </TooltipProvider>
  )
}
