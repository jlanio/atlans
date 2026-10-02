"use client"
import { ReactFlow, useReactFlow, useNodesState, useEdgesState, Edge, Background, BackgroundVariant, Connection } from "@xyflow/react"
import React, { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react"
import { INodeContext, useFlowContext } from "@/context/useFlowContext";
import { TbPlus } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { useConfigNodeParams } from "@/app/hooks/workflow/useConfigNodeParams";
import { useSubWorkflowContractSync } from "@/app/hooks/workflow/useSubWorkflowContractSync";
import { useDynamicPortsSync } from "@/app/hooks/workflow/useDynamicPortsSync";
import { useHandleRegistrySync } from "@/app/hooks/workflow/useHandleRegistrySync";
import { IWorkflow } from "@/service/types";
import { v4 as uuid } from 'uuid';
import WorkflowLocation from "./workflow-location";
import { useSidebar } from "../ui/sidebar";
import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams";
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast";
import ActionsButton from "./buttons";
import RunPanel from "./run-panel";
import AssistentePainel from "./assistente";
import type { ResultadoDaProposta } from "./utils/aplicar-proposta"
import {
  cabeNoEnquadrado, semMovimento, ZOOM_MAXIMO_DO_ENQUADRAMENTO, DURACAO_DO_ENQUADRAMENTO,
  type Caixa,
} from "./utils/enquadrar";
import WorkflowDrawer from "./drawer";
import { getTypeIcon } from "@/utils/getTypeIconsUtils";
import { nodeTypesFlow, customEdges } from "./canvas-types";
import { useTheme } from "@/context/ThemeContext"
import CanvasToolbar from "./canvas-toolbar";
import { CanvasInteractionProvider, useCanvasReadOnlyRoot } from "./canvas-interaction";
import { useCanvasHistory } from "@/app/hooks/workflow/useCanvasHistory";
import { fromBackend } from "@/lib/dayjs";
import { dadoOuAviso } from "@/lib/respostas";
import { viewportSalvoValido } from "./utils/viewport-salvo";
import { usePinExpirationTimer } from "@/app/hooks/workflow/usePinExpirationTimer";
import { useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow";
import UnsavedDialog from "./buttons/unsaved-dialog";
import GlobalSaveIndicator from "./global-save-indicator";
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore";
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore";
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore";
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore";
import { useRunPanelStore } from "@/app/stores/runPanelStore";
import { useCanvasViewStore } from "@/app/stores/canvasViewStore";
import { useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore";
import { getCandidateKeys, resolveToKey } from "./utils/resolve-edge-keys";
import { MENSAGEM_DE_RECUSA, validarConexao } from "./utils/valida-conexao";
import { toast } from "sonner";
import { contratoDoNo } from "./utils/node-ports"
import { buildEdges, buildNodes } from "./utils/build-canvas";
import SubflowViewer from "./subflow-viewer";
import CanvasViewLayer from "./canvas-view-layer";
import CanvasLoading from "./canvas-loading";
import { useCanvasFocus } from "@/app/hooks/workflow/useCanvasFocus";
import { useZoomLod } from "@/app/hooks/workflow/useZoomLod";

// O modal de configuração e tudo que ele arrasta junto (editor JSON do
// json-edit-react, inspetor de entrada, preview de saída, helpers de webhook e
// o guia de Jinja) só é usado depois de um duplo-clique num nó. Estaticamente
// importado, esse peso era baixado e parseado antes de o primeiro nó aparecer
// na tela. Mesmo tratamento já dado ao Monaco em code-field.
const NodeConfigModal = dynamic(() => import("./node-config-modal"), { ssr: false })

interface IReactFlowComponent {
  workflow?: IWorkflow
  reloadWorkflow?: () => Promise<void>
}

/**
 * Projeção de `nodes` que só troca de identidade quando um nó entra, sai ou tem
 * o `data` substituído.
 *
 * Arrastar um nó recria o array e cada objeto de nó a cada pointermove, mas o
 * `data` continua sendo o MESMO objeto. Os três hooks de sincronização abaixo só
 * olham `id` e `data` — alimentá-los com `nodes` cru fazia cada quadro de
 * arraste reconstruir três assinaturas de string sobre o grafo inteiro só para
 * concluir que nada mudou.
 */
function useNosEstruturais(nodes: INodeContext[]): INodeContext[] {
  const anterior = useRef<INodeContext[]>([])
  const igual =
    anterior.current.length === nodes.length &&
    nodes.every((n, i) => anterior.current[i]?.id === n.id && anterior.current[i]?.data === n.data)
  if (!igual) anterior.current = nodes
  return anterior.current
}

const ReactFlowComponent = ({ workflow, reloadWorkflow }: IReactFlowComponent) => {

  const reactFlowInstance = useReactFlow();
  const domNode = React.useRef<HTMLDivElement>(null);

  const { setFlowContext } = useFlowContext()
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)
  const setNewlyAddedNodeId = useWorkflowCatalogStore(s => s.setNewlyAddedNodeId)
  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  useConfigNodeParams()
  const { status } = useSession()
  const { theme } = useTheme()
  const [nodes, setNodes, onNodesChange] = useNodesState<INodeContext>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  // Nenhuma das três sincronizações reage a posição — todas leem `id` e `data`.
  const nosEstruturais = useNosEstruturais(nodes);
  // Sincroniza portas dinamicas dos nodes SubWorkflow com o contrato do
  // workflow alvo (SubWorkflowInput/SubWorkflowOutput).
  useSubWorkflowContractSync(nosEstruturais);
  // Portas do Script Python: `data.inputs` acompanha a propriedade `ports`.
  // Sem isto, definir as portas só surtiria efeito ao recarregar a página.
  useDynamicPortsSync(nosEstruturais);
  // Ponto de conexão acrescentado a um nó já renderizado é desenhado pelo React
  // mas não entra no registro do ReactFlow: aparece na tela e não aceita
  // conexão. Vale para as portas do Script Python e para as dos sub-fluxos.
  useHandleRegistrySync(nosEstruturais);
  const { saveSnapshot, captureBaseline, undo, redo, canUndo, canRedo } = useCanvasHistory()

  /** A última caixa que a câmera enquadrou, em coordenadas do grafo. */
  const enquadradoRef = useRef<Caixa | null>(null)

  /** O que o assistente desenha entra no canvas: com animação, e à vista.
   *
   * Duas coisas que não são enfeite:
   *
   * 1. **Enquadrar.** `computeAutoLayout` põe os nós novos em coordenadas do
   *    grafo, que podem cair FORA da viewport visível. Sem enquadrar, a pessoa
   *    fica olhando para uma tela parada enquanto o fluxo cresce fora dela — o
   *    recurso não funcionando, não um detalhe.
   *
   *    Mas enquadrar a CADA passo era o outro extremo: `fitView` reenquadra o
   *    grafo inteiro, então o zoom mudava a cada nó e o que se via era a tela
   *    saltando de escala, não acompanhando. Agora só se mexe quando o desenho
   *    sai do que já estava enquadrado — o resto do tempo a câmera fica parada,
   *    inclusive se a pessoa tiver arrastado o canvas para olhar alguma coisa.
   *    Quando se mexe, vai devagar e com teto de zoom: sem o teto, um fluxo de
   *    dois nós é enquadrado bem de perto e o passo seguinte dá um tranco para
   *    trás. É o mesmo cuidado de `run-panel/shared.tsx` e do visualizador de
   *    sub-fluxo, que passam `maxZoom` pelo mesmo motivo.
   *
   * 2. A classe só nos ids NOVOS, limpa depois. Sem a limpeza ela ficaria no
   *    objeto do nó para sempre; sem a seleção, o fluxo inteiro piscaria a cada
   *    nó acrescentado.
   */
  const aplicarDoAssistente = useCallback((resultado: ResultadoDaProposta) => {
    saveSnapshot()
    setNodes(resultado.nodes.map(no => (
      resultado.idsNovos.has(no.id) ? { ...no, className: "assistente-entrando" } : no
    )))
    setEdges(resultado.edges.map(aresta => (
      resultado.idsArestasNovas.has(aresta.id)
        ? { ...aresta, className: "assistente-aresta-entrando" }
        : aresta
    )))

    // Depois de o React desenhar: medir antes disso mediria o canvas velho.
    requestAnimationFrame(() => {
      const caixa = reactFlowInstance.getNodesBounds(reactFlowInstance.getNodes())
      if (cabeNoEnquadrado(caixa, enquadradoRef.current)) return
      enquadradoRef.current = caixa
      reactFlowInstance.fitView({
        padding: 0.2,
        maxZoom: ZOOM_MAXIMO_DO_ENQUADRAMENTO,
        duration: semMovimento() ? 0 : DURACAO_DO_ENQUADRAMENTO,
      })
    })

    // A classe sai quando a animação acaba. Ela cumpriu o papel, e deixá-la
    // gruda um estado de "acabei de chegar" em nós que já estão ali há minutos.
    // 700ms cobre a mais longa das duas (a aresta: 120ms de atraso + 400ms);
    // cortar antes do fim faria o nó saltar para o estado final no meio.
    const limpar = setTimeout(() => {
      setNodes(atuais => atuais.map(no => (no.className ? { ...no, className: undefined } : no)))
      setEdges(atuais => atuais.map(a => (a.className ? { ...a, className: undefined } : a)))
    }, 700)
    return () => clearTimeout(limpar)
  }, [reactFlowInstance, saveSnapshot, setEdges, setNodes])
  const snapshotTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { setOpen } = useSidebar()
  // No telefone o canvas vira visualizador: dá para navegar, executar e ler a
  // configuração, mas não para arrastar nó nem puxar conexão. Não é preguiça de
  // adaptar — é que acertar um handle de 8px com o dedo, num grafo em que o pan
  // usa o mesmo gesto do arraste, produz mais edição acidental do que edição.
  // Ver canvas-interaction para o porquê do gate ser largura e não ponteiro.
  const canvasSomenteLeitura = useCanvasReadOnlyRoot()
  const { saveWorkflow, saveStatus, initSnapshot, buildPayload } = useSaveWorkflow()
  // `workflow` (prop) é undefined tanto em /workflow/create quanto em
  // /workflow/[id] antes de a busca responder; só a rota diz qual é qual.
  const { id: idDaRota } = useParams<{ id?: string }>()
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  // O grafo já foi posto no canvas (loadNodes/loadEdges). É estado, e não a
  // ref `hidratadoPara`, porque precisa re-renderizar: é o que tira a
  // animação de carga e libera o botão de adicionar nó.
  const [hidratado, setHidratado] = useState(false)
  // Só a rota com id espera por alguma coisa; a tela de criação nasce pronta.
  const carregando = Boolean(idDaRota) && !hidratado
  usePinExpirationTimer()

  // Abre dialog quando o save detecta que o nome está vazio
  useEffect(() => {
    if (saveStatus === 'needs_name') setShowUnsavedDialog(true)
  }, [saveStatus])

  // Ver o comentário no <UnsavedDialog>: sem esta saída de 'needs_name', um
  // segundo clique em Salvar não reabre o diálogo. Fechar sem nomear não salvou
  // nada — se o canvas tem algo, o aviso de "não salvo" volta (o detector só
  // roda quando o grafo muda, então aqui a decisão é imediata).
  const fecharSemNomear = useCallback(() => {
    const store = useWorkflowSaveStore.getState()
    if (store.saveStatus !== 'needs_name') return
    const { nodesReq, edgesReq } = buildPayload()
    store.setStatus(store.isDirty(nodesReq, edgesReq, store.workflowName) ? 'unsaved' : 'idle')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Salva snapshot com debounce para não gerar histórico em cada keystroke de drag
  const debouncedSave = useCallback(() => {
    if (snapshotTimerRef.current) clearTimeout(snapshotTimerRef.current)
    snapshotTimerRef.current = setTimeout(saveSnapshot, 300)
  }, [saveSnapshot])

  const handleNodesChange = useCallback((changes: Parameters<typeof onNodesChange>[0]) => {
    onNodesChange(changes)
    // Só salva snapshot em mudanças estruturais (adicionar/remover/reposicionar após drag)
    const hasStructural = changes.some(c => c.type === "add" || c.type === "remove" || (c.type === "position" && !c.dragging))
    if (hasStructural) debouncedSave()
  }, [onNodesChange, debouncedSave])

  const handleEdgesChange = useCallback((changes: Parameters<typeof onEdgesChange>[0]) => {
    onEdgesChange(changes)
    // `replace` entra aqui porque trocar a chave de dado de uma aresta (badge
    // do CustomEdge) muda o que o nó destino recebe — é edição de conteúdo do
    // fluxo, tão desfazível quanto criar ou remover a conexão.
    const hasStructural = changes.some(
      c => c.type === "add" || c.type === "remove" || c.type === "replace",
    )
    if (hasStructural) debouncedSave()
  }, [onEdgesChange, debouncedSave])
  const { removeLinkNodeParam } = useLinkNodeParams()

  // Canvas → painel: clicar num nó rola até a linha dele no painel de execução.
  // Se o nó falhou e o painel está fechado, abre direto em "Problemas" — é o
  // caminho mais curto entre "vi o nó vermelho" e "sei por que ele quebrou".
  const revealNodeInPanel = useCallback((node: INodeContext) => {
    const panel = useRunPanelStore.getState()
    const execution = useWorkflowExecutionStore.getState()
    if (execution.events.length === 0) return

    const failed = execution.statusWorkflow?.nodes?.some(n => n.id === node.id && n.status === "failed")
    if (!panel.open && failed) panel.openAt("problems")
    if (panel.open || failed) panel.reveal(node.id)
  }, [])

  // Realce de caminho (hover/pin) e nível de detalhe por zoom.
  // Desestruturado de propósito: os handlers são estáveis individualmente, mas o
  // objeto de retorno é novo a cada render — usá-lo como dependência tornaria
  // `handleNodeClick` instável e re-renderizaria todos os nós (NodeRenderer é
  // `memo` e recebe `onNodeClick` como prop).
  const {
    onNodeMouseEnter,
    onNodeMouseLeave,
    onNodeClick: onNodeFocusClick,
    onPaneClick,
  } = useCanvasFocus()
  useZoomLod()

  const handleNodeClick = useCallback((event: React.MouseEvent, node: INodeContext) => {
    revealNodeInPanel(node)
    onNodeFocusClick(event, node)
  }, [revealNodeInPanel, onNodeFocusClick])

  // Avisa o usuário ao tentar fechar/recarregar a página com edições em
  // andamento — e SÓ nesse caso. Avisar sempre, como era, fazia o navegador
  // dizer "alterações podem não ser salvas" logo depois de um save, e essa era
  // justamente a dúvida que o usuário tinha ("salvou ou não?").
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      const { saveStatus } = useWorkflowSaveStore.getState()
      if (saveStatus === 'idle' || saveStatus === 'saved') return
      event.preventDefault();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Atalho Ctrl+S / Cmd+S para salvar o workflow
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveWorkflow()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [saveWorkflow])

  // Escuta evento do Command Palette para adicionar nó ao canvas
  useEffect(() => {
    function handleCommandAddNode(e: Event) {
      const node = (e as CustomEvent).detail
      if (!node?.name) return

      const apiNode = nodesAPI.find(n => n.name === node.name)
      if (!apiNode) return

      const viewPort = reactFlowInstance.getViewport()
      const clientWidth = domNode.current?.clientWidth ?? 0
      const clientHeight = domNode.current?.clientHeight ?? 0

      const properties: Record<string, string> = {}
      apiNode.properties.forEach(field => {
        const isObject = typeof field.default === "object"
        properties[field.name] = isObject ? field.default as string : field.default as string ?? ""
      })

      const newNode: INodeContext = {
        id: uuid(),
        type: getTypeIcon(node),
        data: {
          ...node,
          fields: apiNode.properties,
          properties,
          // Um lugar só: o `data` é montado aqui e no `loadNodes`, e campo
          // esquecido num deles funciona no nó novo e some ao recarregar.
          ...contratoDoNo(apiNode, properties),
        },
        position: {
          x: (clientWidth / 2) - viewPort.x - 80,
          y: (clientHeight / 2) - viewPort.y - 30,
        },
      }

      setNodes(prev => [...prev, newNode])
      setNewlyAddedNodeId(newNode.id)
    }

    window.addEventListener("command-add-node", handleCommandAddNode)
    return () => window.removeEventListener("command-add-node", handleCommandAddNode)
  }, [nodesAPI, reactFlowInstance, setNodes, setNewlyAddedNodeId])

  // Inicializa referências estáticas — apenas no mount.
  // setFlowContext aqui só atualiza os 3 campos imutáveis do context
  // (reactFlowInstance, flowRef, reloadWorkflow). Campos dinâmicos
  // (nodesAPI, credentials, pinnedNodes, drawerState) moveram para o
  // workflowCatalogStore (Zustand).
  useEffect(() => {
    setFlowContext({
      flowRef: domNode,
      reactFlowInstance,
      reloadWorkflow,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sincroniza workflowName e flagActive no store dedicado quando o workflow
  // mudar. Antes esses campos viviam no FlowContext, mas o refactor Zustand
  // (3089cba) os moveu para useWorkflowSaveStore. O setFlowContext aqui
  // estava escrevendo em campos inexistentes → workflowName ficava "" e todo
  // save caía em 'needs_name'; flagActive sempre true fazia Executar ficar
  // habilitado em workflows desativados.
  useEffect(() => {
    const saveStore = useWorkflowSaveStore.getState()
    saveStore.setWorkflowName(workflow?.name ?? "")
    saveStore.setFlagActive(workflow?.flag_ative ?? true)
  }, [workflow?.name, workflow?.flag_ative])

  // Reset de stores ao trocar de workflow — as stores Zustand são globais,
  // então ao navegar /workflow/A → /workflow/B o estado de execução/save de A
  // contaminaria B (nodes "completed" fantasmas, lastSavedSnapshot inválido,
  // isDirty falso-positivo, etc.). Limpa antes da hidratação do novo canvas.
  useEffect(() => {
    useWorkflowExecutionStore.getState().resetExecution()
    // A memória de colunas NÃO segue o reset de execução: ela pertence ao
    // workflow, não ao run — só a troca de workflow a limpa (e reabrir o mesmo
    // não). Node ids de um workflow duplicado repetem os do original, então
    // sem este corte as colunas de A apareceriam como sugestão em B.
    useKnownColumnsStore.getState().prepararParaWorkflow(idDaRota ?? null)
    // Limpa campos por-workflow do catálogo (pins, newly-added, drawer). nodesAPI
    // e credentials são do usuário (globais) e ficam intactos.
    useWorkflowCatalogStore.getState().resetWorkflowScoped()
    // Um realce fixado em A apontaria para ids que não existem em B.
    useCanvasViewStore.getState().resetView()
    // O visualizador de sub-fluxo cobre o canvas: deixado aberto, o sub-fluxo de
    // A ficaria sobreposto ao editor de B, com uma trilha de nós inexistentes.
    useSubflowDrilldownStore.getState().close()
    // Limpa snapshot e status — workflowName/flagActive são repopulados pelo
    // outro useEffect quando o prop `workflow` chegar.
    //
    // Num workflow existente o baseline verdadeiro é o pós-hidratação (o
    // primeiro initSnapshot real); até lá, sem snapshot, o detector fica
    // calado. Na tela de criação não haverá hidratação nenhuma — e sem
    // baseline o detector nunca rodava, então um workflow novo nunca dizia
    // "não salvo". Lá o baseline é o canvas vazio: o primeiro nó já é edição.
    // snapshotIniciadoEm zera nos dois casos: a janela de autocorreção pertence
    // à hidratação do novo workflow, e quem a abre é aquele initSnapshot.
    useWorkflowSaveStore.setState({
      lastSavedSnapshot: idDaRota ? null : JSON.stringify({ name: "", nodes: [], edges: [] }),
      lastSavedAt: null,
      lastError: null,
      isSaving: false,
      saveStatus: 'idle',
      snapshotIniciadoEm: null,
    })
    // Permite o effect de hidratação do snapshot rodar novamente para o novo workflow.
    snapshotInitializedFor.current = null
    // E o de viewport: o de B é o de B, não o enquadramento feito para A.
    initialFitDone.current = false
    // O canvas volta a esperar até o grafo de B entrar.
    setHidratado(false)
  }, [workflow?.id_hash, idDaRota])

  // Carrega pins do workflow
  useEffect(() => {
    if (workflow?.id_hash) loadPinnedNodes()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow?.id_hash])

  async function loadPinnedNodes() {
    if (!workflow?.id_hash) return
    const dados = dadoOuAviso(await GisFlowService.listPinnedNodes(workflow.id_hash), "Erro ao carregar nós fixados")
    if (dados?.pinned_nodes) setPinnedNodes(dados.pinned_nodes)
  }

  useEffect(() => {
    setOpen(false)
    removeLinkNodeParam()
    if (status === "authenticated") {
      // Dispara em paralelo — corta ~N×latency para ~max(latencies).
      // As duas listas são globais do usuário e sobrevivem à troca de workflow
      // (resetWorkflowScoped as preserva): quem decide se há download é o TTL da
      // store. Antes, ir para /projects e abrir outro fluxo rebaixava ~100 KB de
      // catálogo e o canvas só desenhava depois que ele chegava.
      Promise.all([getNodesAPI(), getCredentialsAPI()]).catch(() => { /* cada fetch loga o próprio erro */ })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const initialFitDone = useRef(false)

  // Carrega nodes e edges do workflow (não cuida do snapshot — esse fica em
  // outro effect que dispara quando o ReactFlow já processou os dados).
  //
  // A hidratação é IDEMPOTENTE por objeto de workflow, e não reage à identidade
  // de `nodesAPI`. Antes, qualquer escritor do catálogo (o Ctrl+K passou a ser
  // um, ao chamar ensureNodesAPI com TTL vencido) trocava a referência da lista
  // e este efeito redesenhava o grafo a partir de `workflow.definition` — o
  // objeto buscado UMA vez ao abrir a página. O canvas voltava ao estado inicial
  // e o save seguinte gravava essa reversão no backend. Só o que precisa mesmo
  // re-hidratar (restaurar uma versão via reloadWorkflow) troca o OBJETO
  // `workflow`, e é isso que a guarda deixa passar.
  const hidratadoPara = useRef<IWorkflow | null>(null)
  const catalogoDeNosPronto = nodesAPI.length > 0
  useEffect(() => {
    if (!workflow || !catalogoDeNosPronto) return
    if (hidratadoPara.current === workflow) return
    hidratadoPara.current = workflow
    // loadEdges precisa das portas declaradas por cada nó para resolver o
    // handle de origem — por isso consome o retorno de loadNodes.
    const loadedNodes = loadNodes()
    loadEdges(loadedNodes)
    setHidratado(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow, catalogoDeNosPronto])

  // Inicializa snapshot de referência APÓS o ReactFlow processar nodes/edges.
  // Usa buildPayload() — a mesma função do isDirty — para garantir simetria
  // total entre o snapshot inicial e a comparação posterior. Sem isso, o
  // detect-dirty acusava "Não salvo" mesmo sem edições, porque o snapshot
  // inicial (loadedNodes direto) divergia sutilmente do snapshot atual
  // (nodes via useNodes() já processado pelo ReactFlow).
  const snapshotInitializedFor = useRef<string | null>(null)
  useEffect(() => {
    if (!workflow?.id_hash) return
    if (snapshotInitializedFor.current === workflow.id_hash) return
    if (!nodesAPI?.length || nodes.length === 0) return

    snapshotInitializedFor.current = workflow.id_hash
    const { nodesReq, edgesReq } = buildPayload()
    // O `updated_at` do servidor é o "salvo às" que o chip mostra antes do
    // primeiro save desta sessão. `fromBackend` porque a data vem sem offset.
    initSnapshot(
      nodesReq, edgesReq, workflow.name ?? "",
      fromBackend(workflow.updated_at)?.valueOf() ?? null,
      viewportSalvoValido(workflow.definition?.viewport) ? workflow.definition.viewport : null,
    )
    // F10: baseline do histórico de undo/redo com o estado recém-hidratado. Sem
    // isto o histórico começa vazio e a PRIMEIRA edição de aresta não era
    // desfazível (undo guarda pointer <= 0). Espelha o initSnapshot do save.
    captureBaseline()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, workflow?.id_hash, workflow?.name, nodesAPI?.length])

  // Restaura o viewport salvo, ou enquadra os nós, depois do carregamento.
  //
  // Antes o viewport salvo era entregue ao <ReactFlow> por `defaultViewport`.
  // Só que essa prop vale UMA vez, na montagem — e o canvas monta antes de o
  // workflow chegar (a página renderiza com `workflow` undefined enquanto
  // busca). O valor real chegava tarde e era ignorado; este effect via um
  // viewport salvo, pulava o fitView, e o workflow abria em (0,0) com zoom 1,
  // como se nunca tivesse sido salvo. `setViewport` aplica de fato. Sem rAF: o
  // enquadramento precisa dos nós medidos, restaurar um viewport não — e
  // esperar um quadro é piscar na posição errada.
  useEffect(() => {
    if (nodes.length > 0 && !initialFitDone.current) {
      initialFitDone.current = true
      const savedViewport = workflow?.definition?.viewport
      if (viewportSalvoValido(savedViewport)) {
        reactFlowInstance.setViewport(savedViewport)
      } else {
        // Sem viewport salvo — enquadra todos os nodes
        requestAnimationFrame(() => reactFlowInstance.fitView({ padding: 0.15 }))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes])

  async function getNodesAPI() {
    try {
      await useWorkflowCatalogStore.getState().ensureNodesAPI()
    } catch (err) {
      createToast.error("Erro ao carregar nós", String(err))
    }
  }

  async function getCredentialsAPI() {
    try {
      await useWorkflowCatalogStore.getState().ensureCredentials()
    } catch (err) {
      createToast.error("Erro ao carregar credenciais", String(err))
    }
  }

  // A montagem em si vive em utils/build-canvas, pura: o visualizador de
  // sub-fluxo desenha o grafo de OUTRO workflow com as mesmas regras, e duplicá-las
  // faria o `data` divergir entre os dois canvas.
  function loadEdges(loadedNodes: INodeContext[] = []) {
    const edges = buildEdges(workflow?.definition, loadedNodes)
    setEdges(edges)
    return edges
  }

  function loadNodes() {
    const nodes = buildNodes(workflow?.definition, nodesAPI)
    setNodes(nodes)
    return nodes
  }

  function addEdgeWithKey(connection: Connection, from_key?: string, to_key?: string) {
    setEdges(prev => [
      ...prev,
      {
        ...connection,
        id: uuid(),
        type: 'custom',
        data: {
          ...(from_key ? { from_key } : {}),
          ...(to_key   ? { to_key   } : {}),
        },
      }
    ])
  }

  function handleConnectNodes(connections: Connection) {
    // A validação mora em `validarConexao` (uma casa só, derivada do
    // catálogo): auto-conexão, duplicata, funil sem portas e tipo
    // incompatível. `isValidConnection` já segura o gesto na maioria dos
    // casos; aqui é a segunda linha (e a que fala) — o toast explica o que a
    // linha recusada não diz.
    const recusa = validarConexao(connections, nodes as never[], edges)
    if (recusa) {
      toast.warning(MENSAGEM_DE_RECUSA[recusa])
      return
    }

    const sourceNode = nodes.find(n => n.id === connections.source)
    const targetNode = nodes.find(n => n.id === connections.target)

    // Candidatos de from_key: os campos de saída do nó (ver getCandidateKeys).
    // Mesma regra usada pelo botão "+" do handle (drawer) — ver resolve-edge-keys.
    const candidateKeys = getCandidateKeys(sourceNode?.data)

    // Só preenche quando o destino declara múltiplos inputs nomeados — a regra
    // vive em resolve-edge-keys porque o botão "+" (drawer) cria aresta também.
    const to_key = resolveToKey(connections.targetHandle, targetNode?.data?.inputs)

    if (connections.sourceHandle) {
      const handleIsDataKey = candidateKeys.some(f => f.name === connections.sourceHandle)

      if (handleIsDataKey) {
        // Handle de porta (DefaultTypeIcon, triggers): o handle já é a chave de dado
        addEdgeWithKey(connections, connections.sourceHandle, to_key)
        return
      }

      // Handle de roteamento (ex: "true"/"false"): a chave de DADO ainda precisa
      // ser escolhida, mas não vale interromper — nasce com o primeiro
      // candidato e o badge da aresta permite trocar.
      addEdgeWithKey(connections, candidateKeys[0]?.name, to_key)
      return
    }

    // Sem sourceHandle: mesma regra. Zero candidatos deixa a aresta sem
    // from_key (executor espalha tudo via inputs.update — comportamento legado
    // mantido para nós sem schema declarado).
    addEdgeWithKey(connections, candidateKeys[0]?.name, to_key)
  }

  return (
    <>

      {/* Fechar sem nomear precisa DEVOLVER o status. `saveWorkflow` responde a
          um nome vazio com `setStatus('needs_name')`; se o status já for esse, o
          seletor da store compara igual, nada re-renderiza, o efeito que abre
          este diálogo não dispara — e o botão Salvar passa a não fazer nada.
          Enquanto o nome era editável no canvas havia saída; agora não há. */}
      <UnsavedDialog
        open={showUnsavedDialog}
        onOpenChange={aberto => {
          setShowUnsavedDialog(aberto)
          if (!aberto) fecharSemNomear()
        }}
        onSave={() => { setShowUnsavedDialog(false); saveWorkflow() }}
        onDiscard={() => { setShowUnsavedDialog(false); fecharSemNomear() }}
      />

      <WorkflowDrawer />

      <NodeConfigModal />

      <div className="flex w-full h-full relative">

        {/* A área do canvas é um wrapper próprio para que ela ENCOLHA quando a
            gaveta do assistente abre — e com ela o botão de adicionar nó, que
            antes ancorava na página e ficava debaixo da gaveta. Com a gaveta
            fechada o wrapper é exatamente a caixa de antes. */}
        <div className="relative flex h-full min-w-0 flex-1">

        {/* Some no telefone junto com o resto da edição: um botão que abre um
            catálogo para inserir nós não faz sentido num canvas onde eles não
            podem ser posicionados nem conectados. */}
        {/* Enquanto o workflow carrega o botão some (e não pulsa): o canvas está
            vazio porque o grafo ainda não chegou, não porque o workflow é novo. */}
        {!canvasSomenteLeitura && (
          <Button
            size="icon"
            onClick={() => setNodesDrawerState('opened')}
            className={`absolute z-10 top-5 right-5 h-11 w-11 rounded-lg shadow-lg
              bg-primary hover:bg-primary/90 text-primary-foreground border-0
              transition-all hover:scale-105 active:scale-95
              ${carregando ? "opacity-0 pointer-events-none" : ""}
              ${nodes.length === 0 && !carregando ? "add-node-pulse" : ""}`}
            title="Adicionar nó"
          >
            <TbPlus size={22} strokeWidth={2.5} />
          </Button>
        )}

        <ReactFlow nodes={nodes}
          colorMode={theme}
          ref={domNode}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          nodeTypes={nodeTypesFlow}
          edgeTypes={customEdges}
          onConnect={handleConnectNodes}
          // A16: a linha proibida nem cola — mesma regra do onConnect,
          // derivada do catálogo (ver utils/valida-conexao).
          isValidConnection={(c) => validarConexao(c as Connection, nodes as never[], edges) === null}
          onNodeClick={handleNodeClick}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          onPaneClick={onPaneClick}
          onlyRenderVisibleElements
          // Visualizador no telefone. `elementsSelectable` continua ligado de
          // propósito: tocar um nó é como se abre a configuração e como o
          // realce de caminho ancora — desligar isso tiraria a navegação junto
          // com a edição. `deleteKeyCode` some porque um teclado externo (ou o
          // do próprio sistema) ainda alcança o canvas.
          nodesDraggable={!canvasSomenteLeitura}
          nodesConnectable={!canvasSomenteLeitura}
          edgesReconnectable={!canvasSomenteLeitura}
          deleteKeyCode={canvasSomenteLeitura ? null : undefined}
        >

          <CanvasInteractionProvider>
          <CanvasViewLayer />
          <CanvasLoading carregando={carregando} />

          {/* O chip de salvamento vai na mesma fileira da trilha — é junto do
              nome do workflow que se procura "isto está salvo?". */}
          <WorkflowLocation workspaceId={workflow?.workspace_id} carregando={carregando}>
            <GlobalSaveIndicator />
          </WorkflowLocation>

          <ActionsButton workflow={workflow} />

          <RunPanel />

          <Background
            variant={theme === "dark" ? BackgroundVariant.Cross : BackgroundVariant.Dots} gap={12} size={1} />

          <CanvasToolbar
            onUndo={undo}
            onRedo={redo}
            canUndo={canUndo}
            canRedo={canRedo}
            onSaveSnapshot={saveSnapshot}
          />

          </CanvasInteractionProvider>
        </ReactFlow>

        </div>

        {/* Irmã flex do canvas, e não sobreposição: o canvas encolhe e os dois
            ficam visíveis — dá para ver o fluxo aparecer enquanto se lê a
            explicação. O assistente NÃO grava; aplicar é o que traz a definição
            para cá, e salvar continua sendo o botão Salvar.

            O snapshot vem ANTES do `setNodes`: é ele que faz Ctrl+Z desfazer
            uma aplicação, que é a rede de segurança de um botão destrutivo. */}
        <AssistentePainel
          workflowId={workflow?.id_hash}
          abrirPorPadrao={!idDaRota}
          onAplicar={aplicarDoAssistente}
        />

        {/* Sobreposto ao canvas, e não dentro dele: é um segundo React Flow, com
            provider próprio, desenhando o grafo do sub-fluxo executado. */}
        <SubflowViewer rootLabel={workflow?.name ?? ""} />
      </div>

    </>
  )
}

export default ReactFlowComponent
