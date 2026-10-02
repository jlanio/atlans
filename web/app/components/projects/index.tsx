"use client"

import {
  Suspense, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode,
} from "react"
import { TbFolderOpen, TbFolderPlus, TbGripVertical } from "react-icons/tb"
import type { IParamSchema, IWorkflow, IWorkflowGroup } from "@/service/types"
import { GisFlowService } from "@/service/GisFlowService"
import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"
import { moveTargets, useWorkspace } from "@/context/WorkspaceContext"
import { useActiveRuns, type RunningRun } from "@/context/ActiveRunsContext"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import PageRoot from "../page-root"
import { Button } from "../ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog"
import ExecuteParamsDialog from "@/app/components/workflow/execute-params-dialog"
import PortalSettingsDialog from "@/app/components/workflow/PortalSettingsDialog"
import ConfigureProject from "./dialog-content/configure-project"
import CreateGroup from "./dialog-content/create-group"
import DeleteProject from "./dialog-content/delete-project"
import MoveWorkflowDialog from "./dialog-content/move-workflow"
import RenameGroup from "./dialog-content/rename-group"
import { CabecalhoDeProjetos, type ContagensDoCabecalho } from "./cabecalho"
import { derivarComoAnda, type ComoAnda } from "./como-anda"
import { ConfirmarDesativar } from "./confirmar-desativar"
import { ErroDeCarga, MetricasIndisponiveis, SemResultado, SkeletonDeProjetos, VazioPrimeiroUso } from "./estados"
import { BarraDeFiltros } from "./filtros-barra"
import { casaBusca, contarPorFiltro, ordenar, predicadoDoFiltro, type ContextoDeFiltro } from "./filtros"
import { derivarGatilho, resumirAgendamento, type Gatilho, type ResumoDoAgendamento } from "./gatilho"
import { GrupoSecao, textoDaContagemDoGrupo } from "./grupo-secao"
import { chaveDosColapsados, gravarColapsados, lerColapsados } from "./grupos-colapsados"
import { LinhaWorkflow } from "./linha-workflow"
import { moverGrupo } from "./ordem-dos-grupos"
import { filtrosAtivos } from "./projetos-url"
import { useProjetosDados } from "./use-projetos-dados"
import { useProjetosUrl } from "./use-projetos-url"

/**
 * Projetos (docs/specs/projects.md §3.1). Este arquivo só orquestra: o estado
 * de busca/chip/ordem mora na URL, os dados no hook, os runs vivos no
 * `ActiveRunsContext`, as permissões no `WorkspaceContext`; a lógica pura fica
 * nos módulos ao lado e cada bloco decide o próprio texto.
 *
 * O `Suspense` é exigido pelo `useSearchParams` na build estática — mesmo
 * motivo da página do Histórico.
 */
export default function ProjectActions() {
  return (
    <Suspense fallback={<PageRoot><SkeletonDeProjetos /></PageRoot>}>
      <Projetos />
    </Suspense>
  )
}

/** O que cada linha precisa e que só muda quando os dados mudam (não a cada tecla da busca). */
interface Derivados {
  gatilho: Gatilho
  resumo: ResumoDoAgendamento | null
  comoAnda: ComoAnda
}

