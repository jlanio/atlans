import { ReactNode } from "react"
import { SidebarProvider } from "../ui/sidebar"
import ShellSidebar from "./shell-sidebar"
import { AppHeader } from "../app-header"
import { CamadasDasExtensoes } from "./camadas-das-extensoes"

interface SidebarRootProps {
  children: ReactNode
  // Casca lateral. Por padrão o ShellSidebar escolhe pela rota (Home × app);
  // o layout pode injetar uma explícita. Seam explícito — em vez de tornar o
  // AppSidebar polimórfico, a Home tem um HomeSidebar irmão.
  sidebar?: ReactNode
  // Estado inicial recolhido/expandido, lido do cookie `sidebar_state` pelo
  // layout no servidor. O cookie era GRAVADO (ui/sidebar.tsx) mas nunca lido —
  // recolher a barra não sobrevivia ao F5. Passar `defaultOpen` conserta isso.
  defaultOpen?: boolean
  // Largura escolhida no separador da borda, em px, lida do cookie
  // `sidebar_width` pelo layout — mesmo molde do `defaultOpen`.
  defaultWidth?: number
}

const SidebarRoot = ({ children, sidebar, defaultOpen = true, defaultWidth }: SidebarRootProps) => {

  return (
    <SidebarProvider defaultOpen={defaultOpen} defaultWidth={defaultWidth}>
      {sidebar ?? <ShellSidebar />}
      <main className="flex-1 overflow-auto bg-card flex flex-col">
        {/* AppHeader devolve null na Home e no canvas (full-bleed). */}
        <AppHeader />
        <div className="flex-1">
          {children}
        </div>
      </main>
      {/* Fora do `Sidebar`, e é o ponto todo: no telefone ele vive num `Sheet`
          do Radix, DESMONTADO enquanto fechado. Um modal de extensão lá dentro,
          aberto de fora do sidebar (do aviso de cota, por exemplo), mexeria
          numa store sem ninguém inscrito — e não aconteceria nada. Aqui as
          camadas são montadas uma vez, nas duas cascas, e a paleta do portal
          vem de quem abriu. */}
      <CamadasDasExtensoes />
    </SidebarProvider>
  )
}

export default SidebarRoot
