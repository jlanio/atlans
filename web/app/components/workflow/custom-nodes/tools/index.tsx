import { INodeContext } from "@/context/useFlowContext";
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore";
import { useConfigNodeParams } from "@/app/hooks/workflow/useConfigNodeParams";
import { cn } from "@/lib/utils";
import { useReactFlow, Edge } from "@xyflow/react";
import { FaTrash } from "react-icons/fa";
import { IoCopySharp } from "react-icons/io5";
import { MdEdit } from "react-icons/md";
import { TbPinFilled, TbPinnedOff, TbSubtask } from "react-icons/tb";
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore";
import { useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore";
import { useSubflowReadOnly } from "../../subflow-viewer/scope";
import { useCanvasReadOnly } from "../../canvas-interaction";
import { v4 as uuid } from "uuid"
import { useParams } from "next/navigation";
import { useState } from "react";
import { GisFlowService } from "@/service/GisFlowService";
import { createToast } from "@/utils/createToast";
import PinDialog from "./pin-dialog";

interface ToolsIconProps {
  nodeId: string
  open: boolean
}

const ToolsIcon = ({ open, nodeId }: ToolsIconProps) => {

  const { setEdges, setNodes, addNodes, getNode } = useReactFlow<INodeContext, Edge>()
  const { setConfigNodeParam } = useConfigNodeParams()
  const pinnedNodes = useWorkflowCatalogStore(s => s.pinnedNodes)
  const setPinnedNodes = useWorkflowCatalogStore(s => s.setPinnedNodes)
  const { id: workflowId } = useParams<{ id?: string }>()
  const [pinDialogOpen, setPinDialogOpen] = useState(false)

  const isPinned = pinnedNodes.some(p => p.node_id === nodeId && !p.expired)

  // Only offer drilling down when the loaded run actually executed something in there:
  // without an execution there is nothing to paint, and the viewer would show a
  // gray graph that passes for "nothing ran" when the truth is "no run is open".
  const ranSubflow = useWorkflowExecutionStore(s => s.subflowRoots.has(nodeId))
  const openSubflow = useSubflowDrilldownStore(s => s.open)
  const inViewer = useSubflowReadOnly()
  const readOnly = useCanvasReadOnly()

  function handleOpenSubflow() {
    const node = getNode(nodeId)
    const props = (node?.data?.properties ?? {}) as Record<string, unknown>
    const hash = String(props.workflowHash ?? "").trim()
    if (!hash) return
    openSubflow([{
      canvasNodeId: nodeId,
      workflowHash: hash,
      label: (props.alias as string) || (node?.data?.alias as string) || "Sub-fluxo",
    }])
  }

  function handleDeleteNode() {
    setNodes(nds => nds.filter((node) => node.id !== nodeId))
    setEdges(edgs => edgs.filter((edg) => edg.target !== nodeId && edg.source !== nodeId))
  }

  function copyNode() {
    const node = getNode(nodeId)
    if (!node) return

    const newNode = {
      ...node,
      id: uuid(),
      position: {
        x: node.position.x + 35,
        y: node.position.y - 35
      },
    } satisfies INodeContext

    addNodes(newNode)
    setNodes(nds => nds.map(nd =>
      nd.id === nodeId ? { ...nd, selected: false } : nd
    ))
  }

  async function handleUnpin() {
    if (!workflowId) return
    try {
      const res = await GisFlowService.unpinNodeOutput(workflowId, nodeId)
      if (res?.error) {
        createToast.error("Erro ao remover pin", res.error.message)
        return
      }
      setPinnedNodes(pinnedNodes.filter(p => p.node_id !== nodeId))
      createToast.success("Pin removido")
    } catch (err) {
      createToast.error("Erro ao remover pin", String(err))
    }
  }

  function handlePinClick() {
    if (isPinned) {
      handleUnpin()
    } else {
      setPinDialogOpen(true)
    }
  }

  // The sub-workflow viewer draws the CHILD's graph: editing, duplicating,
  // deleting or pinning here would act on the wrong canvas — the ids don't even
  // exist in the workflow open in the editor. In there, going down a level is
  // the double-click.
  // The whole bar is revealed by `open`, which comes from hover — an event that
  // touch doesn't produce. On a phone it would be dead code anyway: it showed up
  // for an instant after a tap, with edit/copy/delete that the canvas there
  // doesn't even allow. The configuration is still reachable by tapping the node.
  if (inViewer || readOnly) return null

  return (
    <>
      <div
        className={cn(
          "absolute flex items-center gap-2 rounded-md -top-9 px-3 py-1.5 bg-card border shadow-sm cursor-auto transition-opacity duration-100 z-50",
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      >
        <MdEdit
          onClick={() => setConfigNodeParam(nodeId)}
          size={16} className="cursor-pointer hover:text-primary" />

        {ranSubflow && (
          <button
            onClick={handleOpenSubflow}
            title="Ver o que rodou dentro do sub-fluxo"
            className="flex items-center"
          >
            <TbSubtask size={16} className="cursor-pointer text-indigo-500 hover:text-indigo-600" />
          </button>
        )}

        <button
          onClick={handlePinClick}
          title={isPinned ? "Remover pin" : "Fixar output"}
          className="flex items-center"
        >
          {isPinned
            ? <TbPinnedOff size={16} className="cursor-pointer text-amber-500 hover:text-amber-600" />
            : <TbPinFilled size={16} className="cursor-pointer hover:text-amber-500" />
          }
        </button>

        <IoCopySharp
          onClick={copyNode}
          size={15} className="cursor-pointer hover:text-muted-foreground" />

        <FaTrash
          onClick={handleDeleteNode}
          size={13} className="cursor-pointer hover:text-destructive" />
      </div>

      {pinDialogOpen && (
        <PinDialog
          nodeId={nodeId}
          workflowId={workflowId ?? ""}
          onClose={() => setPinDialogOpen(false)}
        />
      )}
    </>
  )

}

export default ToolsIcon;
