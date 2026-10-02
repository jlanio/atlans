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
import UserSidebar from "./user-sidebar";
import NotificationBell from "./notification-bell";
import ActiveRunsIndicator from "./active-runs-indicator";
import ExecutorLocalBadge from "./executor-local-badge";
import { useSession } from "next-auth/react";
import { GisFlowService } from "@/service/GisFlowService";
import { readCachedHasAgents, writeCachedHasAgents, clearCachedHasAgents } from "@/lib/sidebar-cache";

// Organização: o ambiente em que os workflows vivem.
const organizationSection = [
  { title: "Workspaces",     url: "/workspaces",    icon: TbBuildingFactory2 },
]

// Automação: criação e execução de workflows.
// "Dashboard" é do administrador do sistema por enquanto: inserido só para admin
// em AppSidebar, o mesmo padrão de "Executores". O middleware barra a rota; aqui
// só escondemos o caminho para quem não a alcança.
const dashboardItem = { title: "Dashboard", url: "/dashboard", icon: TbLayoutDashboard }
const automationBase = [
  { title: "Projetos",       url: "/projects",      icon: TbFolders },
]

// Recursos: infraestrutura que os workflows consomem.
// "Executores" é inserido condicionalmente em AppSidebar (admin sempre; demais
// usuários só quando têm ao menos um executor acessível).
const executoresItem = { title: "Executores", url: "/executores", icon: TbServer }
const resourcesBase = [
  { title: "Credenciais",    url: "/credentials",   icon: TbId },
  { title: "Drive",          url: "/drive",          icon: TbDatabaseImport },
]

// Monitoramento: resultados e observabilidade
const monitoringSection = [
  { title: "Histórico", url: "/observability", icon: TbHistory },
  { title: "Artefatos",       url: "/artifacts",     icon: TbPackage },
]

// Admin: configurações globais da plataforma
const adminSection = [
  { title: "Usuários",       url: "/admin/users",    icon: TbUsers },
  { title: "Configurações",  url: "/admin/settings", icon: TbSettings },
]

function NavGroup({ label, items }: { label: string; items: { title: string; url: string; icon: React.ElementType }[] }) {
  // Detecta rota ativa para destacar o item no menu
  const pathname = usePathname()
  // No telefone a sidebar é uma gaveta sobre a página: sem fechar no clique, o
  // usuário navega e continua olhando para o menu.
  const { isMobile, setOpenMobile } = useSidebar()

  return (
    <SidebarGroup>
      {/* Rótulo de seção como "eyebrow": mono, versalete e discreto. Dá ritmo à
          lista sem competir com os itens. */}
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
                    // Estado ativo refinado: barra indicadora terracota à esquerda
                    // + ícone tingido com a primária da marca. O rótulo mantém o
                    // sidebar-accent-foreground que o estado ativo padrão já aplica.
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

  // Não-admin: descobre se há algum executor acessível para decidir exibir o menu.
  // Admin sempre vê — dispensa o fetch.
  //
  // Começa em `false`: é o MESMO valor que o servidor renderiza (lá não há
  // sessionStorage). Ler o cache no inicializador do useState fazia a primeira
  // render do cliente divergir do HTML entregue — erro de hidratação e
  // re-render da raiz. O cache é aplicado logo após a montagem, o que continua
  // evitando o flicker do F5.
  const [hasAgents, setHasAgents] = useState(false)

  // Aplica o cache e detecta troca de usuário na mesma aba (logout + login de
  // outro user): cache escrito por outro user é descartado, para não mostrar
  // estado alheio até o novo fetch resolver.
  useEffect(() => {
    const cached = readCachedHasAgents()
    if (!cached.userId) return
    if (userId && cached.userId !== userId) {
      clearCachedHasAgents()
      return
    }
    if (cached.value) setHasAgents(true)
  }, [userId])

  // Fetch só dispara quando NextAuth confirma status === "authenticated"
  // (garante que o SessionSync já populou o access_token no axios). O resultado
  // atualiza o cache para a próxima render/F5.
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

  // Mostra o menu também quando o user tem cota pra criar — sem isso, admin
  // pode conceder cota mas o user não enxerga o caminho pra criar.
  const showExecutores = isAdmin || hasAgents || quota > 0
  const resourcesSection = showExecutores ? [executoresItem, ...resourcesBase] : resourcesBase
  const automationSection = isAdmin ? [dashboardItem, ...automationBase] : automationBase

  return (
    <Sidebar collapsible="icon" className="border-border">
      <SidebarHeader>
        {/* `app-region-drag`: no app desktop este cabeçalho arrasta a janela
            (o título é só texto); o gatilho leva `no-drag`. Ver globals.css. */}
        <div className="app-region-drag flex items-center gap-2 group-data-[collapsible=icon]:justify-center">
          {/* Marca + wordmark (bloco compartilhado com o HomeSidebar). Some no
              modo ícone: o gatilho de recolher é o único no desktop (ver
              app-header.tsx) e precisa centralizar sozinho no trilho de 3rem. No
              app padrão a marca é só rótulo — sem link. */}
          <Marca />
          <div className="flex-1 group-data-[collapsible=icon]:hidden" />
          <SidebarTrigger className="app-region-no-drag" size={'sm'} />
        </div>
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
          {/* Só aparece dentro do app desktop (feature-detect); no navegador
              comum não renderiza nada — nem o <li>, pois o próprio componente é
              dono do SidebarMenuItem. */}
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
