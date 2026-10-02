"use client"

import { Suspense, useCallback, useMemo, useRef } from "react"
import { TbArrowRight } from "react-icons/tb"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"
import PageRoot from "../page-root"
import { montarAtencao, textoDeVazio, type AcaoDeAtencao, type ItemDeAtencao } from "../observability/atencao"
import { AtencaoLista } from "../observability/atencao-lista"
import { GraficoPorDia } from "../observability/grafico-por-dia"
import { Indicadores } from "../observability/indicadores"
import { CabecalhoDoDashboard } from "./cabecalho"
import type { Periodo } from "./dashboard-url"
import { AvisoDeSecao, ErroDoPainel, SkeletonDoDashboard, VazioDePrimeiroUso } from "./estados"
import { proximas } from "./proximas"
import { ProximasLista } from "./proximas-lista"
import { SaudeHero } from "./saude-hero"
import { tomDeSaude } from "./saude"
import { useDashboardDados } from "./use-dashboard-dados"
import { useDashboardUrl } from "./use-dashboard-url"

/**
 * Dashboard (docs/specs/dashboard.md §3.1) — visão geral do administrador do
 * sistema (rota restrita ao admin por enquanto; a landing pós-login virou a Home
 * `/`, com o globo). Este arquivo
 * só orquestra: o escopo mora na URL (`useDashboardUrl`) + no `WorkspaceContext`,
 * os dados no hook escopado (`useDashboardDados`), a lógica pura nos módulos ao
 * lado, e cada bloco decide o próprio texto. Reusa `indicadores`, `grafico-por-dia`
 * e `atencao-lista` do Histórico — a mesma família, sem a superfície interativa.
 *
 * O `Suspense` é exigido pelo `useSearchParams` (dentro de `useDashboardUrl`) na
 * build estática, como nas páginas irmãs.
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

  // O escopo desce resolvido para o hook: `null` = "todos" (sem `workspace_id`),
  // senão o id do workspace ativo. Assim o hook recarrega ao trocar o escopo E
  // ao trocar `current` no escopo ativo, mas não ao trocar `current` no "todos"
  // (onde `escopoWorkspaceId` é sempre `null`), como a spec pede — sem o hook
  // conhecer o context.
  //
  // Enquanto a lista de workspaces carrega, o escopo "ativo" ainda não tem id:
  // `undefined` diz ao hook para NÃO buscar (mantém o skeleton) em vez de buscar
  // "todos" por um instante e piscar o escopo errado. O gatilho é `loading` (não
  // `current == null`): um usuário SEM workspace nenhum nunca teria `current`, e
  // gatilhar por ele deixaria o skeleton para sempre — com `loading`, ao terminar
  // a carga o escopo "ativo" vira `null` (→ "todos"), que é o que ele pode ver.
  const escopoWorkspaceId = escopo === "todos" ? null : loading ? undefined : (current?.id_hash ?? null)
  const dados = useDashboardDados(escopoWorkspaceId, periodo)
  const { metrics, workflows, runs } = dados

  // ── Atenção + saúde ─────────────────────────────────────────────────────────
  // A origem do fluxo vem da listagem (as métricas não a carregam): é o que
  // permite ao alerta dizer que o fluxo é do assistente.
  const origemPorWorkflow = useMemo(() => {
    const m = new Map<string, string | null | undefined>()
    for (const wf of workflows) m.set(wf.id_hash, wf.origem)
    return m
  }, [workflows])

  const atencao = useMemo(
    () => montarAtencao({
      metrics,
      executores: dados.executores,
      origemDoWorkflow: hash => origemPorWorkflow.get(hash),
    }),
    [metrics, dados.executores, origemPorWorkflow],
  )
  const temAtencao = atencao.length > 0
  const tom = tomDeSaude(metrics?.now, temAtencao)
  const vazioDaAtencao = useMemo(() => textoDeVazio(metrics), [metrics])

  // Contagem por tipo da lista já montada, para o veredito dizer "2 workflows
  // falhando"/"1 executor no teto" (§3.4) sem reler `top_failing`. As presas
  // não entram: têm motivo próprio na saúde e seriam recontadas.
  const resumoDaAtencao = useMemo(() => ({
    falhas: atencao.filter(i => i.tipo === "falhas").length,
    saturado: atencao.filter(i => i.tipo === "saturado").length,
  }), [atencao])
  // Escopo com workflows mas sem nenhuma execução no período (§3.10): o calmo
  // vira "nada rodando ainda". O vazio de primeiro uso (sem workflows) é outro.
  const semExecucoes = (metrics?.total_runs ?? 0) === 0

  // ── Etiqueta de workspace (só no escopo "todos") ────────────────────────────
  // O join da spec §3.5/§3.6: `workflow_hash → Workflow.id_hash → workspace_id →
  // WorkspaceContext`. Montado a partir de `workflows` (já buscado para as
  // Próximas) e de `now.stuck` (que casa run_id → workflow_hash). Não resolveu →
  // sem etiqueta, nunca inventa.
  const nomePorWorkspaceId = useMemo(() => {
    const m = new Map<string, string>()
    for (const w of workspaces) m.set(w.id_hash, w.name)
    return m
  }, [workspaces])

  const workspaceIdPorWorkflow = useMemo(() => {
    const m = new Map<string, string | undefined>()
    for (const wf of workflows) m.set(wf.id_hash, wf.workspace_id)
    return m
  }, [workflows])

  const workflowHashPorRun = useMemo(() => {
    const m = new Map<string, string>()
    for (const s of metrics?.now?.stuck ?? []) m.set(s.run_id, s.workflow_hash)
    return m
  }, [metrics])

  // Nome do workspace de um workflow, pela cadeia do join. Usado pelas Próximas
  // (recebe `workspace_id`) diretamente.
  const nomeDoWorkspace = useCallback((workspaceId: string | null | undefined): string | null => {
    if (!workspaceId) return null
    return nomePorWorkspaceId.get(workspaceId) ?? null
  }, [nomePorWorkspaceId])

  // No escopo "todos", prefixa o `detalhe` de cada item de atenção com a
  // etiqueta do workspace (o componente de atenção do Histórico não tem um
  // slot próprio, e mexer nele seria reinventá-lo). O workflow vem do `acao`:
  // falhas trazem o `workflowHash`; presa traz o `runId`, que `now.stuck`
  // resolve para o hash. Executor no teto não tem workflow → sem etiqueta.
  const itensDeAtencao = useMemo<ItemDeAtencao[]>(() => {
    if (escopo !== "todos") return atencao
    return atencao.map(item => {
      let hash: string | undefined
      if (item.acao.tipo === "filtrar-workflow") hash = item.acao.workflowHash
      else if (item.acao.tipo === "abrir-execucao") hash = workflowHashPorRun.get(item.acao.runId)
      const nome = hash ? nomeDoWorkspace(workspaceIdPorWorkflow.get(hash)) : null
      return nome ? { ...item, detalhe: `«${nome}» · ${item.detalhe}` } : item
    })
  }, [escopo, atencao, workflowHashPorRun, workspaceIdPorWorkflow, nomeDoWorkspace])

  // ── Próximas execuções ──────────────────────────────────────────────────────
  const listaProximas = useMemo(() => proximas(workflows), [workflows])

  // ── Roteamento das ações ────────────────────────────────────────────────────
  // O "&workspace=" só entra quando o painel está escopado a um workspace; no
  // "todos" as telas irmãs abrem sem recorte. Deriva do MESMO id que o hook
  // buscou (coage o `undefined` de "carregando" para `null`) — as ações só são
  // clicáveis no estado de conteúdo, quando o escopo já está resolvido.
  const workspaceQuery = escopoWorkspaceId ?? null
  const sufixoWorkspace = workspaceQuery ? `&workspace=${encodeURIComponent(workspaceQuery)}` : ""

  const verEmAndamento = useCallback(() => {
    router.push(`/observability?status=running${sufixoWorkspace}`)
  }, [router, sufixoWorkspace])

  const abrirExecucao = useCallback((runId: string) => {
    router.push(`/observability/run/${runId}`)
  }, [router])

  const aoAcaoDeAtencao = useCallback((acao: AcaoDeAtencao) => {
    switch (acao.tipo) {
      case "abrir-execucao":
        router.push(`/observability/run/${acao.runId}`)
        break
      case "filtrar-workflow":
        // Visão padrão (execuções) aplica `workflow` + `status`; a visão
        // "workflows" ignora ambos e cairia numa lista sem filtro. `&workspace=`
        // preserva o escopo ativo (vazio no "todos").
        router.push(`/observability?workflow=${encodeURIComponent(acao.workflowHash)}&status=${acao.status}${sufixoWorkspace}`)
        break
      case "abrir-executor":
        router.push("/executores")
        break
    }
  }, [router, sufixoWorkspace])

  const verNoHistorico = useCallback(() => {
    router.push(workspaceQuery ? `/observability?workspace=${encodeURIComponent(workspaceQuery)}` : "/observability")
  }, [router, workspaceQuery])

  // Editor `/workflow/[id]` é a rota mais pesada; aquece no primeiro hover,
  // como em Projetos. O `Set` evita repetir a chamada na mesma linha.
  const abrirWorkflow = useCallback((id: string) => router.push(`/workflow/${id}`), [router])
  const aquecidos = useRef<Set<string>>(new Set())
  const prefetchWorkflow = useCallback((id: string) => {
    if (aquecidos.current.has(id)) return
    aquecidos.current.add(id)
    router.prefetch(`/workflow/${id}`)
  }, [router])

  const criarWorkflow = useCallback(() => router.push("/workflow/create"), [router])
  const atualizar = useCallback(() => dados.recarregar({ force: true }), [dados])
  const tentarDeNovo = useCallback(() => dados.recarregar(), [dados])

  // ── Estados da tela (§3.10) ─────────────────────────────────────────────────
  const carregando = dados.carregando
  const comErro = !carregando && dados.erroEspinha != null
  // Nada rodou ainda: sem workflow, sem execução recente e sem execução no
  // período. Os três juntos afastam o "0 no período" de um workspace que só
  // teve execuções antigas. As listas vazias só valem se REALMENTE carregaram:
  // uma falha em `workflows`/`runs` também as deixa vazias, e sem esta guarda um
  // erro de rede pintaria o convite de "primeiro uso" para quem já tem projetos.
  const primeiroUso =
    !carregando && !comErro && workflows.length === 0 && runs.length === 0 && (metrics?.total_runs ?? 0) === 0
    && !dados.falhas.workflows && !dados.falhas.runs
  const conteudo = !carregando && !comErro && !primeiroUso

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

      {comErro && <ErroDoPainel mensagem={dados.erroEspinha!} onTentar={tentarDeNovo} />}

      {primeiroUso && <VazioDePrimeiroUso canEdit={canEdit} onCriar={criarWorkflow} />}

      {conteudo && (
        <>
          <SaudeHero
            now={metrics?.now}
            tom={tom}
            resumo={resumoDaAtencao}
            semExecucoes={semExecucoes}
            escopo={escopo}
            workspaceId={current?.id_hash ?? null}
            carregando={carregando}
            onVerEmAndamento={verEmAndamento}
            onAbrirPresa={abrirExecucao}
          />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <AtencaoLista
              itens={itensDeAtencao}
              carregando={carregando}
              vazio={vazioDaAtencao}
              onAcao={aoAcaoDeAtencao}
              falha={dados.falhas.metrics ? "Não foi possível reler o painel." : undefined}
            />
            <div className="flex flex-col gap-2">
              {dados.falhas.workflows && (
                <AvisoDeSecao onTentar={tentarDeNovo}>Não foi possível carregar as próximas execuções.</AvisoDeSecao>
              )}
              <ProximasLista
                workflows={listaProximas}
                escopo={escopo}
                nomeDoWorkspace={nomeDoWorkspace}
                onAbrir={abrirWorkflow}
                onPrefetch={prefetchWorkflow}
              />
            </div>
          </div>

          <ResumoDoPeriodo periodo={periodo} onVerNoHistorico={verNoHistorico}>
            <Indicadores metrics={metrics} dias={dados.dias} carregando={carregando} periodo={periodo} />
            <GraficoPorDia
              dias={dados.dias}
              periodo={periodo}
              carregando={carregando}
              falha={dados.falhas.dias ? "Não foi possível carregar o gráfico." : undefined}
            />
          </ResumoDoPeriodo>
        </>
      )}
    </PageRoot>
  )
}

/**
 * "Resumo do período · últimos N dias" (§3.1): a janela escolhida no cabeçalho
 * (seletor de período), aqui só ecoada no eyebrow. O "Ver no Histórico →" acima
 * dos indicadores e do gráfico reusados — família do Histórico, sem tabela.
 */
function ResumoDoPeriodo({ children, periodo, onVerNoHistorico }: { children: React.ReactNode; periodo: Periodo; onVerNoHistorico: () => void }) {
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
