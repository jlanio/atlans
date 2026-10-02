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
import { montarAtencao, textoDeVazio, type AcaoDeAtencao } from "@/app/components/observability/atencao"
import { AtencaoLista } from "@/app/components/observability/atencao-lista"
import { CabecalhoDoHistorico } from "@/app/components/observability/cabecalho"
import { Filtros } from "@/app/components/observability/filtros"
import { GraficoPorDia } from "@/app/components/observability/grafico-por-dia"
import { filtrosAtivos, type Visao } from "@/app/components/observability/historico-url"
import { Indicadores } from "@/app/components/observability/indicadores"
import { PainelExecucao } from "@/app/components/observability/painel-execucao"
import { TabelaExecucoes } from "@/app/components/observability/tabela-execucoes"
import { useExecucoes } from "@/app/components/observability/use-execucoes"
import { useHistoricoDados } from "@/app/components/observability/use-historico-dados"
import { useHistoricoUrl } from "@/app/components/observability/use-historico-url"
import { usePendingAcks, VisaoConfirmacoes } from "@/app/components/observability/visao-confirmacoes"
import { VisaoExecutores } from "@/app/components/observability/visao-executores"
import { VisaoWorkflows } from "@/app/components/observability/visao-workflows"
import { VisoesAbas, type ContagensDasVisoes } from "@/app/components/observability/visoes-abas"

/**
 * Histórico (docs/specs/metrics-history.md §4.3). A página só compõe: o
 * estado mora na URL, os dados nos dois hooks, e cada bloco decide o próprio
 * texto. O `Suspense` é exigido pelo `useSearchParams` na build estática.
 */
export default function HistoricoPage() {
  return (
    <Suspense fallback={<PageRoot><EsqueletoDaPagina /></PageRoot>}>
      <Historico />
    </Suspense>
  )
}

function Historico() {
  const { data: session, status } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const habilitado = status === "authenticated"
  const { workspaces: meusWorkspaces } = useWorkspace()

  const { estado, atualizar, abrirExecucao, fecharExecucao } = useHistoricoUrl()
  const dados = useHistoricoDados(estado, { habilitado })
  const execucoes = useExecucoes(estado, { habilitado })
  const acks = usePendingAcks({ enabled: isAdmin })

  // "Confirmações" é admin-only; a sessão resolve depois do primeiro render e
  // uma URL colada por um admin não pode deixar outra pessoa numa aba vazia.
  const visao: Visao = estado.visao === "confirmacoes" && !isAdmin ? "execucoes" : estado.visao

  // Origem do fluxo por hash: as métricas do alerta não a trazem, o
  // inventário por workflow sim — é o que dá o selo do assistente na atenção.
  const origemPorWorkflow = useMemo(() => {
    const m = new Map<string, string | null | undefined>()
    for (const wf of dados.workflows) m.set(wf.workflow_hash, wf.origem)
    return m
  }, [dados.workflows])

  const atencao = useMemo(
    () => montarAtencao({
      metrics: dados.metrics,
      executores: dados.executores,
      origemDoWorkflow: hash => origemPorWorkflow.get(hash),
    }),
    [dados.metrics, dados.executores, origemPorWorkflow],
  )

  // O chip "Assistente" também recorta a visão "Por workflow". Aqui é local: o
  // inventário vem inteiro numa chamada só, sem paginação a refazer.
  const workflowsVisiveis = useMemo(
    () => estado.assistente ? dados.workflows.filter(w => w.origem === "assistente") : dados.workflows,
    [dados.workflows, estado.assistente],
  )
  const vazioDaAtencao = useMemo(() => textoDeVazio(dados.metrics), [dados.metrics])

  // Workspaces do filtro: os da pessoa, mais os que aparecem nas linhas de
  // workflow — para admin, é assim que os workspaces alheios entram na lista.
  // As opções só crescem: com um workspace escolhido, `dados.workflows` vem
  // recortado por ele, e sem a memória o select do admin perderia os outros.
  const workspacesVistos = useRef(new Map<string, string>())
  const workspacesDoFiltro = useMemo(() => {
    const porId = workspacesVistos.current
    for (const w of meusWorkspaces) porId.set(w.id_hash, w.name)
    for (const wf of dados.workflows) {
      if (wf.workspace_id && !porId.has(wf.workspace_id)) porId.set(wf.workspace_id, wf.workspace_name ?? wf.workspace_id)
    }
    return [...porId].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name))
  }, [meusWorkspaces, dados.workflows])
  const mostrarWorkspace = isAdmin || workspacesDoFiltro.length > 1

  // Nome amigável dos executores para a visão Confirmações, que só recebe ids.
  const nomesDosExecutores = useMemo(() => {
    const m: Record<string, string> = {}
    for (const e of dados.executores) if (e.executor_id) m[e.executor_id] = e.display_name
    return m
  }, [dados.executores])

  const contagens: ContagensDasVisoes = useMemo(() => ({
    execucoes: execucoes.total,
    workflows: dados.workflows.length || null,
    executores: dados.executores.length || null,
    // Em confirmações o que importa é o atraso: a pílula só aparece (vermelha)
    // quando há alguma, senão o número seria "quantas estão em voo agora".
    confirmacoes: isAdmin && acks.atrasadas.length > 0 ? acks.atrasadas.length : null,
  }), [execucoes.total, dados.workflows.length, dados.executores.length, isAdmin, acks.atrasadas.length])

  const atualizarTudo = useCallback(() => {
    dados.recarregar()
    execucoes.recarregar()
  }, [dados, execucoes])

  const aoAcaoDeAtencao = useCallback((acao: AcaoDeAtencao) => {
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

  // O toast é daqui porque é aqui que a mensagem da API chega; a visão só
  // precisa saber se desfaz o interruptor. A lista volta com `force` para o
  // Redis de 45 s não devolver o `active` antigo.
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
        onAtualizar={atualizarTudo}
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

      {/* Duas colunas no desktop; abaixo de `lg` o gráfico vem primeiro e a
          lista de atenção logo depois — ela é a que se lê no telefone. */}
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
          vazio={vazioDaAtencao}
          onAcao={aoAcaoDeAtencao}
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
                // As contagens vêm das métricas, que só conhecem período,
                // workspace e workflow: com executor, origem ou busca ativos o
                // número do chip seria de outra lista — melhor nenhum.
                contagens={estado.executor || estado.origem || estado.q.trim() ? undefined : dados.metrics?.by_status}
                workspaces={workspacesDoFiltro}
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

          {/* Os recortes por workspace e por workflow valem para a página
              inteira (indicadores, gráfico, atenção e listas): fora da visão
              Execuções, onde ficam os selects, precisam ao menos ser vistos e
              removíveis. */}
          {visao !== "execucoes" && (estado.workspace || estado.workflow) && (
            <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              Filtrado por
              {estado.workspace && (
                <span>workspace <span className="font-medium text-foreground">«{workspacesDoFiltro.find(w => w.id === estado.workspace)?.name ?? estado.workspace}»</span></span>
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
                linhas={workflowsVisiveis}
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
            <VisaoConfirmacoes acks={acks} onAbrirExecucao={abrirExecucao} nomes={nomesDosExecutores} />
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

/** Falha parcial: o bloco abaixo continua com o que tinha; o aviso diz que está velho. */
function Aviso({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
      {children}
    </p>
  )
}

function EsqueletoDaPagina() {
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
