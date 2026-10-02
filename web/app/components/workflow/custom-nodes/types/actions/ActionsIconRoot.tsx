import { NodeProps, useNodeConnections } from "@xyflow/react";
import { memo, ReactNode, useCallback } from "react";
import IconRoot from "../../icon-root";
import { HandleSource, HandleTarget } from "../../handle";
import AddConnectionHandle from "../../add-connection-handle";
import { INodeContext } from "@/context/useFlowContext";
import ToolsIcon from "../../tools";
import { useTools } from "@/app/hooks/workflow/useTools";

interface ActionsIconRootProps extends NodeProps<INodeContext> {
  children: ReactNode
}

// `selected` vem da prop do React Flow — ver o comentário em default-type.tsx.
const ActionsIconRoot = ({ children, id, data, selected }: ActionsIconRootProps) => {

  const { toolState, handleToolState } = useTools()

  const onEnter = useCallback(() => handleToolState('onFocus'), [handleToolState])
  const onLeave = useCallback(() => handleToolState('leave'), [handleToolState])

  // `useNodeConnections` lê o índice de conexões que o React Flow já mantém por
  // nó. Antes isto era um efeito que varria TODAS as arestas (O(N·E) somando o
  // canvas) e chamava setState: além do custo, forçava um segundo commit por
  // nó, e era por isso que o "+" do handle piscava a cada nova conexão.
  const saidas = useNodeConnections({ id, handleType: "source" })
  // Mesma fonte das saídas: a porta de entrada também precisa saber se está
  // ligada para escolher entre traço sólido e tracejado.
  const entradas = useNodeConnections({ id, handleType: "target" })

  const title = (data.properties?.["alias"] as string | undefined) || (data.alias as string)

  return (
    <IconRoot
      id={id}
      nodeType="action"
      title={title}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      data-selected={`${!!selected}`}
    >
      <ToolsIcon nodeId={id} open={toolState !== "disable"} />

      {children}

      <AddConnectionHandle nodeId={id} connectionVisible={saidas.length === 0}>
        <HandleSource livre={saidas.length === 0} />
      </AddConnectionHandle>

      <HandleTarget livre={entradas.length === 0} />
    </IconRoot>
  )
}

// memo: evita re-render quando o pai (ex: HttpRequestIcon) re-renderiza sem
// mudança real nos props do node (shallow compare em id/data/selected/dragging
// já cobre os casos reais — data é referencialmente estável no ReactFlow).
export default memo(ActionsIconRoot);
