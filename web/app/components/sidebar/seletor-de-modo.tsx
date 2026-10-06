"use client"
import Link from "next/link"
import type { MouseEvent } from "react"
import { useSession } from "next-auth/react"
import { TbLayoutDashboard, TbMessages } from "react-icons/tb"
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from "../ui/sidebar"
import { useShellTexts } from "../home/i18n/da-casca"
import { useViewTransitionRouter } from "@/app/hooks/useViewTransition"
import { cn } from "@/lib/utils"

export type Modo = "chat" | "workspace"

/**
 * Where each side of the switch lands. Workspace opens on the Dashboard for the
 * admin and on Projetos for everyone else: the Dashboard is admin-only
 * (`proxy.ts`), so a user sent there would bounce back to the Home.
 */
export function destinoDoModo(modo: Modo, isAdmin: boolean): string {
  if (modo === "chat") return "/"
  return isAdmin ? "/dashboard" : "/projects"
}

/**
 * The attribute on `<html>` that names the switch while it animates
 * (globals.css): it gives `view-transition-name`s to the stage and to the
 * switcher's thumb, and its value is the side being entered, which picks the
 * direction of the slide. It exists only for the length of the transition, so
 * every other navigation keeps the app's plain cross-fade.
 */
export const ATRIBUTO_DA_TROCA = "data-troca-de-modo"

// Longer than the hook's default (200ms): both sides are prefetched by the
// links, but the globe and the dashboard's first render take a few frames more
// than a cached listing. Past this, the hook skips the animation and the switch
// still happens.
const ESPERA_MAXIMA_MS = 600

/**
 * The Chat / Workspace switcher, at the top of BOTH bars: HomeSidebar passes
 * `modo="chat"` and AppSidebar `modo="workspace"`. Chat is the Home (globe and
 * assistant); Workspace is the rest of the app, entered through the Dashboard.
 * Without it neither side had a visible way to the other: the Home only had the
 * brand (to /projects, admin only) and the app's brand is just a label.
 *
 * **Every signed-in person**, admin or not: both sides open for any role
 * (`proxy.ts` keeps only /admin and /dashboard for the admin). A session with
 * no role does not see it, and neither does a session still loading.
 *
 * **Links, not buttons**: it is navigation, so middle-click and Ctrl+click open
 * the other side in a new tab, and `next/link` prefetches it. A plain click
 * goes through `useViewTransitionRouter` instead, with the attribute above set
 * for the length of the transition: the Workspace slides in over the globe and
 * slides back out on the way back (the animations live in globals.css).
 *
 * **On the phone** the bar is a Sheet: the click closes it and navigates
 * without the transition, which would otherwise capture the Sheet half-closed.
 *
 * **On the 3rem rail** the two halves do not fit side by side: they become two
 * icon buttons with tooltips, the current one marked active.
 */
export default function SeletorDeModo({
  modo,
  portalClassName,
}: {
  modo: Modo
  /** The tooltips are portals: the Home passes `home-portal` (see HomeSidebar). */
  portalClassName?: string
}) {
  const t = useShellTexts().casca.barraLateral.modo
  const { data: session } = useSession()
  const { isMobile, setOpenMobile } = useSidebar()
  const router = useViewTransitionRouter()

  const role = session?.user?.role
  if (!role) return null
  const isAdmin = role === "admin"

  function trocar(destino: Modo, evento: MouseEvent<HTMLAnchorElement>) {
    if (destino === modo) {
      evento.preventDefault()
      return
    }
    // New tab, new window, download: the browser's call, not ours.
    if (evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return
    if (isMobile) {
      setOpenMobile(false)
      return
    }
    evento.preventDefault()
    const html = document.documentElement
    html.setAttribute(ATRIBUTO_DA_TROCA, destino)
    const transicao = router.push(destinoDoModo(destino, isAdmin), { maxWaitMs: ESPERA_MAXIMA_MS })
    const limpar = () => html.removeAttribute(ATRIBUTO_DA_TROCA)
    if (transicao?.finished) transicao.finished.then(limpar, limpar)
    else limpar()
  }

  const lados: { modo: Modo; rotulo: string; Icone: typeof TbMessages }[] = [
    { modo: "chat", rotulo: t.chat, Icone: TbMessages },
    { modo: "workspace", rotulo: t.workspace, Icone: TbLayoutDashboard },
  ]

  return (
    <>
      {/* Expanded: a two-position control with a thumb that marks the current side. */}
      <nav
        aria-label={t.rotulo}
        className="relative grid grid-cols-2 rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-[3px] group-data-[collapsible=icon]:hidden"
      >
        <span
          aria-hidden
          className={cn(
            "vt-seletor-indicador pointer-events-none absolute inset-y-[3px] left-[3px] w-[calc(50%-3px)] rounded-md bg-sidebar-accent shadow-sm",
            modo === "workspace" && "translate-x-full",
          )}
        />
        {lados.map(({ modo: lado, rotulo, Icone }) => (
          <Link
            key={lado}
            href={destinoDoModo(lado, isAdmin)}
            onClick={(e) => trocar(lado, e)}
            aria-current={lado === modo ? "page" : undefined}
            className={cn(
              "app-region-no-drag relative z-10 flex h-7 items-center justify-center gap-1.5 rounded-md text-xs font-medium outline-none max-md:h-9",
              "text-sidebar-foreground/65 transition-colors hover:text-sidebar-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring",
              lado === modo && "text-sidebar-foreground",
            )}
          >
            <Icone className="size-4" aria-hidden />
            <span>{rotulo}</span>
          </Link>
        ))}
      </nav>

      {/* The 3rem rail: two icons, stacked. */}
      <SidebarMenu aria-label={t.rotulo} className="hidden group-data-[collapsible=icon]:flex">
        {lados.map(({ modo: lado, rotulo, Icone }) => (
          <SidebarMenuItem key={lado}>
            <SidebarMenuButton
              asChild
              isActive={lado === modo}
              tooltip={{ children: rotulo, className: portalClassName }}
            >
              <Link
                href={destinoDoModo(lado, isAdmin)}
                onClick={(e) => trocar(lado, e)}
                aria-current={lado === modo ? "page" : undefined}
              >
                <Icone aria-hidden />
                <span>{rotulo}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </>
  )
}
