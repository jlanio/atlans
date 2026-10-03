import { JSX } from "react"
import { NodeProps } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import CustomEdge from "./custom-edges"
import DefaultTypeIcon from "./custom-nodes/types/default-type"
import ConditionalIcon from "./custom-nodes/types/control/ConditionalIcon"
import DefaultTriggerIcon from "./custom-nodes/types/trigger/default-trigger-icon"
import NotFoundIcon from "./custom-nodes/NotFoundIcon"
import HttpRequestIcon from "./custom-nodes/types/actions/HttpRequestIcon"

/**
 * React Flow render maps — which components draw each node and each edge.
 *
 * They live in their own module, not in the editor, because two consumers need
 * them without needing the whole editor: `getTypeIcon` (utils), which only looks
 * up the keys to pick the icon, and the sub-workflow viewer, which builds a
 * second read-only canvas. Importing from `workflow/index.tsx` pulled the full
 * editor — with its save, history and execution hooks — into both, and closed
 * an import cycle between the editor and a utility it uses itself.
 */
export const nodeTypesFlow = {
  //default-trigger
  "DefaultTriggerIcon": DefaultTriggerIcon,

  //action
  "HttpRequest": HttpRequestIcon,

  //control
  "Conditional": ConditionalIcon,

  //notfound
  "NotFound": NotFoundIcon,

  //default
  "DefaultIcon": DefaultTypeIcon,

} as Record<"NotFound" | "DefaultIcon" | (string & {}), (nodeProps: NodeProps<INodeContext>) => JSX.Element>

export const customEdges = {
  "custom": CustomEdge
}
