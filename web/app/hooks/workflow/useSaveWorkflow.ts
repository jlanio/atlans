import { INodeContext } from "@/context/useFlowContext"
import { INodesDefinition, IEdgeDefinition } from "@/service/types"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { Edge, useReactFlow, useStoreApi, type Viewport } from "@xyflow/react"
import { useParams, useRouter } from "next/navigation"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { serializeEdge } from "@/app/components/workflow/utils/edge-persistence"
import { viewportsIguais } from "@/app/components/workflow/utils/viewport-salvo"

export interface OpcoesDeSave {
  /** Save disparado por outra ação (o Executar grava antes de despachar): sem
   *  toast de erro — quem chamou responde pelo próprio — e sem piscar "Salvo"
   *  quando não há nada a salvar. O chip continua refletindo o estado. */
  silent?: boolean
}

// Normaliza properties ordenando chaves — JSON.stringify preserva ordem de
// inserção, então dois objetos com mesmas entradas mas ordens diferentes
// produzem strings diferentes. ReactFlow pode recriar o objeto internamente
// com ordem diferente após medição de dimensões, o que dispararia falso
// positivo no isDirty.
function normalizeProperties(properties: unknown): Record<string, string> {
  if (!properties || typeof properties !== 'object') return {}
  const source = properties as Record<string, string>
  const sorted: Record<string, string> = {}
  for (const key of Object.keys(source).sort()) {
    sorted[key] = source[key]
  }
  return sorted
}

/**
 * Projeção persistível do grafo — o que vai para `definition` no backend.
 *
 * Pura e exportada de propósito: o detector de "não salvo" mora em outro
 * componente (global-save-indicator) e precisa montar EXATAMENTE o mesmo
 * payload que o save grava. Qualquer assimetria entre os dois vira um "Não
 * salvo" que nunca some.
 */
export function montarPayloadDoGrafo(nodes: INodeContext[], edges: Edge[]) {
  const nodesReq = nodes.map(node => {
    const { data: { name, alias, properties, type }, position } = node
    // Normaliza position para { x, y } — descarta campos extras que o
    // ReactFlow pode ter injetado (positionAbsolute, etc).
    return {
      id: node.id,
      name,
      alias,
      type,
      properties: normalizeProperties(properties),
      position: { x: position.x, y: position.y }
    } satisfies INodesDefinition
  })

  // A serialização vive em utils/edge-persistence para ficar simétrica com o
  // loadEdges e testável — o detect-dirty usa esta mesma função.
  const edgesReq = edges.map(serializeEdge)

  return { nodesReq, edgesReq }
}

