import { useCallback, useRef, useEffect, useReducer } from "react"
import { Edge, useReactFlow } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"

interface Snapshot {
  nodes: INodeContext[]
  edges: Edge[]
}

const MAX_HISTORY = 50

/**
 * Hook de undo/redo para o canvas ReactFlow.
 * - Chame `saveSnapshot()` após cada operação que deve ser desfeita (adicionar/remover nó, etc.)
 * - Registra Ctrl+Z / Ctrl+Y automaticamente.
 */
export function useCanvasHistory() {
  const { getNodes, getEdges, setNodes, setEdges } = useReactFlow<INodeContext, Edge>()

  const history = useRef<Snapshot[]>([])
  const pointer = useRef(-1)  // -1 = nenhum snapshot ainda
  const isTravelingRef = useRef(false)  // evita salvar durante undo/redo

  // `history`/`pointer` são refs para não re-renderizar o canvas a cada snapshot,
  // mas `canUndo`/`canRedo` derivam deles — sem este bump os botões da toolbar
  // ficavam presos em `disabled` até que algo *outro* re-renderizasse o canvas.
  const [, bumpVersion] = useReducer((v: number) => v + 1, 0)

  /** Salva o estado atual no histórico (descarta futuros após o ponteiro). */
  const saveSnapshot = useCallback(() => {
    if (isTravelingRef.current) return

    const snapshot: Snapshot = {
      nodes: getNodes() as INodeContext[],
      edges: getEdges(),
    }

    // Remove snapshots "futuros" (após desfazer e depois mudar)
    history.current = history.current.slice(0, pointer.current + 1)
    history.current.push(snapshot)

    // Limita o tamanho do histórico
    if (history.current.length > MAX_HISTORY) {
      history.current = history.current.slice(-MAX_HISTORY)
    }

    pointer.current = history.current.length - 1
    bumpVersion()
  }, [getNodes, getEdges])

  /**
   * Reinicia o histórico com o estado ATUAL do canvas como baseline (pointer=0).
   * Chamar UMA vez após a hidratação de um workflow. Sem um baseline, o histórico
   * começa vazio (pointer=-1) e o primeiro snapshot é o estado PÓS-edição; como
   * `undo()` guarda `pointer <= 0`, a PRIMEIRA edição de aresta (delete / troca de
   * from_key) ficava presa e nunca era desfeita (F10). Resetar também evita que o
   * histórico de um workflow vaze para o próximo ao trocar de workflow.
   */
  const captureBaseline = useCallback(() => {
    history.current = [{ nodes: getNodes() as INodeContext[], edges: getEdges() }]
    pointer.current = 0
    bumpVersion()
  }, [getNodes, getEdges])

  const undo = useCallback(() => {
    if (pointer.current <= 0) return
    pointer.current -= 1
    const snap = history.current[pointer.current]
    isTravelingRef.current = true
    setNodes(snap.nodes)
    setEdges(snap.edges)
    bumpVersion()
    setTimeout(() => { isTravelingRef.current = false }, 0)
  }, [setNodes, setEdges])

  const redo = useCallback(() => {
    if (pointer.current >= history.current.length - 1) return
    pointer.current += 1
    const snap = history.current[pointer.current]
    isTravelingRef.current = true
    setNodes(snap.nodes)
    setEdges(snap.edges)
    bumpVersion()
    setTimeout(() => { isTravelingRef.current = false }, 0)
  }, [setNodes, setEdges])

  const canUndo = pointer.current > 0
  const canRedo = pointer.current < history.current.length - 1

  // Registra atalhos globais de teclado no canvas
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Ignora quando o foco está em input/textarea
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable) return

      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "z") {
        e.preventDefault()
        undo()
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.shiftKey && e.key === "z"))) {
        e.preventDefault()
        redo()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [undo, redo])

  return { saveSnapshot, captureBaseline, undo, redo, canUndo, canRedo }
}
