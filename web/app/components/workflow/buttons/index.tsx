import { useParams } from "next/navigation"
import ExecuteWorkflow from "./execute-workflow"
import SaveWorkflow from "./save-workflow"
import VersionHistory from "./version-history"
import RecentRuns from "./recent-runs"
import PortalShare from "./portal-share"
import { IWorkflow } from "@/service/types"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useRunDockHeight } from "@/app/stores/runPanelStore"
import { CAMADA_SOBRE_O_CANVAS } from "../canvas-layers"

interface ActionsButtonProps {
  workflow?: IWorkflow
}

const ActionsButton = ({ workflow }: ActionsButtonProps) => {

  const { id } = useParams<{ id: string }>()
  const { canEdit, canExecute } = useWorkspace()
  // Rises together with the run panel dock — without this the buttons sit
  // behind the bar. The console button left here: the panel now has its own
  // bar, always visible, which already serves as the trigger.
  const dockHeight = useRunDockHeight()

  return (
    // This bar was the only one with no declared layer: a node on top covered the
    // buttons, the click went to the node and the cursor became the canvas's. The
    // `z-10` that each button had was inert — `z-index` does nothing on a
    // `position: static` element; the layer has to belong to the CONTAINER. See
    // canvas-layers.
    <div
      data-canvas-chrome=""
      className={`${CAMADA_SOBRE_O_CANVAS} left-2 sm:left-4 pl-safe flex flex-col gap-2 transition-[bottom] duration-150`}
      style={{ bottom: dockHeight + 16 }}
    >
      {id ?
        <>
          {canEdit && <PortalShare workflow={workflow} />}
          {canEdit && <VersionHistory />}
          <RecentRuns />
          {canEdit && <SaveWorkflow />}
          {canExecute && <ExecuteWorkflow />}
        </>
        :
        <SaveWorkflow />
      }
    </div>
  )
}

export default ActionsButton