export const useSaveWorkflow = () => {

  const router = useRouter()
  const { current: currentWorkspace } = useWorkspace()
  const reactFlowInstance = useReactFlow()
  // Leitura imperativa da store do React Flow em vez de useNodes()/useEdges().
  // Este hook está montado em vários pontos da árvore do canvas (editor, botão
  // Salvar, botão Executar, chip de estado): assinar os dois arrays
  // re-renderizava todos a cada pointermove de um arraste. E ler no momento da
  // chamada também dispensa as refs que existiam aqui para cobrir closure stale
  // — a store nunca está atrasada, então o save silencioso do Execute não tem
  // como gravar vazio.
  const flowStore = useStoreApi()
  const { id } = useParams<{ id: string }>()
  // Acessa a store Zustand — permite GlobalSaveIndicator ver o mesmo status
  const isSaving = useWorkflowSaveStore(s => s.isSaving)
  const saveStatus = useWorkflowSaveStore(s => s.saveStatus)

  function buildPayload() {
    const { nodes, edges } = flowStore.getState()
    const { nodesReq, edgesReq } = montarPayloadDoGrafo(nodes as unknown as INodeContext[], edges)
    const viewportReq = reactFlowInstance.getViewport()
    return { nodesReq, edgesReq, viewportReq }
  }


  function handleSaveWorkflow(opcoes: OpcoesDeSave = {}) {
    // Guard único — a decisão de iniciar está em saveWorkflow. Antes do
    // refactor Zustand, handleSaveWorkflow setava isSaving=true aqui; mas
    // Zustand é síncrono, então o guard seguinte em saveWorkflow bloqueava
    // tudo imediatamente e nenhum PUT era disparado.
    if (useWorkflowSaveStore.getState().isSaving) return
    return saveWorkflow(opcoes)
  }

  async function saveWorkflow({ silent = false }: OpcoesDeSave = {}) {

    const store = useWorkflowSaveStore.getState()
    if (store.isSaving)
      return

    // Captura o valor mais recente da store
    const currentName = store.workflowName
    if (!currentName || currentName.trim() === "") {
      // Nome ausente: marca o status mas NÃO seta isSaving (se ativasse, o
      // próximo clique — após o usuário preencher o nome no UnsavedDialog —
      // seria bloqueado pelo guard `if (store.isSaving) return` acima).
      store.setStatus('needs_name')
      return
    }

    const { nodesReq, edgesReq, viewportReq } = buildPayload()

    // Guard-rail anti-perda de dados: nunca sobrescreve um workflow existente
    // com definition vazio. Se o usuário realmente quiser zerar o workflow,
    // precisa apagar os nós no canvas (que trás isDirty com nodes=[] explícito
    // como último estado renderizado). Protege contra closures stale que
    // chamaram saveWorkflow antes do canvas hidratar.
    if (id && nodesReq.length === 0 && store.lastSavedSnapshot) {
      try {
        const prev = JSON.parse(store.lastSavedSnapshot) as { nodes?: unknown[] }
        if (prev.nodes && prev.nodes.length > 0) {
          // Workflow tinha nós — recusamos sobrescrever com vazio.
          console.warn(
            "[useSaveWorkflow] Tentativa de salvar workflow existente com 0 nós bloqueada "
            + "(provável closure stale pré-hidratação).",
          )
          return { data: null, error: null }
        }
      } catch {
        // snapshot corrompido — não bloqueia
      }
    }

    if (id && !store.isDirty(nodesReq, edgesReq, currentName)) {
      // O grafo é o salvo. Só o viewport pode ter mudado — e ele é parte do que
      // se salva ("reabrir no mesmo zoom e posição"), mas não é edição: não
      // marca "não salvo" e o save silencioso do Executar não o persegue. Vai
      // junto quando o USUÁRIO pede o save; o backend não abre versão por isso
      // (`_has_substantial_changes` ignora posição e viewport).
      const viewportMudou = !viewportsIguais(viewportReq, store.lastSavedViewport)
      if (silent || !viewportMudou) {
        // Nada a gravar — sem PUT. Mas um Ctrl+S que não responde nada é
        // indistinguível de um atalho quebrado: pisca "Salvo" para confirmar que
        // está tudo gravado. Nenhum reset de status é necessário, pois
        // startSaving() ainda não foi chamado.
        if (!silent) store.flashSaved()
        return { data: null, error: null }
      }
    }

    // Só agora marca como saving — haverá PUT a partir daqui.
    // Qualquer caminho abaixo sai via completeSave/failSave/catch que limpam
    // isSaving. (Antes o start ficava em handleSaveWorkflow e os early-returns
    // acima deixavam isSaving=true preso).
    store.startSaving()

    try {
      if (id) {
        // Payload mínimo: apenas os campos que o canvas edita. Enviar
        // flag_ative/description/version/priority aqui SOBRESCREVERIA os
        // valores reais no backend (ex: workflow desativado via switch
        // voltava a ficar ativo em toda edição).
        const data = await GisFlowService.updateWorkflowById(id, {
          name: currentName,
          definition: {
            nodes: nodesReq,
            edges: edgesReq,
            viewport: viewportReq,
          },
        })

        if (data.error) {
          store.failSave(data.error.message)
          // Em save silent (disparado pelo Execute antes do dispatch), o chip
          // já mostra "Falha ao salvar" — o toast aqui seria o segundo aviso.
          if (!silent) createToast.error(`Workflow não salvo`, data.error.message)
          return data
        }

        const snapshot = JSON.stringify({ name: currentName, nodes: nodesReq, edges: edgesReq })
        // Sem toast de sucesso: o chip ao lado do caminho do workflow diz
        // "Salvo" e continua dizendo "Salvo há N min". Um toast a cada Ctrl+S
        // era ruído sobre a mesma informação.
        store.completeSave(snapshot, viewportReq)
        // Salvou, mas o agendamento pode não ter sido aplicado (workflow
        // inativo, expressão inválida): o backend devolve o motivo em
        // `schedule_notices`. Nesse caso o "Salvo" no chip esconderia uma
        // ressalva importante — mostra um toast âmbar (mesmo em save silent:
        // o usuário precisa saber que o agendamento não valeu).
        for (const aviso of data.data?.schedule_notices ?? []) {
          createToast.warning("Agendamento não aplicado", aviso.message)
        }
        return data
      }

      // Workflow novo: defaults razoáveis para campos de metadado.
      // created_by_id/updated_by_id são preenchidos pelo backend a partir
      // do usuário autenticado — não são enviados pelo frontend.
      const data = await GisFlowService.createWorkflow({
        flag_ative: true,
        name: currentName,
        description: "",
        version: "v1",
        priority: 0,
        workspace_id: currentWorkspace?.id_hash ?? undefined,
        definition: {
          nodes: nodesReq,
          edges: edgesReq,
          viewport: viewportReq,
        },
      })

      if (data.error) {
        store.failSave(data.error.message)
        createToast.error(`Workflow não criado`, data.error.message)
        return data
      }

      store.completeSave(JSON.stringify({ name: currentName, nodes: nodesReq, edges: edgesReq }), viewportReq)

      // O workflow agora existe: a URL passa a ser a dele, e o editor continua
      // aberto. Antes, o botão mandava para a lista de projetos (abandonando o
      // que se estava editando) e o Ctrl+S ficava em /workflow/create sem id —
      // o Ctrl+S seguinte criava uma cópia. `replace`, e não `push`: voltar
      // para /create no histórico seria voltar para "criar outro".
      const novoId = data.data?.id_hash
      if (novoId) router.replace(`/workflow/${novoId}`)

      return data
    } catch (err) {
      store.failSave(String(err))
      createToast.error("Erro ao salvar workflow", String(err))
    }

  }

  /**
   * Inicializa o snapshot de referência com o estado carregado do backend.
   * Deve ser chamado UMA VEZ após hidratação do canvas (loadNodes+loadEdges).
   * Com o snapshot preenchido, isDirty() retorna false quando o usuário não
   * editou nada — evitando um PUT desnecessário antes do POST /execute.
   *
   * `savedAt` é o `updated_at` do servidor (epoch ms): é o que o chip mostra em
   * repouso antes do primeiro save desta sessão. `viewport` é o que veio na
   * `definition`: referência para saber se um save explícito tem viewport novo
   * a gravar.
   *
   * IMPORTANTE: o formato de nodesReq/edgesReq deve ser idêntico ao que
   * buildPayload() produz (INodesDefinition[] / IEdgeDefinition[]).
   */
  function initSnapshot(nodesReq: INodesDefinition[], edgesReq: IEdgeDefinition[], name: string, savedAt?: number | null, viewport?: Viewport | null) {
    const store = useWorkflowSaveStore.getState()
    store.initSnapshot(nodesReq, edgesReq, name, savedAt, viewport)
  }

  return {
    isSaving,
    saveStatus,
    saveWorkflow: handleSaveWorkflow,
    initSnapshot,
    buildPayload,
  }
}
