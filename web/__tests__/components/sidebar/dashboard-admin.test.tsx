import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import type { ComponentProps } from "react"

/**
 * "Dashboard" and "Projetos" in the side menu are for everyone: the API filters
 * the Dashboard's numbers (the admin sees the whole fleet, everyone else only
 * their own workspaces). The "Admin" group stays for the admin.
 */

const sessao = vi.hoisted(() => ({ role: "user" as "user" | "admin" }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { user: { role: sessao.role, id_hash: "u1", agent_quota: 0 } },
    status: "authenticated",
  }),
}))

// `useRouter`: the Chat / Workspace switcher at the top of the bar navigates with it.
vi.mock("next/navigation", () => ({ usePathname: () => "/", useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }) }))
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

// shadcn primitives: passthrough. Only the rendered text matters here.
vi.mock("@/app/components/ui/sidebar", () => {
  const P = ({ children }: ComponentProps<"div">) => <div>{children}</div>
  return {
    Sidebar: P, SidebarHeader: P, SidebarContent: P, SidebarFooter: P,
    SidebarGroup: P, SidebarGroupContent: P, SidebarGroupLabel: P,
    SidebarMenu: P, SidebarMenuItem: P, SidebarTrigger: P,
    SidebarMenuButton: ({ children }: ComponentProps<"button">) => <button>{children}</button>,
    useSidebar: () => ({ isMobile: false, setOpenMobile: vi.fn() }),
  }
})

// No accessible executor: the fetch never changes the test result.
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getMyAgentsCount: vi.fn().mockResolvedValue({ data: { count: 0 } }) },
}))
vi.mock("@/lib/sidebar-cache", () => ({
  readCachedHasAgents: () => ({ userId: null, value: false }),
  writeCachedHasAgents: vi.fn(),
  clearCachedHasAgents: vi.fn(),
}))

// Children of the footer and the brand — each has its own dependencies; stub.
vi.mock("@/app/components/sidebar/user-sidebar", () => ({
  default: (p: { portalClassName?: string }) => <div data-testid="user-sidebar" data-portal={p.portalClassName ?? ""} />,
}))
vi.mock("@/app/components/sidebar/notification-bell", () => ({ default: () => null }))
vi.mock("@/app/components/sidebar/active-runs-indicator", () => ({ default: () => null }))
vi.mock("@/app/components/sidebar/executor-local-badge", () => ({ default: () => null }))
vi.mock("@/app/components/sidebar/title-sidebar", () => ({ default: () => null }))

import AppSidebar from "@/app/components/sidebar/app-sidebar"

afterEach(cleanup)

describe("AppSidebar — Dashboard para todos, Admin só para admin", () => {
  it("não-admin vê Dashboard e Projetos, sem o grupo Admin", () => {
    sessao.role = "user"
    render(<AppSidebar />)
    expect(screen.getByText("Dashboard")).toBeTruthy()
    expect(screen.getByText("Projetos")).toBeTruthy()
    expect(screen.queryByText("Usuários")).toBeNull()
    expect(screen.queryByText("Configurações")).toBeNull()
  })

  it("admin vê Dashboard, Projetos e o grupo Admin", () => {
    sessao.role = "admin"
    render(<AppSidebar />)
    expect(screen.getByText("Dashboard")).toBeTruthy()
    expect(screen.getByText("Projetos")).toBeTruthy()
    expect(screen.getByText("Usuários")).toBeTruthy()
  })

  it("o menu de conta segue no tema do app — a paleta da Home é só da Home", () => {
    render(<AppSidebar />)
    expect(screen.getByTestId("user-sidebar").getAttribute("data-portal")).toBe("")
  })
})
