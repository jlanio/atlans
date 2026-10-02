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
 * Mapas de renderização do React Flow — quais componentes desenham cada nó e
 * cada aresta.
 *
 * Vivem num módulo próprio, e não no editor, porque dois consumidores precisam
 * deles sem precisar do editor inteiro: `getTypeIcon` (utils), que só consulta
 * as chaves para escolher o ícone, e o visualizador de sub-fluxo, que monta um
 * segundo canvas read-only. Importar do `workflow/index.tsx` puxava o editor
 * completo — com seus hooks de save, histórico e execução — para dentro de
 * ambos, e fechava um ciclo de imports entre o editor e um utilitário que ele
 * mesmo usa.
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
