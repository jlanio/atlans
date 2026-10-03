import { ReactNode } from "react"
import { SidebarProvider } from "../ui/sidebar"
import ShellSidebar from "./shell-sidebar"
import { AppHeader } from "../app-header"
import { ExtensionLayers } from "./camadas-das-extensoes"

interface SidebarRootProps {
  children: ReactNode
  // Side shell. By default ShellSidebar picks by route (Home × app); the
  // layout can inject an explicit one. Explicit seam — instead of making
  // AppSidebar polymorphic, the Home has a sibling HomeSidebar.
  sidebar?: ReactNode
  // Initial collapsed/expanded state, read from the `sidebar_state` cookie by
  // the layout on the server. The cookie was WRITTEN (ui/sidebar.tsx) but never
  // read — collapsing the bar didn't survive F5. Passing `defaultOpen` fixes that.
  defaultOpen?: boolean
  // Width chosen on the edge separator, in px, read from the `sidebar_width`
  // cookie by the layout — same template as `defaultOpen`.
  defaultWidth?: number
}

const SidebarRoot = ({ children, sidebar, defaultOpen = true, defaultWidth }: SidebarRootProps) => {

  return (
    <SidebarProvider defaultOpen={defaultOpen} defaultWidth={defaultWidth}>
      {sidebar ?? <ShellSidebar />}
      <main className="flex-1 overflow-auto bg-card flex flex-col">
        {/* AppHeader returns null on the Home and on the canvas (full-bleed). */}
        <AppHeader />
        <div className="flex-1">
          {children}
        </div>
      </main>
      {/* Outside the `Sidebar`, and that's the whole point: on the phone it lives
          in a Radix `Sheet`, UNMOUNTED while closed. An extension modal in there,
          opened from outside the sidebar (from the quota warning, for example),
          would touch a store with nobody subscribed — and nothing would happen.
          Here the layers are mounted once, in both shells, and the portal
          palette comes from whoever opened it. */}
      <ExtensionLayers />
    </SidebarProvider>
  )
}

export default SidebarRoot
