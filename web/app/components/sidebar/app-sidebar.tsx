"use client"
import { useEffect, useState } from "react";
import {
  SidebarHeader,
  SidebarContent,
  SidebarGroup,
  SidebarFooter,
  Sidebar,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "../ui/sidebar"
import { TbHistory, TbFolders, TbId, TbSettings, TbPackage, TbDatabaseImport, TbServer, TbLayoutDashboard, TbUsers, TbBuildingFactory2 } from "react-icons/tb";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import Marca from "./marca";
import SeletorDeModo from "./seletor-de-modo";
import UserSidebar from "./user-sidebar";
import NotificationBell from "./notification-bell";
import ActiveRunsIndicator from "./active-runs-indicator";
import ExecutorLocalBadge from "./executor-local-badge";
import { useSession } from "next-auth/react";
import { GisFlowService } from "@/service/GisFlowService";
import { readCachedHasAgents, writeCachedHasAgents, clearCachedHasAgents } from "@/lib/sidebar-cache";

// Organization: the environment in which workflows live.
const organizationSection = [
  { title: "Workspaces",     url: "/workspaces",    icon: TbBuildingFactory2 },
]

// Automation: creating and executing workflows.
// "Dashboard" is for everyone: the API filters its numbers (the admin sees the
// whole fleet, everyone else only their own workspaces).
const automationSection = [
  { title: "Dashboard",      url: "/dashboard",     icon: TbLayoutDashboard },
  { title: "Projetos",       url: "/projects",      icon: TbFolders },
]

// Resources: infrastructure that workflows consume.
// "Executores" is inserted conditionally in AppSidebar (admin always; other
// users only when they have at least one accessible executor).
const executorsItem = { title: "Executores", url: "/executores", icon: TbServer }
const resourcesBase = [
  { title: "Credenciais",    url: "/credentials",   icon: TbId },
  { title: "Drive",          url: "/drive",          icon: TbDatabaseImport },
]

// Monitoramento: resultados e observabilidade
const monitoringSection = [
  { title: "Histórico", url: "/observability", icon: TbHistory },
  { title: "Artefatos",       url: "/artifacts",     icon: TbPackage },
]

// Admin: global platform settings
const adminSection = [
  { title: "Usuários",       url: "/admin/users",    icon: TbUsers },
  { title: "Configurações",  url: "/admin/settings", icon: TbSettings },
]

function NavGroup({ label, items }: { label: string; items: { title: string; url: string; icon: React.ElementType }[] }) {
  // Detects the active route to highlight the item in the menu
  const pathname = usePathname()
  // On the phone the sidebar is a drawer over the page: without closing on click,
  // the user navigates and keeps looking at the menu.
  const { isMobile, setOpenMobile } = useSidebar()

  return (
    <SidebarGroup>
      {/* Section label as an "eyebrow": mono, small caps and discreet. Gives the
          list rhythm without competing with the items. */}
      <SidebarGroupLabel className="font-mono text-[10px] uppercase tracking-[0.12em] text-sidebar-foreground/55">{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const isActive = pathname === item.url || pathname.startsWith(item.url + "/")
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  asChild
                  isActive={isActive}
                  tooltip={item.title}
                  className={cn(
                    "relative h-10",
                    // Refined active state: terracotta indicator bar on the left
                    // + icon tinted with the brand primary. The label keeps the
                    // sidebar-accent-foreground the default active state already applies.
                    isActive &&
                      "before:absolute before:left-0 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-sidebar-primary before:content-[''] [&>svg]:text-sidebar-primary",
                  )}
                >
                  <Link href={item.url} onClick={() => { if (isMobile) setOpenMobile(false) }}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

const AppSidebar = () => {
  const { data: session, status } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const userId = session?.user?.id_hash
  const quota = session?.user?.agent_quota ?? 0

  // Non-admin: finds out whether there is any accessible executor to decide
  // whether to show the menu. Admin always sees it — skips the fetch.
  //
  // Starts at `false`: it's the SAME value the server renders (there is no
  // sessionStorage there). Reading the cache in the useState initializer made the
  // client's first render diverge from the delivered HTML — hydration error and a
  // re-render of the root. The cache is applied right after mount, which still
  // avoids the F5 flicker.
  const [hasAgents, setHasAgents] = useState(false)

  // Applies the cache and detects a user switch in the same tab (logout + login
  // of another user): cache written by another user is discarded, so as not to
  // show someone else's state until the new fetch resolves.
  useEffect(() => {
    const cached = readCachedHasAgents()
    if (!cached.userId) return
    if (userId && cached.userId !== userId) {
      clearCachedHasAgents()
      return
    }
    if (cached.value) setHasAgents(true)
  }, [userId])

  // The fetch only fires when NextAuth confirms status === "authenticated"
  // (ensures SessionSync has already put the access_token on axios). The result
  // updates the cache for the next render/F5.
  useEffect(() => {
    if (status !== "authenticated" || isAdmin || !userId) return
    let active = true
    GisFlowService.getMyAgentsCount().then(res => {
      if (!active || !res.data) return
      const value = res.data.count > 0
      setHasAgents(value)
      writeCachedHasAgents(userId, value)
    })
    return () => { active = false }
  }, [status, isAdmin, userId])

  // Also shows the menu when the user has quota to create — without this, admin
  // can grant quota but the user doesn't see the path to create.
  const showExecutors = isAdmin || hasAgents || quota > 0
  const resourcesSection = showExecutors ? [executorsItem, ...resourcesBase] : resourcesBase

  return (
    <Sidebar collapsible="icon" className="border-border">
      <SidebarHeader>
        {/* `app-region-drag`: in the desktop app this header drags the window
            (the title is just text); the trigger gets `no-drag`. See globals.css. */}
        <div className="app-region-drag flex items-center gap-2 group-data-[collapsible=icon]:justify-center">
          {/* Brand + wordmark (block shared with HomeSidebar). Disappears in
              icon mode: the collapse trigger is the only one on desktop (see
              app-header.tsx) and needs to center by itself on the 3rem rail. In
              the standard app the brand is just a label — no link. */}
          <Marca />
          <div className="flex-1 group-data-[collapsible=icon]:hidden" />
          <SidebarTrigger className="app-region-no-drag" size={'sm'} />
        </div>
        {/* Chat / Workspace: the way back to the Home. */}
        <SeletorDeModo modo="workspace" />
      </SidebarHeader>
      <SidebarContent>
        <NavGroup label="Organização"  items={organizationSection} />
        <NavGroup label="Automação"     items={automationSection} />
        <NavGroup label="Recursos"      items={resourcesSection} />
        <NavGroup label="Monitoramento" items={monitoringSection} />
        {isAdmin && <NavGroup label="Admin" items={adminSection} />}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          {/* Only appears inside the desktop app (feature-detect); in a regular
              browser it renders nothing — not even the <li>, since the component
              itself owns the SidebarMenuItem. */}
          <ExecutorLocalBadge />
          <SidebarMenuItem>
            <ActiveRunsIndicator />
          </SidebarMenuItem>
          <SidebarMenuItem>
            <NotificationBell />
          </SidebarMenuItem>
          <SidebarMenuItem>
            <UserSidebar />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
