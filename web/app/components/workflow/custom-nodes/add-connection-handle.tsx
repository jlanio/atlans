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
  // In the sub-workflow viewer the "+" would create a node on the EDITOR canvas
  // linked to an id that only exists inside the child. The line and the port
  // label stay: they're information, and it's the only place that names the free port.
  const readOnly = useSubflowReadOnly()

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

      {/* Line + "+" button appear only when there's no connection yet.
          `data-role` disappears when zoomed out (LOD): the stub takes ~56px per
          free port and is the largest source of noise on a big canvas. */}
      {open && <div data-role="add-connection" className={cn("port-top absolute flex items-center -right-1.5", className)} style={{ ...style, transform: 'translateY(-50%)' }}>

        <div className="absolute flex items-center w-14">
          <div className={"absolute z-0 bg-muted-foreground dark:bg-foreground w-14 h-0.5"} />
          {label &&
            <div className="absolute left-1/2 z-20 -translate-x-1/2 bg-card px-1 rounded">
              <p className="text-xs max-w-20 truncate">{label}</p>
            </div>
          }
        </div>

        {!readOnly && <button
          data-active={`${(!handleId && linkNodeIdParam === nodeId) || (handleId === linkHandleIdParam && linkNodeIdParam === nodeId)}`}
          // The platform accent is `--primary` (orange); this button used raw
          // `blue-500`, and since it wasn't a token it needed a whole `dark:`
          // ladder just to stay legible in the dark theme. With the token, both
          // themes come out of the same rule.
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