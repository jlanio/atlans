"use client"

import { memo, type ReactNode } from "react"
import {
  TbArrowsSort, TbChevronDown, TbChevronLeft, TbChevronRight, TbChevronUp,
  TbDots, TbServer,
} from "react-icons/tb"
import { IAdminUser } from "@/service/GisFlowService"
import { formatLocal } from "@/lib/dayjs"
import { Button } from "@/app/components/ui/button"
import { Checkbox } from "@/app/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/app/components/ui/tooltip"
import { CABECALHO_DE_COLUNAS, LINHA_EMPILHADA } from "@/app/components/shared/tabela-empilhada"
import { cn } from "@/lib/utils"
import { formatarInteiro } from "@/lib/formatos"
import {
  SuspendUserDialog, ReactivateUserDialog, DeleteUserDialog,
  ChangeRoleDialog, ChangeAgentQuotaDialog,
} from "./dialogs"

/*
 * The table of the Admin › Users screen, extracted from the page. It keeps the
 * dense "rail" variant (table rows that become a stacked card on the phone via
 * shared/tabela-empilhada) and all the behavior — bulk selection, sorting by
 * column, per-row action menu — only standardizing the frame, the status/role
 * colors (sanctioned light/dark pairs) and the sorting (button + aria-sort +
 * react-icons icon, not ▲/▼ glyphs).
 */

// ── Cores de status e role (pares claro/escuro sancionados, contrato §6) ────────

const COR_STATUS: Record<IAdminUser["status"], string> = {
  active:    "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400",
  suspended: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400",
  deleted:   "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
}

const ROTULO_STATUS: Record<IAdminUser["status"], string> = {
  active:    "Ativo",
  suspended: "Suspenso",
  deleted:   "Excluído",
}

function StatusUsuarioBadge({ status }: { status: IAdminUser["status"] }) {
  return (
    <span
      data-status={status}
      className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium select-none", COR_STATUS[status])}
    >
      {ROTULO_STATUS[status]}
    </span>
  )
}

function RoleUsuarioBadge({ role, quota }: { role: string; quota: number }) {
  const admin = role === "admin"
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span
        data-role={role}
        className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium select-none",
          admin
            ? "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400"
            : "bg-muted text-muted-foreground",
        )}
      >
        {admin ? "Admin" : "Usuário"}
      </span>
      {/* Executor quota: only makes sense for non-admins with quota > 0. */}
      {!admin && quota > 0 && (
        <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium select-none bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400 tabular-nums">
          <TbServer size={11} aria-hidden="true" /> {quota}
        </span>
      )}
    </div>
  )
}

// ── Sortable header ─────────────────────────────────────────────────────────────

interface Props {
  users: IAdminUser[]
  loading: boolean
  currentUserId: string | null
  selected: Set<string>
  selectableUsers: IAdminUser[]
  allOnPageSelected: boolean
  onToggleSelect: (id: string) => void
  onToggleSelectAll: () => void
  sortBy: string
  sortOrder: "asc" | "desc"
  onSort: (col: string) => void
  total: number
  offset: number
  pageSize: number
  onOffset: (offset: number) => void
  onCompleted: () => void
}

