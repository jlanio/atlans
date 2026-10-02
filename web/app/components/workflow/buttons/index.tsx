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
  // Sobe junto com o dock do painel de execução — sem isso os botões ficam
  // atrás da barra. O botão de console saiu daqui: o painel agora tem barra
  // própria, sempre visível, que já serve de gatilho.
  const dockHeight = useRunDockHeight()

  return (
    // Esta barra era a única sem camada declarada: um nó por cima cobria os
    // botões, o clique ia para o nó e o cursor virava o do canvas. O `z-10` que
    // havia em cada botão era inerte — `z-index` não faz nada em elemento
    // `position: static`; a camada tem de ser do CONTÊINER. Ver canvas-layers.
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
