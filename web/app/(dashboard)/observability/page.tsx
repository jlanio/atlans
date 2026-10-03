"use client"

import { Suspense, useCallback, useMemo, useRef } from "react"
import { useSession } from "next-auth/react"
import PageRoot from "@/app/components/page-root"
import { Button } from "@/app/components/ui/button"
import { Skeleton } from "@/app/components/ui/skeleton"
import { useWorkspace } from "@/context/WorkspaceContext"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { AgoraFaixa } from "@/app/components/observability/agora-faixa"
import { montarAtencao, textoDeVazio, type AttentionAction } from "@/app/components/observability/atencao"
import { AtencaoLista } from "@/app/components/observability/atencao-lista"
import { CabecalhoDoHistorico } from "@/app/components/observability/cabecalho"
import { Filtros } from "@/app/components/observability/filtros"
import { GraficoPorDia } from "@/app/components/observability/grafico-por-dia"
import { filtrosAtivos, type ViewKind } from "@/app/components/observability/historico-url"
import { Indicadores } from "@/app/components/observability/indicadores"
import { PainelExecucao } from "@/app/components/observability/painel-execucao"
import { TabelaExecucoes } from "@/app/components/observability/tabela-execucoes"
import { useExecucoes } from "@/app/components/observability/use-execucoes"
import { useHistoricoDados } from "@/app/components/observability/use-historico-dados"
import { useHistoricoUrl } from "@/app/components/observability/use-historico-url"
import { usePendingAcks, VisaoConfirmacoes } from "@/app/components/observability/visao-confirmacoes"
import { VisaoExecutores } from "@/app/components/observability/visao-executores"
import { VisaoWorkflows } from "@/app/components/observability/visao-workflows"
import { VisoesAbas, type ViewCounts } from "@/app/components/observability/visoes-abas"

/**
 * History (docs/specs/metrics-history.md §4.3). The page only composes: the
 * state lives in the URL, the data in the two hooks, and each block decides its
 * own text. The `Suspense` is required by `useSearchParams` in the static build.
 */
export default function HistoryPage() {
  return (
    <Suspense fallback={<PageRoot><PageSkeleton /></PageRoot>}>
      <HistoryView />
    </Suspense>
  )
}

