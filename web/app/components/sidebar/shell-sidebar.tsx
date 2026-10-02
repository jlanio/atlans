"use client"
import { usePathname } from "next/navigation"
import AppSidebar from "./app-sidebar"
import HomeSidebar from "./home-sidebar"

/**
 * Escolhe a casca lateral pela rota, no cliente. O layout (dashboard) é
 * COMPARTILHADO entre a Home (`/`) e o resto do app; em vez de dois layouts —
 * que dariam dois SidebarProvider e perderiam o estado recolhido ao navegar
 * entre a Home e uma página do app — um seam só troca a barra: a Home ganha o
 * HomeSidebar (Meus → Agendamentos, Artefatos, Chats); toda outra rota mantém o
 * AppSidebar de sempre.
 *
 * `usePathname() === "/"` é casamento EXATO — um `startsWith("/")` casaria todas
 * as rotas do app.
 */
export default function ShellSidebar() {
  const pathname = usePathname()
  return pathname === "/" ? <HomeSidebar /> : <AppSidebar />
}
