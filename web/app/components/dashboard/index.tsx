"use client"

import { Suspense, useCallback, useMemo, useRef } from "react"
import { TbArrowRight } from "react-icons/tb"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"
import PageRoot from "../page-root"
import { montarAtencao, textoDeVazio, type AttentionAction, type AttentionItem } from "../observability/atencao"
import { AtencaoLista } from "../observability/atencao-lista"
import { GraficoPorDia } from "../observability/grafico-por-dia"
import { Indicadores } from "../observability/indicadores"
import { CabecalhoDoDashboard } from "./cabecalho"
import type { Period } from "./dashboard-url"
import { AvisoDeSecao, ErroDoPainel, SkeletonDoDashboard, VazioDePrimeiroUso } from "./estados"
import { proximas } from "./proximas"
import { ProximasLista } from "./proximas-lista"
import { SaudeHero } from "./saude-hero"
import { tomDeSaude } from "./saude"
import { useDashboardDados } from "./use-dashboard-dados"
import { useDashboardUrl } from "./use-dashboard-url"

/**
 * Dashboard (docs/specs/dashboard.md §3.1) — overview for the system
 * administrator (route restricted to admins for now; the post-login landing
 * became the Home `/`, with the globe). This file
 * only orchestrates: the scope lives in the URL (`useDashboardUrl`) + in `WorkspaceContext`,
 * the data in the scoped hook (`useDashboardDados`), the pure logic in the
 * neighboring modules, and each block decides its own text. Reuses `indicadores`,
 * `grafico-por-dia` and `atencao-lista` from History — the same family, without
 * the interactive surface.
 *
 * The `Suspense` is required by `useSearchParams` (inside `useDashboardUrl`) in
 * the static build, as in the sibling pages.
 */
export default function DashboardView() {
  return (
    <Suspense fallback={<PageRoot><SkeletonDoDashboard /></PageRoot>}>
      <Dashboard />
    </Suspense>
  )
}

