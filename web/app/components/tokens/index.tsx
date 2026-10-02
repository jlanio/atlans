"use client"

// Tela «Tokens de acesso» (/settings/tokens) — contrato screen-patterns.md.
//
// Lista pessoal: os tokens do usuário logado, mais recente primeiro. Cada um
// vale só para o que a conta já pode fazer, recortado por escopos, workspaces
// e validade. Revogar é imediato e definitivo, mas o token fica na lista como
// «Revogado». Molde: `credentials/index.tsx` (cabeçalho, precedência dos 4
// estados, `atualizadoEm`, Atualizar em ghost e uma única primária).

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

// `fromNow()` só fala português depois que alguém carrega o locale — hoje isso
// acontece como efeito colateral de módulos do canvas. Quem entra direto nesta
// tela veria «2 hours ago». Mesmo precedente de `workflow/buttons/recent-runs`.
dayjs.locale("pt-br")

const ESCOPO_DA_TELA = "Para agentes e integrações — valem só para o que a sua conta já pode fazer"

/** A partir de quantos dias o selo «Ativo» vira «Expira em N dias». */
const AVISO_DE_EXPIRACAO_DIAS = 14

/** Dias inteiros até `expires_at` (negativo se já passou); `null` sem data. */
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
 * «Todos os workspaces» quando o token não tem recorte; senão a contagem com
 * os nomes que a lista de workspaces resolveu (sem nomes, só a contagem — a
 * lista pode ter falhado ou o workspace pode ter saído).
 */
export function textoDeWorkspaces(ids: string[] | null, nomes: ReadonlyMap<string, string>): string {
  if (ids == null) return "Todos os workspaces"
  if (ids.length === 0) return "Nenhum workspace"
  const resolvidos = ids.map(id => nomes.get(id)).filter((n): n is string => !!n)
  if (ids.length === 1) return resolvidos[0] ? `Workspace: ${resolvidos[0]}` : "1 workspace"
  const contagem = plural(ids.length, "workspace")
  return resolvidos.length > 0 ? `${contagem}: ${resolvidos.join(", ")}` : contagem
}

/** A lista guarda só os metadados: o segredo não fica no estado da página. */
function semSegredo(criado: ApiTokenCreated): ApiToken {
  const { id, name, token_prefix, scopes, workspace_ids, expires_at, last_used_at, revoked_at, created_at, status } = criado
  return { id, name, token_prefix, scopes, workspace_ids, expires_at, last_used_at, revoked_at, created_at, status }
}

const TokensDeAcesso = () => {
  const { status } = useSession()
  const [workspaces, setWorkspaces] = useState<IWorkspace[]>([])
  // A carga da lista é o `useFetchData`: `loading` (o `firstLoad` dele) cobre
  // só a PRIMEIRA carga (skeleton); `refreshing` é a recarga, com a lista na
  // tela, opaca, e o botão girando. O gate de sessão também é dele.
  //
  // Sem o ramo de erro, falha de rede caía no vazio de primeiro uso — a tela
  // mentiria, dizendo que não há tokens quando não conseguiu carregar. O
  // cartão de erro só vale sem carga aceita (`atualizadoEm == null`); recarga
  // que falha sobre lista pronta mantém o que havia e avisa por toast
  // (contrato §3.2).
  const {
    data, firstLoad: loading, refreshing, error, atualizadoEm, refetch, setData: setTokens,
  } = useFetchData(() => GisFlowService.listApiTokens(), "Não foi possível carregar os tokens de acesso.", [], 0, {
    onErroComDados: mensagem => createToast.error("Não foi possível atualizar os tokens de acesso", mensagem),
  })
  const tokens = useMemo(() => data ?? [], [data])
  const loadError = error != null && atualizadoEm == null
  const [createOpen, setCreateOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<ApiToken | null>(null)

  // Só para traduzir ids em nomes (cartões e caixas do diálogo). Falhar aqui
  // não é motivo para quebrar a tela: sem nomes, o cartão mostra a contagem.
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
    // Mais recente primeiro, como a listagem do backend.
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

  // Subtítulo do cabeçalho: o escopo da tela; com tokens, a contagem entra na
  // frente. O zero some (contrato §7) — «0 ativos» não ajuda ninguém.
  function textoDoSubtitulo(): string {
    if (!hasTokens) return ESCOPO_DA_TELA
    const partes = [plural(tokens.length, "token")]
    if (ativos > 0) partes.push(plural(ativos, "ativo"))
    return `${partes.join(" · ")} — valem só para o que a sua conta já pode fazer`
  }

  // Selo de status: sempre traduzido, valor cru em `data-status`. Pares
  // canônicos do contrato §6 — verde (ativo), âmbar (a vencer), vermelho
  // (expirado); revogado é neutro, porque não é falha nem aviso.
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
            // Revogado não se revoga de novo; expirado ainda pode ser revogado
            // (deixa de contar como existente para quem audita).
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
      {/* Cabeçalho fixo do contrato §1: título + subtítulo de escopo à esquerda,
          ações à direita (Atualizar em ghost e Novo token como única primária).
          Só duas ações — cabem na linha também no telefone, sem menu ⋯. */}
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-foreground">Tokens de acesso</h1>
          {/* Região viva estável: o `aria-live` fica no contêiner, que sobrevive
              à troca Skeleton↔texto, para o leitor de tela anunciar a contagem
              quando ela muda (ex.: após criar ou revogar). */}
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

      {/* Precedência do contrato §3: carregando → erro (só na 1ª carga) →
          primeiro uso → conteúdo. */}
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

      {/* Montado só enquanto aberto: o formulário nasce limpo a cada abertura e
          o segredo do passo 2 sai da memória junto com o diálogo. */}
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
