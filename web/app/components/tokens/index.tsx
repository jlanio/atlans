"use client"

// "Tokens de acesso" screen (/settings/tokens) — contract screen-patterns.md.
//
// Personal list: the logged-in user's tokens, most recent first. Each one is
// valid only for what the account can already do, narrowed by scopes, workspaces
// and expiry. Revoking is immediate and final, but the token stays in the list
// as "Revogado". Template: `credentials/index.tsx` (header, precedence of the 4
// states, `atualizadoEm`, Refresh as ghost and a single primary).

import "dayjs/locale/pt-br"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useSession } from "next-auth/react"
import { TbAlertTriangle, TbClock, TbKey, TbPlus, TbRefresh, TbShieldOff } from "react-icons/tb"
import { GisFlowService } from "@/service/GisFlowService"
import type { ApiToken, ApiTokenCreated, IWorkspace } from "@/service/types"
import { dayjs, formatLocal, fromBackend, fromNowLocal } from "@/lib/dayjs"
import { cn } from "@/lib/utils"
import { createToast } from "@/utils/createToast"
import { useFetchData } from "@/app/hooks/useFetchData"
import PageRoot from "../page-root"
import { Button } from "../ui/button"
import { Dialog } from "../ui/dialog"
import { Skeleton } from "../ui/skeleton"
import { EntityCard } from "../shared/EntityCard"
import { plural } from "@/lib/formatos"
import { ErroDeCarga, SkeletonDeTokens, VazioPrimeiroUso } from "./estados"
import { ordenarEscopos, rotuloDeEscopo, rotuloDeStatus } from "./escopo-rotulos"
import CreateToken from "./dialog-content/create-token"
import RevokeToken from "./dialog-content/revoke-token"

// `fromNow()` only speaks Portuguese after someone loads the locale — today that
// happens as a side effect of canvas modules. Whoever lands directly on this
// screen would see "2 hours ago". Same precedent as `workflow/buttons/recent-runs`.
dayjs.locale("pt-br")

const ESCOPO_DA_TELA = "Para agentes e integrações — valem só para o que a sua conta já pode fazer"

/** A partir de quantos dias o selo «Ativo» vira «Expira em N dias». */
const AVISO_DE_EXPIRACAO_DIAS = 14

/** Whole days until `expires_at` (negative if already past); `null` without a date. */
export function diasAteExpirar(expiresAt: string | null | undefined, agora = Date.now()): number | null {
  const exp = fromBackend(expiresAt)
  if (!exp) return null
  return Math.ceil((exp.valueOf() - agora) / 86_400_000)
}

/** «Expira hoje» / «Expira em 1 dia» / «Expira em 12 dias». */
export function textoDeExpiracao(dias: number): string {
  return dias <= 0 ? "Expira hoje" : `Expira em ${plural(dias, "dia")}`
}

/**
 * "Todos os workspaces" when the token has no restriction; otherwise the count
 * with the names the workspace list resolved (without names, just the count — the
 * list may have failed or the workspace may have left).
 */
export function textoDeWorkspaces(ids: string[] | null, nomes: ReadonlyMap<string, string>): string {
  if (ids == null) return "Todos os workspaces"
  if (ids.length === 0) return "Nenhum workspace"
  const resolvidos = ids.map(id => nomes.get(id)).filter((n): n is string => !!n)
  if (ids.length === 1) return resolvidos[0] ? `Workspace: ${resolvidos[0]}` : "1 workspace"
  const contagem = plural(ids.length, "workspace")
  return resolvidos.length > 0 ? `${contagem}: ${resolvidos.join(", ")}` : contagem
}

/** The list keeps only the metadata: the secret doesn't stay in the page state. */
function semSegredo(criado: ApiTokenCreated): ApiToken {
  const { id, name, token_prefix, scopes, workspace_ids, expires_at, last_used_at, revoked_at, created_at, status } = criado
  return { id, name, token_prefix, scopes, workspace_ids, expires_at, last_used_at, revoked_at, created_at, status }
}