function Dashboard() {
  const router = useViewTransitionRouter()
  const { current, workspaces, canEdit, loading } = useWorkspace()
  const { escopo, setEscopo, periodo, setPeriodo } = useDashboardUrl()

  // The scope flows down to the hook already resolved: `null` = "todos" (no
  // `workspace_id`), otherwise the active workspace's id. So the hook reloads
  // when the scope changes AND when `current` changes in the active scope, but
  // not when `current` changes in "todos" (where `escopoWorkspaceId` is always
  // `null`), as the spec asks — without the hook knowing about the context.
  //
  // While the workspace list is loading, the "ativo" scope has no id yet:
  // `undefined` tells the hook NOT to fetch (keeps the skeleton) instead of
  // fetching "todos" for an instant and flashing the wrong scope. The trigger is
  // `loading` (not `current == null`): a user with NO workspace at all would
  // never have `current`, and triggering on it would leave the skeleton forever
  // — with `loading`, once loading ends the "ativo" scope becomes `null`
  // (→ "todos"), which is what they can see.
  const scopeWorkspaceId = escopo === "todos" ? null : loading ? undefined : (current?.id_hash ?? null)
  const dados = useDashboardDados(scopeWorkspaceId, periodo)
  const { metrics, workflows, runs } = dados

  // ── Attention + health ──────────────────────────────────────────────────────
  // The workflow's origin comes from the listing (the metrics don't carry it):
  // that is what lets the alert say the workflow belongs to the assistant.
  const originByWorkflow = useMemo(() => {
    const m = new Map<string, string | null | undefined>()
    for (const wf of workflows) m.set(wf.id_hash, wf.origem)
    return m
  }, [workflows])

  const atencao = useMemo(
    () => montarAtencao({
      metrics,
      executores: dados.executores,
      origemDoWorkflow: hash => originByWorkflow.get(hash),
    }),
    [metrics, dados.executores, originByWorkflow],
  )
  const temAtencao = atencao.length > 0
  const tom = tomDeSaude(metrics?.now, temAtencao)
  const attentionEmptyText = useMemo(() => textoDeVazio(metrics), [metrics])

  // Count per type of the list already built, so the verdict can say "2 workflows
  // falhando"/"1 executor no teto" (§3.4) without rereading `top_failing`. Stuck
  // runs are not included: they have their own reason in health and would be
  // counted twice.
  const attentionSummary = useMemo(() => ({
    falhas: atencao.filter(i => i.tipo === "falhas").length,
    saturado: atencao.filter(i => i.tipo === "saturado").length,
  }), [atencao])
  // Scope with workflows but no run at all in the period (§3.10): the calm
  // state becomes "nada rodando ainda". The first-use empty state (no workflows) is another.
  const semExecucoes = (metrics?.total_runs ?? 0) === 0

  // ── Workspace label (only in the "todos" scope) ─────────────────────────────
  // The join from spec §3.5/§3.6: `workflow_hash → Workflow.id_hash → workspace_id →
  // WorkspaceContext`. Built from `workflows` (already fetched for Upcoming)
  // and from `now.stuck` (which maps run_id → workflow_hash). Not resolved →
  // no label, never invents one.
  const nameByWorkspaceId = useMemo(() => {
    const m = new Map<string, string>()
    for (const w of workspaces) m.set(w.id_hash, w.name)
    return m
  }, [workspaces])

  const workspaceIdByWorkflow = useMemo(() => {
    const m = new Map<string, string | undefined>()
    for (const wf of workflows) m.set(wf.id_hash, wf.workspace_id)
    return m
  }, [workflows])

  const workflowHashByRun = useMemo(() => {
    const m = new Map<string, string>()
    for (const s of metrics?.now?.stuck ?? []) m.set(s.run_id, s.workflow_hash)
    return m
  }, [metrics])

  // Workspace name of a workflow, via the join chain. Used directly by
  // Upcoming (which receives `workspace_id`).
  const nomeDoWorkspace = useCallback((workspaceId: string | null | undefined): string | null => {
    if (!workspaceId) return null
    return nameByWorkspaceId.get(workspaceId) ?? null
  }, [nameByWorkspaceId])

  // In the "todos" scope, prefixes each attention item's `detalhe` with the
  // workspace label (History's attention component has no slot of its own,
  // and changing it would mean reinventing it). The workflow comes from
  // `acao`: failures carry `workflowHash`; a stuck run carries `runId`, which
  // `now.stuck` resolves to the hash. An executor at its ceiling has no workflow → no label.
  const attentionItems = useMemo<AttentionItem[]>(() => {
    if (escopo !== "todos") return atencao
    return atencao.map(item => {
      let hash: string | undefined
      if (item.acao.tipo === "filtrar-workflow") hash = item.acao.workflowHash
      else if (item.acao.tipo === "abrir-execucao") hash = workflowHashByRun.get(item.acao.runId)
      const nome = hash ? nomeDoWorkspace(workspaceIdByWorkflow.get(hash)) : null
      return nome ? { ...item, detalhe: `«${nome}» · ${item.detalhe}` } : item
    })
  }, [escopo, atencao, workflowHashByRun, workspaceIdByWorkflow, nomeDoWorkspace])

  // ── Upcoming runs ───────────────────────────────────────────────────────────
  const upcomingList = useMemo(() => proximas(workflows), [workflows])

  // ── Action routing ──────────────────────────────────────────────────────────
  // "&workspace=" is only added when the dashboard is scoped to a workspace; in
  // "todos" the sibling screens open unsliced. Derives from the SAME id the hook
  // fetched (coerces the "loading" `undefined` to `null`) — the actions are only
  // clickable in the content state, when the scope is already resolved.
  const workspaceQuery = scopeWorkspaceId ?? null
  const workspaceSuffix = workspaceQuery ? `&workspace=${encodeURIComponent(workspaceQuery)}` : ""

  const viewInProgress = useCallback(() => {
    router.push(`/observability?status=running${workspaceSuffix}`)
  }, [router, workspaceSuffix])

  const abrirExecucao = useCallback((runId: string) => {
    router.push(`/observability/run/${runId}`)
  }, [router])

  const onAttentionAction = useCallback((acao: AttentionAction) => {
    switch (acao.tipo) {
      case "abrir-execucao":
        router.push(`/observability/run/${acao.runId}`)
        break
      case "filtrar-workflow":
        // The default view (runs) applies `workflow` + `status`; the
        // "workflows" view ignores both and would land on an unfiltered list.
        // `&workspace=` preserves the active scope (empty in "todos").
        router.push(`/observability?workflow=${encodeURIComponent(acao.workflowHash)}&status=${acao.status}${workspaceSuffix}`)
        break
      case "abrir-executor":
        router.push("/executores")
        break
    }
  }, [router, workspaceSuffix])

  const viewInHistory = useCallback(() => {
    router.push(workspaceQuery ? `/observability?workspace=${encodeURIComponent(workspaceQuery)}` : "/observability")
  }, [router, workspaceQuery])

  // The `/workflow/[id]` editor is the heaviest route; warm it up on first
  // hover, as in Projects. The `Set` avoids repeating the call on the same row.
  const openWorkflow = useCallback((id: string) => router.push(`/workflow/${id}`), [router])
  const prefetched = useRef<Set<string>>(new Set())
  const prefetchWorkflow = useCallback((id: string) => {
    if (prefetched.current.has(id)) return
    prefetched.current.add(id)
    router.prefetch(`/workflow/${id}`)
  }, [router])

  const createWorkflow = useCallback(() => router.push("/workflow/create"), [router])
  const atualizar = useCallback(() => dados.recarregar({ force: true }), [dados])
  const tentarDeNovo = useCallback(() => dados.recarregar(), [dados])

  // ── Screen states (§3.10) ───────────────────────────────────────────────────
  const carregando = dados.carregando
  const hasError = !carregando && dados.erroEspinha != null
  // Nothing has run yet: no workflow, no recent run and no run in the
  // period. The three together rule out the "0 in the period" of a workspace
  // that only had old runs. The empty lists only count if they REALLY loaded:
  // a failure in `workflows`/`runs` also leaves them empty, and without this
  // guard a network error would paint the "first use" invitation for someone
  // who already has projects.
  const firstUse =
    !carregando && !hasError && workflows.length === 0 && runs.length === 0 && (metrics?.total_runs ?? 0) === 0
    && !dados.falhas.workflows && !dados.falhas.runs
  const conteudo = !carregando && !hasError && !firstUse

  return (
    <PageRoot>
      <CabecalhoDoDashboard
        escopo={escopo}
        onEscopo={setEscopo}
        periodo={periodo}
        onPeriodo={setPeriodo}
        workspaceNome={current?.name ?? null}
        workspaces={workspaces.length}
        ativos={metrics?.active_workflows ?? null}
        atualizando={dados.atualizando}
        onAtualizar={atualizar}
      />

      {carregando && <SkeletonDoDashboard />}

      {hasError && <ErroDoPainel mensagem={dados.erroEspinha!} onTentar={tentarDeNovo} />}

      {firstUse && <VazioDePrimeiroUso canEdit={canEdit} onCriar={createWorkflow} />}

      {conteudo && (
        <>
          <SaudeHero
            now={metrics?.now}
            tom={tom}
            resumo={attentionSummary}
            semExecucoes={semExecucoes}
            escopo={escopo}
            workspaceId={current?.id_hash ?? null}
            carregando={carregando}
            onVerEmAndamento={viewInProgress}
            onAbrirPresa={abrirExecucao}
          />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <AtencaoLista
              itens={attentionItems}
              carregando={carregando}
              vazio={attentionEmptyText}
              onAcao={onAttentionAction}
              falha={dados.falhas.metrics ? "Não foi possível reler o painel." : undefined}
            />
            <div className="flex flex-col gap-2">
              {dados.falhas.workflows && (
                <AvisoDeSecao onTentar={tentarDeNovo}>Não foi possível carregar as próximas execuções.</AvisoDeSecao>
              )}
              <ProximasLista
                workflows={upcomingList}
                escopo={escopo}
                nomeDoWorkspace={nomeDoWorkspace}
                onAbrir={openWorkflow}
                onPrefetch={prefetchWorkflow}
              />
            </div>
          </div>

          <PeriodSummary periodo={periodo} onVerNoHistorico={viewInHistory}>
            <Indicadores metrics={metrics} dias={dados.dias} carregando={carregando} periodo={periodo} />
            <GraficoPorDia
              dias={dados.dias}
              periodo={periodo}
              carregando={carregando}
              falha={dados.falhas.dias ? "Não foi possível carregar o gráfico." : undefined}
            />
          </PeriodSummary>
        </>
      )}
    </PageRoot>
  )
}

/**
 * "Resumo do período · últimos N dias" (§3.1): the window chosen in the header
 * (period selector), only echoed in the eyebrow here. The "Ver no Histórico →"
 * above the reused indicators and chart — History's family, without the table.
 */
function PeriodSummary({ children, periodo, onVerNoHistorico }: { children: React.ReactNode; periodo: Period; onVerNoHistorico: () => void }) {
  return (
    <section aria-labelledby="resumo-titulo" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h2 id="resumo-titulo" className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
          Resumo do período · últimos {periodo} dias
        </h2>
        <button
          type="button"
          onClick={onVerNoHistorico}
          className="inline-flex items-center gap-1 rounded-sm text-xs font-medium text-primary underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
        >
          Ver no Histórico <TbArrowRight size={13} aria-hidden="true" />
        </button>
      </div>
      {children}
    </section>
  )
}
