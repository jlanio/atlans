import { useCallback, useEffect, useRef } from "react"
import { Edge, useStoreApi, type NodeMouseHandler } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import { useCanvasViewStore } from "@/app/stores/canvasViewStore"
import { FocusGraph, buildFocusGraph, collectPath } from "@/app/components/workflow/utils/graph-traversal"

/** Atraso antes de realçar — evita piscar ao arrastar o cursor pelo canvas. */
const ENTER_DELAY = 90
/** Atraso antes de apagar — assimétrico de propósito: sair rápido demais faz o
 *  grafo piscar ao cruzar a borda entre dois cards vizinhos. */
const LEAVE_DELAY = 140

/**
 * Realce de caminho: passar o mouse sobre um nó destaca tudo que o alimenta e
 * tudo que ele alimenta; clicar fixa o realce até clicar no canvas ou apertar
 * Escape. `F` liga/desliga o modo.
 *
 * Chamado uma única vez no componente raiz do canvas — não por nó.
 *
 * PERF: os quatro handlers têm identidade estável para sempre. Eles são
 * repassados ao `<ReactFlow>`, e o `NodeRenderer` é `memo` recebendo-os como
 * props — um handler novo a cada render re-renderizaria TODOS os nós do canvas.
 * Por isso as arestas são lidas da store no momento do evento (via `getState()`)
 * em vez de por `useEdges()`: nada aqui entra na lista de dependências.
 */
export function useCanvasFocus() {

  const store = useStoreApi()
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const graphCache = useRef<{ source: Edge[]; graph: FocusGraph } | null>(null)

  const schedule = useCallback((delay: number, run: () => void) => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(run, delay)
  }, [])

  const cancel = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
  }, [])

  useEffect(() => cancel, [cancel])

  const focus = useCallback((nodeId: string, origin: "hover" | "pin") => {
    const edges = store.getState().edges
    // Memo por identidade do array: o grafo só é remontado quando a topologia
    // muda de fato, não a cada hover.
    if (graphCache.current?.source !== edges) {
      graphCache.current = { source: edges, graph: buildFocusGraph(edges) }
    }

    const { nodes, edges: touched } = collectPath(graphCache.current.graph, nodeId)
    useCanvasViewStore.getState().applyFocus(nodeId, origin, nodes, touched)
  }, [store])

  const onNodeMouseEnter = useCallback<NodeMouseHandler<INodeContext>>((event, node) => {
    const { focusEnabled, focusOrigin } = useCanvasViewStore.getState()
    if (!focusEnabled) return
    // O pin é deliberado — passar o mouse por cima não o substitui.
    if (focusOrigin === "pin") return
    // Arrastando um nó ou puxando uma conexão: esmaecer o grafo atrapalha a mira.
    if (event.buttons !== 0) return
    if (store.getState().connection.inProgress) return

    schedule(ENTER_DELAY, () => focus(node.id, "hover"))
  }, [focus, schedule, store])

  const onNodeMouseLeave = useCallback<NodeMouseHandler<INodeContext>>(() => {
    schedule(LEAVE_DELAY, () => useCanvasViewStore.getState().clearFocus("hover"))
  }, [schedule])

  /** Composto com o handler de clique já existente do canvas — só alterna o pin. */
  const onNodeClick = useCallback<NodeMouseHandler<INodeContext>>((_, node) => {
    const { focusEnabled, focusNodeId, focusOrigin, clearFocus } = useCanvasViewStore.getState()
    if (!focusEnabled) return

    cancel()

    if (focusOrigin === "pin" && focusNodeId === node.id) clearFocus("pin")
    else focus(node.id, "pin")
  }, [cancel, focus])

  const onPaneClick = useCallback(() => {
    cancel()
    useCanvasViewStore.getState().clearFocus("pin")
  }, [cancel])

  // Escape solta o pin; F liga/desliga o modo. Mesma guarda de campos de texto
  // usada pelos atalhos de undo/redo.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      const tag = target?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable) return
      if (event.ctrlKey || event.metaKey || event.altKey) return

      if (event.key === "Escape") {
        useCanvasViewStore.getState().clearFocus("pin")
        return
      }

      // Sem `preventDefault`: uma letra solta fora de campo de texto não tem
      // ação padrão para cancelar, e cancelá-la quebraria o typeahead de
      // componentes como o Select do Radix.
      if (event.key === "f" || event.key === "F") {
        useCanvasViewStore.getState().toggleFocusEnabled()
      }
    }

    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return { onNodeMouseEnter, onNodeMouseLeave, onNodeClick, onPaneClick }
}
