"use client"
import { useEffect, useState } from "react"
import { useReactFlow } from "@xyflow/react"
import {
  TbCircleCheck, TbCircleX, TbCircleDashed, TbAlertTriangle, TbHelpCircle,
} from "react-icons/tb"
import ExecActivity from "@/app/components/shared/exec-activity"
import { cn } from "@/lib/utils"
import { NodeRun, NodeRunStatus } from "./timeline"
import { useRunPanelStore } from "@/app/stores/runPanelStore"
import { SubflowLevel, useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore"
import { caminhoDeChamada, idLocal } from "../utils/subflow-path"

/** Rótulos PT-BR das categorias da taxonomia de erro do backend.
 *
 * O backend publica a categoria estável (string); a tradução vive aqui para o
 * painel poder dizer "não adianta repetir, corrija a entrada" em vez de só
 * despejar o stack trace.
 */
export const ERROR_CATEGORY_LABEL: Record<string, string> = {
  user:       "Entrada ou configuração inválida",
  validation: "Reprovado na validação de segurança",
  timeout:    "Tempo limite excedido",
  resource:   "Recursos insuficientes (memória)",
  transient:  "Falha temporária de infraestrutura",
  internal:   "Erro interno inesperado",
}

const MINUTE_MS = 60_000

/** Acima de um minuto, `m:ss` — "2m07s" se lê de imediato; "127.40s" não. */
function longForm(ms: number): string {
  const minutes = Math.floor(ms / MINUTE_MS)
  const seconds = Math.floor((ms % MINUTE_MS) / 1000)
  return `${minutes}m${String(seconds).padStart(2, "0")}s`
}

export function formatOffset(ms: number | null): string {
  if (ms == null) return "—"
  if (ms < 1000) return `+${Math.round(ms)}ms`
  if (ms >= MINUTE_MS) return `+${longForm(ms)}`
  return `+${(ms / 1000).toFixed(2)}s`
}

export function formatMs(ms?: number | null): string {
  if (ms == null) return "—"
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms >= MINUTE_MS) return longForm(ms)
  return `${(ms / 1000).toFixed(2)}s`
}

// O painel e o card do nó falam do MESMO estado, a poucos centímetros um do
// outro, então usam o mesmo glifo e a mesma cor. O `running` mostrava um
// spinner girando enquanto o card mostrava as barras de atividade, e as cores
// vinham de classes fixas do Tailwind em vez dos tokens `--exec-*` — que, ao
// contrário delas, acompanham o tema.
export function NodeStatusIcon({ status, size = 13 }: { status: NodeRunStatus; size?: number }) {
  if (status === "completed") return <TbCircleCheck size={size} className="text-exec-success shrink-0" />
  if (status === "failed")    return <TbCircleX size={size} className="text-exec-error shrink-0" />
  if (status === "running")   return <ExecActivity size={size} className="text-exec-running shrink-0" />
  // `unknown` NÃO pode cair no ícone de "aguardando": o nó começou, o run
  // acabou, e o que falta é a notícia do término — não o trabalho.
  if (status === "unknown")   return <TbHelpCircle size={size} className="text-exec-unknown shrink-0" />
  return <TbCircleDashed size={size} className="text-muted-foreground/40 shrink-0" />
}

export function DriftBadge({ drift }: { drift: { missing: string[]; extra: string[] } }) {
  const parts = [
    drift.missing.length > 0 ? `faltando ${drift.missing.join(", ")}` : null,
    drift.extra.length > 0 ? `extra ${drift.extra.join(", ")}` : null,
  ].filter(Boolean).join(" · ")
  return (
    <span
      title={`Schema declarado difere da saída real: ${parts}`}
      className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-px text-[10px] text-amber-600 dark:text-amber-400"
    >
      <TbAlertTriangle size={10} /> schema
    </span>
  )
}

/** Cronômetro auto-contido — só monta enquanto algo está de fato rodando.
 *
 * O painel antigo derivava `startedAt` de `Date.now()` dentro de um `useMemo`
 * que dependia do array de nós, e esse array muda a cada mensagem do WebSocket:
 * o contador voltava para zero a cada evento de qualquer nó.
 */
export function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(id)
  }, [])
  const ms = Math.max(0, now - since)
  const text = ms >= MINUTE_MS
    ? longForm(ms)
    : ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
  return <span className="tabular-nums">{text}</span>
}

/** Linha do painel que sabe a qual nó do CANVAS corresponde.
 *
 * Só `canvasNodeId` — nunca `nodeId`. Para um nó de dentro de sub-fluxo os dois
 * são diferentes: o id do filho não existe no canvas do pai, e usá-lo aqui era
 * um no-op silencioso (nem foco, nem destaque, nem configuração). Pedir a linha
 * inteira em vez de uma string tira a escolha de quem chama — passar o id
 * errado deixa de compilar.
 */
export interface AlvoNoCanvas {
  canvasNodeId: string
}