// React.memo: the page re-renders on every keystroke in the search, but the props
// here already come stable (memoized in the page) — the memo avoids repainting the
// ~25 Radix rows on every keystroke.
export const TabelaDeUsuarios = memo(function TabelaDeUsuarios({
  users, loading, currentUserId,
  selected, selectableUsers, allOnPageSelected, onToggleSelect, onToggleSelectAll,
  sortBy, sortOrder, onSort,
  total, offset, pageSize, onOffset, onCompleted,
}: Props) {
  const currentPage = Math.floor(offset / pageSize) + 1
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const showFrom = total > 0 ? offset + 1 : 0
  const showTo = Math.min(offset + pageSize, total)

  return (
    // `aria-busy` on a reload over the ready list; the opacity gives the
    // "updating" feedback without erasing what is on screen.
    <div
      aria-busy={loading}
      className={cn("flex flex-col gap-4 transition-opacity duration-300", loading ? "opacity-60" : "opacity-100")}
    >
      {/* Card frame. Internal `overflow-x-auto`: from `md` up the fixed-width
          columns add up to more than the viewport and the body is
          `overflow-x: clip` — without its own scrolling here the last columns
          would be unreachable. Below `md` the row becomes a card
          (shared/tabela-empilhada) and there is no scrolling. */}
      <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-sm md:min-w-[720px]">
            <thead className={CABECALHO_DE_COLUNAS}>
              <tr className="border-b bg-muted/50">
                <th className="w-10 px-3 py-2.5">
                  <Checkbox
                    checked={allOnPageSelected && selectableUsers.length > 0}
                    onCheckedChange={onToggleSelectAll}
                    disabled={selectableUsers.length === 0}
                    aria-label="Selecionar todos os usuários da página"
                  />
                </th>
                <ColunaOrdenavel col="username" label="Usuário" {...{ sortBy, sortOrder, onSort }} />
                <ColunaOrdenavel col="status" label="Status" {...{ sortBy, sortOrder, onSort }} />
                <ColunaOrdenavel col="role" label="Role" {...{ sortBy, sortOrder, onSort }} />
                <ColunaOrdenavel col="last_login_at" label="Último login" className="hidden md:table-cell" {...{ sortBy, sortOrder, onSort }} />
                <ColunaOrdenavel col="created_at" label="Criado em" className="hidden lg:table-cell" {...{ sortBy, sortOrder, onSort }} />
                <th className="w-12 px-3 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {users.map(user => {
                const isSelf = user.id_hash === currentUserId
                const isDeleted = user.status === "deleted"
                return (
                  <tr
                    key={user.id_hash}
                    className={cn(
                      "border-b last:border-b-0 transition-colors hover:bg-accent/40",
                      LINHA_EMPILHADA,
                    )}
                  >
                    <td className="px-3 py-3">
                      {isSelf || isDeleted ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex">
                              <Checkbox checked={false} disabled aria-label="Seleção indisponível" />
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="right" className="text-xs">
                            {isSelf
                              ? "Você não pode aplicar ações em massa em si mesmo."
                              : "Usuário já excluído — nenhuma ação em massa disponível."}
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <Checkbox
                          checked={selected.has(user.id_hash)}
                          onCheckedChange={() => onToggleSelect(user.id_hash)}
                          aria-label={`Selecionar «${user.username}»`}
                        />
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex min-w-0 flex-col">
                        <span className="font-medium text-foreground truncate">{user.username}</span>
                        <span className="text-xs text-muted-foreground truncate">{user.email}</span>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <StatusUsuarioBadge status={user.status} />
                    </td>
                    <td className="px-3 py-3">
                      <RoleUsuarioBadge role={user.role} quota={user.agent_quota} />
                    </td>
                    <td className="px-3 py-3 text-xs text-muted-foreground tabular-nums hidden md:table-cell">
                      {formatLocal(user.last_login_at)}
                    </td>
                    <td className="px-3 py-3 text-xs text-muted-foreground tabular-nums hidden lg:table-cell">
                      {formatLocal(user.created_at)}
                    </td>
                    <td className="px-3 py-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button size="icon" variant="ghost" className="size-8 max-md:size-10" aria-label={`Ações para «${user.username}»`}>
                            <TbDots className="text-muted-foreground" aria-hidden="true" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {user.status === "active" && !isSelf && (
                            <SuspendUserDialog user={user} onCompleted={onCompleted} />
                          )}
                          {user.status === "suspended" && (
                            <ReactivateUserDialog user={user} onCompleted={onCompleted} />
                          )}
                          {!isDeleted && !isSelf && (
                            <ChangeRoleDialog user={user} onCompleted={onCompleted} />
                          )}
                          {!isDeleted && user.role !== "admin" && (
                            <ChangeAgentQuotaDialog user={user} onCompleted={onCompleted} />
                          )}
                          {!isDeleted && !isSelf && (
                            <>
                              <DropdownMenuSeparator />
                              <DeleteUserDialog user={user} onCompleted={onCompleted} />
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground tabular-nums">
            Mostrando <span className="font-medium text-foreground">{formatarInteiro(showFrom)}</span>–<span className="font-medium text-foreground">{formatarInteiro(showTo)}</span> de{" "}
            <span className="font-medium text-foreground">{formatarInteiro(total)}</span>
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="icon"
              variant="outline"
              className="size-8 max-md:size-10"
              disabled={offset === 0}
              aria-label="Página anterior"
              onClick={() => onOffset(Math.max(0, offset - pageSize))}
            >
              <TbChevronLeft size={16} aria-hidden="true" />
            </Button>
            <span className="text-xs text-muted-foreground tabular-nums">
              {currentPage} / {totalPages}
            </span>
            <Button
              size="icon"
              variant="outline"
              className="size-8 max-md:size-10"
              disabled={offset + pageSize >= total}
              aria-label="Próxima página"
              onClick={() => onOffset(offset + pageSize)}
            >
              <TbChevronRight size={16} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
})

/**
 * Sortable `<th>`: a `<button>` (not `<th onClick>`) with `aria-sort` on the
 * header and a `react-icons/tb` icon instead of a ▲/▼ glyph. Inactive, it shows
 * the faded neutral arrow to say "you can sort by this".
 */
function ColunaOrdenavel({
  col, label, className, sortBy, sortOrder, onSort,
}: {
  col: string
  label: ReactNode
  className?: string
  sortBy: string
  sortOrder: "asc" | "desc"
  onSort: (col: string) => void
}) {
  const ativo = sortBy === col
  return (
    <th
      aria-sort={ativo ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}
      className={cn("px-0 py-0 text-left font-medium text-muted-foreground", className)}
    >
      <button
        type="button"
        onClick={() => onSort(col)}
        className="flex w-full items-center gap-1 px-3 py-2.5 text-left outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <span className="select-none">{label}</span>
        {ativo
          ? (sortOrder === "asc"
              ? <TbChevronUp size={13} aria-hidden="true" />
              : <TbChevronDown size={13} aria-hidden="true" />)
          : <TbArrowsSort size={13} className="opacity-40" aria-hidden="true" />}
      </button>
    </th>
  )
}
