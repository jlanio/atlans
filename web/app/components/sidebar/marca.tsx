"use client"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip"
import { useSidebar } from "../ui/sidebar"
import { useNomeNaTela } from "../share/nome-na-tela"
import TitleSidebar from "./title-sidebar"

/**
 * The brand: workflow glyph (two connected nodes, echoing the workflow canvas) +
 * the wordmark — this installation's name (NOME_NA_TELA; "Atlans" without it, see
 * lib/nome-na-tela.ts). Extracted from AppSidebar so HomeSidebar reuses the
 * SAME block — the Home's shell is "like Claude Code", with the brand at the top.
 *
 * In icon mode the block disappears (`group-data-[collapsible=icon]:hidden`): on
 * the app's 3rem rail only the collapse trigger remains, which centers by itself.
 * With `glifoNoTrilho` the GLYPH stays and only the wordmark goes — as `sr-only`,
 * not `hidden`, because the glyph is `aria-hidden` and the `<h1>` is the link's
 * name. The Home uses this: there the brand is the admin's only explicit
 * navigation, and collapsed it vanished entirely, exit included. The `tooltip`
 * (only with `href`) states the destination on the rail, the same way
 * `SidebarMenuButton` does for the items.
 *
 * `href` — when present, the whole brand becomes a link. That's how the Home uses
 * it: there the brand is the ONLY explicit navigation to the rest of the app (it
 * goes to /projects; the account menu has no shortcuts, and the rest is reached
 * via the Ctrl+K palette). In the standard app the brand is just a label and goes
 * WITHOUT href.
 */
/**
 * Just the glyph (the terracotta square with the two connected nodes), without
 * the wordmark. Exported because the Home's sign-in modal puts it in the card
 * header — outside the sidebar, without `useSidebar`.
 */
export function GlifoDaMarca() {
  return (
    <span
      aria-hidden
      className="flex size-7 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
    >
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2.1} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="7.3" cy="7.8" r="2.4" />
        <circle cx="16.7" cy="16.2" r="2.4" />
        <path d="M9.3 9.4 14.7 14.6" />
      </svg>
    </span>
  )
}

export default function Marca({
  href,
  glifoNoTrilho = false,
  tooltip,
}: {
  href?: string
  glifoNoTrilho?: boolean
  tooltip?: React.ComponentProps<typeof TooltipContent>
}) {
  const { state, isMobile } = useSidebar()
  const nome = useNomeNaTela()

  const glifo = <GlifoDaMarca />
  const wordmark = (
    <TitleSidebar
      title={nome}
      className={glifoNoTrilho ? "group-data-[collapsible=icon]:sr-only" : undefined}
    />
  )

  const classe = cn("flex items-center gap-2", !glifoNoTrilho && "group-data-[collapsible=icon]:hidden")

  if (!href) {
    return (
      <span className={classe}>
        {glifo}
        {wordmark}
      </span>
    )
  }

  const link = (
    <Link
      href={href}
      // Discreet clickable target: a light highlight on hover says it's a link,
      // without a permanent box competing with the list.
      className={cn(classe, "rounded-md transition-opacity hover:opacity-80")}
    >
      {glifo}
      {wordmark}
    </Link>
  )
  if (!tooltip) return link

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      {/* Only on the rail: expanded, the wordmark already says it all; the phone has no rail. */}
      <TooltipContent side="right" align="center" hidden={state !== "collapsed" || isMobile} {...tooltip} />
    </Tooltip>
  )
}
