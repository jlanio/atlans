"use client"
import { usePathname } from "next/navigation"
import AppSidebar from "./app-sidebar"
import HomeSidebar from "./home-sidebar"

/**
 * Picks the side shell by route, on the client. The (dashboard) layout is
 * SHARED between the Home (`/`) and the rest of the app; instead of two layouts —
 * which would give two SidebarProviders and lose the collapsed state when
 * navigating between the Home and an app page — a single seam swaps the bar: the
 * Home gets HomeSidebar (Meus → Agendamentos, Artefatos, Chats); every other
 * route keeps the usual AppSidebar.
 *
 * `usePathname() === "/"` is an EXACT match — a `startsWith("/")` would match
 * every app route.
 */
export default function ShellSidebar() {
  const pathname = usePathname()
  return pathname === "/" ? <HomeSidebar /> : <AppSidebar />
}
