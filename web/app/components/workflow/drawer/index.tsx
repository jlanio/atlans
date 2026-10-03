import OptionsDrawer from "./options-drawer"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useStore } from "@xyflow/react"
import NodesDrawer from "./nodes-drawer"
import { Separator } from "@/app/components/ui/separator"
import DrawerRoot from "./components/drawer-root"
import HeaderDrawer from "./components/header-drawer"
import { Input } from "@/app/components/ui/input"
import { TbSearch, TbX } from "react-icons/tb"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { nomeDoTipo } from "@/consts/NodeTypeStyles"

const WorkflowDrawer = () => {
  const drawerAddNodes = useWorkflowCatalogStore(s => s.nodesDrawerState)
  const [filter, setFilter] = useState("")
  // All that matters is whether the canvas is empty. Subscribing to `useNodes()`
  // re-rendered the whole drawer on every pointermove of a drag — and it is
  // always mounted, just translated off screen, so the cost was invisible.
  const canvasVazio = useStore(s => s.nodeLookup.size === 0)
  const isOpen = drawerAddNodes !== "closed"

  return (
    <div className={cn(
      "fixed right-0 top-0 h-screen z-40 border-l border-border/60 transition-transform duration-300 ease-in-out shadow-lg",
      isOpen ? "translate-x-0" : "translate-x-full"
    )}>
      <DrawerRoot>

        {drawerAddNodes === "opened" || drawerAddNodes === "closed" ? (
          canvasVazio ? (
            <HeaderDrawer
              title="Qual será o trigger?"
              description="O trigger é o ponto de início do workflow" />
          ) : (
            <HeaderDrawer title="Adicionar nó" />
          )
        ) : (
          <HeaderDrawer title={nomeDoTipo(drawerAddNodes)} />
        )}

        <Separator />

        {/* Search bar */}
        <div className="px-3 py-2.5 flex items-center gap-2">
          <div className="relative flex-1">
            <TbSearch className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <Input
              id="search"
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Pesquise um nó..."
              className="pl-8 pr-8 h-8 text-sm bg-muted/40 border-border/60 focus-visible:ring-1"
            />
            {filter && (
              <button
                onClick={() => setFilter("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <TbX className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">

          {(!canvasVazio && drawerAddNodes === "opened" && filter === "") &&
            <OptionsDrawer />
          }

          {(canvasVazio || (drawerAddNodes !== "opened" && drawerAddNodes !== "closed") || filter !== "") &&
            <NodesDrawer aliasFilter={filter} />
          }

        </div>
      </DrawerRoot>
    </div>
  )
}

export default WorkflowDrawer
