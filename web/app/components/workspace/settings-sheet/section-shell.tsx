"use client"

import { ReactNode } from "react"
import { TbAlertTriangle, TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"

interface Props {
  title: string
  description?: ReactNode
  /** Ação no canto superior direito da seção (ex.: "Adicionar membro"). */
  action?: ReactNode
  /**
   * Coloca a `action` numa linha ABAIXO do título/descrição, em vez do canto
   * superior direito. Para ações largas (um link + um botão) que, num painel
   * estreito, espremem o título a ponto de quebrá-lo em duas linhas.
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
 * Casca de uma seção do painel de configurações.
 *
 * A ordem de decisão — carregando, depois ERRO, depois vazio — é o ponto todo
 * deste componente. Antes, cada seção fazia `catch { toast }` e deixava a lista
 * vazia: uma falha de rede ao carregar membros virava "Nenhum membro convidado
 * ainda", ou seja, a tela afirmava um fato sobre os dados quando na verdade não
 * tinha dado nenhum. O toast some em segundos e o texto errado fica.
 *
 * Erro também precisa de saída: `onRetry` evita que o usuário tenha de recarregar
 * a página inteira para tentar de novo uma seção.
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
