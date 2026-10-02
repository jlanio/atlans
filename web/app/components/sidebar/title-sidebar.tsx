"use client"
import { cn } from "@/lib/utils"
import { useSidebar } from "../ui/sidebar"

interface TitleSidebarProps {
  title: string
  className?: string
}


const TitleSidebar = ({ title, className }: TitleSidebarProps) => {

  const { open, isMobile } = useSidebar()
  // `open` é o estado do DESKTOP. Na gaveta do telefone quem manda é
  // `openMobile`, e o Sheet só existe aberto — então lá o wordmark aparece
  // sempre. Sem esta guarda, o cookie `sidebar_state=false` (barra recolhida no
  // desktop) deixava o wordmark em `opacity-0` dentro da gaveta.
  const visivel = isMobile || open

  return (
    <h1 className={cn(
      // Transição só sob motion-safe: quem pede menos movimento vê a troca seca.
      "motion-safe:transition text-base font-semibold tracking-[-0.01em]",
      visivel ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
      className,
    )}>
      {title}
    </h1>
  )
}
export default TitleSidebar