/** Ações de correlação painel → canvas. */
export function useNodeFocus() {
  const reactFlow = useReactFlow()
  const guardarHover = useRunPanelStore(s => s.setHovered)

  function setHovered(alvo: AlvoNoCanvas | null) {
    guardarHover(alvo?.canvasNodeId ?? null)
  }

  /** Seleciona e centraliza o nó no canvas — possível porque o painel deixou
   *  de ser modal: antes o overlay do Sheet cobria e desabilitava o canvas. */
  function focusNode(alvo: AlvoNoCanvas) {
    const nodeId = alvo.canvasNodeId
    const exists = reactFlow.getNodes().some(n => n.id === nodeId)
    if (!exists) return
    // Só realoca os nós cuja seleção MUDOU. Recriar o array inteiro fazia todo
    // o grafo re-renderizar a cada clique numa linha do painel.
    reactFlow.setNodes(nodes => nodes.map(n => {
      const selected = n.id === nodeId
      return n.selected === selected ? n : { ...n, selected }
    }))
    reactFlow.fitView({ nodes: [{ id: nodeId }], duration: 400, maxZoom: 1.3, padding: 0.6 })
  }

  return { focusNode, setHovered }
}

/**
 * Painel → canvas do sub-fluxo: abre o grafo do filho no nó que esta linha
 * representa.
 *
 * Complementa `focusNode`, que para uma linha de dentro de sub-fluxo só consegue
 * centralizar o nó SubWorkflow do pai — o único id daquela linha que existe no
 * canvas do editor. Aqui o destino é o nó de verdade.
 *
 * O caminho sai do `nodeId` da linha, que é o endereço completo (`sA::sB::X`);
 * o `workflowHash` de cada degrau vem dos nós SubWorkflow atravessados. Só o
 * primeiro degrau está no canvas do editor: os seguintes vivem dentro de fluxos
 * ainda não carregados, e o visualizador os resolve ao descer.
 */
export function useAbrirSubfluxo() {
  const reactFlow = useReactFlow()
  const open = useSubflowDrilldownStore(s => s.open)

  /** A linha veio de dentro de um sub-fluxo E dá para montar o caminho? */
  function podeAbrir(node: NodeRun): boolean {
    return caminhoDeChamada(node.nodeId).length > 0 && !!hashDoNoNoCanvas(node)
  }

  function hashDoNoNoCanvas(node: NodeRun): string {
    const raiz = caminhoDeChamada(node.nodeId)[0]
    const alvo = reactFlow.getNodes().find(n => n.id === raiz)
    const props = (alvo?.data?.properties ?? {}) as Record<string, unknown>
    return String(props.workflowHash ?? "").trim()
  }

  function abrir(node: NodeRun) {
    const caminho = caminhoDeChamada(node.nodeId)
    if (caminho.length === 0) return

    const nosDoCanvas = reactFlow.getNodes()
    // Só o degrau raiz é resolvível daqui. Os mais fundos entram com hash vazio
    // e o visualizador os preenche ao descer — mas a descida direta para um nível
    // profundo pararia no primeiro degrau sem hash, então abrimos até ali.
    const degraus: SubflowLevel[] = []
    for (const canvasNodeId of caminho) {
      const noCanvas = nosDoCanvas.find(n => n.id === canvasNodeId)
      const props = (noCanvas?.data?.properties ?? {}) as Record<string, unknown>
      const hash = String(props.workflowHash ?? "").trim()
      if (!hash) break
      const data = (noCanvas?.data ?? {}) as { alias?: string }
      degraus.push({
        canvasNodeId,
        workflowHash: hash,
        label: (props.alias as string) || data.alias || "Sub-fluxo",
      })
    }
    if (degraus.length === 0) return

    // Centraliza o nó da linha só quando chegamos ao nível dele; parando antes,
    // o alvo não existe no grafo aberto e o visualizador enquadra o todo.
    const chegou = degraus.length === caminho.length
    open(degraus, chegou ? idLocal(node.nodeId) : null)
  }

  return { abrir, podeAbrir }
}

/** Destaca no DOM o nó sob o cursor no painel.
 *
 * Alterna uma classe direto no elemento do React Flow em vez de passar por
 * `setNodes` — mudar o array de nós a cada hover re-renderizaria o grafo inteiro.
 */
export function useCanvasHoverHighlight() {
  const hoveredNodeId = useRunPanelStore(s => s.hoveredNodeId)
  useEffect(() => {
    if (!hoveredNodeId) return
    const el = document.querySelector(`.react-flow__node[data-id="${CSS.escape(hoveredNodeId)}"]`)
    el?.classList.add("run-panel-hover")
    return () => el?.classList.remove("run-panel-hover")
  }, [hoveredNodeId])
}

/** Destaca termos da busca dentro de um texto. */
export function Highlight({ text, term }: { text: string; term: string }) {
  if (!term) return <>{text}</>
  const index = text.toLowerCase().indexOf(term.toLowerCase())
  if (index < 0) return <>{text}</>
  return (
    <>
      {text.slice(0, index)}
      <mark className="bg-amber-300/40 text-inherit rounded-sm px-px">
        {text.slice(index, index + term.length)}
      </mark>
      {text.slice(index + term.length)}
    </>
  )
}

export function EmptyHint({ children }: { children: React.ReactNode }) {
  return (
    <p className={cn("p-6 text-center text-xs text-muted-foreground/60 select-none")}>
      {children}
    </p>
  )
}
