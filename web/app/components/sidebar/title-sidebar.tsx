"use client"
import { cn } from "@/lib/utils"
import { useSidebar } from "../ui/sidebar"

interface TitleSidebarProps {
  title: string
  className?: string
}


const TitleSidebar = ({ title, className }: TitleSidebarProps) => {

  const { open, isMobile } = useSidebar()
  // `open` is the DESKTOP state. In the phone drawer what rules is
  // `openMobile`, and the Sheet only exists while open — so there the wordmark
  // always shows. Without this guard, the `sidebar_state=false` cookie (bar
  // collapsed on desktop) left the wordmark at `opacity-0` inside the drawer.
  const visivel = isMobile || open

  return (
    <h1 className={cn(
      // Transition only under motion-safe: whoever asks for less motion sees an abrupt swap.
      "motion-safe:transition text-base font-semibold tracking-[-0.01em]",
      visivel ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
      className,
    )}>
      {title}
    </h1>
  )
}
export default TitleSidebar