function HistoryView() {
  const { data: session, status } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const habilitado = status === "authenticated"
  const { workspaces: myWorkspaces } = useWorkspace()

  const { estado, atualizar, abrirExecucao, fecharExecucao } = useHistoricoUrl()
  const dados = useHistoricoDados(estado, { habilitado })
  const execucoes = useExecucoes(estado, { habilitado })
  const acks = usePendingAcks({ enabled: isAdmin })

  // "Confirmações" is admin-only; the session resolves after the first render and
  // a URL pasted by an admin must not leave someone else on an empty tab.
  const visao: ViewKind = estado.visao === "confirmacoes" && !isAdmin ? "execucoes" : estado.visao

  // Workflow origin by hash: the alert metrics do not carry it, the per-workflow
  // inventory does — it is what gives the assistant badge in the attention list.
  const originByWorkflow = useMemo(() => {
    const m = new Map<string, string | null | undefined>()
    for (const wf of dados.workflows) m.set(wf.workflow_hash, wf.origem)
    return m
  }, [dados.workflows])

  const atencao = useMemo(
    () => montarAtencao({
      metrics: dados.metrics,
      executores: dados.executores,
      origemDoWorkflow: hash => originByWorkflow.get(hash),
    }),
    [dados.metrics, dados.executores, originByWorkflow],
  )

  // The "Assistente" chip also slices the "Por workflow" view. Here it is local:
  // the inventory comes whole in a single call, with no pagination to redo.
  const visibleWorkflows = useMemo(
    () => estado.assistente ? dados.workflows.filter(w => w.origem === "assistente") : dados.workflows,
    [dados.workflows, estado.assistente],
  )
  const attentionEmptyText = useMemo(() => textoDeVazio(dados.metrics), [dados.metrics])

  // Workspaces for the filter: the person's own, plus those that appear in the
  // workflow rows — for an admin, that is how other people's workspaces get into
  // the list. The options only grow: with a workspace chosen, `dados.workflows`
  // comes sliced by it, and without the memory the admin's select would lose the others.
  const seenWorkspaces = useRef(new Map<string, string>())
  const filterWorkspaces = useMemo(() => {
    const byId = seenWorkspaces.current
    for (const w of myWorkspaces) byId.set(w.id_hash, w.name)
    for (const wf of dados.workflows) {
      if (wf.workspace_id && !byId.has(wf.workspace_id)) byId.set(wf.workspace_id, wf.workspace_name ?? wf.workspace_id)
    }
    return [...byId].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name))
  }, [myWorkspaces, dados.workflows])
  const mostrarWorkspace = isAdmin || filterWorkspaces.length > 1

  // Friendly executor names for the Confirmações view, which only receives ids.
  const executorNames = useMemo(() => {
    const m: Record<string, string> = {}
    for (const e of dados.executores) if (e.executor_id) m[e.executor_id] = e.display_name
    return m
  }, [dados.executores])

  const contagens: ViewCounts = useMemo(() => ({
    execucoes: execucoes.total,
    workflows: dados.workflows.length || null,
    executores: dados.executores.length || null,
    // In confirmations what matters is the delay: the pill only appears (red)
    // when there is some, otherwise the number would be "how many are in flight now".
    confirmacoes: isAdmin && acks.atrasadas.length > 0 ? acks.atrasadas.length : null,
  }), [execucoes.total, dados.workflows.length, dados.executores.length, isAdmin, acks.atrasadas.length])

  const refreshAll = useCallback(() => {
    dados.recarregar()
    execucoes.recarregar()
  }, [dados, execucoes])

  const onAttentionAction = useCallback((acao: AttentionAction) => {
    switch (acao.tipo) {
      case "abrir-execucao":
        abrirExecucao(acao.runId)
        break
      case "filtrar-workflow":
        atualizar({ workflow: acao.workflowHash, status: acao.status, visao: "execucoes" })
        break
      case "abrir-executor":
        atualizar({ executor: acao.agentHost, visao: "execucoes" })
        break
    }
  }, [abrirExecucao, atualizar])

  const limparFiltros = useCallback(() => {
    atualizar({ status: null, workspace: null, workflow: null, executor: null, origem: null, q: "" })
  }, [atualizar])

  // The toast is here because this is where the API message arrives; the view only
  // needs to know whether to undo the switch. The list comes back with `force` so
  // the 45 s Redis cache does not return the old `active`.
  const alternarAtivo = useCallback(async (workflowHash: string, ativo: boolean) => {
    const res = await GisFlowService.setAdminWorkflowStatus(workflowHash, ativo)
    if (res.error || !res.data) {
      createToast.error("Não foi possível alterar o workflow", res.error?.message)
      return false
    }
    const nome = dados.workflows.find(w => w.workflow_hash === workflowHash)?.workflow_name
    createToast.success(ativo ? "Workflow ativado" : "Workflow desativado", nome ? `«${nome}»` : undefined)
    dados.recarregar()
    return true
  }, [dados])

  return (
    <PageRoot>
      <CabecalhoDoHistorico
        periodo={estado.periodo}
        onPeriodo={p => atualizar({ periodo: p })}
        carregando={dados.carregando}
        onAtualizar={refreshAll}
        comparandoCom={estado.periodo}
      />

      {dados.falhas.metrics && <Aviso>{dados.falhas.metrics}{dados.metrics && " Mostrando a última leitura."}</Aviso>}

      <AgoraFaixa
        now={dados.metrics?.now}
        carregando={dados.carregando}
        onVerEmAndamento={() => atualizar({ status: "running", visao: "execucoes" })}
        onAbrirPresa={abrirExecucao}
      />

      <Indicadores
        metrics={dados.metrics}
        dias={dados.dias}
        carregando={dados.carregando}
        periodo={dados.periodoDosDados}
      />

      {/* Two columns on desktop; below `lg` the chart comes first and the
          attention list right after — it is the one people read on the phone. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,1fr)]">
        <GraficoPorDia
          dias={dados.dias}
          periodo={dados.periodoDosDados}
          carregando={dados.carregando}
          falha={dados.falhas.dias}
        />
        <AtencaoLista
          itens={atencao}
          carregando={dados.carregando}
          vazio={attentionEmptyText}
          onAcao={onAttentionAction}
          falha={dados.falhas.executores}
        />
      </div>

      <div className="flex flex-col gap-3">
        <VisoesAbas
          visao={visao}
          onVisao={v => atualizar({ visao: v })}
          contagens={contagens}
          isAdmin={isAdmin}
          alerta={isAdmin && acks.atrasadas.length > 0}
        />

        <div id="visao-painel" role="tabpanel" aria-labelledby={`visao-aba-${visao}`} className="flex flex-col gap-3">
          {visao === "execucoes" && (
            <>
              <Filtros
                estado={estado}
                onEstado={atualizar}
                // The counts come from the metrics, which only know period,
                // workspace and workflow: with executor, origin or search active
                // the chip's number would belong to another list — better none.
                contagens={estado.executor || estado.origem || estado.q.trim() ? undefined : dados.metrics?.by_status}
                workspaces={filterWorkspaces}
                workflows={dados.workflows}
                executores={dados.executores}
                mostrarWorkspace={mostrarWorkspace}
              />
              <TabelaExecucoes
                runs={execucoes.runs}
                total={execucoes.total}
                hasMore={execucoes.hasMore}
                carregando={execucoes.carregando}
                carregandoMais={execucoes.carregandoMais}
                falhou={execucoes.falhou}
                filtrado={filtrosAtivos(estado) > 0}
                onCarregarMais={execucoes.carregarMais}
                onAbrir={abrirExecucao}
                onLimparFiltros={limparFiltros}
                onRecarregar={execucoes.recarregar}
                abertaId={estado.execucao}
              />
            </>
          )}

          {/* The workspace and workflow slices apply to the whole page
              (indicators, chart, attention and lists): outside the
              Execuções view, where the selects are, they at least need to be
              visible and removable. */}
          {visao !== "execucoes" && (estado.workspace || estado.workflow) && (
            <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              Filtrado por
              {estado.workspace && (
                <span>workspace <span className="font-medium text-foreground">«{filterWorkspaces.find(w => w.id === estado.workspace)?.name ?? estado.workspace}»</span></span>
              )}
              {estado.workflow && (
                <span>workflow <span className="font-medium text-foreground">«{dados.workflows.find(w => w.workflow_hash === estado.workflow)?.workflow_name ?? estado.workflow}»</span></span>
              )}
              <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => atualizar({ workspace: null, workflow: null })}>
                Limpar
              </Button>
            </p>
          )}

          {visao === "workflows" && (
            <>
              {dados.falhas.workflows && <Aviso>{dados.falhas.workflows}{dados.workflows.length > 0 && " Mostrando a última leitura."}</Aviso>}
              <VisaoWorkflows
                linhas={visibleWorkflows}
                carregando={dados.carregando}
                isAdmin={isAdmin}
                onVerExecucoes={hash => atualizar({ workflow: hash, visao: "execucoes" })}
                onAlternarAtivo={alternarAtivo}
              />
            </>
          )}

          {visao === "executores" && (
            <>
              {dados.falhas.executores && <Aviso>{dados.falhas.executores}{dados.executores.length > 0 && " Mostrando a última leitura."}</Aviso>}
              <VisaoExecutores
                linhas={dados.executores}
                carregando={dados.carregando}
                onVerExecucoes={host => atualizar({ executor: host, visao: "execucoes" })}
              />
            </>
          )}

          {visao === "confirmacoes" && (
            <VisaoConfirmacoes acks={acks} onAbrirExecucao={abrirExecucao} nomes={executorNames} />
          )}
        </div>
      </div>

      <PainelExecucao
        runId={estado.execucao}
        onFechar={fecharExecucao}
        onFiltrarWorkflow={hash => atualizar({ workflow: hash, visao: "execucoes" })}
      />
    </PageRoot>
  )
}

/** Partial failure: the block below keeps what it had; the notice says it is stale. */
function Aviso({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
      {children}
    </p>
  )
}

function PageSkeleton() {
  return (
    <div className="flex flex-col gap-4" role="status" aria-busy="true" aria-label="Carregando o Histórico">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-10 w-full" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" />)}
      </div>
      <Skeleton className="h-56 w-full" />
    </div>
  )
}
