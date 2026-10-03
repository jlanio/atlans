import { CSSProperties } from "react"
import { INodeContext } from "@/context/useFlowContext"

/**
 * Geometric metrics of the node card.
 *
 * Single source for the node components (which need the height to position
 * the ports) and for the auto-layout (which needs it to avoid overlapping cards).
 * The calculation used to be duplicated in `types/default-type.tsx` and
 * `types/trigger/default-trigger-icon.tsx`, and the auto-layout used a fixed
 * vertical step that ignored tall nodes.
 */

/** Largura do card — definida em `icon-root.tsx` via `w-[158px]`. */
export const NODE_WIDTH = 158

/** Minimum card height — `icon-root.tsx` via `h-[60px]`. */
export const NODE_MIN_HEIGHT = 60

/** Vertical space reserved per port, so the edges do not stick together. */
export const PX_PER_PORT = 26

/** Card height as a function of the number of ports on the more populated side. */
export function calcNodeHeight(portCount: number): number {
  return Math.max(NODE_MIN_HEIGHT, portCount * PX_PER_PORT + 8)
}

type PortStyle = CSSProperties & { '--port-top': string }

/**
 * Distributes port `index` of `total` evenly along the height.
 * The value comes out as a CSS var consumed by the `.port-top` class (globals.css) —
 * the class is static so Tailwind can scan it.
 */
export function portTopStyle(index: number, total: number, height: number): PortStyle {
  const px = Math.round(((index + 1) / (total + 1)) * height)
  return { '--port-top': `${px}px` }
}

/**
 * Effective height of an already mounted node. Prefers React Flow's real
 * measurement (`measured`, filled by v12's ResizeObserver) and falls back to the
 * per-port calculation when the node has not been measured yet — the case of a
 * freshly created node or of a node outside the viewport with
 * `onlyRenderVisibleElements`.
 */
export function measuredHeight(node: INodeContext): number {
  const measured = node.measured?.height
  if (measured && measured > 0) return measured

  const outputs = Array.isArray(node.data?.outputs) ? node.data.outputs.length : 0
  const inputs = Array.isArray(node.data?.inputs) ? node.data.inputs.length : 0
  const isOutputNode = node.data?.type === "output"

  return calcNodeHeight(Math.max(isOutputNode ? 0 : outputs, inputs))
}

/** Effective width of an already mounted node, falling back to the card's fixed width. */
export function measuredWidth(node: INodeContext): number {
  const measured = node.measured?.width
  return measured && measured > 0 ? measured : NODE_WIDTH
}
