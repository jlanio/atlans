import { useLinkNodeParams } from "@/app/hooks/workflow/useLinkNodeParams";
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore";
import { useSubflowReadOnly } from "../subflow-viewer/scope";
import { cn } from "@/lib/utils";
import { HTMLAttributes, ReactNode } from "react";
import { FaPlus } from "react-icons/fa";

interface AddConnectionHandleProps extends HTMLAttributes<HTMLDivElement> {
  connectionVisible?: boolean
  nodeId: string
  handleId?: string
  children: ReactNode
  label?: string
}

const AddConnectionHandle = ({ connectionVisible: open, children, label, nodeId, handleId, className, style }: AddConnectionHandleProps) => {

  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  const { linkNodeIdParam, linkHandleIdParam, setLinkNodeParam, removeLinkNodeParam } = useLinkNodeParams()
  // No visualizador de sub-fluxo o "+" criaria um nó no canvas do EDITOR ligado
  // a um id que só existe dentro do filho. A linha e o rótulo da porta ficam:
  // são informação, e é o único lugar que nomeia a porta livre.
  const somenteLeitura = useSubflowReadOnly()

  function handleOpenDrawerState() {

    if ((!handleId && linkNodeIdParam === nodeId) || (handleId === linkHandleIdParam && linkNodeIdParam === nodeId)) {
      setNodesDrawerState('closed')
      return removeLinkNodeParam()
    }

    setNodesDrawerState('opened')
    setLinkNodeParam(nodeId, handleId)

  }

  return (
    <div className={"flex items-center"}>

      {children}

      {/* Linha + botão + aparecem apenas quando ainda não há conexão.
          `data-role` some com o zoom afastado (LOD): o stub ocupa ~56px por
          porta livre e é a maior fonte de ruído num canvas grande. */}
      {open && <div data-role="add-connection" className={cn("port-top absolute flex items-center -right-1.5", className)} style={{ ...style, transform: 'translateY(-50%)' }}>

        <div className="absolute flex items-center w-14">
          <div className={"absolute z-0 bg-muted-foreground dark:bg-foreground w-14 h-0.5"} />
          {label &&
            <div className="absolute left-1/2 z-20 -translate-x-1/2 bg-card px-1 rounded">
              <p className="text-xs max-w-20 truncate">{label}</p>
            </div>
          }
        </div>

        {!somenteLeitura && <button
          data-active={`${(!handleId && linkNodeIdParam === nodeId) || (handleId === linkHandleIdParam && linkNodeIdParam === nodeId)}`}
          // O acento da plataforma e o `--primary` (laranja); este botao usava
          // `blue-500` cru, e por nao ser token precisava de uma escada `dark:`
          // inteira so para nao ficar ilegivel no tema escuro. Com o token, os
          // dois temas saem da mesma regra.
          className={cn(
            "group absolute -right-19 bg-transparent border-2 border-muted-foreground dark:border-foreground rounded-sm p-1 cursor-pointer transition-colors",
            "hover:border-primary hover:bg-primary/10",
            "data-[active=true]:border-primary data-[active=true]:bg-primary/15",
          )}
          onClick={handleOpenDrawerState}
        >
          <FaPlus className="text-foreground group-data-[active=true]:text-primary" size={12} />
        </button>}

      </div>}


    </div>
  )
}

export default AddConnectionHandle;