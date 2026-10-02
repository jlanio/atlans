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
import { formatarInteiro, plural } from "@/lib/formatos"
import { BulkActionDialog } from "@/app/components/admin/users/dialogs"
import { TabelaDeUsuarios } from "@/app/components/admin/users/tabela"
import {
  ErroDeCarga, SemAcesso, SemResultado, SkeletonDeUsuarios, VazioPrimeiroUso,
} from "@/app/components/admin/users/estados"

// ── Página principal ─────────────────────────────────────────────────────────

type StatusFilter = "all" | "active" | "suspended" | "deleted"

const PAGE_SIZE = 25

const OPCOES_STATUS: { value: StatusFilter; label: string }[] = [
  { value: "all",       label: "Todos" },
  { value: "active",    label: "Ativos" },
  { value: "suspended", label: "Suspensos" },
  { value: "deleted",   label: "Excluídos" },
]

/**
 * Subtítulo de escopo: diz quantas contas o recorte atual alcança e o que o
 * filtra. O total vem do backend para a consulta corrente (`data.total`); as
 * partes com role/busca só entram quando há filtro. Enquanto não há o que
 * contar (1ª carga), o cabeçalho mostra um Skeleton no lugar (contrato §1).
 */
function textoDeEscopo(total: number, status: StatusFilter, role: string, q: string): string {
  const nucleo = (() => {
    switch (status) {
      case "active":    return total === 1 ? "1 usuário ativo"    : `${formatarInteiro(total)} usuários ativos`
      case "suspended": return total === 1 ? "1 usuário suspenso" : `${formatarInteiro(total)} usuários suspensos`
      case "deleted":   return total === 1 ? "1 usuário excluído" : `${formatarInteiro(total)} usuários excluídos`
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

  // Estado de filtros e busca
  const [search, setSearch]                   = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [statusFilter, setStatusFilter]       = useState<StatusFilter>("active")
  const [roleFilter, setRoleFilter]           = useState<string>("all")
  const [sortBy, setSortBy]                   = useState("created_at")
  const [sortOrder, setSortOrder]             = useState<"asc" | "desc">("desc")
  const [offset, setOffset]                   = useState(0)

  // Seleção em massa
  const [selected, setSelected]     = useState<Set<string>>(new Set())
  const [bulkAction, setBulkAction] = useState<"suspend" | "reactivate" | "delete" | null>(null)

  // Debounce da busca (400ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
      setOffset(0) // reset paginação ao buscar
    }, 400)
    return () => clearTimeout(timer)
  }, [search])

  // Fetch de dados. Os filtros são deps do `useFetchData`: cada troca de
  // filtro, de página ou da busca (debounce) dispara uma busca nova, e a guarda
  // de geração dele descarta a resposta de uma busca anterior que chegue
  // depois — antes a que resolvesse por último vencia, e a lista de um filtro
  // antigo sobrescrevia a do atual. `loading` é o dele: qualquer busca em voo.
  //
  // `erro` só governa o cartão de erro na 1ª carga; numa recarga que falha
  // sobre a lista pronta mantemos o que havia + um toast (contrato §3.2).
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

  // useCallback: `handleRefresh` desce como `onCompleted` para a tabela
  // memoizada — recriá-lo a cada tecla na busca anularia o React.memo.
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

  // Seleção
  // Memoizado por `data`: o `?? []` produzia um array novo a cada render quando
  // `data.items` fosse indefinido, e isso desestabilizaria as deps abaixo.
  const users = useMemo(() => data?.items ?? [], [data])
  const total = data?.total ?? 0
  // useMemo: props estáveis para a tabela memoizada — sem isto o array/booleano
  // recriado a cada tecla na busca anularia o React.memo.
  const selectableUsers = useMemo(
    () => users.filter(u => u.id_hash !== currentUserId && u.status !== "deleted"),
    [users, currentUserId],
  )
  const allOnPageSelected = useMemo(
    () => selectableUsers.length > 0 && selectableUsers.every(u => selected.has(u.id_hash)),
    [selectableUsers, selected],
  )

  // useCallback: handlers estáveis passados à tabela memoizada.
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

  // Ordenação por coluna. useCallback: `onSort` estável para a tabela memoizada.
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
    // Um provider para a página inteira: cada `<td>` de checkbox desabilitado
    // montava o seu, e o provider existe para ser único por árvore — 25 cópias
    // são 25 contextos independentes, sem o "skip delay" entre tooltips
    // vizinhos e com o custo de montagem multiplicado a cada troca de página.
    <TooltipProvider delayDuration={100}>
      <PageRoot>
        {/* Cabeçalho (contrato §1). `flex-wrap`: sem ele o título e a fila de
            ações disputam a mesma linha no telefone e quem cede é o título. */}
        <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold text-foreground">Usuários</h1>
            {data ? (
              <p className="text-sm font-medium text-muted-foreground">
                {textoDeEscopo(total, statusFilter, roleFilter, debouncedSearch)}
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

            {/* Filtro de status: grupo de toggle canônico (contrato §1). */}
            <div
              role="group"
              aria-label="Filtrar por status"
              className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
            >
              {OPCOES_STATUS.map(opt => {
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

            {/* Filtro de role */}
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

          {/* Barra de ações em massa. Entrada por CSS sob `motion-safe:` no lugar
              do framer-motion. */}
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

        {/* Corpo — precedência: carregando → erro (só se nunca houve carga) →
            vazio/sem-resultado → tabela (contrato §3). */}
        {data === null && loading && <SkeletonDeUsuarios />}

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
          <TabelaDeUsuarios
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

        {/* Diálogo de ação em massa */}
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
