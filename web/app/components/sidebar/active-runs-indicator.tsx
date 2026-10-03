"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { TbActivity } from "react-icons/tb"
import { useActiveRuns } from "@/context/ActiveRunsContext"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { SidebarMenuButton } from "../ui/sidebar"

const ActiveRunsIndicator = () => {
  const { runningRuns, runningCount } = useActiveRuns()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const active = runningCount > 0

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton tooltip="Execuções em andamento" className="relative">
          <div className="relative">
            <TbActivity className={cn("size-4", active && "text-primary")} />
            {active && (
              <span className="absolute -top-1.5 -right-1.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-primary text-[8px] font-bold text-primary-foreground ring-2 ring-sidebar">
                {runningCount > 9 ? "9+" : runningCount}
              </span>
            )}
          </div>
          <span>Execuções</span>
        </SidebarMenuButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="right"
        align="end"
        sideOffset={8}
        className="z-50 w-64 rounded-lg border border-border bg-popover shadow-lg overflow-hidden p-0"
      >
        <div className="px-3 py-2 border-b border-border">
          <p className="text-xs font-semibold">Em andamento</p>
        </div>
        {runningRuns.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
            <TbActivity size={22} />
            <p className="text-xs">Nenhuma execução em andamento</p>
          </div>
        ) : (
          <div className="max-h-72 overflow-y-auto">
            {runningRuns.map((r) => (
              <button
                key={r.runId}
                onClick={() => { setOpen(false); router.push(`/workflow/${r.workflowHash}`) }}
                className="flex w-full items-center gap-2.5 px-3 py-2.5 border-b border-border last:border-0 hover:bg-accent/50 text-left"
              >
                {/* `exec-running`, not `blue-500`: the token exists so that the
                    execution state follows the theme and matches the color used
                    on cards and edges (globals.css). */}
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-exec-running opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-exec-running" />
                </span>
                <span className="flex-1 min-w-0 truncate text-xs font-medium">{r.name}</span>
              </button>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default ActiveRunsIndicator