const TokensDeAcesso = () => {
  const { status } = useSession()
  const [workspaces, setWorkspaces] = useState<IWorkspace[]>([])
  // The list load is `useFetchData`: `loading` (its `firstLoad`) covers only
  // the FIRST load (skeleton); `refreshing` is the reload, with the list on
  // screen, faded, and the button spinning. The session gate is its job too.
  //
  // Without the error branch, a network failure fell into the first-use empty
  // state — the screen would lie, saying there are no tokens when it couldn't
  // load. The error card only applies with no accepted load
  // (`atualizadoEm == null`); a reload that fails over a ready list keeps what
  // was there and warns via toast (contract §3.2).
  const {
    data, firstLoad: loading, refreshing, error, atualizadoEm, refetch, setData: setTokens,
  } = useFetchData(() => GisFlowService.listApiTokens(), "Não foi possível carregar os tokens de acesso.", [], 0, {
    onErroComDados: mensagem => createToast.error("Não foi possível atualizar os tokens de acesso", mensagem),
  })
  const tokens = useMemo(() => data ?? [], [data])
  const loadError = error != null && atualizadoEm == null
  const [createOpen, setCreateOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<ApiToken | null>(null)

  // Only to translate ids into names (cards and the dialog's checkboxes). Failing
  // here is no reason to break the screen: without names, the card shows the count.
  const carregarWorkspaces = useCallback(async () => {
    const res = await GisFlowService.listWorkspaces()
    if (!res.error) setWorkspaces(res.data ?? [])
  }, [])

  useEffect(() => {
    if (status === "authenticated") carregarWorkspaces()
  }, [status, carregarWorkspaces])

  function handleRefresh() {
    refetch()
    carregarWorkspaces()
  }

  function handleCreated(criado: ApiTokenCreated) {
    // Most recent first, like the backend's listing.
    setTokens(prev => [semSegredo(criado), ...(prev ?? [])])
  }

  function handleRevoked(revogado: ApiToken) {
    setTokens(prev => prev && prev.map(t => (t.id === revogado.id ? revogado : t)))
  }

  const nomeDoWorkspace = useMemo(
    () => new Map(workspaces.map(w => [w.id_hash, w.name])),
    [workspaces],
  )

  const ativos = useMemo(() => tokens.filter(t => t.status === "active").length, [tokens])
  const hasTokens = tokens.length > 0

  // Header subtitle: the screen's scope; with tokens, the count goes in
  // front. Zero disappears (contract §7) — "0 ativos" helps nobody.
  function textoDoSubtitulo(): string {
    if (!hasTokens) return ESCOPO_DA_TELA
    const partes = [plural(tokens.length, "token")]
    if (ativos > 0) partes.push(plural(ativos, "ativo"))
    return `${partes.join(" · ")} — valem só para o que a sua conta já pode fazer`
  }

  // Status badge: always translated, raw value in `data-status`. Canonical
  // pairs from contract §6 — green (active), amber (expiring), red
  // (expired); revoked is neutral, because it's neither a failure nor a warning.
  function seloDeStatus(token: ApiToken) {
    const base = "flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium tabular-nums"
    if (token.status === "revoked") {
      return (
        <span data-status="revoked" className={cn(base, "bg-muted text-muted-foreground")}>
          <TbShieldOff className="size-3" aria-hidden="true" />
          {rotuloDeStatus("revoked")}
        </span>
      )
    }
    if (token.status === "expired") {
      return (
        <span data-status="expired" className={cn(base, "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400")}>
          <TbAlertTriangle className="size-3" aria-hidden="true" />
          {rotuloDeStatus("expired")}
        </span>
      )
    }
    const dias = diasAteExpirar(token.expires_at)
    if (dias != null && dias <= AVISO_DE_EXPIRACAO_DIAS) {
      return (
        <span data-status="active" className={cn(base, "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400")}>
          <TbClock className="size-3" aria-hidden="true" />
          {textoDeExpiracao(dias)}
        </span>
      )
    }
    return (
      <span data-status="active" className={cn(base, "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400")}>
        {rotuloDeStatus("active")}
      </span>
    )
  }

  function renderCard(token: ApiToken) {
    const inativo = token.status !== "active"
    const ultimoUso = token.last_used_at ? `Último uso: ${fromNowLocal(token.last_used_at)}` : "Nunca usado"
    return (
      <li key={token.id} data-token-status={token.status} className={cn(inativo && "opacity-75")}>
        <EntityCard
          title={token.name}
          badge={seloDeStatus(token)}
          leading={
            <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-md", inativo ? "bg-muted" : "bg-primary/10")}>
              <TbKey className={cn("size-4", inativo ? "text-muted-foreground" : "text-primary")} aria-hidden="true" />
            </span>
          }
          meta={
            <div className="mt-1 flex flex-col gap-1 text-xs text-muted-foreground">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <code className="rounded bg-muted px-1 font-mono text-[11px] text-foreground/80" title="Início do token">
                  {token.token_prefix}…
                </code>
                <ul aria-label="Escopos" className="flex flex-wrap gap-1">
                  {ordenarEscopos(token.scopes).map(escopo => (
                    <li
                      key={escopo}
                      className="rounded-full border border-transparent bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground"
                    >
                      {rotuloDeEscopo(escopo)}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                <span>{textoDeWorkspaces(token.workspace_ids, nomeDoWorkspace)}</span>
                <span aria-hidden="true">·</span>
                <span title={token.last_used_at ? formatLocal(token.last_used_at) : undefined}>{ultimoUso}</span>
                <span aria-hidden="true">·</span>
                <span title={formatLocal(token.created_at)}>Criado {fromNowLocal(token.created_at)}</span>
              </div>
            </div>
          }
          actions={
            // A revoked token can't be revoked again; an expired one can still be revoked
            // (it stops counting as existing for whoever audits).
            token.status !== "revoked" ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRevokeTarget(token)}
                aria-label={`Revogar o token ${token.name}`}
                className="gap-1.5 max-md:h-10"
              >
                <TbShieldOff size={14} aria-hidden="true" />
                Revogar
              </Button>
            ) : undefined
          }
        />
      </li>
    )
  }

  return (
    <PageRoot>
      {/* Fixed header from contract §1: title + scope subtitle on the left,
          actions on the right (Refresh as ghost and New token as the only primary).
          Only two actions — they fit on the line on the phone too, no ⋯ menu. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-foreground">Tokens de acesso</h1>
          {/* Stable live region: the `aria-live` sits on the container, which survives
              the Skeleton↔text swap, so the screen reader announces the count
              when it changes (e.g. after creating or revoking). */}
          <div aria-live="polite" aria-atomic="true">
            {loading ? (
              <Skeleton className="mt-1 h-4 w-64" />
            ) : (
              <p className="text-sm font-medium tabular-nums text-muted-foreground">{textoDoSubtitulo()}</p>
            )}
          </div>
        </div>

        <div className="flex w-full flex-wrap items-center gap-2 select-none sm:w-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={loading || refreshing}
            aria-label="Atualizar a lista de tokens"
            className="gap-1.5 max-md:h-10"
          >
            <TbRefresh size={14} className={refreshing ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
            Atualizar
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)} className="flex-1 max-md:h-10 sm:flex-none">
            <TbPlus size={15} aria-hidden="true" />
            Novo token
          </Button>
        </div>
      </div>

      {/* Precedence from contract §3: loading → error (only on the 1st load) →
          first use → content. */}
      {loading ? (
        <SkeletonDeTokens />
      ) : loadError && atualizadoEm == null ? (
        <ErroDeCarga onTentar={handleRefresh} />
      ) : !hasTokens ? (
        <VazioPrimeiroUso onCriar={() => setCreateOpen(true)} />
      ) : (
        <ul
          aria-busy={refreshing}
          className={cn(
            "flex flex-col gap-3 transition-opacity motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300",
            refreshing && "opacity-60",
          )}
        >
          {tokens.map(renderCard)}
        </ul>
      )}

      {/* Mounted only while open: the form is born clean on every opening and
          the step 2 secret leaves memory together with the dialog. */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        {createOpen && (
          <CreateToken
            workspaces={workspaces}
            onCreated={handleCreated}
            onClose={() => setCreateOpen(false)}
          />
        )}
      </Dialog>

      <Dialog open={revokeTarget != null} onOpenChange={aberto => { if (!aberto) setRevokeTarget(null) }}>
        {revokeTarget && (
          <RevokeToken
            token={revokeTarget}
            onRevoked={handleRevoked}
            onClose={() => setRevokeTarget(null)}
          />
        )}
      </Dialog>
    </PageRoot>
  )
}

export default TokensDeAcesso
