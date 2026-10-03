"use client"

import { ReactNode } from "react"
import { TbAlertTriangle, TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"

interface Props {
  title: string
  description?: ReactNode
  /** Action in the section's top-right corner (e.g. "Adicionar membro"). */
  action?: ReactNode
  /**
   * Puts the `action` on a line BELOW the title/description, instead of the
   * top-right corner. For wide actions (a link + a button) that, in a narrow
   * panel, squeeze the title to the point of breaking it into two lines.
   */
  actionBelow?: boolean
  loading?: boolean
  /** Mensagem do backend. Presente, vence o estado vazio. */
  error?: string | null
  onRetry?: () => void
  isEmpty?: boolean
  emptyMessage?: string
  children?: ReactNode
}

/**
 * Shell of a settings panel section.
 *
 * The decision order — loading, then ERROR, then empty — is the whole point of
 * this component. Before, each section did `catch { toast }` and left the list
 * empty: a network failure while loading members became "Nenhum membro
 * convidado ainda" (no members invited yet), i.e. the screen asserted a fact
 * about the data when in fact it had no data at all. The toast disappears in
 * seconds and the wrong text stays.
 *
 * An error also needs a way out: `onRetry` saves the user from having to reload
 * the whole page to retry a section.
 */
export function SheetSection({
  title, description, action, actionBelow,
  loading, error, onRetry,
  isEmpty, emptyMessage,
  children,
}: Props) {
  return (
    <section className="space-y-4">
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              {title}
            </h3>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          {action && !actionBelow && <div className="shrink-0">{action}</div>}
        </div>
        {action && actionBelow && (
          <div className="flex flex-wrap items-center justify-end gap-1">{action}</div>
        )}
      </div>

      {loading ? (
        <div className="space-y-2" aria-busy="true">
          <Skeleton className="h-9 w-full rounded-md" />
          <Skeleton className="h-9 w-3/4 rounded-md" />
        </div>
      ) : error ? (
        <div
          role="alert"
          className="space-y-3 rounded-md border border-destructive/30 bg-destructive/5 p-3"
        >
          <div className="flex items-start gap-2">
            <TbAlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
            <p className="text-sm text-foreground">{error}</p>
          </div>
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
              <TbRefresh className="size-3.5" aria-hidden="true" />
              Tentar novamente
            </Button>
          )}
        </div>
      ) : isEmpty ? (
        <p className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
          {emptyMessage}
        </p>
      ) : (
        children
      )}
    </section>
  )
}