function Projetos() {
  const router = useViewTransitionRouter()
  const { current: currentWorkspace, canEdit, canExecute, canManage, workspaces } = useWorkspace()
  // Execuções em andamento (polling global): vencem as métricas por serem
  // mais frescas, e são o que transforma o Executar em "Ver execução".
  const { runningRuns, refresh: refreshActiveRuns } = useActiveRuns()
  const { estado, atualizar, limparFiltros } = useProjetosUrl()
  const dados = useProjetosDados()
  const { workflows, grupos, metricas, metricasIndisponiveis, definirWorkflows, definirGrupos, recarregar } = dados

  // ── Grupos recolhidos ──────────────────────────────────────────────────────
  // O estado de recolhido sobrevive ao recarregamento — sem isso, quem recolhe
  // os grupos que não usa recolhe tudo de novo a cada visita. A leitura é num
  // efeito (e não no `useState` inicial) porque `localStorage` não existe no
  // render do servidor.
  const [recolhidos, setRecolhidos] = useState<Set<string>>(new Set())
  const chaveColapso = chaveDosColapsados(currentWorkspace?.id_hash)
  useEffect(() => {
    setRecolhidos(lerColapsados(chaveColapso))
  }, [chaveColapso])

  const alternarGrupo = useCallback((groupId: string) => {
    setRecolhidos(prev => {
      const next = new Set(prev)
      if (next.has(groupId)) next.delete(groupId)
      else next.add(groupId)
      gravarColapsados(chaveColapso, next)
      return next
    })
  }, [chaveColapso])

  function recolherTodos() {
    const next = new Set(grupos.map(g => g.id_hash))
    gravarColapsados(chaveColapso, next)
    setRecolhidos(next)
  }

  function expandirTodos() {
    const next = new Set<string>()
    gravarColapsados(chaveColapso, next)
    setRecolhidos(next)
  }

  const todosRecolhidos = grupos.length > 0 && grupos.every(g => recolhidos.has(g.id_hash))
  // ──────────────────────────────────────────────────────────────────────────

  // ── Derivações por workflow ────────────────────────────────────────────────
  const runPorHash = useMemo(
    () => new Map<string, RunningRun>(runningRuns.map(r => [r.workflowHash, r])),
    [runningRuns],
  )
  const gruposPorId = useMemo(() => new Map(grupos.map(g => [g.id_hash, g])), [grupos])

  // Relógio de minuto para os textos relativos ("há 4 min"). Sem ele, a frescura
  // dependia de um EFEITO COLATERAL do poll de métricas trocar a identidade de
  // `metricas` — se o poll não mudasse nada, os tempos congelavam. Só avança com
  // a aba visível (ninguém lê uma aba oculta) e um retorno ao foco recalcula na
  // hora, para o "há N min" não voltar defasado.
  const [minuto, setMinuto] = useState(0)
  useEffect(() => {
    const bump = () => { if (document.visibilityState === "visible") setMinuto(m => m + 1) }
    const timer = setInterval(bump, 60_000)
    document.addEventListener("visibilitychange", bump)
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", bump) }
  }, [])

  // Gatilho, agendamento e "como anda" de cada linha, recalculados a cada
  // mudança de DADOS ou do relógio de minuto — e não a cada render: as linhas
  // são memoizadas e recebem estes objetos por identidade, então uma tecla na
  // busca não pode recriá-los. `minuto` mantém os tempos relativos frescos por
  // conta própria, independente da cadência do poll de métricas.
  const derivados = useMemo(() => {
    const agora = new Date()
    const mapa = new Map<string, Derivados>()
    for (const wf of workflows) {
      mapa.set(wf.id_hash, {
        gatilho: derivarGatilho(wf),
        resumo: resumirAgendamento(wf.schedule, wf.flag_ative, agora),
        comoAnda: derivarComoAnda(wf, metricas?.get(wf.id_hash), runPorHash.get(wf.id_hash), metricasIndisponiveis, agora),
      })
    }
    return mapa
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflows, metricas, runPorHash, metricasIndisponiveis, minuto])

  const contexto = useMemo<ContextoDeFiltro>(() => {
    const comoAndaPorHash = new Map<string, ComoAnda>()
    const resumoDoAgendamentoPorHash = new Map<string, ResumoDoAgendamento | null>()
    for (const [hash, d] of derivados) {
      comoAndaPorHash.set(hash, d.comoAnda)
      resumoDoAgendamentoPorHash.set(hash, d.resumo)
    }
    return { comoAndaPorHash, resumoDoAgendamentoPorHash }
  }, [derivados])

  // Chips e subtítulo: sempre sobre a lista inteira.
  const contagens = useMemo(() => contarPorFiltro(workflows, contexto), [workflows, contexto])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Busca, chip, ordem ─────────────────────────────────────────────────────
  // PERF: useDeferredValue — o campo responde imediatamente enquanto a
  // filtragem é deferida para uma transição de baixa prioridade. Evita
  // travamento do caret ao digitar em listas grandes.
  const qDiferido = useDeferredValue(estado.q)
  const recorteAtivo = filtrosAtivos({ ...estado, q: qDiferido }) > 0

  const visiveis = useMemo(() => {
    const casaFiltro = predicadoDoFiltro(estado.filtro, contexto)
    return workflows.filter(wf => casaBusca(wf, gruposPorId, qDiferido) && casaFiltro(wf))
  }, [workflows, estado.filtro, contexto, gruposPorId, qDiferido])

  // Quantos casariam só com a busca: o "Há N com «q» sem o filtro" do vazio.
  const soComBusca = useMemo(
    () => workflows.filter(wf => casaBusca(wf, gruposPorId, qDiferido)).length,
    [workflows, gruposPorId, qDiferido],
  )

  const porGrupo = useMemo(() => {
    const mapa = new Map<string, IWorkflow[]>()
    for (const wf of visiveis) {
      if (!wf.group_id) continue
      const lista = mapa.get(wf.group_id) ?? []
      lista.push(wf)
      mapa.set(wf.group_id, lista)
    }
    for (const [id, lista] of mapa) mapa.set(id, ordenar(lista, estado.ordem, contexto))
    return mapa
  }, [visiveis, estado.ordem, contexto])

  const semGrupo = useMemo(
    () => ordenar(visiveis.filter(wf => !wf.group_id), estado.ordem, contexto),
    [visiveis, estado.ordem, contexto],
  )

  // Contagem do cabeçalho de cada seção: do grupo INTEIRO, não do recorte —
  // contada aqui, e não por `workflow_count`, porque a lista local já reflete
  // as movimentações otimistas antes de o servidor responder.
  const totais = useMemo(() => {
    const mapa = new Map<string | null, { total: number; ativos: number }>()
    for (const wf of workflows) {
      const chave = wf.group_id ?? null
      const t = mapa.get(chave) ?? { total: 0, ativos: 0 }
      t.total++
      if (wf.flag_ative) t.ativos++
      mapa.set(chave, t)
    }
    return mapa
  }, [workflows])
  const totalSemGrupo = totais.get(null) ?? { total: 0, ativos: 0 }

  // Com busca ou chip ativo, grupos sem nenhuma linha correspondente somem;
  // sem recorte, todos aparecem (inclusive vazios). Memoizado para não refiltrar
  // a cada render (ex.: cada tecla da busca).
  const gruposVisiveis = useMemo(
    () => recorteAtivo
      ? grupos.filter(g => (porGrupo.get(g.id_hash)?.length ?? 0) > 0)
      : grupos,
    [recorteAtivo, grupos, porGrupo],
  )
  // ──────────────────────────────────────────────────────────────────────────

  // ── Execução rápida ────────────────────────────────────────────────────────
  const [runningId, setRunningId] = useState<string | null>(null)
  const [preparandoId, setPreparandoId] = useState<string | null>(null)
  // Alvo do diálogo de parâmetros: o schema vem junto porque a LISTAGEM não o
  // traz (ver handleRunClick).
  const [executeTarget, setExecuteTarget] =
    useState<{ project: IWorkflow; schema: Record<string, IParamSchema> } | null>(null)

  const handleRunWorkflow = useCallback(async (project: IWorkflow, inputs: Record<string, unknown> = {}) => {
    setExecuteTarget(null)
    setRunningId(project.id_hash)
    const res = await GisFlowService.executeWorkflow(project.id_hash, inputs, false)
    setRunningId(null)
    if (res?.error) {
      createToast.error("Erro ao executar workflow", res.error.message)
    } else {
      createToast.success(`Workflow "${project.name}" iniciado!`)
      // Atualiza o indicador global de execuções sem esperar o próximo poll.
      refreshActiveRuns()
    }
  }, [refreshActiveRuns])

  /**
   * `GET /workflows/` responde o schema leve (WorkflowListItem), que não traz
   * `params_schema` — ler `project.params_schema` aqui dava SEMPRE undefined, e
   * workflows com inputs obrigatórios eram disparados com `{}` e falhavam no
   * executor. O schema é buscado no clique, uma requisição só, em vez de
   * engordar a listagem inteira com um campo que quase nenhuma linha usa.
   */
  const handleRunClick = useCallback(async (project: IWorkflow) => {
    // Estado próprio, e não `runningId`: durante a busca do schema o workflow
    // ainda NÃO está executando, e o ponto "em execução" da linha leria essa
    // espera como uma execução em curso.
    setPreparandoId(project.id_hash)
    const res = await GisFlowService.getWorkflowById(project.id_hash)
    setPreparandoId(null)
    // "Não tem schema" e "não consegui saber se tem" são coisas diferentes: sem
    // este ramo, um 500/timeout aqui caía no else e DISPARAVA o workflow com
    // inputs vazios — exatamente a falha que buscar o schema veio corrigir, de
    // volta pelo caminho de erro e agora pior, porque o usuário passou a confiar
    // que o diálogo de parâmetros aparece quando é necessário.
    if (res.error || !res.data) {
      createToast.error(
        "Não foi possível preparar a execução.",
        res.error?.message ?? "Falha ao ler os parâmetros do workflow. Tente de novo.",
      )
      return
    }
    const schema = res.data.params_schema
    if (schema && Object.keys(schema).length > 0) {
      setExecuteTarget({ project, schema })
    } else {
      handleRunWorkflow(project)
    }
  }, [handleRunWorkflow])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Ativar / Desativar ─────────────────────────────────────────────────────
  const [desativando, setDesativando] = useState<IWorkflow | null>(null)

  // Lê o valor da PRÓPRIA linha em vez de procurar na lista, e atualiza o
  // estado por função: sem isso o callback fechava sobre `workflows` e trocava
  // de identidade a cada resposta do servidor — e o memo das linhas não valia.
  const mudarStatus = useCallback(async (workflow: IWorkflow, novo: boolean) => {
    const aplicar = (valor: boolean) => definirWorkflows(prev =>
      prev.map(p => p.id_hash === workflow.id_hash ? { ...p, flag_ative: valor } : p),
    )
    // Otimista, com reversão: a troca de status é o tipo de mudança em que
    // esperar o servidor faz a linha "voltar" sob o cursor.
    aplicar(novo)
    const res = await GisFlowService.updateStatusWorkflow(workflow.id_hash, { flag_ative: novo })
    if (res.error) {
      aplicar(!novo)
      createToast.error("Erro ao atualizar status do workflow.", res.error.message)
      return
    }
    createToast.success(`«${workflow.name}» ${novo ? "ativado" : "desativado"}`)
  }, [definirWorkflows])

  // Ativar é seguro e fica a um clique; Desativar passa pela confirmação que
  // diz o que pausa (`ConfirmarDesativar`).
  const ativar = useCallback((workflow: IWorkflow) => { void mudarStatus(workflow, true) }, [mudarStatus])
  const pedirDesativar = useCallback((workflow: IWorkflow) => setDesativando(workflow), [])
  const confirmarDesativar = useCallback((workflow: IWorkflow) => {
    setDesativando(null)
    void mudarStatus(workflow, false)
  }, [mudarStatus])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Duplicação ─────────────────────────────────────────────────────────────
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null)

  const handleDuplicate = useCallback(async (project: IWorkflow) => {
    setDuplicatingId(project.id_hash)
    const res = await GisFlowService.duplicateWorkflowById(project.id_hash)
    setDuplicatingId(null)

    if (res?.error) {
      createToast.error("Erro ao duplicar workflow", res.error.message)
      return
    }
    // Recarrega em vez de inserir a cópia à mão: quem escolhe o nome é o
    // backend (desambigua quando "Cópia de X" já existe) e a listagem traz
    // campos que a resposta da duplicação não tem.
    //
    // O aviso é incondicional: a listagem não traz `definition`, então não há
    // como saber daqui se este workflow tem agendamento — e a regra do endpoint
    // vale para todos (a cópia nasce com o agendamento desligado).
    createToast.success(
      `Cópia criada: "${res.data?.name}"`,
      "Se o original tinha agendamento, a cópia nasce com ele desligado.",
    )
    recarregar()
  }, [recarregar])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Grupos: criar, renomear, excluir, mover para dentro/fora ───────────────
  const [modalNovoGrupo, setModalNovoGrupo] = useState(false)
  const [editGroup, setEditGroup] = useState<IWorkflowGroup | null>(null)
  const [deleteGroupConfirm, setDeleteGroupConfirm] = useState<IWorkflowGroup | null>(null)

  function handleGroupCreated(group: IWorkflowGroup) {
    setModalNovoGrupo(false)
    definirGrupos(prev => [...prev, group])
  }

  // Excluir grupo com workflows dentro era BLOQUEADO, e o operador tinha de
  // esvaziar o grupo à mão antes. A FK é `ondelete='SET NULL'`: os workflows
  // apenas voltam a ficar sem grupo, nenhum é apagado. A confirmação diz
  // quantos serão desagrupados — é o que justifica não bloquear.
  async function handleDeleteGroup(groupId: string) {
    const result = await GisFlowService.deleteWorkflowGroup(groupId)
    if (result?.error) { createToast.error("Erro ao excluir grupo"); return }
    createToast.success("Grupo excluído.")
    definirGrupos(prev => prev.filter(g => g.id_hash !== groupId))
    // Espelha o SET NULL do banco: sem isto as linhas sumiriam da tela até o
    // próximo carregamento, porque o grupo que as continha deixou de existir.
    definirWorkflows(prev => prev.map(p => p.group_id === groupId ? { ...p, group_id: null } : p))
  }

  async function handleRenameGroup(groupId: string, name: string, description: string | null) {
    const result = await GisFlowService.updateWorkflowGroup(groupId, { name, description })
    if (result?.error) { createToast.error("Erro ao renomear grupo"); return }
    definirGrupos(prev => prev.map(g => g.id_hash === groupId ? { ...g, name, description } : g))
  }

  // Os handlers que vão para as linhas são `useCallback` com deps estáveis e
  // atualização funcional do estado: identidade constante é o que faz o
  // React.memo da LinhaWorkflow valer alguma coisa.
  const handleAddToGroup = useCallback(async (workflowId: string, groupId: string) => {
    const result = await GisFlowService.addWorkflowToGroup(groupId, workflowId)
    if (result?.error) { createToast.error("Erro ao mover workflow para o grupo"); return }
    definirWorkflows(prev => prev.map(p => p.id_hash === workflowId ? { ...p, group_id: groupId } : p))
  }, [definirWorkflows])

  /** Troca de grupo em um passo: o backend sobrescreve `group_id`, então
   *  chamar só o "adicionar" já tira do anterior. */
  const handleMoveToGroup = useCallback(async (project: IWorkflow, groupId: string) => {
    if (project.group_id === groupId) return
    await handleAddToGroup(project.id_hash, groupId)
  }, [handleAddToGroup])

  const handleRemoveFromGroup = useCallback(async (workflowId: string, groupId: string) => {
    const result = await GisFlowService.removeWorkflowFromGroup(groupId, workflowId)
    if (result?.error) { createToast.error("Erro ao remover workflow do grupo"); return }
    definirWorkflows(prev => prev.map(p => p.id_hash === workflowId ? { ...p, group_id: null } : p))
  }, [definirWorkflows])
  // ──────────────────────────────────────────────────────────────────────────

  // ── Drag and Drop ──────────────────────────────────────────────────────────
  // Duas coisas arrastam — a linha e o grupo inteiro — e o alvo do drop é o
  // MESMO retângulo. Sem saber o que está na mão, soltar um grupo sobre outro
  // seria interpretado como "mover workflow para este grupo".
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [draggingGroupId, setDraggingGroupId] = useState<string | null>(null)
  const [dragOverGroupId, setDragOverGroupId] = useState<string | null>(null)
  const [dragOverUngrouped, setDragOverUngrouped] = useState(false)

  // `useCallback` porque descem como prop para cada linha memoizada.
  const handleDragStart = useCallback((workflowId: string) => {
    setDraggingId(workflowId)
  }, [])

  const handleDragEnd = useCallback(() => {
    setDraggingId(null)
    setDraggingGroupId(null)
    setDragOverGroupId(null)
    setDragOverUngrouped(false)
  }, [])

  /** Solta um grupo sobre outro: o arrastado assume a posição do alvo. */
  async function handleReorderGroups(alvoId: string) {
    const origemId = draggingGroupId
    handleDragEnd()
    if (!origemId || origemId === alvoId) return

    const atual = grupos.map(g => g.id_hash)
    const ordem = moverGrupo(atual, origemId, alvoId)
    // Identidade preservada quando não houve movimento — não vale um POST.
    if (ordem === atual) return

    // Otimista, com reversão — mesmo padrão de `mudarStatus`. A ordem é o tipo
    // de mudança em que esperar o servidor faz o item "voltar" sob o cursor, e
    // isso lê como falha mesmo quando deu certo.
    const anterior = grupos
    const porId = new Map(grupos.map(g => [g.id_hash, g]))
    definirGrupos(ordem.map(id => porId.get(id)!).filter(Boolean))

    const result = await GisFlowService.reorderWorkflowGroups(ordem)
    if (result?.error) {
      definirGrupos(anterior)
      createToast.error("Erro ao reordenar grupos")
    }
  }

  async function handleDropOnGroup(groupId: string) {
    if (draggingGroupId) return handleReorderGroups(groupId)
    if (!draggingId) return
    const workflow = workflows.find(p => p.id_hash === draggingId)
    handleDragEnd()
    if (!workflow) return
    // Uma chamada, não duas: `add_workflow_to_group` sobrescreve o `group_id`.
    // Tirar do grupo antes abria uma janela em que o workflow ficava sem grupo
    // nenhum se a segunda chamada falhasse.
    await handleMoveToGroup(workflow, groupId)
  }

  async function handleDropOnUngrouped() {
    if (!draggingId) return
    const workflow = workflows.find(p => p.id_hash === draggingId)
    handleDragEnd()
    if (!workflow || !workflow.group_id) return
    await handleRemoveFromGroup(workflow.id_hash, workflow.group_id)
  }

  const arrastando = draggingId ? workflows.find(p => p.id_hash === draggingId) ?? null : null
  const zonaDeRemover = {
    onDragOver: (e: DragEvent<HTMLElement>) => { e.preventDefault(); setDragOverUngrouped(true) },
    onDragLeave: (e: DragEvent<HTMLElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverUngrouped(false)
    },
    onDrop: () => { void handleDropOnUngrouped() },
  }
  // ──────────────────────────────────────────────────────────────────────────

  // ── Diálogos por workflow ──────────────────────────────────────────────────
  const [deleteProjectId, setDeleteProjectId] = useState<string | null>(null)
  const [configureProjectId, setConfigureProjectId] = useState<string | null>(null)
  const [portalDialogProject, setPortalDialogProject] = useState<IWorkflow | null>(null)
  const [moveDialogProject, setMoveDialogProject] = useState<IWorkflow | null>(null)
  // Por id, e não por objeto: o workflow pode mudar na lista (renomeado,
  // ativado) enquanto o diálogo está aberto, e ele deve ler a versão atual.
  const workflowParaExcluir = deleteProjectId ? workflows.find(p => p.id_hash === deleteProjectId) ?? null : null
  const workflowParaConfigurar = configureProjectId ? workflows.find(p => p.id_hash === configureProjectId) ?? null : null
  // ──────────────────────────────────────────────────────────────────────────

  // Mesma lista que o diálogo oferece no select — o menu só decide se há alguma.
  const podeMover = useMemo(
    () => moveTargets(workspaces, currentWorkspace?.id_hash).length > 0,
    [workspaces, currentWorkspace?.id_hash],
  )

  // ── Callbacks estáveis entregues às linhas ─────────────────────────────────
  // Tudo o que desce para a LinhaWorkflow tem identidade constante — caso
  // contrário o React.memo nunca acerta e a lista inteira volta a re-renderizar
  // a cada tecla da busca.
  const abrirWorkflow = useCallback(
    (id: string) => router.push(`./workflow/${id}`),
    [router],
  )
  /**
   * Aquece a rota do editor no primeiro hover sobre a linha.
   *
   * `/workflow/[id]` é a rota mais pesada da aplicação (React Flow + Monaco) e
   * as linhas navegam por `onClick`, não por <Link>: o App Router não tinha como
   * pré-carregá-la, então cada abertura pagava payload RSC + chunks do zero e a
   * listagem ficava segundos parada, sem retorno visual nenhum. Com a rota
   * quente o comite cabe no teto de espera de `useViewTransitionRouter`, e a
   * transição de rota passa a acontecer de verdade.
   *
   * O `Set` evita repetir a chamada a cada entrada do ponteiro na mesma linha —
   * o cache do Next já deduplica, mas não de graça.
   */
  const aquecidos = useRef<Set<string>>(new Set())
  const prefetchWorkflow = useCallback((id: string) => {
    if (aquecidos.current.has(id)) return
    aquecidos.current.add(id)
    router.prefetch(`./workflow/${id}`)
  }, [router])
  // Histórico já recortado ao workflow (spec §3.9); a execução viva abre
  // direto no painel dela.
  const verExecucoes = useCallback(
    (id: string) => router.push(`/observability?workflow=${encodeURIComponent(id)}`),
    [router],
  )
  const verExecucao = useCallback(
    (runId: string) => router.push(`/observability?execucao=${encodeURIComponent(runId)}`),
    [router],
  )
  const abrirPortal = useCallback((project: IWorkflow) => setPortalDialogProject(project), [])
  const abrirMover = useCallback((project: IWorkflow) => setMoveDialogProject(project), [])
  const abrirConfigurar = useCallback((id: string) => setConfigureProjectId(id), [])
  const abrirExcluir = useCallback((id: string) => setDeleteProjectId(id), [])
  const criarWorkflow = useCallback(() => router.push("./workflow/create"), [router])
  const atualizarLista = useCallback(() => recarregar({ force: true }), [recarregar])
  const tentarDeNovo = useCallback(() => recarregar(), [recarregar])
  // ──────────────────────────────────────────────────────────────────────────

  const hasDnd = grupos.length > 0

  /** A linha de um workflow, com o que já foi derivado para ele. */
  function linha(wf: IWorkflow): ReactNode {
    const d = derivados.get(wf.id_hash)
    if (!d) return null
    return (
      <LinhaWorkflow
        workflow={wf}
        gatilho={d.gatilho}
        resumoDoAgendamento={d.resumo}
        comoAnda={d.comoAnda}
        grupos={grupos}
        canEdit={canEdit}
        canExecute={canExecute}
        canManage={canManage}
        podeMover={podeMover}
        hasDnd={hasDnd}
        isDragging={draggingId === wf.id_hash}
        executando={runningId === wf.id_hash || preparandoId === wf.id_hash}
        duplicando={duplicatingId === wf.id_hash}
        runIdVivo={runPorHash.get(wf.id_hash)?.runId ?? null}
        onOpen={abrirWorkflow}
        onPrefetch={prefetchWorkflow}
        onRun={handleRunClick}
        onVerExecucao={verExecucao}
        onAtivar={ativar}
        onDesativar={pedirDesativar}
        onConfigure={abrirConfigurar}
        onPortal={abrirPortal}
        onMove={abrirMover}
        onDuplicate={handleDuplicate}
        onDelete={abrirExcluir}
        onViewRuns={verExecucoes}
        onAddToGroup={handleAddToGroup}
        onRemoveFromGroup={handleRemoveFromGroup}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      />
    )
  }

  // ── Estados da tela ────────────────────────────────────────────────────────
  const carregando = dados.carregando
  // O bloco de erro toma a tela apenas quando NUNCA houve uma carga aceita
  // (`atualizadoEm == null`): quem trocou de workspace não pode ver a estante
  // do anterior como se fosse a nova. Uma recarga que falha (Atualizar,
  // Duplicar) sobre uma lista já pronta não a apaga — o hook mantém o que
  // havia e o toast avisa; bloquear a tela inteira por um erro transitório
  // seria pior que o problema.
  const comErro = !carregando && dados.erro != null && dados.atualizadoEm == null
  const primeiroUso = !carregando && !comErro && workflows.length === 0 && grupos.length === 0
  const semResultado = !carregando && !comErro && !primeiroUso && recorteAtivo && visiveis.length === 0
  const listaPronta = !carregando && !comErro && !primeiroUso
  // O subtítulo só some enquanto não há nada para contar (primeira carga, ou
  // erro antes de qualquer resposta).
  const contagensDoCabecalho: ContagensDoCabecalho | null =
    carregando || (comErro && dados.atualizadoEm == null)
      ? null
      : { workflows: workflows.length, grupos: grupos.length, ativos: contagens.ativos, agendados: contagens.agendados, portal: contagens.portal }
  // ──────────────────────────────────────────────────────────────────────────

  return (
    <PageRoot>
      <CabecalhoDeProjetos
        contagens={contagensDoCabecalho}
        atualizando={dados.atualizando}
        canEdit={canEdit}
        onAtualizar={atualizarLista}
        onNovoGrupo={() => setModalNovoGrupo(true)}
        onCriarWorkflow={criarWorkflow}
      />

      {carregando && <SkeletonDeProjetos />}

      {comErro && <ErroDeCarga mensagem={dados.erro!} onTentar={tentarDeNovo} />}

      {primeiroUso && <VazioPrimeiroUso canEdit={canEdit} onCriar={criarWorkflow} />}

      {listaPronta && (
        <>
          {metricasIndisponiveis && <MetricasIndisponiveis onTentar={atualizarLista} />}

          <BarraDeFiltros
            estado={estado}
            onEstado={atualizar}
            onLimpar={limparFiltros}
            contagens={contagens}
            temGrupos={grupos.length > 0}
            todosRecolhidos={todosRecolhidos}
            onRecolherTodos={recolherTodos}
            onExpandirTodos={expandirTodos}
          />

          {semResultado && (
            <SemResultado q={estado.q} filtro={estado.filtro} semFiltro={soComBusca} onLimpar={limparFiltros} />
          )}

          {/* Sem grupo vem ANTES dos grupos. Seção com título só quando há
              grupos; sem eles, a lista sai sem título — não há do que se
              distinguir. */}
          {!semResultado && semGrupo.length > 0 && (
            grupos.length > 0 ? (
              <section aria-labelledby="sem-grupo-titulo" {...zonaDeRemover} className="flex flex-col gap-1.5">
                <h2 className="flex flex-wrap items-baseline gap-x-2 px-1">
                  <span id="sem-grupo-titulo" className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                    Sem grupo
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {textoDaContagemDoGrupo(
                      totalSemGrupo.total,
                      totalSemGrupo.ativos,
                      semGrupo.length < totalSemGrupo.total ? semGrupo.length : null,
                    )}
                  </span>
                </h2>
                <ul className="flex flex-col gap-1.5">
                  {semGrupo.map(wf => <li key={wf.id_hash}>{linha(wf)}</li>)}
                </ul>
              </section>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {semGrupo.map(wf => <li key={wf.id_hash}>{linha(wf)}</li>)}
              </ul>
            )
          )}

          {!semResultado && gruposVisiveis.map(grupo => {
            const id = grupo.id_hash
            const total = totais.get(id) ?? { total: 0, ativos: 0 }
            // Arrastar GRUPO não tinha retorno visual nenhum: a pessoa segurava
            // a alça e nada na tela dizia onde o grupo cairia. Os dois estados
            // são distintos de propósito — "receber um workflow" e "trocar de
            // posição" acontecem sobre o mesmo retângulo.
            const arrastandoEste = draggingGroupId === id
            return (
              <GrupoSecao
                key={id}
                grupo={grupo}
                workflows={porGrupo.get(id) ?? []}
                totalNoGrupo={total.total}
                ativosNoGrupo={total.ativos}
                recolhido={recolhidos.has(id)}
                onToggle={alternarGrupo}
                canEdit={canEdit}
                podeArrastar={canEdit && grupos.length > 1}
                arrastandoEste={arrastandoEste}
                alvoDeReordenacao={dragOverGroupId === id && !!draggingGroupId && !arrastandoEste}
                recebendoWorkflow={dragOverGroupId === id && !!draggingId}
                nomeDoArrastado={arrastando?.name ?? null}
                onDragOver={e => { e.preventDefault(); setDragOverGroupId(id) }}
                onDragLeave={e => {
                  if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverGroupId(null)
                }}
                onDrop={() => { void handleDropOnGroup(id) }}
                onDragStartGrupo={setDraggingGroupId}
                onDragEndGrupo={handleDragEnd}
                onRenomear={setEditGroup}
                onExcluir={setDeleteGroupConfirm}
                renderLinha={linha}
              />
            )
          })}

          {/* Zona fixa — aparece ao arrastar um workflow agrupado. */}
          {arrastando?.group_id && (
            <div
              {...zonaDeRemover}
              className={cn(
                "flex items-center justify-center gap-2 rounded-lg border-2 border-dashed py-4 text-sm transition-colors select-none",
                dragOverUngrouped
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border text-muted-foreground/50",
              )}
            >
              <TbFolderOpen size={16} aria-hidden="true" />
              Solte aqui para remover do grupo
            </div>
          )}

          {/* O recurso de grupos não tinha onde se apresentar: sem nenhum grupo
              criado, nada na lista sugeria que agrupar era possível — nem a alça
              de arrastar, que só aparece a partir do primeiro grupo. Este
              convite é o único lugar em que ele pode se mostrar. */}
          {canEdit && !recorteAtivo && grupos.length === 0 && workflows.length > 2 && (
            <button
              type="button"
              onClick={() => setModalNovoGrupo(true)}
              className="flex items-center gap-3 rounded-lg border border-dashed border-border px-4 py-3 text-left transition-colors outline-none hover:border-primary/50 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              <TbFolderPlus className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-sm font-medium">Agrupar workflows</span>
                <span className="block text-xs text-muted-foreground">
                  Crie um grupo e arraste as linhas para dentro. Grupos podem ser
                  recolhidos e reordenados.
                </span>
              </span>
            </button>
          )}

          {/* Dica de arrastar, no primeiro grupo criado: a alça só passa a
              existir a partir daí, e nada explicaria que ela apareceu. */}
          {canEdit && grupos.length === 1 && totalSemGrupo.total > 0 && (
            <p className="flex items-center gap-2 px-1 text-xs text-muted-foreground">
              <TbGripVertical size={14} className="shrink-0" aria-hidden="true" />
              Arraste um workflow pela alça para colocá-lo no grupo — ou use
              &quot;Mover para grupo&quot; no menu do workflow.
            </p>
          )}
        </>
      )}

      {/* ── Diálogos ──────────────────────────────────────────────────────── */}
      <Dialog open={modalNovoGrupo} onOpenChange={setModalNovoGrupo}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo grupo</DialogTitle>
            <DialogDescription>Organize workflows dentro de um grupo.</DialogDescription>
          </DialogHeader>
          <CreateGroup onSuccess={handleGroupCreated} />
        </DialogContent>
      </Dialog>

      <Dialog open={!!editGroup} onOpenChange={open => { if (!open) setEditGroup(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Renomear grupo</DialogTitle>
            <DialogDescription>O nome e a descrição aparecem no cabeçalho do grupo.</DialogDescription>
          </DialogHeader>
          {editGroup && (
            <RenameGroup
              key={editGroup.id_hash}
              group={editGroup}
              onSubmit={(nome, descricao) => handleRenameGroup(editGroup.id_hash, nome, descricao)}
              onDone={() => setEditGroup(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteGroupConfirm} onOpenChange={open => { if (!open) setDeleteGroupConfirm(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir grupo{deleteGroupConfirm ? ` «${deleteGroupConfirm.name}»` : ""}?</DialogTitle>
            <DialogDescription>
              {(() => {
                const dentro = totais.get(deleteGroupConfirm?.id_hash ?? "")?.total ?? 0
                if (dentro === 0) return "Tem certeza que deseja excluir este grupo?"
                return dentro === 1
                  ? "1 workflow volta para «Sem grupo». Nenhum é excluído."
                  : `${dentro} workflows voltam para «Sem grupo». Nenhum é excluído.`
              })()}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setDeleteGroupConfirm(null)}>Cancelar</Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteGroupConfirm) void handleDeleteGroup(deleteGroupConfirm.id_hash)
                setDeleteGroupConfirm(null)
              }}
            >
              Excluir
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!workflowParaExcluir} onOpenChange={open => { if (!open) setDeleteProjectId(null) }}>
        {workflowParaExcluir && (
          <DeleteProject
            workflow={workflowParaExcluir}
            onDeleted={id => {
              definirWorkflows(prev => prev.filter(p => p.id_hash !== id))
              setDeleteProjectId(null)
            }}
          />
        )}
      </Dialog>

      <Dialog open={!!workflowParaConfigurar} onOpenChange={open => { if (!open) setConfigureProjectId(null) }}>
        {workflowParaConfigurar && (
          <ConfigureProject
            key={workflowParaConfigurar.id_hash}
            workflow={workflowParaConfigurar}
            onSaved={atualizado => definirWorkflows(prev => prev.map(p => p.id_hash === atualizado.id_hash ? atualizado : p))}
            onDone={() => setConfigureProjectId(null)}
          />
        )}
      </Dialog>

      {/* Diálogo de parâmetros para execução rápida — o schema vem do
          `getWorkflowById` disparado no clique, porque a listagem não o traz. */}
      {executeTarget && (
        <ExecuteParamsDialog
          open
          paramsSchema={executeTarget.schema}
          onConfirm={inputs => handleRunWorkflow(executeTarget.project, inputs)}
          onCancel={() => setExecuteTarget(null)}
        />
      )}

      <ConfirmarDesativar workflow={desativando} onConfirm={confirmarDesativar} onCancel={() => setDesativando(null)} />

      {portalDialogProject && (
        <PortalSettingsDialog
          open={!!portalDialogProject}
          onOpenChange={open => { if (!open) setPortalDialogProject(null) }}
          workflowId={portalDialogProject.id_hash}
          workflowName={portalDialogProject.name}
          initialAccess={portalDialogProject.portal_access ?? "disabled"}
          initialSharedWith={portalDialogProject.portal_shared_with ?? null}
          onSaved={(access, shared) => {
            definirWorkflows(prev => prev.map(p =>
              p.id_hash === portalDialogProject.id_hash
                ? { ...p, portal_access: access, portal_shared_with: shared }
                : p,
            ))
            setPortalDialogProject(null)
          }}
        />
      )}

      {moveDialogProject && (
        <MoveWorkflowDialog
          open={!!moveDialogProject}
          onOpenChange={open => { if (!open) setMoveDialogProject(null) }}
          workflowId={moveDialogProject.id_hash}
          workflowName={moveDialogProject.name}
          portalAccess={moveDialogProject.portal_access}
          onMoved={() => {
            // O workflow saiu do workspace ativo, então sai da listagem. Update
            // otimista em vez de refetch: a lista inteira piscaria à toa.
            definirWorkflows(prev => prev.filter(p => p.id_hash !== moveDialogProject.id_hash))
          }}
        />
      )}
    </PageRoot>
  )
}
