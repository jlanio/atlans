import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useStore } from "@xyflow/react"
import ReturnDrawerButton from "./return-drawer-button"
import CloseDrawerButton from "./close-drawer-button"

interface HeaderDrawerProps {
  title: string
  description?: string
}

const HeaderDrawer = ({ title, description }: HeaderDrawerProps) => {
  const drawerAddNodes = useWorkflowCatalogStore(s => s.nodesDrawerState)
  // A boolean instead of `useNodes()`: only "empty canvas" changes the header,
  // and subscribing to the whole list re-rendered the drawer on every drag frame.
  const canvasVazio = useStore(s => s.nodeLookup.size === 0)

  return (
    <div className="flex items-center gap-3 px-4 py-3.5 select-none min-h-[56px]">

      {(!canvasVazio && drawerAddNodes === "opened" || drawerAddNodes === "closed") &&
        <CloseDrawerButton />
      }

      {(canvasVazio || (drawerAddNodes !== "opened" && drawerAddNodes !== "closed")) &&
        <ReturnDrawerButton />
      }

      <div className="flex flex-col">
        <h4 className="text-base font-semibold text-foreground leading-tight">
          {title}
        </h4>
        {description &&
          <p className="text-muted-foreground text-xs leading-snug mt-0.5">{description}</p>
        }
      </div>
    </div>
  )
}

export default HeaderDrawer
