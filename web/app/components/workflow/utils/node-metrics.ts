import { CSSProperties } from "react"
import { INodeContext } from "@/context/useFlowContext"

/**
 * Métricas geométricas do card de nó.
 *
 * Fonte única para os componentes de nó (que precisam da altura para posicionar
 * as portas) e para o auto-layout (que precisa dela para não sobrepor cards).
 * Antes o cálculo estava duplicado em `types/default-type.tsx` e
 * `types/trigger/default-trigger-icon.tsx`, e o auto-layout usava um passo
 * vertical fixo que ignorava nós altos.
 */

/** Largura do card — definida em `icon-root.tsx` via `w-[158px]`. */
export const NODE_WIDTH = 158

/** Altura mínima do card — `icon-root.tsx` via `h-[60px]`. */
export const NODE_MIN_HEIGHT = 60

/** Espaço vertical reservado por porta, para as arestas não se colarem. */
export const PX_PER_PORT = 26

/** Altura do card em função do número de portas do lado mais populoso. */
export function calcNodeHeight(portCount: number): number {
  return Math.max(NODE_MIN_HEIGHT, portCount * PX_PER_PORT + 8)
}

type PortStyle = CSSProperties & { '--port-top': string }

/**
 * Distribui a porta `index` de `total` uniformemente ao longo da altura.
 * O valor sai como CSS var consumida pela classe `.port-top` (globals.css) —
 * a classe é estática para o Tailwind conseguir escaneá-la.
 */
export function portTopStyle(index: number, total: number, height: number): PortStyle {
  const px = Math.round(((index + 1) / (total + 1)) * height)
  return { '--port-top': `${px}px` }
}

/**
 * Altura efetiva de um nó já montado. Prefere a medição real do React Flow
 * (`measured`, preenchido pelo ResizeObserver do v12) e cai no cálculo por
 * portas quando o nó ainda não foi medido — caso de nó recém-criado ou de
 * nó fora da viewport com `onlyRenderVisibleElements`.
 */
export function measuredHeight(node: INodeContext): number {
  const measured = node.measured?.height
  if (measured && measured > 0) return measured

  const outputs = Array.isArray(node.data?.outputs) ? node.data.outputs.length : 0
  const inputs = Array.isArray(node.data?.inputs) ? node.data.inputs.length : 0
  const isOutputNode = node.data?.type === "output"

  return calcNodeHeight(Math.max(isOutputNode ? 0 : outputs, inputs))
}

/** Largura efetiva de um nó já montado, com fallback na largura fixa do card. */
export function measuredWidth(node: INodeContext): number {
  const measured = node.measured?.width
  return measured && measured > 0 ? measured : NODE_WIDTH
}
